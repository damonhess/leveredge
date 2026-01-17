#!/bin/bash
# promote-schema.sh - Promote schema changes from DEV to PROD Supabase
#
# Usage: promote-schema.sh [table_name]
#   No args: Compare all tables and show differences
#   table_name: Promote specific table DDL from DEV to PROD
#
# Architecture:
#   DEV:  supabase-db-dev (127.0.0.1:54323/postgres)
#   PROD: supabase-db-prod (127.0.0.1:54322/postgres)

set -e

DEV_CONTAINER="supabase-db-dev"
PROD_CONTAINER="supabase-db-prod"
DEV_DB="postgres"
PROD_DB="postgres"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_containers() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${DEV_CONTAINER}$"; then
        log_error "DEV container ${DEV_CONTAINER} not running"
        exit 1
    fi
    if ! docker ps --format '{{.Names}}' | grep -q "^${PROD_CONTAINER}$"; then
        log_error "PROD container ${PROD_CONTAINER} not running"
        exit 1
    fi
}

list_tables() {
    local container=$1
    local db=$2
    docker exec "$container" psql -U postgres -d "$db" -t -c \
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;" 2>/dev/null | tr -d ' '
}

compare_schemas() {
    log_info "Comparing DEV and PROD schemas..."

    DEV_TABLES=$(list_tables "$DEV_CONTAINER" "$DEV_DB")
    PROD_TABLES=$(list_tables "$PROD_CONTAINER" "$PROD_DB")

    echo ""
    echo "=== Tables in DEV but not in PROD ==="
    comm -23 <(echo "$DEV_TABLES" | sort) <(echo "$PROD_TABLES" | sort) | while read table; do
        [ -n "$table" ] && echo "  + $table"
    done

    echo ""
    echo "=== Tables in PROD but not in DEV ==="
    comm -13 <(echo "$DEV_TABLES" | sort) <(echo "$PROD_TABLES" | sort) | while read table; do
        [ -n "$table" ] && echo "  - $table"
    done

    echo ""
    log_info "To promote a table: $0 <table_name>"
}

promote_table() {
    local table=$1

    log_info "Promoting table '$table' from DEV to PROD..."

    # Check table exists in DEV
    if ! docker exec "$DEV_CONTAINER" psql -U postgres -d "$DEV_DB" -t -c \
        "SELECT 1 FROM information_schema.tables WHERE table_name = '$table';" 2>/dev/null | grep -q 1; then
        log_error "Table '$table' not found in DEV"
        exit 1
    fi

    # Check if table already exists in PROD
    if docker exec "$PROD_CONTAINER" psql -U postgres -d "$PROD_DB" -t -c \
        "SELECT 1 FROM information_schema.tables WHERE table_name = '$table';" 2>/dev/null | grep -q 1; then
        log_warn "Table '$table' already exists in PROD"
        read -p "Overwrite? This will DROP and recreate the table (y/N): " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_info "Aborted"
            exit 0
        fi
        docker exec "$PROD_CONTAINER" psql -U postgres -d "$PROD_DB" -c "DROP TABLE IF EXISTS $table CASCADE;" 2>/dev/null
    fi

    # Export DDL from DEV
    log_info "Exporting DDL from DEV..."
    docker exec "$DEV_CONTAINER" pg_dump -U postgres -d "$DEV_DB" \
        --schema-only --no-owner --no-acl -t "$table" > /tmp/promote_${table}.sql 2>/dev/null

    # Import to PROD
    log_info "Importing DDL to PROD..."
    docker cp /tmp/promote_${table}.sql "$PROD_CONTAINER":/tmp/
    docker exec "$PROD_CONTAINER" psql -U postgres -d "$PROD_DB" -f /tmp/promote_${table}.sql 2>&1

    # Cleanup
    rm -f /tmp/promote_${table}.sql

    log_info "Table '$table' promoted successfully"
}

# Main
check_containers

if [ -z "$1" ]; then
    compare_schemas
else
    promote_table "$1"
fi
