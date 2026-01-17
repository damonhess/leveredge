#!/bin/bash
# ============================================================
# ARIA Demo Environment Reset Script
# Resets the demo environment to a clean state
# ============================================================

set -e

# Configuration
DEMO_DIR="/opt/leveredge/demo"
DEMO_DB="/tmp/demo-aria.db"
DEMO_CONTAINER="demo-n8n"
DEMO_NETWORK="demo-net"
DEMO_PORT=5681
LOG_FILE="/var/log/leveredge/demo-reset.log"
ANALYTICS_DIR="$DEMO_DIR/analytics"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Console output (unless quiet mode)
    if [[ "$QUIET_MODE" != "true" ]]; then
        case $level in
            INFO)  echo -e "${BLUE}[$timestamp]${NC} $message" ;;
            OK)    echo -e "${GREEN}[$timestamp]${NC} $message" ;;
            WARN)  echo -e "${YELLOW}[$timestamp]${NC} $message" ;;
            ERROR) echo -e "${RED}[$timestamp]${NC} $message" ;;
        esac
    fi

    # File logging
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE" 2>/dev/null || true
}

# Show usage
usage() {
    echo "ARIA Demo Environment Reset Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --init       Initialize demo environment (first-time setup)"
    echo "  --full       Full reset with fresh containers"
    echo "  --restart    Restart demo containers"
    echo "  --status     Check demo environment status"
    echo "  --quiet      Suppress output (for cron jobs)"
    echo "  --help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Quick reset (database only)"
    echo "  $0 --init         # First-time setup"
    echo "  $0 --full         # Full reset with container rebuild"
    echo "  $0 --status       # Check status"
}

# Check if demo container is running
check_container() {
    docker ps --format '{{.Names}}' | grep -q "^${DEMO_CONTAINER}$"
}

# Get container health
get_container_health() {
    docker inspect --format='{{.State.Health.Status}}' "$DEMO_CONTAINER" 2>/dev/null || echo "unknown"
}

# Reset database
reset_database() {
    log INFO "Resetting demo database..."

    # Remove old database
    rm -f "$DEMO_DB" 2>/dev/null || true

    # Create fresh database with demo data
    sqlite3 "$DEMO_DB" < "$DEMO_DIR/demo-data.sql"

    # Set permissions
    chmod 666 "$DEMO_DB"

    log OK "Database reset complete"
}

# Export analytics before reset (if enabled)
export_analytics() {
    if [[ -f "$DEMO_DB" ]]; then
        log INFO "Exporting analytics before reset..."

        mkdir -p "$ANALYTICS_DIR"

        local timestamp=$(date '+%Y%m%d-%H%M%S')
        local export_file="$ANALYTICS_DIR/sessions-$timestamp.json"

        # Export session data
        sqlite3 "$DEMO_DB" <<EOF > "$export_file" 2>/dev/null || true
.mode json
SELECT
    id,
    started_at,
    expires_at,
    message_count,
    is_active
FROM demo_sessions
WHERE message_count > 0;
EOF

        log OK "Analytics exported to $export_file"
    fi
}

# Clear session data only (quick reset)
quick_reset() {
    log INFO "Performing quick reset..."

    if [[ -f "$DEMO_DB" ]]; then
        # Clear session-specific data but keep demo data
        sqlite3 "$DEMO_DB" <<EOF
DELETE FROM demo_sessions;
DELETE FROM demo_messages;
DELETE FROM demo_analytics WHERE created_at < datetime('now', '-1 hour');

-- Reset any task status changes
UPDATE tasks SET status = 'pending' WHERE id NOT IN ('task-009');
UPDATE tasks SET status = 'completed' WHERE id = 'task-009';

-- Insert fresh session placeholder
INSERT INTO demo_sessions (id, started_at, expires_at, message_count, max_messages, is_active)
VALUES ('demo-init-session', datetime('now'), datetime('now', '+15 minutes'), 0, 10, 1);

VACUUM;
EOF
        log OK "Quick reset complete"
    else
        log WARN "Database not found, performing full database reset"
        reset_database
    fi
}

# Create Docker network if not exists
create_network() {
    if ! docker network ls | grep -q "$DEMO_NETWORK"; then
        log INFO "Creating demo network..."
        docker network create "$DEMO_NETWORK" 2>/dev/null || true
        log OK "Network created"
    fi
}

# Start demo container
start_container() {
    log INFO "Starting demo container..."

    create_network

    # Stop existing container if running
    docker stop "$DEMO_CONTAINER" 2>/dev/null || true
    docker rm "$DEMO_CONTAINER" 2>/dev/null || true

    # Start new container
    docker run -d \
        --name "$DEMO_CONTAINER" \
        --network "$DEMO_NETWORK" \
        --restart unless-stopped \
        -p "${DEMO_PORT}:5678" \
        -v "$DEMO_DB:/tmp/demo-aria.db" \
        -v "$DEMO_DIR/n8n-demo-workflow.json:/home/node/.n8n/workflows/demo.json:ro" \
        -e N8N_HOST="0.0.0.0" \
        -e N8N_PORT=5678 \
        -e N8N_PROTOCOL="https" \
        -e N8N_EDITOR_BASE_URL="https://demo.n8n.leveredgeai.com" \
        -e WEBHOOK_URL="https://demo.leveredgeai.com" \
        -e N8N_ENCRYPTION_KEY="${N8N_DEMO_ENCRYPTION_KEY:-demo-encryption-key-change-me}" \
        -e N8N_USER_MANAGEMENT_DISABLED="true" \
        -e N8N_DIAGNOSTICS_ENABLED="false" \
        -e N8N_TEMPLATES_ENABLED="false" \
        -e GENERIC_TIMEZONE="America/Los_Angeles" \
        --memory="512m" \
        --cpus="0.5" \
        n8nio/n8n:latest

    # Wait for container to be healthy
    log INFO "Waiting for container to be ready..."
    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s "http://localhost:${DEMO_PORT}/healthz" > /dev/null 2>&1; then
            log OK "Demo container started and healthy"
            return 0
        fi
        sleep 2
        ((attempt++))
    done

    log ERROR "Container failed to become healthy"
    return 1
}

