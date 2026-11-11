"""Pydantic request/response models for the API."""
from typing import Literal

from pydantic import BaseModel, Field


# --------------------------------------------------
# Requests
# --------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language question to answer.",
        examples=["How does Alice meet the Mad Hatter?"],
    )


class SymbolicIngestRequest(BaseModel):
    limit: int | None = Field(
        default=None,
        ge=1,
        description="Only send the first N chunks to the WSD service (same as the CLI --limit flag). "
        "Omit to process every chunk (slow: ~8s per chunk).",
    )


# --------------------------------------------------
# Responses
# --------------------------------------------------

class IngestResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str


class SymbolicIngestResponse(IngestResponse):
    chunks_total: int = Field(description="Chunks sent to the WSD entity-linking service.")
    chunks_inserted: int = Field(description="Chunk nodes written to Neo4j.")
    senses_processed: int = Field(description="Sense links written to Neo4j.")
    failed_chunks: list[str] = Field(description="IDs of chunks the WSD service failed to link.")


class VectorQueryResponse(BaseModel):
    query: str
    found: bool = Field(description="False when no chunk scored above the relevance threshold (0.7).")
    answer: str | None = None
    sources: list[str | None] = Field(default_factory=list)


class QuerySynset(BaseModel):
    surface: str = Field(description="Text in the query that was linked.")
    synset_id: str


class SymbolicQueryResponse(BaseModel):
    query: str
    found: bool = Field(description="False when no chunk in Neo4j mentions any of the query's synsets.")
    answer: str | None = None
    sources: list[str] = Field(default_factory=list, description="'<source> (<chunk_id>)', best match first.")
    synsets: list[QuerySynset] = Field(default_factory=list, description="Synsets the query's entities linked to.")


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
