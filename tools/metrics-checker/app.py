from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Metrics Checker Service")

class MetricsRequest(BaseModel):
    service: str

SCENARIOS = {
    "payment-api": {
        "cpu_percent": 72.4,
        "memory_percent": 68.1,
        "request_rate_per_sec": 142.3,
        "error_rate_percent": 18.7,
        "latency_p50_ms": 840,
        "latency_p99_ms": 4200,
        "db_connections_active": 10,
        "db_connections_max": 10,
    },
    "recommendation-service": {
        "cpu_percent": 41.2,
        "memory_percent": 94.1,
        "request_rate_per_sec": 38.7,
        "error_rate_percent": 3.2,
        "latency_p50_ms": 620,
        "latency_p99_ms": 2800,
        "db_connections_active": 4,
        "db_connections_max": 20,
        "pod_uptime_hours": 97,
        "gc_overhead_percent": 27.4,
    },
    "checkout-service": {
        "cpu_percent": 28.3,
        "memory_percent": 52.0,
        "request_rate_per_sec": 61.4,
        "error_rate_percent": 4.1,
        "latency_p50_ms": 980,
        "latency_p99_ms": 3100,
        "db_connections_active": 6,
        "db_connections_max": 20,
        "upstream_error_rate_percent": {
            "inventory-api": 54.3,
            "pricing-service": 1.2,
        },
    },
    "auth-service": {
        "cpu_percent": 18.2,
        "memory_percent": 41.5,
        "request_rate_per_sec": 89.3,
        "error_rate_percent": 34.1,
        "latency_p50_ms": 210,
        "latency_p99_ms": 380,
        "tls_handshake_failure_rate_percent": 34.1,
        "tls_handshake_success_rate_percent": 65.9,
        "active_sessions": 1821,
    },
}

@app.post("/metrics")
async def get_metrics(request: MetricsRequest):
    metrics = SCENARIOS.get(request.service, {})
    return {"service": request.service, "metrics": metrics}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "metrics-checker"}
