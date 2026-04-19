from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta

app = FastAPI(title="Log Checker Service")

class LogRequest(BaseModel):
    service: str
    minutes: int = 30

SCENARIOS = {
    "payment-api": [
        {"timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(), "level": "ERROR", "message": "Connection pool exhausted: timeout waiting for connection"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=4)).isoformat(), "level": "ERROR", "message": "DB_POOL_SIZE=10 connections all in use"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=3)).isoformat(), "level": "WARN",  "message": "Request latency p99=4200ms exceeds SLO threshold"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=2)).isoformat(), "level": "ERROR", "message": "Transaction failed: could not acquire DB connection"},
    ],
    "recommendation-service": [
        {"timestamp": (datetime.utcnow() - timedelta(hours=6)).isoformat(),    "level": "WARN",  "message": "GC overhead warning: GC time exceeding 10% of runtime"},
        {"timestamp": (datetime.utcnow() - timedelta(hours=3)).isoformat(),    "level": "WARN",  "message": "GC overhead warning: GC time exceeding 18% of runtime"},
        {"timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),    "level": "WARN",  "message": "GC overhead warning: GC time exceeding 27% of runtime"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(), "level": "ERROR", "message": "GC overhead limit approaching critical threshold — heap usage at 94%"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=10)).isoformat(), "level": "ERROR", "message": "Request latency degrading: p99=2800ms, likely GC pause impact"},
    ],
    "checkout-service": [
        {"timestamp": (datetime.utcnow() - timedelta(minutes=20)).isoformat(), "level": "WARN",  "message": "Upstream timeout: inventory-api failed to respond within 3000ms"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=18)).isoformat(), "level": "WARN",  "message": "Upstream timeout: inventory-api failed to respond within 3000ms"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(), "level": "ERROR", "message": "Circuit breaker OPEN: inventory-api error rate exceeded 50% threshold"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=12)).isoformat(), "level": "WARN",  "message": "Checkout latency elevated: p99=3100ms — awaiting inventory-api responses"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),  "level": "ERROR", "message": "Circuit breaker still OPEN: inventory-api unresponsive"},
    ],
    "auth-service": [
        {"timestamp": (datetime.utcnow() - timedelta(minutes=28)).isoformat(), "level": "ERROR", "message": "TLS handshake failed: certificate verify error — unknown CA"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=27)).isoformat(), "level": "ERROR", "message": "TLS handshake failed: certificate verify error — unknown CA"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=26)).isoformat(), "level": "ERROR", "message": "TLS handshake failed: certificate verify error — unknown CA"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=25)).isoformat(), "level": "WARN",  "message": "Authentication failure rate rising: 34% of requests failing TLS negotiation"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=20)).isoformat(), "level": "ERROR", "message": "Certificate CN=auth-service.prod, issuer=internal-ca-v2 not trusted by clients"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=15)).isoformat(), "level": "ERROR", "message": "TLS handshake failed: certificate verify error — unknown CA"},
        {"timestamp": (datetime.utcnow() - timedelta(minutes=10)).isoformat(), "level": "ERROR", "message": "TLS handshake failed: certificate verify error — unknown CA"},
    ],
}

@app.post("/logs")
async def get_logs(request: LogRequest):
    logs = SCENARIOS.get(request.service, [])
    return {"service": request.service, "minutes_searched": request.minutes, "entries": logs}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "log-checker"}
