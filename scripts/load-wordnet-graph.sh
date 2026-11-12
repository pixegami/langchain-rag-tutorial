#!/usr/bin/env bash
# Pull the WordNet glosstag dataset with DVC, build its graph CSVs, and MERGE them into the
# Neo4j that the devpod workspace runs (container neo4j-database), keeping the data already there.
# It builds the same graph that wsd-entity-linker serves on port 7688. See wordnet/load_wordnet_graph.py.
#
# Run it on your machine, from anywhere in the repo, with the workspace up (`devpod up .`).
# DVC needs Google credentials: `gcloud auth application-default login`.
#
#   scripts/load-wordnet-graph.sh            # pull, build if needed, load
#   REBUILD=1 scripts/load-wordnet-graph.sh  # rebuild the CSVs too
set -euo pipefail

cd "$(dirname "$0")/.."
NEO4J_CONTAINER=${NEO4J_CONTAINER:-neo4j-database}   # container_name in docker-compose.yml
PYTHON_IMAGE=python:3.11-slim                        # the app image's Python (Dockerfile)
W=wordnet

[ -f .env ] || { echo "error: .env missing (see .env.example)" >&2; exit 1; }
set -a; . ./.env; set +a
: "${NEO4J_PASSWORD:?Set NEO4J_PASSWORD in .env}"

if [ "$(docker inspect -f '{{.State.Running}}' "$NEO4J_CONTAINER" 2>/dev/null)" != "true" ]; then
    echo "error: Neo4j container '$NEO4J_CONTAINER' isn't running. Start the workspace with 'devpod up .'" >&2
    exit 1
fi
# The loader joins Neo4j's network. DevPod renames the compose network (e.g. default-la-e1621_docker),
# so read it from the container rather than from docker-compose.yml.
NETWORK=${NETWORK:-$(docker inspect -f '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}} {{end}}' "$NEO4J_CONTAINER" | awk '{print $1}')}

echo "=== 1/3 Pulling the dataset with DVC"
command -v dvc >/dev/null || { echo "error: dvc not found. Install it: pipx install \"dvc[gs]~=3.67\"" >&2; exit 1; }
dvc pull "$W/merged_with_tag_un_annotated_haiku.dvc" "$W/common-senses.json.dvc"

echo "=== 2/3 Building the graph CSVs"
if [ -f "$W/output/neo4j/gloss_links_to.csv" ] && [ -z "${REBUILD:-}" ]; then
    echo "already built in $W/output/neo4j, skipping (REBUILD=1 to rebuild)"
else
    # Written to a temporary folder first, so a failed build leaves nothing behind.
    # The GraphML copy isn't loaded, so it's deleted.
    rm -rf "$W/output.tmp"
    docker run --rm -v "$PWD:/app" -w /app "$PYTHON_IMAGE" \
        python "$W/glosstag_to_graph.py" --merged "$W/data/merged_with_tag_un_annotated_haiku" \
        --ignore-senses "$W/data/common-senses.json" --out "$W/output.tmp"
    rm "$W/output.tmp/wordnet-glosstag.graphml"
    rm -rf "$W/output" && mv "$W/output.tmp" "$W/output"
fi

echo "=== 3/3 Loading into $NEO4J_CONTAINER (MERGE, existing data is kept)"
docker run --rm --network "$NETWORK" -v "$PWD:/app" -w /app \
    -e NEO4J_URI="neo4j://$NEO4J_CONTAINER:7687" \
    -e NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}" -e NEO4J_PASSWORD \
    -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore \
    "$PYTHON_IMAGE" sh -c 'pip install -q "neo4j==6.4.1" && python wordnet/load_wordnet_graph.py'

echo "=== Done"