# Import demo workflow
import_workflow() {
    log INFO "Importing demo workflow..."

    # Wait a bit for n8n to fully initialize
    sleep 5

    # Import workflow via API
    local workflow_file="$DEMO_DIR/n8n-demo-workflow.json"

    if [[ -f "$workflow_file" ]]; then
        curl -s -X POST "http://localhost:${DEMO_PORT}/api/v1/workflows" \
            -H "Content-Type: application/json" \
            -d @"$workflow_file" > /dev/null 2>&1 || true

        log OK "Workflow imported"
    else
        log WARN "Workflow file not found: $workflow_file"
    fi
}

# Full initialization
initialize() {
    log INFO "=== Initializing ARIA Demo Environment ==="

    # Create directories
    mkdir -p "$ANALYTICS_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"

    # Reset database
    reset_database

    # Start container
    start_container

    # Import workflow
    import_workflow

    log OK "=== Demo environment initialized ==="
    log INFO "Demo URL: https://demo.leveredgeai.com"
    log INFO "Admin URL: https://demo.n8n.leveredgeai.com"
}

# Full reset (rebuild everything)
full_reset() {
    log INFO "=== Performing full demo reset ==="

    # Export analytics
    export_analytics

    # Stop and remove container
    docker stop "$DEMO_CONTAINER" 2>/dev/null || true
    docker rm "$DEMO_CONTAINER" 2>/dev/null || true

    # Reset database
    reset_database

    # Start container
    start_container

    # Import workflow
    import_workflow

    log OK "=== Full reset complete ==="
}

# Restart containers
restart_containers() {
    log INFO "Restarting demo containers..."

    docker restart "$DEMO_CONTAINER" 2>/dev/null || {
        log WARN "Container not running, starting fresh..."
        start_container
    }

    log OK "Restart complete"
}

# Show status
show_status() {
    echo ""
    echo "=== ARIA Demo Environment Status ==="
    echo ""

    # Container status
    echo "Container: $DEMO_CONTAINER"
    if check_container; then
        echo "  Status: RUNNING"
        echo "  Health: $(get_container_health)"
        echo "  Port: $DEMO_PORT"
    else
        echo "  Status: STOPPED"
    fi
    echo ""

    # Database status
    echo "Database: $DEMO_DB"
    if [[ -f "$DEMO_DB" ]]; then
        local db_size=$(du -h "$DEMO_DB" | cut -f1)
        echo "  Status: EXISTS"
        echo "  Size: $db_size"

        # Session stats
        local active_sessions=$(sqlite3 "$DEMO_DB" "SELECT COUNT(*) FROM demo_sessions WHERE is_active = 1;" 2>/dev/null || echo "?")
        local total_messages=$(sqlite3 "$DEMO_DB" "SELECT COUNT(*) FROM demo_messages;" 2>/dev/null || echo "?")
        echo "  Active Sessions: $active_sessions"
        echo "  Total Messages: $total_messages"
    else
        echo "  Status: NOT FOUND"
    fi
    echo ""

    # Network status
    echo "Network: $DEMO_NETWORK"
    if docker network ls | grep -q "$DEMO_NETWORK"; then
        echo "  Status: EXISTS"
    else
        echo "  Status: NOT FOUND"
    fi
    echo ""

    # Connectivity test
    echo "Connectivity:"
    if curl -s "http://localhost:${DEMO_PORT}/healthz" > /dev/null 2>&1; then
        echo "  Local: OK (http://localhost:$DEMO_PORT)"
    else
        echo "  Local: FAILED"
    fi
    echo ""

    # Analytics
    echo "Analytics:"
    if [[ -d "$ANALYTICS_DIR" ]]; then
        local file_count=$(ls -1 "$ANALYTICS_DIR"/*.json 2>/dev/null | wc -l || echo "0")
        echo "  Export Files: $file_count"
    else
        echo "  Directory: NOT FOUND"
    fi
    echo ""
}

# Parse arguments
QUIET_MODE="false"
ACTION="quick"

while [[ $# -gt 0 ]]; do
    case $1 in
        --init)
            ACTION="init"
            shift
            ;;
        --full)
            ACTION="full"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --quiet)
            QUIET_MODE="true"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Execute action
case $ACTION in
    init)
        initialize
        ;;
    full)
        full_reset
        ;;
    restart)
        restart_containers
        ;;
    status)
        show_status
        ;;
    quick)
        export_analytics
        quick_reset
        ;;
esac

exit 0
