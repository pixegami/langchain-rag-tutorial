"""Symbolic (WSD entity linking + Neo4j) ingestion and retrieval, backed by
symbolic_link_data.py and query_data_by_wsd.py."""
import threading
import urllib.error
from types import ModuleType

from api.services import IngestionInProgressError, ServiceError

_ingest_lock = threading.Lock()


def _load_symbolic_link_data() -> ModuleType:
    # symbolic_link_data calls sys.exit() at import time when SYMBOLIC_WSD_URL is unset.
    # SystemExit is a BaseException, so it must be caught explicitly or it would stop the server.
    try:
        import symbolic_link_data
    except SystemExit as e:
        raise ServiceError(str(e.code)) from None
    except KeyError as e:  # it imports create_database, which needs OPENAI_API_KEY
        raise ServiceError(f"Missing required environment variable: {e}") from e
    return symbolic_link_data


def _wsd_unreachable(e: Exception) -> ServiceError:
    return ServiceError(f"Symbolic WSD service request failed: {e}", status_code=502)


def ingest(limit: int | None = None) -> dict:
    """Do what `python symbolic_link_data.py [--limit N]` does, returning the counts instead of printing them.

    Uses the script's own make_chunks, link_entities, to_senses and process_and_store.
    """
    if not _ingest_lock.acquire(blocking=False):
        raise IngestionInProgressError("Symbolic")
    try:
        sld = _load_symbolic_link_data()

        chunks = sld.make_chunks()
        if limit:
            chunks = chunks[:limit]

        results, failed = [], []
        for chunk in chunks:
            try:
                senses = sld.to_senses(sld.link_entities(chunk["text"]))
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
                failed.append(chunk["chunk_id"])
                continue
            results.append({**chunk, "senses": senses})

        graph_data = sld.process_and_store(results)
        return {
            "chunks_total": len(chunks),
            "chunks_inserted": graph_data["chunks_inserted"],
            "senses_processed": graph_data["senses_processed"],
            "failed_chunks": failed,
        }
    finally:
        _ingest_lock.release()


def query(query_text: str) -> dict:
    """Answer a question from the Neo4j graph.

    Makes the same calls as query_data_by_wsd.main(): link the query's entities to synsets
    with the WSD service, fetch every chunk mentioning one of those synsets, then answer
    with the shared prompt and model. main() itself can't be called because it parses
    sys.argv and prints its answer instead of returning it.
    """
    sld = _load_symbolic_link_data()

    try:
        senses = sld.to_senses(sld.link_entities(query_text))
    except (urllib.error.URLError, TimeoutError) as e:
        raise _wsd_unreachable(e) from e
    synsets = [{"surface": s["surface"], "synset_id": s["synset_id"]} for s in senses]
    synset_ids = list(dict.fromkeys(s["synset_id"] for s in senses))

    from langchain.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    from neo4j_graphdb import GraphRepository
    from query_data import PROMPT_TEMPLATE

    results = []
    if synset_ids:
        graph = GraphRepository()
        try:
            results = graph.find_chunks_by_synset_ids(synset_ids)
        finally:
            graph.close()
    if len(results) == 0:
        return {"found": False, "answer": None, "sources": [], "synsets": synsets}

    context_text = "\n\n---\n\n".join([chunk["text"] for chunk in results])
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE).format(
        context=context_text, question=query_text
    )

    model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    response_text = model.invoke(prompt).content

    sources = [f"{chunk['source']} ({chunk['chunk_id']})" for chunk in results]
    return {"found": True, "answer": response_text, "sources": sources, "synsets": synsets}
