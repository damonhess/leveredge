#!/bin/bash
#
# run-migrations.sh - Migration runner for Supabase databases
#
# Tracks and applies SQL migrations from a directory to target database.
# Uses a apollo_migrations table to track what's been applied.
#
# Usage:
#   ./run-migrations.sh dev                    # Run on DEV
#   ./run-migrations.sh prod                   # Run on PROD
#   ./run-migrations.sh prod --dry-run         # Show what would run on PROD
#   ./run-migrations.sh prod --status          # Show migration status
#
# Created: 2026-01-20

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="/opt/leveredge/data-plane/dev/supabase/migrations"

# Database containers
DEV_CONTAINER="supabase-db-dev"
PROD_CONTAINER="supabase-db-prod"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# ARGUMENTS
# ============================================================================

ENV="${1:-}"
DRY_RUN=false
STATUS_ONLY=false

shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --status) STATUS_ONLY=true; shift ;;
        -h|--help)
            echo "Usage: $0 <dev|prod> [--dry-run] [--status]"
            echo ""
            echo "Arguments:"
            echo "  dev|prod     Target environment"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be run without applying"
            echo "  --status     Show migration status only"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$ENV" ]]; then
    echo "Usage: $0 <dev|prod> [--dry-run] [--status]"
    exit 1
fi

# Set container based on environment
if [[ "$ENV" == "dev" ]]; then
    CONTAINER="$DEV_CONTAINER"
elif [[ "$ENV" == "prod" ]]; then
    CONTAINER="$PROD_CONTAINER"
else
    log_error "Unknown environment: $ENV (use 'dev' or 'prod')"
    exit 1
fi

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

run_sql() {
    local sql="$1"
    docker exec "$CONTAINER" psql -U postgres -d postgres -t -c "$sql" 2>/dev/null | tr -d ' \t'
}

run_sql_file() {
    local file="$1"
    docker exec -i "$CONTAINER" psql -U postgres -d postgres < "$file" 2>&1
}

# ============================================================================
# ENSURE MIGRATIONS TABLE EXISTS
# ============================================================================

ensure_migrations_table() {
    log_info "Ensuring apollo_migrations table exists..."

    docker exec "$CONTAINER" psql -U postgres -d postgres -c "
        CREATE TABLE IF NOT EXISTS apollo_migrations (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMPTZ DEFAULT NOW(),
            checksum VARCHAR(64),
            applied_by VARCHAR(100) DEFAULT 'apollo'
        );

        CREATE INDEX IF NOT EXISTS idx_apollo_migrations_filename
            ON apollo_migrations(filename);

        COMMENT ON TABLE apollo_migrations IS
            'Tracks applied database migrations - managed by Apollo deployment system';
    " &>/dev/null || true

    log_ok "Migration tracking table ready"
}

# ============================================================================
# GET MIGRATION STATUS
# ============================================================================

get_applied_migrations() {
    run_sql "SELECT filename FROM apollo_migrations ORDER BY filename;"
}

get_pending_migrations() {
    local applied
    applied=$(get_applied_migrations) || applied=""

    local pending=()
    for file in "$MIGRATIONS_DIR"/*.sql; do
        [[ ! -f "$file" ]] && continue
        local fname=$(basename "$file")
        if [[ -z "$applied" ]] || ! echo "$applied" | grep -q "^${fname}$"; then
            pending+=("$fname")
        fi
    done

    # Sort by filename (which starts with timestamp)
    if [[ ${#pending[@]} -gt 0 ]]; then
        printf '%s\n' "${pending[@]}" | sort
    fi
}

show_status() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "MIGRATION STATUS: $ENV"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    echo "Applied migrations:"
    local applied
    applied=$(docker exec "$CONTAINER" psql -U postgres -d postgres -t -c "
        SELECT filename || ' (' || to_char(applied_at, 'YYYY-MM-DD HH24:MI') || ')'
        FROM apollo_migrations
        ORDER BY filename;
    " 2>/dev/null)

    if [[ -z "$applied" || "$applied" =~ ^[[:space:]]*$ ]]; then
        echo "  (none)"
    else
        echo "$applied" | sed 's/^/  /'
    fi

    echo ""
    echo "Pending migrations:"
    local pending
    pending=$(get_pending_migrations)

    if [[ -z "$pending" ]]; then
        echo "  (none - all migrations applied)"
    else
        echo "$pending" | sed 's/^/  /'
    fi

    echo ""
}

# ============================================================================
# RUN MIGRATIONS
# ============================================================================

run_migrations() {
    local pending
    pending=$(get_pending_migrations)

    if [[ -z "$pending" ]]; then
        log_ok "No pending migrations for $ENV"
        return 0
    fi

    local count=$(echo "$pending" | wc -l | tr -d ' ')
    log_info "Found $count pending migration(s) for $ENV"

    if $DRY_RUN; then
        echo ""
        echo "DRY RUN - Would apply these migrations:"
        echo "$pending" | sed 's/^/  /'
        echo ""
        return 0
    fi

    local applied=0
    local failed=0

    while IFS= read -r migration; do
        [[ -z "$migration" ]] && continue

        local filepath="$MIGRATIONS_DIR/$migration"

        if [[ ! -f "$filepath" ]]; then
            log_error "Migration file not found: $filepath"
            ((failed++))
            continue
        fi

        log_info "Applying: $migration"

        # Calculate checksum
        local checksum=$(sha256sum "$filepath" | cut -d' ' -f1)

        # Apply migration
        local output
        if output=$(run_sql_file "$filepath" 2>&1); then
            # Record in migrations table
            docker exec "$CONTAINER" psql -U postgres -d postgres -c "
                INSERT INTO apollo_migrations (filename, checksum, applied_by)
                VALUES ('$migration', '$checksum', 'apollo')
                ON CONFLICT (filename) DO NOTHING;
            " &>/dev/null

            log_ok "Applied: $migration"
            ((applied++)) || true
        else
            log_error "Failed: $migration"
            echo "$output" | head -20
            ((failed++)) || true

            # Stop on first failure
            log_error "Stopping migration run due to failure"
            break
        fi
    done <<< "$pending"

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "MIGRATION SUMMARY: $ENV"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Applied: $applied"
    echo "  Failed:  $failed"
    echo ""

    if [[ $failed -gt 0 ]]; then
        return 1
    fi
    return 0
}

# ============================================================================
# MAIN
# ============================================================================

# Check container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    log_error "Container $CONTAINER is not running"
    exit 1
fi

# Check migrations directory
if [[ ! -d "$MIGRATIONS_DIR" ]]; then
    log_error "Migrations directory not found: $MIGRATIONS_DIR"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              APOLLO MIGRATION RUNNER                          ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
printf "║  Environment: %-47s ║\n" "$ENV"
printf "║  Container:   %-47s ║\n" "$CONTAINER"
printf "║  Migrations:  %-47s ║\n" "$MIGRATIONS_DIR"
if $DRY_RUN; then
printf "║  Mode:        %-47s ║\n" "DRY RUN"
fi
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

ensure_migrations_table

if $STATUS_ONLY; then
    show_status
    exit 0
fi

run_migrations
exit_code=$?

# Report to LCIS
if [[ $exit_code -eq 0 ]]; then
    curl -s -X POST http://localhost:8050/ingest \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"success\",
            \"source_agent\": \"APOLLO\",
            \"title\": \"Migrations applied to $ENV\",
            \"content\": \"Successfully ran migrations on $ENV database\",
            \"domain\": \"DEPLOYMENT\",
            \"tags\": [\"migration\", \"database\", \"$ENV\"]
        }" &>/dev/null || true
fi

exit $exit_code
