# Langchain RAG Tutorial

## Install dependencies

1. Do the following before installing the dependencies found in `requirements.txt` file because of current challenges installing `onnxruntime` through `pip install onnxruntime`. 

    - For MacOS users, a workaround is to first install `onnxruntime` dependency for `chromadb` using:

    ```python
     conda install onnxruntime -c conda-forge
    ```
    See this [thread](https://github.com/microsoft/onnxruntime/issues/11037) for additonal help if needed. 

     - For Windows users, follow the guide [here](https://github.com/bycloudai/InstallVSBuildToolsWindows?tab=readme-ov-file) to install the Microsoft C++ Build Tools. Be sure to follow through to the last step to set the enviroment variable path.


2. Now run this command to install dependenies in the `requirements.txt` file. 

```python
pip install -r requirements.txt
```

3. Install markdown depenendies with: 

```python
pip install "unstructured[md]"
```

## Create database

Create the Chroma DB.

```python
python create_database.py
```

## Query the database

Query the Chroma DB.

```python
python query_data.py "How does Alice meet the Mad Hatter?"
```

> You'll also need to set up an OpenAI account (and set the OpenAI key in your environment variable) for this to work.

## Run as a REST API

The same four operations are exposed by a FastAPI service in [`api/`](api/). Start it from the repository root:

```bash
uvicorn api.main:app --reload
```

Interactive docs are at http://localhost:8000/docs.

| CLI | Endpoint | Body |
| --- | --- | --- |
| `python create_database.py` | `POST /api/v1/ingest/vector` | none |
| `python symbolic_link_data.py [--limit N]` | `POST /api/v1/ingest/symbolic` | optional `{"limit": N}` |
| `python query_data.py "<query>"` | `POST /api/v1/query/vector` | `{"query": "<query>"}` |
| `python query_data_by_wsd.py "<query>"` | `POST /api/v1/query/symbolic` | `{"query": "<query>"}` |

```bash
curl -X POST http://localhost:8000/api/v1/query/vector \
  -H "Content-Type: application/json" \
  -d '{"query": "How does Alice meet the Mad Hatter?"}'
```

Ingestion runs synchronously, so the request stays open until it finishes. Full symbolic ingestion takes about 8 seconds per chunk; pass `limit` for a quick run. A second ingestion of the same type while one is running returns `409`. A script failure returns `500` with the error in `detail`, and an unreachable WSD service returns `502`.

Here is a step-by-step tutorial video: [RAG+Langchain Python Project: Easy AI/Chat For Your Docs](https://www.youtube.com/watch?v=tcqEUSNCn8I&ab_channel=pixegami).
