import os
import json
import chromadb
from chromadb.utils import embedding_functions

# Data directory — local filesystem, persists via Docker volume mount
DATA_DIR = os.environ.get("RAG_DATA_DIR", "./data")

# Use a lightweight sentence transformer for embeddings
# all-MiniLM-L6-v2 is small, fast, and works well for technical text
EMBEDDING_FN = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def get_collection():
    client = chromadb.PersistentClient(path=DATA_DIR)
    return client.get_or_create_collection(
        name="incidents",
        embedding_function=EMBEDDING_FN,
        metadata={"hnsw:space": "cosine"}
    )

def build_embedding_text(incident: dict) -> str:
    """
    Concatenate the most semantically rich fields for embedding.
    This is what the vector search actually matches against.
    """
    parts = [
        incident.get("alert_text", ""),
        incident.get("root_cause", ""),
        incident.get("narrative", ""),
        " ".join(incident.get("symptoms", {}).get("key_log_messages", [])),
        " ".join(incident.get("evidence", [])),
        " ".join(incident.get("tags", [])),
    ]
    return " ".join(p for p in parts if p)

def store_incident(incident: dict) -> str:
    """Store a single incident. Returns the incident ID."""
    collection = get_collection()
    text = build_embedding_text(incident)
    collection.upsert(
        ids=[incident["id"]],
        documents=[text],
        metadatas=[{
            "service": incident.get("service", ""),
            "root_cause_category": incident.get("root_cause_category", ""),
            "root_cause": incident.get("root_cause", ""),
            "remediation": incident.get("remediation", ""),
            "duration_minutes": incident.get("duration_minutes", 0),
            "tags": json.dumps(incident.get("tags", [])),
            "full_incident": json.dumps(incident),
        }]
    )
    return incident["id"]

def search_incidents(query: str, n_results: int = 3) -> list[dict]:
    """
    Search for similar past incidents by natural language query.
    Returns top N matches with similarity scores.
    """
    collection = get_collection()

    # Don't search if collection is empty
    if collection.count() == 0:
        return []

    n_results = min(n_results, collection.count())

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["metadatas", "distances"]
    )

    incidents = []
    for metadata, distance in zip(
        results["metadatas"][0],
        results["distances"][0]
    ):
        incident = json.loads(metadata["full_incident"])
        incident["similarity_score"] = round(1 - distance, 3)
        incidents.append(incident)

    return incidents

def get_incident_count() -> int:
    return get_collection().count()
