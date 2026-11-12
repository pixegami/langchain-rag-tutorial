"""Load the WordNet glosstag graph CSVs into the running Neo4j, without wiping what's already there.

Reads the CSVs glosstag_to_graph.py writes (wordnet/output/neo4j/) and MERGEs them in batches:

    (:Synset {id})-[:GLOSS_LINKS_TO {token, ...}]->(:Sense {id})-[:IN_SYNSET]->(:Synset {id})

This is the same graph wsd-entity-linker bulk-imports on port 7688. neo4j-admin's bulk
import replaces the whole database, so this script uses MERGE instead. Running it again
updates the same nodes and edges and creates no duplicates.

Nodes are matched by key: Synset by `id` (e.g. n00001740), Sense by `id` (the sense key,
e.g. entity%1:03:00::), IN_SYNSET by its two ends, and GLOSS_LINKS_TO by its two ends plus
`token`. That key is unique in the CSVs.

Chunk senses already in the graph: symbolic_link_data.py stores what a chunk mentions as
(:Chunk)-[:MENTIONS]->(:Sense {synset_id}), and synset_id uses the same strings as
Synset.id. A Sense node whose synset_id names a WordNet synset is that synset, so it is
reused rather than duplicated. It gets the Synset label and `id` = synset_id, and the
WordNet edges attach to it. Its MENTIONS edges and its `sense` property stay. Wikipedia
ids (w...) match no WordNet synset and are left as they are.

Usage (scripts/load-wordnet-graph.sh runs it in a container on the compose network):
    NEO4J_URI=neo4j://neo4j-database:7687 python wordnet/load_wordnet_graph.py [--csv-dir DIR]
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase

HERE = Path(__file__).resolve().parent
LIST_SEP = "|"  # glosstag_to_graph.py joins list properties (terms, examples) with it

CONSTRAINTS = [
    # Same names and keys as wsd-entity-linker's graph, so the two databases share their indexes.
    "CREATE CONSTRAINT synset_id IF NOT EXISTS FOR (s:Synset) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT sense_id IF NOT EXISTS FOR (s:Sense) REQUIRE s.id IS UNIQUE",
    # neo4j_graphdb.py creates this too. It's needed here so adopting chunk senses is an index lookup.
    "CREATE CONSTRAINT sense_synset_id_unique IF NOT EXISTS FOR (s:Sense) REQUIRE s.synset_id IS UNIQUE",
]

# A chunk's Sense node for a WordNet synset becomes that Synset node.
ADOPT_CHUNK_SENSES = """
UNWIND $rows AS row
MATCH (s:Sense {synset_id: row.id})
WHERE NOT s:Synset
SET s:Synset, s.id = row.id
"""

MERGE_SYNSETS = """
UNWIND $rows AS row
MERGE (s:Synset {id: row.id})
SET s.pos = row.pos, s.offset = row.offset, s.terms = row.terms, s.gloss = row.gloss,
    s.definition = row.definition, s.examples = row.examples
"""

MERGE_SENSES = """
UNWIND $rows AS row
MERGE (s:Sense {id: row.id})
SET s.lemma = row.lemma, s.synset = row.synset
"""

MERGE_IN_SYNSET = """
UNWIND $rows AS row
MATCH (sense:Sense {id: row.start})
MATCH (synset:Synset {id: row.end})
MERGE (sense)-[:IN_SYNSET]->(synset)
"""

MERGE_GLOSS_LINKS = """
UNWIND $rows AS row
MATCH (synset:Synset {id: row.start})
MATCH (sense:Sense {id: row.end})
MERGE (synset)-[r:GLOSS_LINKS_TO {token: row.token}]->(sense)
SET r.text = row.text, r.lemma = row.lemma, r.section = row.section, r.tag = row.tag,
    r.kind = row.kind, r.position = row.position
