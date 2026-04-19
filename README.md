# SRE Agent Demo

An AI-powered incident investigation tool that autonomously diagnoses infrastructure issues and proposes remediations — with a human approval gate before anything touches production.

Built with the Anthropic Claude API, FastAPI, and Server-Sent Events for real-time streaming.

**Live demo:** https://sre-agent-ui.fly.dev

---

## What it does

When an alert fires, the agent:

1. Gathers data autonomously — metrics, logs, pod status, and recent deployment history
2. Reasons across all the evidence to form a diagnosis
3. Proposes a remediation action (rollback, pod restart, etc.)
4. **Pauses and waits for human approval** before executing anything
5. Executes the approved action and summarises the outcome

The human-in-the-loop approval gate is a first-class feature, not an afterthought. The agent can investigate freely but cannot touch production without explicit operator sign-off.

---

## Architecture
┌─────────────────────────────────────────────────────┐
│                    Browser UI                        │
│         (SSE stream + approve/deny buttons)          │
└─────────────────┬───────────────────────────────────┘
│
┌─────────────────▼───────────────────────────────────┐
│                  UI Service (port 8080)               │
│         FastAPI + Anthropic Claude SDK               │
│         Runs agent loop, streams events via SSE      │
└────┬──────────┬──────────┬──────────┬───────────────┘
│          │          │          │
┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌──▼──────┐
│  Log   │ │Metrics │ │Deploy  │ │  Mock   │
│Checker │ │Checker │ │Checker │ │  Infra  │
│ :8001  │ │ :8002  │ │ :8003  │ │  :8004  │
└────────┘ └────────┘ └────────┘ └─────────┘

All services are stateless FastAPI microservices running in Docker. The UI service owns the agent loop and communicates with tool services over HTTP.

---

## Demo scenarios

The demo includes four pre-built incident scenarios, each covering a different class of real-world failure:

| Scenario | Root cause | What the agent does |
|---|---|---|
| `payment-api` | DB pool size misconfigured in a recent deploy | Identifies config change, recommends rollback |
| `recommendation-service` | Memory leak introduced 4 days ago | Spots long pod uptime + progressive GC warnings, recommends rollback |
| `checkout-service` | Upstream dependency (`inventory-api`) is down | Correctly identifies checkout as victim, escalates rather than remediating |
| `auth-service` | TLS cert rotated before clients trusted new CA | Correlates cert rotation timing with TLS errors, recommends rollback |

Each scenario is designed to require different reasoning — the absence of a recent deploy, upstream vs. local failure, infrastructure vs. application changes.

---

## Running locally

**Prerequisites:** Docker Desktop, an Anthropic API key

```bash
git clone https://github.com/YOUR_USERNAME/sre-agent-demo.git
cd sre-agent-demo
export ANTHROPIC_API_KEY=your-key-here
docker compose up --build
```

Then open http://localhost:8080.

---

## Project structure
infra-agent/
├── ui/                          # Web UI + agent loop
│   ├── app.py                   # FastAPI app, SSE streaming, agent orchestration
│   └── templates/index.html     # Single-page UI
├── tools/
│   ├── log-checker/app.py       # Returns simulated log entries per service
│   ├── metrics-checker/app.py   # Returns simulated metrics per service
│   └── deploy-checker/app.py    # Returns simulated deployment history
├── mock-infra/app.py            # Simulates pod status, restart, and rollback
├── agent/app.py                 # Original terminal-only agent (superseded by UI)
└── docker-compose.yml

---

## Key design decisions

**Why FastAPI microservices instead of a monolith?**
Each tool service is independently replaceable. Swapping `mock-infra` for a real Kubernetes API client, or pointing `metrics-checker` at a real Prometheus instance, requires no changes to the agent or UI.

**Why Server-Sent Events instead of WebSockets?**
SSE is unidirectional (server → client) which matches the data flow perfectly. Simpler to implement, no reconnection logic needed, and works through most proxies without configuration.

**Why a human approval gate?**
An agent that can investigate freely but requires sign-off before executing remediations is a realistic and safe model for production use. The approval gate is implemented as an `asyncio.Queue` — the agent loop blocks on `await approval_queue.get()` until the operator clicks Approve or Deny in the browser.

---

## Deploying to fly.io

Each service has a `fly.toml` config. Deploy in this order:

```bash
# Backend services first
cd tools/log-checker && fly apps create sre-agent-log-checker && fly deploy && cd ../..
cd tools/metrics-checker && fly apps create sre-agent-metrics-checker && fly deploy && cd ../..
cd tools/deploy-checker && fly apps create sre-agent-deploy-checker && fly deploy && cd ../..
cd mock-infra && fly apps create sre-agent-mock-infra && fly deploy && cd ..

# UI last (needs backends running first)
cd ui
fly apps create sre-agent-ui
fly secrets set ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
fly secrets set \
  LOG_CHECKER_URL=https://sre-agent-log-checker.fly.dev \
  METRICS_CHECKER_URL=https://sre-agent-metrics-checker.fly.dev \
  DEPLOY_CHECKER_URL=https://sre-agent-deploy-checker.fly.dev \
  MOCK_INFRA_URL=https://sre-agent-mock-infra.fly.dev
fly deploy
```

---

## Roadmap

- [ ] Replace mock services with real backends (Prometheus, Kubernetes API, log aggregator)
- [ ] Fault injection panel — trigger incidents on demand during live demos
- [ ] Multi-service investigation — agent follows dependency chains across services
- [ ] Persistent investigation history
