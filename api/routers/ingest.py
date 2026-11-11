from fastapi import APIRouter

from api.routers._errors import ERROR_RESPONSES, run_script
from api.schemas import ErrorResponse, IngestResponse, SymbolicIngestRequest, SymbolicIngestResponse
from api.services import symbolic_service, vector_service

router = APIRouter(prefix="/ingest", tags=["ingest"])

_INGEST_ERRORS = {
    **ERROR_RESPONSES,
    409: {"model": ErrorResponse, "description": "An ingestion of this type is already running."},
}

# Endpoints are plain `def`, not `async def`: the scripts are blocking, so FastAPI runs them in
# its threadpool and the event loop stays free for other requests.


@router.post("/vector", response_model=IngestResponse, responses=_INGEST_ERRORS)
def ingest_vector() -> IngestResponse:
    """Rebuild the Chroma vector store from data/books (same as `python create_database.py`)."""
    run_script("Vector ingestion", vector_service.ingest)
    return IngestResponse(message="Vector database rebuilt from data/books.")


@router.post("/symbolic", response_model=SymbolicIngestResponse, responses=_INGEST_ERRORS)
def ingest_symbolic(body: SymbolicIngestRequest | None = None) -> SymbolicIngestResponse:
    """Link entities in every chunk with the WSD service and store them in Neo4j
    (same as `python symbolic_link_data.py [--limit N]`). The request body is optional."""
    limit = body.limit if body else None
    result = run_script("Symbolic ingestion", symbolic_service.ingest, limit=limit)
    message = f"Stored {result['chunks_inserted']} of {result['chunks_total']} chunks in Neo4j."
    if result["failed_chunks"]:
        message += f" {len(result['failed_chunks'])} chunks failed entity linking."
    return SymbolicIngestResponse(message=message, **result)