"""


def text(value):
    """neo4j-admin import leaves empty fields out, so store them as no property, not ''."""
    return value or None


def split_list(value):
    return value.split(LIST_SEP) if value else None


def read_csv(path, row_to_params):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header, fixed by glosstag_to_graph.py
        for row in reader:
            yield row_to_params(row)


def synset_row(r):
    # id:ID, :LABEL, pos, offset, terms:string[], gloss, definition, examples:string[]
    return {"id": r[0], "pos": text(r[2]), "offset": text(r[3]), "terms": split_list(r[4]),
            "gloss": text(r[5]), "definition": text(r[6]), "examples": split_list(r[7])}


def sense_row(r):
    # id:ID, :LABEL, lemma, synset
    return {"id": r[0], "lemma": text(r[2]), "synset": text(r[3])}


def in_synset_row(r):
    # :START_ID, :END_ID, :TYPE
    return {"start": r[0], "end": r[1]}


def gloss_link_row(r):
    # :START_ID, :END_ID, :TYPE, token, text, lemma, section, tag, kind, position:int
    return {"start": r[0], "end": r[1], "token": r[3], "text": text(r[4]), "lemma": text(r[5]),
            "section": text(r[6]), "tag": text(r[7]), "kind": text(r[8]), "position": int(r[9])}


def batches(rows, size):
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def run_batched(driver, database, name, rows, queries, batch_size):
    """Run each query on every batch of rows, one write transaction per batch."""
    start, done = time.monotonic(), 0
    for batch in batches(rows, batch_size):
        def work(tx):
            for query in queries:
                tx.run(query, rows=batch).consume()
        with driver.session(database=database) as session:
            session.execute_write(work)
        done += len(batch)
        print(f"\r{name}: {done:,}", end="", file=sys.stderr, flush=True)
    print(f"\r{name}: {done:,} in {time.monotonic() - start:.0f}s", file=sys.stderr)
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--csv-dir", type=Path, default=HERE / "output" / "neo4j",
                        help="directory with glosstag_to_graph.py's CSVs (default: wordnet/output/neo4j)")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "neo4j"))
    args = parser.parse_args()

    uri, password = os.getenv("NEO4J_URI"), os.getenv("NEO4J_PASSWORD")
    if not uri or not password:
        sys.exit("NEO4J_URI and NEO4J_PASSWORD must be set.")
    csv_dir = args.csv_dir
    for name in ("synsets.csv", "senses.csv", "in_synset.csv", "gloss_links_to.csv"):
        if not (csv_dir / name).is_file():
            sys.exit(f"{csv_dir / name} not found. Build the CSVs first (scripts/load-wordnet-graph.sh does).")

    driver = GraphDatabase.driver(uri, auth=(os.getenv("NEO4J_USERNAME", "neo4j"), password),
                                  notifications_min_severity="WARNING")
    try:
        driver.verify_connectivity()
        with driver.session(database=args.database) as session:
            for query in CONSTRAINTS:
                session.run(query).consume()
            session.run("CALL db.awaitIndexes(300)").consume()

        n = args.batch_size
        run_batched(driver, args.database, "Synset nodes", read_csv(csv_dir / "synsets.csv", synset_row),
                    [ADOPT_CHUNK_SENSES, MERGE_SYNSETS], n)
        run_batched(driver, args.database, "Sense nodes", read_csv(csv_dir / "senses.csv", sense_row),
                    [MERGE_SENSES], n)
        run_batched(driver, args.database, "IN_SYNSET edges", read_csv(csv_dir / "in_synset.csv", in_synset_row),
                    [MERGE_IN_SYNSET], n)
        run_batched(driver, args.database, "GLOSS_LINKS_TO edges",
                    read_csv(csv_dir / "gloss_links_to.csv", gloss_link_row), [MERGE_GLOSS_LINKS], n)

        records, _, _ = driver.execute_query(
            """
            CALL () { MATCH (s:Synset) RETURN count(s) AS synsets }
            CALL () { MATCH (s:Sense) WHERE s.id IS NOT NULL AND NOT s:Synset RETURN count(s) AS senses }
            CALL () { MATCH (s:Synset) WHERE s.synset_id IS NOT NULL RETURN count(s) AS shared }
            CALL () { MATCH (c:Chunk) RETURN count(c) AS chunks }
            RETURN synsets, senses, shared, chunks
            """,
            database_=args.database,
        )
        print(f"In the graph now: {records[0].data()} "
              "(shared = Synset nodes that chunks mention)")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
