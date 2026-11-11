"""Vector (Chroma + OpenAI) ingestion and retrieval, backed by create_database.py and query_data.py."""
import threading

from api.services import IngestionInProgressError, ServiceError

# create_database.save_to_chroma deletes and rebuilds the Chroma directory, so two
# concurrent runs would clobber each other. Only one ingestion may run at a time.
_ingest_lock = threading.Lock()


def ingest() -> None:
    """Run create_database.generate_data_store() -- the same thing `python create_database.py` does."""
    if not _ingest_lock.acquire(blocking=False):
        raise IngestionInProgressError("Vector")
    try:
        try:
            import create_database
        except KeyError as e:  # create_database reads os.environ['OPENAI_API_KEY'] at import time
            raise ServiceError(f"Missing required environment variable: {e}") from e
        create_database.generate_data_store()
    finally:
        _ingest_lock.release()


def query(query_text: str) -> dict:
    """Answer a question from the Chroma store.

    Makes the same calls as query_data.main() (same Chroma path, prompt, k=3, 0.7
    relevance cutoff and model). main() itself can't be called because it parses
    sys.argv and prints its answer instead of returning it.
    """
    from langchain.prompts import ChatPromptTemplate
    from langchain_community.vectorstores import Chroma
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    from query_data import CHROMA_PATH, PROMPT_TEMPLATE

    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=OpenAIEmbeddings())

    results = db.similarity_search_with_relevance_scores(query_text, k=3)
    if len(results) == 0 or results[0][1] < 0.7:
        return {"found": False, "answer": None, "sources": []}

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE).format(
        context=context_text, question=query_text
    )

    model = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    response_text = model.invoke(prompt).content

    sources = [doc.metadata.get("source", None) for doc, _score in results]
    return {"found": True, "answer": response_text, "sources": sources}
