#!/bin/bash
#===============================================================================
# LeverEdge Fleet Shutdown Script
# /opt/leveredge/shared/systemd/fleet-stop.sh
#
# Gracefully shuts down the entire LeverEdge fleet:
# 1. Send shutdown notification via HERMES
# 2. Stop all agent services (gracefully)
# 3. Stop Event Bus
# 4. Stop Docker containers
#===============================================================================

set -euo pipefail

# Configuration
LEVEREDGE_HOME="${LEVEREDGE_HOME:-/opt/leveredge}"
LOG_FILE="/var/log/leveredge/fleet-stop.log"
GRACEFUL_TIMEOUT=30

DOCKER_COMPOSE_FILES=(
    "${LEVEREDGE_HOME}/data-plane/prod/n8n/docker-compose.yml"
    "${LEVEREDGE_HOME}/data-plane/dev/n8n/docker-compose.yml"
    "${LEVEREDGE_HOME}/data-plane/prod/supabase/docker-compose.yml"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$(dirname "$LOG_FILE")"

#===============================================================================
# Logging Functions
#===============================================================================
log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} $1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[OK]${NC} $1"
}

log_warn() {
    log "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

#===============================================================================
# Send Shutdown Notification
#===============================================================================
send_shutdown_notification() {
    log_info "Sending shutdown notification via HERMES..."

    local hostname
    hostname=$(hostname)
    local shutdown_time
    shutdown_time=$(date '+%Y-%m-%d %H:%M:%S %Z')

    local message="LeverEdge Fleet Shutting Down

Host: $hostname
Time: $shutdown_time

Graceful shutdown initiated."

    # Try to send via HERMES (may fail if already stopped)
    if curl -sf --max-time 5 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$message\", \"priority\": \"high\"}" \
        "http://localhost:8014/notify" > /dev/null 2>&1; then
        log_success "Shutdown notification sent"
        sleep 2  # Give time for message to be delivered
    else
        log_warn "Could not send shutdown notification (HERMES may be unavailable)"
    fi
}

#===============================================================================
# Stop Agent Service
#===============================================================================
stop_agent() {
    local name="$1"
    local service_name="${2:-${name}.service}"

    log_info "Stopping $name..."

    # Try systemd stop
    if systemctl is-active --quiet "$service_name" 2>/dev/null; then
        systemctl stop "$service_name" 2>/dev/null || true
        log_success "$name stopped (systemd)"
        return 0
    fi

    # Try Docker stop
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
        docker stop "$name" --time "$GRACEFUL_TIMEOUT" 2>/dev/null || true
        log_success "$name stopped (docker)"
        return 0
    fi

    log_info "$name was not running"
    return 0
}

#===============================================================================
# Stop All Agents
#===============================================================================
stop_all_agents() {
    log_info "Stopping all LeverEdge agents..."

    # Stop agents in reverse order (non-core first)
    local AGENTS=(
        "varys"
        "sentinel"
        "iris"
        "procurement"
        "plutus"
        "themis"
        "mentor"
        "librarian"
        "heracles"
        "eros"
        "academic-guide"
        "meal-planner"
        "nutritionist"
        "gym-coach"
        "port-manager"
        "cerberus"
        "thalia"
        "muse"
        "erato"
        "clio"
        "calliope"
        "atlas"
        "scholar"
        "chiron"
        "argus"
        "aloy"
        "athena"
        "chronos"
    )

    for agent in "${AGENTS[@]}"; do
        stop_agent "$agent" || true
    done

    # Stop core agents last
    stop_agent "hephaestus" || true
    stop_agent "aegis" || true
    stop_agent "hermes" || true
    stop_agent "hades" || true
    stop_agent "gaia" || true

    log_success "All agents stopped"
}

#===============================================================================
# Stop Event Bus
#===============================================================================
stop_event_bus() {
    log_info "Stopping Event Bus..."

    if systemctl is-active --quiet event-bus.service 2>/dev/null; then
        systemctl stop event-bus.service
        log_success "Event Bus stopped (systemd)"
    elif docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^event-bus$"; then
        docker stop event-bus --time 30 2>/dev/null || true
        log_success "Event Bus stopped (docker)"
    else
        log_info "Event Bus was not running"
    fi
}

#===============================================================================
# Stop Docker Infrastructure
#===============================================================================
stop_docker_infrastructure() {
    log_info "Stopping Docker infrastructure..."

    for compose_file in "${DOCKER_COMPOSE_FILES[@]}"; do
        if [ -f "$compose_file" ]; then
            local dir
            dir=$(dirname "$compose_file")
            log_info "Stopping containers in $dir..."

            if (cd "$dir" && docker compose down 2>&1 | tee -a "$LOG_FILE"); then
                log_success "Stopped containers in $dir"
            else
                log_warn "Some containers in $dir may not have stopped cleanly"
            fi
        fi
    done

    log_success "Docker infrastructure stopped"
}

#===============================================================================
# Main
#===============================================================================
main() {
    log_info "=============================================="
    log_info "LeverEdge Fleet Shutdown Sequence"
    log_info "=============================================="
    log_info "Started at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    log_info ""

    # Step 1: Notification
    send_shutdown_notification

    # Step 2: Stop agents
    stop_all_agents

    # Step 3: Stop Event Bus
    stop_event_bus

    # Step 4: Stop Docker (optional - uncomment if desired)
    # Note: Usually we leave Docker containers running for faster restart
    # stop_docker_infrastructure

    log_info ""
    log_info "=============================================="
    log_success "Fleet shutdown complete"
    log_info "=============================================="

    exit 0
}

main "$@"
