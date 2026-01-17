#!/bin/bash
# Import coaching tool workflows into DEV n8n - V2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_CONTAINER="dev-n8n-postgres"
DB_NAME="n8n_dev"
DB_USER="n8n"

echo "Importing coaching workflows into DEV n8n..."

for workflow_file in "$SCRIPT_DIR"/1*.json "$SCRIPT_DIR"/2*.json; do
    if [[ -f "$workflow_file" ]]; then
        filename=$(basename "$workflow_file")
        echo "Processing: $filename"

        # Read workflow JSON
        workflow_name=$(jq -r '.name' "$workflow_file")

        # Check if workflow already exists
        existing=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT id FROM workflow_entity WHERE name = '$workflow_name' LIMIT 1" 2>/dev/null || echo "")

        if [[ -n "$existing" && "$existing" != "" ]]; then
            echo "  -> Workflow '$workflow_name' already exists (ID: $existing), skipping..."
            continue
        fi

        # Generate unique IDs
        workflow_id=$(uuidgen | tr -d '-' | head -c 16)
        version_id=$(uuidgen)

        # Create temp file with the workflow data
        tmp_file=$(mktemp)
        cat "$workflow_file" > "$tmp_file"

        # Use psql with proper escaping via \copy
        docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" <<EOSQL
INSERT INTO workflow_entity (
    id,
    name,
    active,
    nodes,
    connections,
    settings,
    "versionId",
    "triggerCount",
    "createdAt",
    "updatedAt"
)
SELECT
    '$workflow_id',
    workflow_data->>'name',
    (workflow_data->>'active')::boolean,
    (workflow_data->'nodes')::json,
    (workflow_data->'connections')::json,
    COALESCE((workflow_data->'settings')::json, '{}'::json),
    '$version_id',
    0,
    NOW(),
    NOW()
FROM (
    SELECT '$(cat "$workflow_file" | jq -c . | sed "s/'/''/g")'::jsonb as workflow_data
) t;
EOSQL

        result=$?
        rm -f "$tmp_file"

        if [[ $result -eq 0 ]]; then
            echo "  -> Imported '$workflow_name' with ID: $workflow_id"
        else
            echo "  -> FAILED to import '$workflow_name'"
        fi
    fi
done

echo ""
echo "Import complete! Verifying..."

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT id, name, active FROM workflow_entity WHERE name LIKE '17%' OR name LIKE '18%' OR name LIKE '19%' OR name LIKE '20%' ORDER BY name;"
