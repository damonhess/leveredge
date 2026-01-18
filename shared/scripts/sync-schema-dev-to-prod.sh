#!/bin/bash
# sync-schema-dev-to-prod.sh
# Automatically sync schema from DEV to PROD (runs nightly)
# Only syncs STRUCTURE, never data

set -e

LOG_FILE="/opt/leveredge/logs/schema-sync.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

DEV_CONTAINER="supabase-db-dev"
PROD_CONTAINER="supabase-db-prod"

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

mkdir -p /opt/leveredge/logs

log "Starting schema sync DEV → PROD"

# Check containers running
if ! docker ps --format '{{.Names}}' | grep -q "^${DEV_CONTAINER}$"; then
    log "ERROR: DEV container not running"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${PROD_CONTAINER}$"; then
    log "ERROR: PROD container not running"
    exit 1
fi

# Export DEV schema (structure only, no data)
log "Exporting DEV schema..."
docker exec "$DEV_CONTAINER" pg_dump -U postgres -d postgres \
    --schema-only \
    --no-owner \
    --no-acl \
    --no-comments \
    -n public \
    > /tmp/dev_schema.sql 2>/dev/null

# Count objects
TABLES=$(grep -c "CREATE TABLE" /tmp/dev_schema.sql || echo 0)
INDEXES=$(grep -c "CREATE INDEX" /tmp/dev_schema.sql || echo 0)
log "DEV has $TABLES tables, $INDEXES indexes"

# Get list of tables in DEV
DEV_TABLES=$(docker exec "$DEV_CONTAINER" psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;" 2>/dev/null | tr -d ' ' | grep -v '^$')

# Get list of tables in PROD
PROD_TABLES=$(docker exec "$PROD_CONTAINER" psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;" 2>/dev/null | tr -d ' ' | grep -v '^$')

# Find tables in DEV but not in PROD
MISSING_TABLES=$(comm -23 <(echo "$DEV_TABLES" | sort) <(echo "$PROD_TABLES" | sort))

if [ -z "$MISSING_TABLES" ]; then
    log "All DEV tables exist in PROD - schemas in sync"
else
    log "Tables missing from PROD: $MISSING_TABLES"
    
    # Promote each missing table
    for table in $MISSING_TABLES; do
        log "Promoting table: $table"
        
        # Export single table DDL
        docker exec "$DEV_CONTAINER" pg_dump -U postgres -d postgres \
            --schema-only --no-owner --no-acl -t "$table" > /tmp/promote_${table}.sql 2>/dev/null
        
        # Import to PROD
        docker cp /tmp/promote_${table}.sql "$PROD_CONTAINER":/tmp/
        docker exec "$PROD_CONTAINER" psql -U postgres -d postgres -f /tmp/promote_${table}.sql 2>&1 | tee -a "$LOG_FILE"
        
        rm -f /tmp/promote_${table}.sql
        log "Promoted: $table"
    done
fi

# Clean up
rm -f /tmp/dev_schema.sql

log "Schema sync complete"

# Optional: Notify HERMES
if [ -n "$MISSING_TABLES" ]; then
    curl -s -X POST http://localhost:8014/notify \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"telegram\", \"message\": \"🔄 Schema sync: Promoted tables to PROD: $MISSING_TABLES\", \"priority\": \"low\"}" || true
fi
