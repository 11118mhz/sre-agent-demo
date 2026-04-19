from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta

app = FastAPI(title="Deploy Checker Service")

class DeployRequest(BaseModel):
    service: str
    hours: int = 24

SCENARIOS = {
    "payment-api": {
        "deployments": [
            {
                "deployment_id": "deploy-4a7c",
                "service": "payment-api",
                "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "image": "payment-api:v2.14.1",
                "previous_image": "payment-api:v2.14.0",
                "deployed_by": "ci-pipeline",
                "status": "completed",
                "change_summary": "Updated database connection pooling library",
            }
        ],
        "recent_config_changes": [
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=2, minutes=15)).isoformat(),
                "change": "Updated DB_POOL_SIZE from 20 to 10 (via ConfigMap)",
                "changed_by": "deploy-4a7c",
            }
        ],
    },
    "recommendation-service": {
        "deployments": [
            {
                "deployment_id": "deploy-9f2a",
                "service": "recommendation-service",
                "timestamp": (datetime.utcnow() - timedelta(days=4)).isoformat(),
                "image": "recommendation-service:v1.8.3",
                "previous_image": "recommendation-service:v1.8.2",
                "deployed_by": "ci-pipeline",
                "status": "completed",
                "change_summary": "Improved recommendation ranking algorithm",
            }
        ],
        "recent_config_changes": [],
    },
    "checkout-service": {
        "deployments": [],
        "recent_config_changes": [],
    },
    "auth-service": {
        "deployments": [],
        "recent_config_changes": [
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
                "change": "Rotated TLS certificate: replaced internal-ca-v1 with internal-ca-v2 (via cert-manager)",
                "changed_by": "platform-team-automation",
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
                "change": "Updated SECRET/auth-service-tls to new certificate bundle",
                "changed_by": "platform-team-automation",
            },
        ],
    },
}

@app.post("/deployments")
async def get_deployments(request: DeployRequest):
    scenario = SCENARIOS.get(request.service, {"deployments": [], "recent_config_changes": []})
    return {"service": request.service, "hours_searched": request.hours, **scenario}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "deploy-checker"}
