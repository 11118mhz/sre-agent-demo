from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mock Infrastructure Service")

class PodStatusRequest(BaseModel):
    service: str
    namespace: str = "default"

class RestartPodRequest(BaseModel):
    pod_name: str
    namespace: str = "default"

class RollbackRequest(BaseModel):
    service: str
    target_revision: str = "previous"

POD_SCENARIOS = {
    "payment-api": {
        "pods": [
            {"name": "payment-api-7d4f8b6c9-x2k4m", "status": "Running", "ready": True,  "restarts": 0, "node": "worker-node-03"},
            {"name": "payment-api-7d4f8b6c9-q8n1p", "status": "Running", "ready": True,  "restarts": 2, "node": "worker-node-05"},
            {"name": "payment-api-7d4f8b6c9-r3t7w", "status": "Running", "ready": False, "restarts": 7, "node": "worker-node-01"},
        ],
        "desired_replicas": 3,
        "available_replicas": 2,
    },
    "recommendation-service": {
        "pods": [
            {"name": "recommendation-service-6b9d4f-m2p8x", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-02"},
            {"name": "recommendation-service-6b9d4f-k7q3n", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-04"},
            {"name": "recommendation-service-6b9d4f-w1r5t", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-06"},
        ],
        "desired_replicas": 3,
        "available_replicas": 3,
    },
    "checkout-service": {
        "pods": [
            {"name": "checkout-service-5c7f2a-h4k9m", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-02"},
            {"name": "checkout-service-5c7f2a-p2n6q", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-04"},
        ],
        "desired_replicas": 2,
        "available_replicas": 2,
    },
    "auth-service": {
        "pods": [
            {"name": "auth-service-8e3c1b-x9p4k", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-01"},
            {"name": "auth-service-8e3c1b-n2m7q", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-03"},
            {"name": "auth-service-8e3c1b-t5r8w", "status": "Running", "ready": True, "restarts": 0, "node": "worker-node-05"},
        ],
        "desired_replicas": 3,
        "available_replicas": 3,
    },
}

@app.post("/pod-status")
async def pod_status(request: PodStatusRequest):
    scenario = POD_SCENARIOS.get(request.service, {"pods": [], "desired_replicas": 0, "available_replicas": 0})
    return {"service": request.service, "namespace": request.namespace, **scenario}

@app.post("/restart-pod")
async def restart_pod(request: RestartPodRequest):
    return {"status": "success", "message": f"Pod {request.pod_name} restarted successfully", "action": "restart"}

@app.post("/rollback")
async def rollback(request: RollbackRequest):
    return {"status": "success", "message": f"Service {request.service} rolled back to {request.target_revision}", "action": "rollback"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-infra"}
