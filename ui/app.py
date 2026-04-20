import os
import json
import asyncio
import uuid
import httpx
import anthropic
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

# --- Service URLs ---
LOG_CHECKER_URL     = os.environ.get("LOG_CHECKER_URL",     "http://log-checker:8001")
METRICS_CHECKER_URL = os.environ.get("METRICS_CHECKER_URL", "http://metrics-checker:8002")
DEPLOY_CHECKER_URL  = os.environ.get("DEPLOY_CHECKER_URL",  "http://deploy-checker:8003")
MOCK_INFRA_URL      = os.environ.get("MOCK_INFRA_URL",      "http://mock-infra:8004")
RAG_SERVICE_URL     = os.environ.get("RAG_SERVICE_URL",     "http://rag-service:8005")

app = FastAPI(title="SRE Agent UI")
templates = Jinja2Templates(directory="templates")

sessions: dict[str, dict] = {}

# --- Tool Definitions ---
TOOLS = [
    {
        "name": "get_logs",
        "description": "Fetch recent error/warn logs for a service",
        "input_schema": {
            "type": "object",
            "properties": {
                "service":  {"type": "string"},
                "minutes":  {"type": "integer", "default": 30}
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_metrics",
        "description": "Fetch current performance metrics for a service",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"}
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_deployments",
        "description": "Fetch recent deployment and config change history for a service",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "hours":   {"type": "integer", "default": 24}
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_pod_status",
        "description": "Fetch current pod status for a service",
        "input_schema": {
            "type": "object",
            "properties": {
                "service":   {"type": "string"},
                "namespace": {"type": "string", "default": "default"}
            },
            "required": ["service"]
        }
    },
    {
        "name": "search_past_incidents",
        "description": (
            "Search the incident library for similar past incidents. "
            "Use this when you have gathered enough evidence to form a hypothesis "
            "and want to check if similar incidents have occurred before. "
            "Provide a natural language description of what you are seeing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of the current symptoms and suspected root cause"
                },
                "n_results": {
                    "type": "integer",
                    "default": 3,
                    "description": "Number of past incidents to retrieve"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "restart_pod",
        "description": "REMEDIATION: Restart a specific pod. Requires human approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod_name":  {"type": "string"},
                "namespace": {"type": "string", "default": "default"}
            },
            "required": ["pod_name"]
        }
    },
    {
        "name": "rollback",
        "description": "REMEDIATION: Roll back a service to a previous deployment. Requires human approval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service":         {"type": "string"},
                "target_revision": {"type": "string", "default": "previous"}
            },
            "required": ["service"]
        }
    },
]

REMEDIATION_TOOLS = {"restart_pod", "rollback"}

# --- Tool Executor ---
def execute_tool(name: str, inputs: dict) -> dict:
    with httpx.Client(timeout=10.0) as http:
        if name == "get_logs":
            return http.post(f"{LOG_CHECKER_URL}/logs", json=inputs).json()
        elif name == "get_metrics":
            return http.post(f"{METRICS_CHECKER_URL}/metrics", json=inputs).json()
        elif name == "get_deployments":
            return http.post(f"{DEPLOY_CHECKER_URL}/deployments", json=inputs).json()
        elif name == "get_pod_status":
            return http.post(f"{MOCK_INFRA_URL}/pod-status", json=inputs).json()
        elif name == "search_past_incidents":
            return http.post(f"{RAG_SERVICE_URL}/search", json=inputs).json()
        elif name == "restart_pod":
            return http.post(f"{MOCK_INFRA_URL}/restart-pod", json=inputs).json()
        elif name == "rollback":
            return http.post(f"{MOCK_INFRA_URL}/rollback", json=inputs).json()
    return {"error": f"Unknown tool: {name}"}

# --- SSE helper ---
def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

# --- Report Writer ---
async def write_incident_report(
    session_id: str,
    alert: str,
    service: str,
    investigation_transcript: list,
    queue: asyncio.Queue
):
    """Second agent pass — writes a structured incident report from the investigation transcript."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    await queue.put(sse("report_start", {"message": "Writing incident report..."}))

    transcript_text = json.dumps(investigation_transcript, indent=2)

    report_prompt = f"""You are an SRE technical writer. Based on the following investigation transcript, write a structured incident report.

Alert: {alert}
Service: {service}

Investigation transcript:
{transcript_text}

Write a structured incident report with these exact sections:
## Incident Summary
## Timeline
## Root Cause
## Evidence
## Remediation Taken
## Follow-up Actions

