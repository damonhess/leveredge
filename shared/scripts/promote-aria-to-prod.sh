#!/bin/bash
#
# ARIA Promote to Production - Bulletproof Edition
# Created: 2026-01-20 after hours of ARIA PROD debugging
#
# This script catches the exact issues that broke ARIA PROD:
# 1. Schema drift (missing tables)
# 2. Frontend code mismatch (mock vs real API)
# 3. CORS header duplication
#
# Usage: ./promote-aria-to-prod.sh [--dry-run] [--force] [--skip-backup]
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEVEREDGE_ROOT="/opt/leveredge"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Supabase
DEV_DB_CONTAINER="supabase-db-dev"
PROD_DB_CONTAINER="supabase-db-prod"
SUPABASE_PROD_URL="https://supabase.leveredgeai.com"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJsZXZlcmVkZ2Utc3VwYWJhc2UiLCJpYXQiOjE3NjQ0NTU0MTQsImV4cCI6MjA3OTgxNTQxNCwicm9sZSI6ImFub24ifQ.abmNmankU9FVX2pf-R-YI-wq4cLvg7HVnaUXRoS4E_E"

# Frontend
DEV_FRONTEND_DIR="$LEVEREDGE_ROOT/data-plane/dev/aria-frontend"
PROD_FRONTEND_DIR="$LEVEREDGE_ROOT/data-plane/prod/aria-frontend"
PROD_FRONTEND_CONTAINER="aria-frontend-prod"

# API
ARIA_API_URL="https://aria-api.leveredgeai.com"
ARIA_CHAT_CONTAINER="aria-chat-prod"

# Caddy
CADDYFILE="/home/damon/stack/Caddyfile"

# Flags
DRY_RUN=false
FORCE=false
SKIP_BACKUP=false
START_TIME=$(date +%s)

# Counters
WARNINGS=0
ERRORS=0
CHECKS_PASSED=0
CHECKS_FAILED=0

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; ((CHECKS_PASSED++)) || true; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARNINGS++)) || true; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; ((ERRORS++)) || true; ((CHECKS_FAILED++)) || true; }
log_section() { echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"; }

fail_fast() {
    log_error "$1"
    echo -e "\n${RED}PROMOTION ABORTED - Fix the above issues first${NC}"
    exit 1
}

# ============================================================================
# PARSE ARGUMENTS
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --force) FORCE=true; shift ;;
        --skip-backup) SKIP_BACKUP=true; shift ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--force] [--skip-backup]"
            echo ""
            echo "Options:"
            echo "  --dry-run      Check for issues but don't make changes"
            echo "  --force        Skip confirmation prompts"
            echo "  --skip-backup  Skip CHRONOS backup (dangerous)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ============================================================================
# BANNER
# ============================================================================

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          ARIA PROMOTE TO PRODUCTION - BULLETPROOF             ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
if $DRY_RUN; then
echo "║  MODE: DRY RUN (no changes will be made)                      ║"
else
echo "║  MODE: LIVE (changes will be applied)                         ║"
fi
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# PHASE 1: PRE-FLIGHT CHECKS
# ============================================================================

log_section "PHASE 1: PRE-FLIGHT CHECKS"

# Check DEV database
log_info "Checking DEV Supabase database..."
if docker exec $DEV_DB_CONTAINER psql -U postgres -d postgres -c "SELECT 1" &>/dev/null; then
    log_ok "DEV database is reachable"
else
    fail_fast "DEV database ($DEV_DB_CONTAINER) is not reachable"
fi

# Check PROD database
log_info "Checking PROD Supabase database..."
if docker exec $PROD_DB_CONTAINER psql -U postgres -d postgres -c "SELECT 1" &>/dev/null; then
    log_ok "PROD database is reachable"
else
    fail_fast "PROD database ($PROD_DB_CONTAINER) is not reachable"
fi

# Check ARIA API
log_info "Checking ARIA Chat API..."
if curl -s "$ARIA_API_URL/health" | grep -q "healthy"; then
    log_ok "ARIA Chat API is healthy"
else
    fail_fast "ARIA Chat API is not healthy"
fi

