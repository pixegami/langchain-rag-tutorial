"""FastAPI entry point.

Run from the repository root with:
    uvicorn api.main:app --reload
or `python -m api.main`.
"""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from api.routers import ingest, query
from api.schemas import HealthResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The scripts use paths relative to the repo root ("chroma", "data/books") and live at the
# repo root, so make both work no matter which directory the server was started from.
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="LangChain RAG API",
    description="REST endpoints for vector (Chroma) and symbolic (WSD + Neo4j) ingestion and retrieval.",
    version="1.0.0",
)

API_PREFIX = "/api/v1"
app.include_router(ingest.router, prefix=API_PREFIX)
app.include_router(query.router, prefix=API_PREFIX)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
