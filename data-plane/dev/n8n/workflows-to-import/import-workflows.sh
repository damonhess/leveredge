#!/bin/bash
# Import coaching tool workflows into DEV n8n

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_CONTAINER="dev-n8n-postgres"
DB_NAME="n8n_dev"
DB_USER="n8n"

echo "Importing coaching workflows into DEV n8n..."

for workflow_file in "$SCRIPT_DIR"/*.json; do
    if [[ -f "$workflow_file" ]]; then
        filename=$(basename "$workflow_file")
        echo "Processing: $filename"

        # Read workflow JSON and extract name
        workflow_name=$(jq -r '.name' "$workflow_file")

        # Check if workflow already exists
        existing=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT id FROM workflow_entity WHERE name = '$workflow_name' LIMIT 1" 2>/dev/null || echo "")

        if [[ -n "$existing" ]]; then
            echo "  -> Workflow '$workflow_name' already exists (ID: $existing), skipping..."
            continue
        fi

        # Generate a unique ID
        workflow_id=$(cat /proc/sys/kernel/random/uuid | tr -d '-' | head -c 16)

        # Extract workflow components
        nodes=$(jq -c '.nodes' "$workflow_file")
        connections=$(jq -c '.connections' "$workflow_file")
        settings=$(jq -c '.settings // {}' "$workflow_file")
        active=$(jq -r '.active // false' "$workflow_file")

        # Escape single quotes for SQL
        nodes_escaped=$(echo "$nodes" | sed "s/'/''/g")
        connections_escaped=$(echo "$connections" | sed "s/'/''/g")
        settings_escaped=$(echo "$settings" | sed "s/'/''/g")
        workflow_name_escaped=$(echo "$workflow_name" | sed "s/'/''/g")

        # Insert workflow
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" <<EOSQL
INSERT INTO workflow_entity (
    id, name, active, nodes, connections, settings, "createdAt", "updatedAt", "triggerCount"
) VALUES (
    '$workflow_id',
    '$workflow_name_escaped',
    $active,
    '$nodes_escaped'::jsonb,
    '$connections_escaped'::jsonb,
    '$settings_escaped'::jsonb,
    NOW(),
    NOW(),
    0
);
EOSQL

        if [[ $? -eq 0 ]]; then
            echo "  -> Imported '$workflow_name' with ID: $workflow_id"
        else
            echo "  -> FAILED to import '$workflow_name'"
        fi
    fi
done

echo ""
echo "Import complete! Verifying..."

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT id, name, active FROM workflow_entity WHERE name LIKE '%Wheel%' OR name LIKE '%Values%' OR name LIKE '%Progress%' OR name LIKE '%Goal%' ORDER BY name;"
