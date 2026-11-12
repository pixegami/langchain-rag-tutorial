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

## Load the WordNet graph into Neo4j

[scripts/load-wordnet-graph.sh](scripts/load-wordnet-graph.sh) loads the WordNet glosstag graph that wsd-entity-linker serves on port 7688 (its "ignore-common" graph) into this repo's Neo4j:

```
(:Synset)-[:GLOSS_LINKS_TO]->(:Sense)-[:IN_SYNSET]->(:Synset)
```

That is 117,659 Synset nodes, 206,941 Sense nodes and about 880k edges. The script runs on your machine and needs:

- The DevPod workspace running (`devpod up .`). The script loads into its `neo4j-database` container.
- DVC: `pipx install "dvc[gs]~=3.67"`.
- Google credentials with the Viewer role on GCP project `symbolic-rag`, set up once with `gcloud auth application-default login`.

```bash
scripts/load-wordnet-graph.sh
```

It takes about 3 minutes and runs three steps:

1. `dvc pull` downloads the Haiku-annotated glosstag XML and `common-senses.json` (342 MB) from `gs://symbolic-rag-datasets/dvc` into `wordnet/data/`.
2. [wordnet/glosstag_to_graph.py](wordnet/glosstag_to_graph.py), a copy of wsd-entity-linker's, builds the CSVs in `wordnet/output/neo4j/`. They match that repo's byte for byte. Later runs skip this step; set `REBUILD=1` to rebuild.
3. [wordnet/load_wordnet_graph.py](wordnet/load_wordnet_graph.py) MERGEs the CSVs into the running database.

The load keeps the data already in the database and is safe to re-run, because it creates no duplicate nodes or edges. A chunk's `Sense {synset_id}` uses the same ids as WordNet's `Synset {id}` (for example `n00001740`), so the two are treated as the same node: it gets the `Synset` label, and the WordNet edges attach to it next to its `MENTIONS` edges. `neo4j_graphdb.py` does the same for chunks ingested after the load. Wikipedia ids (`w...`) have no WordNet synset and stay plain `Sense` nodes.

Here is a step-by-step tutorial video: [RAG+Langchain Python Project: Easy AI/Chat For Your Docs](https://www.youtube.com/watch?v=tcqEUSNCn8I&ab_channel=pixegami).
