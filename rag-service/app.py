import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from store import store_incident, search_incidents, get_incident_count
from seed_incidents import SEED_INCIDENTS

app = FastAPI(title="RAG Service")

# --- Seed the database on startup if empty ---
@app.on_event("startup")
async def seed_on_startup():
    count = get_incident_count()
    if count == 0:
        print(f"Database empty — seeding {len(SEED_INCIDENTS)} incidents...")
        for incident in SEED_INCIDENTS:
            store_incident(incident)
        print(f"Seeded {len(SEED_INCIDENTS)} incidents successfully.")
    else:
        print(f"Database already contains {count} incidents — skipping seed.")

# --- Request/Response Models ---
class SearchRequest(BaseModel):
    query: str
    n_results: int = 3

class StoreRequest(BaseModel):
    incident: dict

class SearchResult(BaseModel):
    incidents: list[dict]
    query: str
    total_in_library: int

# --- Endpoints ---

@app.post("/search")
async def search(request: SearchRequest) -> SearchResult:
    results = search_incidents(request.query, request.n_results)
    return SearchResult(
        incidents=results,
        query=request.query,
        total_in_library=get_incident_count()
    )

@app.post("/store")
async def store(request: StoreRequest):
    incident_id = store_incident(request.incident)
    return {
        "status": "stored",
        "id": incident_id,
        "total_in_library": get_incident_count()
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "rag-service",
        "incidents_in_library": get_incident_count()
    }
