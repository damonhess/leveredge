#!/bin/bash
# Migrate DEV database with LCIS capture
# Usage: migrate-dev [up|down|version|force N]

ENV="dev"
DEV_PW=$(grep "POSTGRES_PASSWORD_URLENCODED" /opt/leveredge/data-plane/dev/supabase/.env | cut -d= -f2)
DATABASE_URL="postgres://postgres:${DEV_PW}@localhost:54323/postgres?sslmode=disable"

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
                \"severity\": \"low\",
                \"tags\": [\"auto-captured\", \"schema\", \"$ENV\", \"migration\"]
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
                \"severity\": \"high\",
                \"tags\": [\"auto-captured\", \"schema\", \"$ENV\", \"migration-failed\"]
            }" &>/dev/null &
        echo "[LCIS] Migration captured: $ENV v$VERSION (FAILED)"
    fi
fi

exit $EXIT_CODE