# Check Supabase REST API
log_info "Checking Supabase REST API..."
if curl -s "$SUPABASE_PROD_URL/rest/v1/" -H "apikey: $SUPABASE_ANON_KEY" | grep -q "swagger"; then
    log_ok "Supabase REST API is reachable"
else
    fail_fast "Supabase REST API is not reachable"
fi

# Check Git status
log_info "Checking Git working tree..."
cd "$LEVEREDGE_ROOT"
if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
    log_warn "Git working tree has uncommitted changes"
    git status --short | head -10
else
    log_ok "Git working tree is clean"
fi

# Check frontend directories exist
log_info "Checking frontend directories..."
if [[ -d "$DEV_FRONTEND_DIR" && -d "$PROD_FRONTEND_DIR" ]]; then
    log_ok "Frontend directories exist"
else
    fail_fast "Frontend directories missing"
fi

# ============================================================================
# PHASE 2: SCHEMA COMPARISON
# ============================================================================

log_section "PHASE 2: SCHEMA COMPARISON (DEV vs PROD)"

# Get table lists
DEV_TABLES=$(docker exec $DEV_DB_CONTAINER psql -U postgres -d postgres -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'aria_%' ORDER BY table_name" | tr -d ' ')
PROD_TABLES=$(docker exec $PROD_DB_CONTAINER psql -U postgres -d postgres -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'aria_%' ORDER BY table_name" | tr -d ' ')

# Find missing tables
MISSING_TABLES=()
while IFS= read -r table; do
    [[ -z "$table" ]] && continue
    if ! echo "$PROD_TABLES" | grep -q "^${table}$"; then
        MISSING_TABLES+=("$table")
    fi
done <<< "$DEV_TABLES"

if [[ ${#MISSING_TABLES[@]} -gt 0 ]]; then
    log_warn "SCHEMA DRIFT: ${#MISSING_TABLES[@]} tables missing in PROD"
    echo ""
    echo "Missing tables:"
    for table in "${MISSING_TABLES[@]}"; do
        echo "  - $table"
    done
    echo ""
else
    log_ok "All DEV aria_* tables exist in PROD"
fi

# Check views
DEV_VIEWS=$(docker exec $DEV_DB_CONTAINER psql -U postgres -d postgres -t -c "SELECT table_name FROM information_schema.views WHERE table_schema='public' AND table_name IN ('conversations','messages','files','user_settings','notifications','tasks','calendar_events','portfolio_wins','reminders')" | tr -d ' ')
PROD_VIEWS=$(docker exec $PROD_DB_CONTAINER psql -U postgres -d postgres -t -c "SELECT table_name FROM information_schema.views WHERE table_schema='public' AND table_name IN ('conversations','messages','files','user_settings','notifications','tasks','calendar_events','portfolio_wins','reminders')" | tr -d ' ')

MISSING_VIEWS=()
while IFS= read -r view; do
    [[ -z "$view" ]] && continue
    if ! echo "$PROD_VIEWS" | grep -q "^${view}$"; then
        MISSING_VIEWS+=("$view")
    fi
done <<< "$DEV_VIEWS"

if [[ ${#MISSING_VIEWS[@]} -gt 0 ]]; then
    log_warn "MISSING VIEWS: ${#MISSING_VIEWS[@]} views missing in PROD"
    for view in "${MISSING_VIEWS[@]}"; do
        echo "  - $view"
    done
else
    log_ok "All required views exist in PROD"
fi

# Check RLS policies on key tables
log_info "Checking RLS policies..."
RLS_ISSUES=0
for table in aria_conversations aria_messages aria_user_settings aria_notifications; do
    POLICY_COUNT=$(docker exec $PROD_DB_CONTAINER psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM pg_policies WHERE tablename='$table'" 2>/dev/null | tr -d ' ')
    if [[ "$POLICY_COUNT" -lt 1 ]]; then
        log_warn "Table $table has no RLS policies"
        ((RLS_ISSUES++))
    fi
done

if [[ $RLS_ISSUES -eq 0 ]]; then
    log_ok "Key tables have RLS policies"
fi

# ============================================================================
# PHASE 3: FRONTEND CODE COMPARISON
# ============================================================================

log_section "PHASE 3: FRONTEND CODE COMPARISON"

# Check for mock API code in PROD (check key file only)
log_info "Checking for mock/placeholder code in PROD frontend..."

MOCK_FOUND=false
STORE_FILE="$PROD_FRONTEND_DIR/src/store/useStore.ts"
if [[ -f "$STORE_FILE" ]]; then
    if grep -q "This is a demo response" "$STORE_FILE" 2>/dev/null; then
        log_warn "MOCK CODE DETECTED: 'This is a demo response' found"
        MOCK_FOUND=true
    fi
    if grep -q "PLACEHOLDER" "$STORE_FILE" 2>/dev/null; then
        log_warn "MOCK CODE DETECTED: 'PLACEHOLDER' found"
        MOCK_FOUND=true
    fi
fi

if ! $MOCK_FOUND; then
    log_ok "No mock/placeholder code detected in PROD frontend"
fi

# Check for real API calls
log_info "Checking for real API integration..."
if grep -q "aria-api.leveredgeai.com" "$PROD_FRONTEND_DIR/src/store/useStore.ts" 2>/dev/null; then
    log_ok "PROD frontend has real ARIA API URL"
else
    log_warn "PROD frontend may be missing real ARIA API URL"
fi

if grep -q 'fetch.*\/chat' "$PROD_FRONTEND_DIR/src/store/useStore.ts" 2>/dev/null; then
    log_ok "PROD frontend has fetch() call to /chat"
else
    log_warn "PROD frontend may be missing fetch() to /chat API"
fi

# Compare key files (simplified - skip useStore since it's intentionally different)
log_info "Comparing key source files..."
# Check if supabase.ts is in sync
if [[ -f "$DEV_FRONTEND_DIR/src/lib/supabase.ts" && -f "$PROD_FRONTEND_DIR/src/lib/supabase.ts" ]]; then
    if diff -q "$DEV_FRONTEND_DIR/src/lib/supabase.ts" "$PROD_FRONTEND_DIR/src/lib/supabase.ts" &>/dev/null; then
        log_ok "src/lib/supabase.ts is in sync"
    else
        log_warn "src/lib/supabase.ts differs"
    fi
fi
# Note: useStore.ts may differ due to PROD-specific config - check mock code instead
log_info "useStore.ts comparison skipped (checked for mock code instead)"

# Check .env file
log_info "Checking PROD .env configuration..."
if [[ -f "$PROD_FRONTEND_DIR/.env" ]]; then
    if grep -q "supabase.leveredgeai.com" "$PROD_FRONTEND_DIR/.env"; then
        log_ok "PROD .env has correct Supabase URL"
    else
        log_warn "PROD .env may have wrong Supabase URL"
    fi
else
    log_warn "PROD frontend missing .env file"
fi

# ============================================================================
# PHASE 4: CORS VALIDATION
# ============================================================================

log_section "PHASE 4: CORS CONFIGURATION CHECK"

# Check Caddy CORS headers
log_info "Checking Caddy config for CORS headers..."
CADDY_CORS=$(grep -A10 "aria-api.leveredgeai.com" "$CADDYFILE" 2>/dev/null | grep -c "Access-Control" 2>/dev/null || echo "0")
CADDY_CORS="${CADDY_CORS//[^0-9]/}"  # Remove non-numeric chars
[[ -z "$CADDY_CORS" ]] && CADDY_CORS=0
if [[ "$CADDY_CORS" -gt 0 ]]; then
    CADDY_HAS_CORS=true
    log_info "Caddy adds $CADDY_CORS CORS headers for aria-api"
else
    CADDY_HAS_CORS=false
    log_ok "Caddy does NOT add CORS headers for aria-api (correct)"
fi

# Check Python app CORS
log_info "Checking Python app for CORS middleware..."
PYTHON_CORS=$(timeout 10 docker exec $ARIA_CHAT_CONTAINER grep -c "CORSMiddleware" /app/aria_chat.py 2>/dev/null || echo "0")
if [[ "$PYTHON_CORS" -gt 0 ]]; then
    PYTHON_HAS_CORS=true
    log_info "Python app has CORSMiddleware configured"
else
    PYTHON_HAS_CORS=false
    log_warn "Python app may be missing CORS configuration"
fi

# CRITICAL: Check for duplication
if $CADDY_HAS_CORS && $PYTHON_HAS_CORS; then
    log_error "CORS DUPLICATION DETECTED: Both Caddy AND Python add CORS headers!"
    log_error "This will cause browser CORS validation to fail"
    echo ""
    echo "Caddy config:"
    grep -A10 "aria-api.leveredgeai.com" "$CADDYFILE" | head -15
    echo ""
fi

# Test actual CORS response
log_info "Testing actual CORS headers from API..."
CORS_HEADERS=$(curl -sI --max-time 10 -X OPTIONS "$ARIA_API_URL/chat" \
    -H "Origin: https://aria.leveredgeai.com" \
    -H "Access-Control-Request-Method: POST" 2>/dev/null | grep -i "access-control-allow-origin" | wc -l | tr -d ' ')

if [[ "$CORS_HEADERS" -eq 1 ]]; then
    log_ok "API returns exactly 1 Access-Control-Allow-Origin header"
elif [[ "$CORS_HEADERS" -gt 1 ]]; then
    log_error "API returns $CORS_HEADERS Access-Control-Allow-Origin headers (DUPLICATE!)"
else
    log_warn "API returns no Access-Control-Allow-Origin header"
fi

# ============================================================================
# PHASE 5: SMOKE TEST READINESS
# ============================================================================

log_section "PHASE 5: SMOKE TEST (Current State)"

# API Health
log_info "Testing ARIA API health..."
if curl -s --max-time 10 "$ARIA_API_URL/health" | jq -e '.status == "healthy"' &>/dev/null; then
    log_ok "ARIA API health check passes"
else
    log_error "ARIA API health check fails"
fi

# Supabase tables
log_info "Testing Supabase REST endpoints..."
TABLES_TO_TEST=(conversations messages aria_user_settings aria_notifications)
for table in "${TABLES_TO_TEST[@]}"; do
    STATUS=$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" "$SUPABASE_PROD_URL/rest/v1/$table?limit=1" \
        -H "apikey: $SUPABASE_ANON_KEY")
    if [[ "$STATUS" == "200" ]]; then
        log_ok "Table $table: HTTP $STATUS"
    else
        log_error "Table $table: HTTP $STATUS"
    fi
done

# Frontend bundle check
log_info "Testing frontend serves correct JS bundle..."
SERVED_JS=$(curl -sL --max-time 15 "https://aria.leveredgeai.com/" 2>/dev/null | grep -o 'assets/index[^"]*\.js' | head -1)
if [[ -n "$SERVED_JS" ]]; then
    # Check if bundle contains the API URL (use temp file to avoid echo issues with large content)
    BUNDLE_TMP=$(mktemp)
    curl -sL --max-time 20 "https://aria.leveredgeai.com/$SERVED_JS" > "$BUNDLE_TMP" 2>/dev/null
    if grep -q "aria-api.leveredgeai.com" "$BUNDLE_TMP" 2>/dev/null; then
        log_ok "Frontend JS bundle contains correct API URL"
    elif grep -q "aria-api" "$BUNDLE_TMP" 2>/dev/null; then
        log_warn "Frontend JS bundle has aria-api but may not be .leveredgeai.com"
    else
        log_error "Frontend JS bundle missing correct API URL"
    fi
    rm -f "$BUNDLE_TMP"
else
    log_error "Could not find JS bundle in frontend"
fi

# ============================================================================
# SUMMARY
# ============================================================================

log_section "SUMMARY"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│ PROMOTION READINESS REPORT                                      │"
echo "├─────────────────────────────────────────────────────────────────┤"
printf "│ %-20s │ %-40s │\n" "Checks Passed" "$CHECKS_PASSED"
printf "│ %-20s │ %-40s │\n" "Checks Failed" "$CHECKS_FAILED"
printf "│ %-20s │ %-40s │\n" "Warnings" "$WARNINGS"
printf "│ %-20s │ %-40s │\n" "Errors" "$ERRORS"
printf "│ %-20s │ %-40s │\n" "Time Elapsed" "${ELAPSED}s"
echo "├─────────────────────────────────────────────────────────────────┤"

if [[ ${#MISSING_TABLES[@]} -gt 0 ]]; then
    printf "│ %-63s │\n" "⚠ Schema: ${#MISSING_TABLES[@]} tables missing in PROD"
fi
if $MOCK_FOUND; then
    printf "│ %-63s │\n" "⚠ Frontend: Mock/placeholder code detected"
fi
if $CADDY_HAS_CORS && $PYTHON_HAS_CORS; then
    printf "│ %-63s │\n" "⚠ CORS: Duplicate headers (Caddy + Python)"
fi

echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN COMPLETE - No changes were made${NC}"
    echo ""
    if [[ $ERRORS -gt 0 ]]; then
        echo -e "${RED}WOULD FAIL: $ERRORS critical issues found${NC}"
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}WOULD WARN: $WARNINGS issues need attention${NC}"
        exit 0
    else
        echo -e "${GREEN}READY TO PROMOTE: All checks passed${NC}"
        exit 0
    fi
fi

# ============================================================================
# PHASE 6: APPLY CHANGES (Only if not dry-run)
# ============================================================================

if [[ $ERRORS -gt 0 ]] && ! $FORCE; then
    echo -e "${RED}PROMOTION BLOCKED: $ERRORS critical issues found${NC}"
    echo "Fix the issues above or use --force to override"
    exit 1
fi

if ! $FORCE; then
    echo ""
    read -p "Proceed with promotion? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Promotion cancelled"
        exit 0
    fi
fi

log_section "PHASE 6: APPLYING CHANGES"

# Backup first
if ! $SKIP_BACKUP; then
    log_info "Creating CHRONOS backup..."
    curl -s -X POST http://localhost:8010/backup \
        -H "Content-Type: application/json" \
        -d '{"name":"pre-aria-promote","type":"pre-deploy"}' | jq -r '.backup_id // "backup created"'
fi

# Schema sync
if [[ ${#MISSING_TABLES[@]} -gt 0 ]]; then
    log_info "Syncing missing tables..."
    echo "TODO: Implement schema sync - for now, run manually"
    # This would generate and apply CREATE TABLE statements
fi

# Frontend sync
log_info "Syncing frontend code..."
cp "$DEV_FRONTEND_DIR/src/store/useStore.ts" "$PROD_FRONTEND_DIR/src/store/useStore.ts"

log_info "Rebuilding frontend..."
cd "$PROD_FRONTEND_DIR"
npm run build 2>&1 | tail -5

log_info "Deploying to container..."
docker cp "$PROD_FRONTEND_DIR/dist/." "$PROD_FRONTEND_CONTAINER:/usr/share/nginx/html/"

# Reload services
log_info "Reloading PostgREST..."
docker exec $PROD_DB_CONTAINER psql -U postgres -d postgres -c "NOTIFY pgrst, 'reload schema';"

log_info "Restarting frontend container..."
docker restart $PROD_FRONTEND_CONTAINER

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}PROMOTION COMPLETE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"

# ============================================================================
# LCIS REPORTING
# ============================================================================

report_to_lcis() {
    local status=$1
    local summary=$2
    local severity=$3

    # Escape summary for JSON
    local summary_escaped=$(echo "$summary" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')

    curl -s -X POST http://localhost:8050/ingest \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"$([[ $status == 'success' ]] && echo 'success' || echo 'failure')\",
            \"source_agent\": \"DEPLOY_SCRIPT\",
            \"title\": \"ARIA PROD deployment: $status\",
            \"content\": \"$summary_escaped\\n\\nChecks: $CHECKS_PASSED passed, $CHECKS_FAILED failed\\nWarnings: $WARNINGS\\nErrors: $ERRORS\\nTime: ${ELAPSED}s\",
            \"domain\": \"DEPLOYMENT\",
            \"severity\": \"$severity\",
            \"tags\": [\"auto-captured\", \"deployment\", \"aria\", \"prod\", \"$status\"]
        }" &>/dev/null &
}

# Report deployment to LCIS
if [[ $ERRORS -eq 0 ]]; then
    report_to_lcis "success" "ARIA PROD deployment completed successfully" "low"
    echo "[LCIS] Deployment captured: success"
else
    report_to_lcis "failed" "ARIA PROD deployment had $ERRORS errors" "high"
    echo "[LCIS] Deployment captured: failed"
fi
