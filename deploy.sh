#!/usr/bin/env bash
set -e

echo "=== 🚀 Deploying Application ==="

# Check for .env file
if [ ! -f .env ]; then
    echo "❌ Error: .env file missing."
    exit 1
fi

# Ensure the external Traefik network exists
docker network inspect docker >/dev/null 2>&1 || docker network create docker
# Build and start services
docker compose up --build -d

echo "=== ✅ Deployment Complete ==="