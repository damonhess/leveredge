#!/bin/bash
# Migrate PROD database with LCIS capture
# Usage: migrate-prod [up|down|version|force N]
#
# WARNING: This affects production data. Always backup first!

ENV="prod"
PROD_PW=$(grep "POSTGRES_PASSWORD_URLENCODED" /opt/leveredge/data-plane/prod/supabase/.env | cut -d= -f2)
DATABASE_URL="postgres://postgres:${PROD_PW}@localhost:54322/postgres?sslmode=disable"

export PATH=$HOME/bin:$PATH

# Run migration and capture output
RESULT=$(migrate -path /opt/leveredge/migrations -database "$DATABASE_URL" "$@" 2>&1)
EXIT_CODE=$?

# Display result
echo "$RESULT"

# Get current version
VERSION=$(migrate -path /opt/leveredge/migrations -database "$DATABASE_URL" version 2>&1 | grep -oE '[0-9]+' | head -1)
VERSION=${VERSION:-"unknown"}

# Report to LCIS (only for up/down operations, not version checks)
if [[ "$1" == "up" || "$1" == "down" ]]; then
    # Escape for JSON
    RESULT_ESCAPED=$(echo "$RESULT" | head -20 | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/\\"/g')

    if [[ $EXIT_CODE -eq 0 ]]; then
        curl -s -X POST http://localhost:8050/ingest \
            -H "Content-Type: application/json" \
            -d "{
                \"type\": \"success\",
                \"source_agent\": \"SCHEMA_WATCHER\",
                \"title\": \"Schema migration $ENV: version $VERSION\",
                \"content\": \"Migration applied successfully.\\n\\nCommand: migrate $@\\nOutput:\\n$RESULT_ESCAPED\",
                \"domain\": \"SCHEMA\",
                \"severity\": \"medium\",
                \"tags\": [\"auto-captured\", \"schema\", \"$ENV\", \"migration\", \"production\"]
            }" &>/dev/null &
        echo "[LCIS] Migration captured: $ENV v$VERSION (success)"
    else
        curl -s -X POST http://localhost:8050/ingest \
            -H "Content-Type: application/json" \
            -d "{
                \"type\": \"failure\",
                \"source_agent\": \"SCHEMA_WATCHER\",
                \"title\": \"Schema migration FAILED $ENV: version $VERSION\",
                \"content\": \"Migration failed!\\n\\nCommand: migrate $@\\nError:\\n$RESULT_ESCAPED\",
                \"domain\": \"SCHEMA\",
                \"severity\": \"critical\",
                \"tags\": [\"auto-captured\", \"schema\", \"$ENV\", \"migration-failed\", \"production\"]
            }" &>/dev/null &
        echo "[LCIS] Migration captured: $ENV v$VERSION (FAILED)"
    fi
fi

exit $EXIT_CODE