Be concise, specific, and use technical language appropriate for an SRE audience."""

    response = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            messages=[{"role": "user", "content": report_prompt}]
        )
    )

    report_text = response.content[0].text

    # Stream the report to the UI
    await queue.put(sse("report_text", {"text": report_text}))

    # Store the report as a new incident in the RAG library
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    new_incident = {
        "id": incident_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "duration_minutes": 0,
        "service": service,
        "alert_text": alert,
        "symptoms": {"key_log_messages": []},
        "root_cause": "",
        "root_cause_category": "unknown",
        "evidence": [],
        "remediation": "",
        "remediation_successful": True,
        "narrative": report_text,
        "follow_up_actions": [],
        "tags": [service]
    }

    try:
        with httpx.Client(timeout=10.0) as http:
            http.post(f"{RAG_SERVICE_URL}/store", json={"incident": new_incident})
        await queue.put(sse("report_stored", {
            "message": f"Report saved to incident library as {incident_id}"
        }))
    except Exception as e:
        await queue.put(sse("report_stored", {
            "message": f"Note: Could not save report to library — {str(e)}"
        }))

    await queue.put(sse("done", {"message": "Investigation complete."}))
    sessions[session_id]["complete"] = True


# --- Agent Loop ---
async def run_agent(session_id: str, alert: str, queue: asyncio.Queue):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    approval_queue: asyncio.Queue = sessions[session_id]["approval_queue"]

    # Extract service name from alert for report writing
    service = alert.split()[0] if alert else "unknown"

    messages = [{"role": "user", "content": alert}]
    system = (
        "You are an SRE agent. Investigate the alert by gathering data with the "
        "read-only tools first. Form a diagnosis, then immediately call the appropriate "
        "remediation tool — do not ask for confirmation in text first. The approval gate "
        "will handle human confirmation before any action executes. Always call the tool; "
        "never ask 'would you like me to proceed?' in text. "
        "When you have gathered enough evidence to form a hypothesis about the root cause, "
        "use the search_past_incidents tool to check if similar incidents have occurred before. "
        "Use the past incident context to inform your diagnosis and remediation recommendation."
    )

    await queue.put(sse("alert", {"message": alert}))

    # Track investigation transcript for report writing
    investigation_transcript = []

    while True:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=messages,
            )
        )

        for block in response.content:
            if hasattr(block, "text") and block.text:
                await queue.put(sse("agent_text", {"text": block.text}))
                investigation_transcript.append({
                    "type": "agent_text",
                    "content": block.text
                })

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_inputs = block.input

            await queue.put(sse("tool_call", {
                "tool": tool_name,
                "inputs": tool_inputs
            }))

            if tool_name in REMEDIATION_TOOLS:
                await queue.put(sse("approval_required", {
                    "tool": tool_name,
                    "inputs": tool_inputs
                }))

                approved = await approval_queue.get()

                if not approved:
                    await queue.put(sse("approval_denied", {"tool": tool_name}))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"status": "denied", "reason": "Operator rejected the action."})
                    })
                    continue
                else:
                    await queue.put(sse("approval_granted", {"tool": tool_name}))

            result = execute_tool(tool_name, tool_inputs)
            await queue.put(sse("tool_result", {
                "tool": tool_name,
                "result": result
            }))

            investigation_transcript.append({
                "type": "tool_call",
                "tool": tool_name,
                "inputs": tool_inputs,
                "result": result
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result)
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    # Write incident report after investigation completes
    await write_incident_report(
        session_id, alert, service, investigation_transcript, queue
    )


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/investigate")
async def investigate(request: Request):
    body = await request.json()
    alert = body.get("alert", "").strip()
    if not alert:
        return {"error": "No alert provided"}

    session_id = str(uuid.uuid4())
    event_queue: asyncio.Queue = asyncio.Queue()
    approval_queue: asyncio.Queue = asyncio.Queue()

    sessions[session_id] = {
        "event_queue": event_queue,
        "approval_queue": approval_queue,
        "complete": False,
    }

    asyncio.create_task(run_agent(session_id, alert, event_queue))
    return {"session_id": session_id}


@app.post("/search-incidents/{session_id}")
async def manual_search(session_id: str, request: Request):
    """Manual search triggered by operator during investigation."""
    if session_id not in sessions:
        return {"error": "Session not found"}

    body = await request.json()
    query = body.get("query", "").strip()
    if not query:
        return {"error": "No query provided"}

    try:
        with httpx.Client(timeout=10.0) as http:
            result = http.post(f"{RAG_SERVICE_URL}/search", json={"query": query, "n_results": 3}).json()

        # Push the result into the session's event queue so it appears in the timeline
        event_queue = sessions[session_id]["event_queue"]
        await event_queue.put(sse("manual_search_result", {
            "query": query,
            "result": result
        }))
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/stream/{session_id}")
async def stream(session_id: str):
    if session_id not in sessions:
        return {"error": "Session not found"}

    event_queue = sessions[session_id]["event_queue"]

    async def generator():
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                yield event
                if '"done"' in event:
                    break
            except asyncio.TimeoutError:
                yield sse("heartbeat", {})

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.post("/approve/{session_id}")
async def approve(session_id: str, request: Request):
    if session_id not in sessions:
        return {"error": "Session not found"}
    body = await request.json()
    approved = body.get("approved", False)
    await sessions[session_id]["approval_queue"].put(approved)
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ui"}
