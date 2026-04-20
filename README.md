# SRE Agent Demo

An AI-powered incident investigation tool that autonomously diagnoses infrastructure issues, draws on a library of past incidents, proposes remediations with human approval, and writes structured incident reports — all streamed live to a browser UI.

Built with the Anthropic Claude API, FastAPI, ChromaDB, and Server-Sent Events.

**Live demo:** https://sre-agent-ui.fly.dev

---

## What it does

When an alert fires, the agent:

1. **Gathers data autonomously** — metrics, logs, pod status, and recent deployment history
2. **Searches past incidents** — queries a vector database of previous incidents for similar cases
3. **Forms a diagnosis** — reasons across current evidence and historical precedent
4. **Proposes remediation** — calls the appropriate tool and pauses for human approval
5. **Executes on approval** — takes action only after explicit operator sign-off
6. **Writes an incident report** — a second agent pass produces a structured report streamed live to the UI
7. **Stores the report** — adds the new incident to the library so the system learns from every investigation

The human-in-the-loop approval gate is a first-class feature. The agent investigates freely but cannot touch production without explicit sign-off. A manual search bar lets operators inject their own past-incident queries at any point during an investigation.

---

## Architecture

All services are stateless FastAPI microservices. The RAG service wraps ChromaDB with a sentence-transformer embedding model for semantic incident search.

- **UI Service** :8080 — FastAPI, Claude SDK, agent loop, report writer, SSE streaming
- **Log Checker** :8001 — Simulated log entries per service
- **Metrics Checker** :8002 — Simulated metrics per service
- **Deploy Checker** :8003 — Simulated deployment history per service
- **Mock Infra** :8004 — Simulated pod status, restart, rollback
- **RAG Service** :8005 — ChromaDB + sentence-transformer semantic search

---

## Demo scenarios

| Scenario | Root cause | Key reasoning | Remediation |
|---|---|---|---|
| payment-api | DB pool size misconfigured in deploy | Config change timing + pool exhaustion | Rollback |
| recommendation-service | Memory leak introduced 4 days ago | Long uptime + progressive GC warnings | Rollback |
| checkout-service | Upstream dependency down | Victim vs culprit reasoning | Escalate |
| auth-service | TLS cert rotated before clients trusted new CA | Cert rotation timing + TLS errors | Rollback |

Each scenario requires different reasoning. The RAG layer surfaces relevant past incidents, and every completed investigation is stored back into the library.

---

## Running locally

**Prerequisites:** Docker Desktop, an Anthropic API key

    git clone https://github.com/11118mhz/sre-agent-demo.git
    cd sre-agent-demo
    export ANTHROPIC_API_KEY=your-key-here
    docker compose up --build

Open http://localhost:8080. On first startup the RAG service seeds 10 incidents into ChromaDB automatically.

---

## Project structure

    infra-agent/
    ├── ui/                       # Web UI + agent loop + report writer
    │   ├── app.py                # FastAPI, SSE streaming, agent orchestration
    │   └── templates/index.html  # Single-page UI with manual search
    ├── rag-service/              # Incident library and semantic search
    │   ├── app.py                # /search, /store, /health endpoints
    │   ├── store.py              # ChromaDB wrapper and embedding logic
    │   └── seed_incidents.py     # 10 seed incidents across 4 failure categories
    ├── tools/
    │   ├── log-checker/          # Simulated logs per service
    │   ├── metrics-checker/      # Simulated metrics per service
    │   └── deploy-checker/       # Simulated deployment history per service
    ├── mock-infra/               # Simulated pod status, restart, rollback
    └── docker-compose.yml

---

## Key design decisions

**RAG for incident history** — Semantic search finds structurally similar incidents even when terminology differs. A query about connection pool exhaustion correctly surfaces past incidents about database connection limits and pool size misconfiguration.

**Second agent pass for reports** — A separate report-writing pass with the full transcript as context produces cleaner output than asking the investigation agent to write a report mid-loop.

**Reports stored back into the library** — Every investigation adds to institutional memory. After real use, the library contains actual incident history from your environment, making future investigations progressively more informed.

**Human approval gate** — Implemented as an asyncio.Queue. The agent loop blocks on await approval_queue.get() until the operator clicks Approve or Deny in the browser.

---

## Incident library

The seed library covers 10 incidents across 4 failure categories:

| Category | Count | Examples |
|---|---|---|
| Misconfiguration | 3 | DB pool reduction, memory limit change, rate limit scope |
| Runtime degradation | 2 | Memory leak, thread pool exhaustion |
| Dependency failure | 3 | Upstream service down, replica lag, queue backlog |
| Infrastructure change | 2 | TLS cert rotation, DNS TTL stale records |

The library persists between runs via a Docker volume mount at ./rag-data.

---

## Roadmap

- Version 2 approval gate: agent proposes RAG search query, operator approves/edits before executing
- Multi-agent architecture: triage agent routes to specialist agents per failure domain
- Real backends: swap mock services for Prometheus, Kubernetes API, and log aggregator clients
- Fault injection panel: trigger incidents on demand for live demos

---

## Documentation

- [Original demo README v1](docs/README-v1-original-demo.md) — the initial four-scenario demo before RAG and report writing were added
