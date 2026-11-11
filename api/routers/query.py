from fastapi import APIRouter

from api.routers._errors import ERROR_RESPONSES, run_script
from api.schemas import QueryRequest, SymbolicQueryResponse, VectorQueryResponse
from api.services import symbolic_service, vector_service

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/vector", response_model=VectorQueryResponse, responses=ERROR_RESPONSES)
def query_vector(body: QueryRequest) -> VectorQueryResponse:
    """Answer a question from the Chroma store with an LLM (same as `python query_data.py "<query>"`)."""
    result = run_script("Vector query", vector_service.query, body.query)
    return VectorQueryResponse(query=body.query, **result)


@router.post("/symbolic", response_model=SymbolicQueryResponse, responses=ERROR_RESPONSES)
def query_symbolic(body: QueryRequest) -> SymbolicQueryResponse:
    """Answer a question from chunks in Neo4j that share the query's WSD synsets
    (same as `python query_data_by_wsd.py "<query>"`)."""
    result = run_script("Symbolic query", symbolic_service.query, body.query)
    return SymbolicQueryResponse(query=body.query, **result)
