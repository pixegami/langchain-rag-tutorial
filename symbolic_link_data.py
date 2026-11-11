"""Send book chunks to the Symbolic RAG entity-linking API (instead of OpenAI embeddings) and print the results.

Usage:
    python symbolic_link_data.py                 # all chunks (slow: ~8s per chunk)
    python symbolic_link_data.py --limit 5       # only the first 5 chunks
    python symbolic_link_data.py --out out.json  # also save the raw API responses
"""
import argparse
import contextlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv

# Same loading and chunking as the Chroma pipeline, so chunk ids line up with what create_database.py stores.
from create_database import load_documents, split_text

load_dotenv()
SYMBOLIC_WSD_URL = os.environ.get("SYMBOLIC_WSD_URL")
if not SYMBOLIC_WSD_URL:
    sys.exit("SYMBOLIC_WSD_URL is not set. Add it to your .env file (see .env.example).")
API_URL = f"{SYMBOLIC_WSD_URL.rstrip('/')}/api/symbolic-rag-entity-linking"


def link_entities(sentence):
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({"sentence": sentence}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def make_chunks():
    """Split documents with create_database.split_text and give each chunk a stable id: <file name>-<chunk number>."""
    chunks, counters = [], {}
    with contextlib.redirect_stdout(sys.stderr):  # split_text prints a sample chunk; keep stdout for the JSON
        docs = split_text(load_documents())
    for doc in docs:
        source = os.path.basename(doc.metadata["source"])
        counters[source] = counters.get(source, 0) + 1
        chunk_id = f"{os.path.splitext(source)[0]}-{counters[source]}"
        chunks.append({"chunk_id": chunk_id, "source": source, "text": doc.page_content})
    return chunks


def to_senses(result):
    """Turn an API response into [{surface, synset_id, sense}], one per linked entity."""
    sentence, senses = result["sentence"], []
    for entity_id, e in enumerate(result["entities"]):
        if not e.get("synset_id"):
            continue
        covered = [w for w in result["words"] if entity_id in w["entities"]]
        surface = sentence[covered[0]["start"]:covered[-1]["end"]] if covered else e["term"]
        # WordNet glosses: 'definition; "example"'. Wikipedia glosses: a paragraph -> keep its first sentence.
        definition = (e.get("gloss") or "").split(";")[0].strip()
        first_sentence = re.match(r'.+?[.!?]["\']?(?=\s+[A-Z])', definition)
        if first_sentence:
            definition = first_sentence.group(0)
        senses.append({"surface": surface, "synset_id": e["synset_id"], "sense": definition})
    return senses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Only send the first N chunks (default: all).")
    parser.add_argument("--out", help="Optional JSON file to also save the results to.")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    chunks = make_chunks()
    if args.limit:
        chunks = chunks[: args.limit]
    total = len(chunks)
    print(f"Sending {total} chunks to {API_URL} ...", file=sys.stderr)

    results, failed = [], []
    for n, chunk in enumerate(chunks, 1):
        try:
            senses = to_senses(link_entities(chunk["text"]))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
            failed.append(chunk["chunk_id"])
            print(f"\n{chunk['chunk_id']} failed: {e}", file=sys.stderr)
            senses = None
        if senses is not None:
            results.append({**chunk, "senses": senses})
        print(f"\rOut of {total}, processed {n} ({len(failed)} failed)", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)

    output = json.dumps(results, indent=2, ensure_ascii=False)
    print(output)
    if failed:
        print(f"Failed chunks: {', '.join(failed)}", file=sys.stderr)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved {len(results)} results to {args.out}.", file=sys.stderr)


if __name__ == "__main__":
    main()
