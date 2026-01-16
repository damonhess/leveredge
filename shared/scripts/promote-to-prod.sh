#!/bin/bash
set -e

WORKFLOW_ID=$1

if [ -z "$WORKFLOW_ID" ]; then
    echo "Usage: promote-to-prod.sh <workflow_id>"
    exit 1
fi

# Load environment if .env exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

DEV_API="http://localhost:5680/api/v1"
PROD_API="http://localhost:5678/api/v1"
DEV_KEY="${N8N_DEV_API_KEY}"
PROD_KEY="${N8N_PROD_API_KEY}"

# Validate API keys
if [ -z "$DEV_KEY" ]; then
    echo "ERROR: N8N_DEV_API_KEY not set"
    echo "Set in environment or $SCRIPT_DIR/.env"
    exit 1
fi

if [ -z "$PROD_KEY" ]; then
    echo "ERROR: N8N_PROD_API_KEY not set"
    echo "Set in environment or $SCRIPT_DIR/.env"
    exit 1
fi

echo "=== PROMOTE WORKFLOW: $WORKFLOW_ID ==="

# 1. Backup via CHRONOS
echo "[1/5] Creating backup..."
curl -s -X POST http://localhost:8010/backup \
    -H "Content-Type: application/json" \
    -d '{"name":"pre-promote-'$WORKFLOW_ID'","type":"pre-deploy"}' | jq .

# 2. Export from DEV
echo "[2/5] Exporting from DEV..."
curl -s "$DEV_API/workflows/$WORKFLOW_ID" \
    -H "X-N8N-API-KEY: $DEV_KEY" > /tmp/workflow_export.json

if [ ! -s /tmp/workflow_export.json ]; then
    echo "ERROR: Failed to export workflow from DEV"
    exit 1
fi

WORKFLOW_NAME=$(jq -r '.name' /tmp/workflow_export.json)
echo "    Workflow: $WORKFLOW_NAME"

# 3. Check if exists in PROD
echo "[3/5] Checking PROD..."
PROD_EXISTS=$(curl -s "$PROD_API/workflows/$WORKFLOW_ID" \
    -H "X-N8N-API-KEY: $PROD_KEY" | jq -r '.id // empty')

# 4. Import/Update in PROD
if [ -n "$PROD_EXISTS" ]; then
    echo "[4/5] Updating existing workflow in PROD..."
    curl -s -X PUT "$PROD_API/workflows/$WORKFLOW_ID" \
        -H "X-N8N-API-KEY: $PROD_KEY" \
        -H "Content-Type: application/json" \
        -d @/tmp/workflow_export.json | jq '.id'
else
    echo "[4/5] Creating new workflow in PROD..."
    curl -s -X POST "$PROD_API/workflows" \
        -H "X-N8N-API-KEY: $PROD_KEY" \
        -H "Content-Type: application/json" \
        -d @/tmp/workflow_export.json | jq '.id'
fi

# 5. Activate in PROD
echo "[5/5] Activating in PROD..."
curl -s -X POST "$PROD_API/workflows/$WORKFLOW_ID/activate" \
    -H "X-N8N-API-KEY: $PROD_KEY" | jq '.active'

echo ""
echo "=== PROMOTION COMPLETE ==="
echo "Workflow: $WORKFLOW_NAME"
echo "ID: $WORKFLOW_ID"
echo "Backup created via CHRONOS"

# Cleanup
rm -f /tmp/workflow_export.json
