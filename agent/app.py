import os
import json
import httpx
import anthropic

# --- Service URLs (resolved by Docker Compose internal DNS) ---
LOG_CHECKER_URL     = os.environ.get("LOG_CHECKER_URL",     "http://log-checker:8001")
METRICS_CHECKER_URL = os.environ.get("METRICS_CHECKER_URL", "http://metrics-checker:8002")
DEPLOY_CHECKER_URL  = os.environ.get("DEPLOY_CHECKER_URL",  "http://deploy-checker:8003")
MOCK_INFRA_URL      = os.environ.get("MOCK_INFRA_URL",      "http://mock-infra:8004")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

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
        elif name == "restart_pod":
            return http.post(f"{MOCK_INFRA_URL}/restart-pod", json=inputs).json()
        elif name == "rollback":
            return http.post(f"{MOCK_INFRA_URL}/rollback", json=inputs).json()
    return {"error": f"Unknown tool: {name}"}

# --- Human Approval Gate ---
def request_approval(tool_name: str, inputs: dict) -> bool:
    print(f"\n{'='*60}")
    print(f"  APPROVAL REQUIRED")
    print(f"{'='*60}")
    print(f"  Action : {tool_name}")
    print(f"  Inputs : {json.dumps(inputs, indent=2)}")
    print(f"{'='*60}")
    response = input("  Approve? (yes/no): ").strip().lower()
    return response in ("yes", "y")

# --- Main Agent Loop ---
def run_agent(alert: str):
    print(f"\n🚨 Alert received: {alert}\n")

    messages = [{"role": "user", "content": alert}]
    system = (
        "You are an SRE agent. Investigate the alert by gathering data with the "
        "read-only tools first. Form a diagnosis before proposing any remediation. "
        "When you recommend a remediation action, use the appropriate tool — but "
        "those actions require human approval before executing."
    )

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Print any text the agent produces
        for block in response.content:
            if hasattr(block, "text"):
                print(f"\n🤖 Agent: {block.text}")

        # If no tool calls, we're done
        if response.stop_reason != "tool_use":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_inputs = block.input

            print(f"\n🔧 Tool call: {tool_name}({json.dumps(tool_inputs)})")

            # Remediation tools need approval
            if tool_name in REMEDIATION_TOOLS:
                approved = request_approval(tool_name, tool_inputs)
                if not approved:
                    print("  ❌ Action denied by operator.")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"status": "denied", "reason": "Operator rejected the action."})
                    })
                    continue

            result = execute_tool(tool_name, tool_inputs)
            print(f"   ↳ Result: {json.dumps(result)[:200]}...")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result)
            })

        # Feed results back into the conversation
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})

    print("\n✅ Investigation complete.\n")


if __name__ == "__main__":
    alert = os.environ.get(
        "ALERT_MESSAGE",
        "payment-api is showing elevated error rates and high latency. Investigate and remediate."
    )
    run_agent(alert)
