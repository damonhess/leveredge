#!/bin/bash
#===============================================================================
# LeverEdge Fleet Startup Script
# /opt/leveredge/shared/systemd/fleet-start.sh
#
# Starts the entire LeverEdge fleet in proper dependency order:
# 1. Docker infrastructure (Supabase, n8n)
# 2. Event Bus (central communication)
# 3. Core agents (HERMES, AEGIS, HADES)
# 4. All other agents
# 5. Health verification
# 6. Boot notification via HERMES
#===============================================================================

set -euo pipefail

# Configuration
LEVEREDGE_HOME="${LEVEREDGE_HOME:-/opt/leveredge}"
LOG_FILE="/var/log/leveredge/fleet-start.log"
HEALTH_TIMEOUT=120  # seconds to wait for health checks
DOCKER_COMPOSE_FILES=(
    "${LEVEREDGE_HOME}/data-plane/prod/supabase/docker-compose.yml"
    "${LEVEREDGE_HOME}/data-plane/prod/n8n/docker-compose.yml"
    "${LEVEREDGE_HOME}/data-plane/dev/n8n/docker-compose.yml"
)

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure log directory exists
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
# Health Check Functions
#===============================================================================
wait_for_service() {
    local name="$1"
    local url="$2"
    local timeout="${3:-30}"
    local elapsed=0

    log_info "Waiting for $name at $url..."

    while [ $elapsed -lt $timeout ]; do
        if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
            log_success "$name is ready"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    log_error "$name failed to become ready within ${timeout}s"
    return 1
}

wait_for_docker() {
    local name="$1"
    local timeout="${2:-60}"
    local elapsed=0

    log_info "Waiting for Docker container: $name..."

    while [ $elapsed -lt $timeout ]; do
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
            # Container exists, check if it's healthy
            local status
            status=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "unknown")
            if [ "$status" = "running" ]; then
                log_success "Container $name is running"
                return 0
            fi
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    log_warn "Container $name not ready within ${timeout}s (may be expected)"
    return 1
}

#===============================================================================
# Start Docker Infrastructure
#===============================================================================
start_docker_infrastructure() {
    log_info "Starting Docker infrastructure..."

    # Start each docker-compose file
    for compose_file in "${DOCKER_COMPOSE_FILES[@]}"; do
        if [ -f "$compose_file" ]; then
            local dir
            dir=$(dirname "$compose_file")
            log_info "Starting containers in $dir..."

            if (cd "$dir" && docker compose up -d 2>&1 | tee -a "$LOG_FILE"); then
                log_success "Started containers in $dir"
            else
                log_warn "Some containers in $dir may have failed to start"
            fi
        else
            log_warn "Compose file not found: $compose_file"
        fi
    done

    # Wait for critical containers
    wait_for_docker "supabase-db" 60 || true
    wait_for_docker "supabase-kong" 60 || true
    wait_for_docker "n8n-prod" 60 || true

    log_success "Docker infrastructure startup complete"
}

#===============================================================================
# Start Event Bus (First)
#===============================================================================
start_event_bus() {
    log_info "Starting Event Bus..."

    if systemctl is-active --quiet event-bus.service 2>/dev/null; then
        log_info "Event Bus already running"
    elif systemctl list-unit-files event-bus.service &>/dev/null; then
        systemctl start event-bus.service
        wait_for_service "Event Bus" "http://localhost:8099/health" 30
    else
        # Try starting as Docker container
        if docker ps -a --format '{{.Names}}' | grep -q "^event-bus$"; then
            docker start event-bus 2>/dev/null || true
            wait_for_service "Event Bus" "http://localhost:8099/health" 30
        else
            log_warn "Event Bus service not found - may need manual start"
        fi
    fi
}

#===============================================================================
# Start Agent Service
#===============================================================================
start_agent() {
    local name="$1"
    local port="$2"
    local service_name="${3:-${name}.service}"

    log_info "Starting $name..."

    # Check if already running
    if curl -sf --max-time 2 "http://localhost:${port}/health" > /dev/null 2>&1; then
        log_info "$name already running on port $port"
        return 0
    fi

    # Try systemd service first
    if systemctl list-unit-files "$service_name" &>/dev/null; then
        systemctl start "$service_name" 2>/dev/null || true
        sleep 2
    fi

    # Try Docker container
    if docker ps -a --format '{{.Names}}' | grep -q "^${name}$"; then
        docker start "$name" 2>/dev/null || true
        sleep 2
    fi

    # Verify started
    if curl -sf --max-time 5 "http://localhost:${port}/health" > /dev/null 2>&1; then
        log_success "$name started successfully"
        return 0
    else
        log_warn "$name may not have started properly"
        return 1
    fi
}

#===============================================================================
# Start All Agents
#===============================================================================
start_all_agents() {
    log_info "Starting all LeverEdge agents..."

    local failed=0

    # Core agents (start first)
    local -A CORE_AGENTS=(
        ["hermes"]=8014
        ["aegis"]=8012
        ["hades"]=8008
        ["gaia"]=8000
    )

    # All other agents
    local -A ALL_AGENTS=(
        ["chronos"]=8010
        ["hephaestus"]=8011
        ["athena"]=8013
        ["aloy"]=8015
        ["argus"]=8016
        ["chiron"]=8017
        ["scholar"]=8018
        ["atlas"]=8019
        ["calliope"]=8020
        ["clio"]=8021
        ["erato"]=8022
        ["muse"]=8023
        ["thalia"]=8024
        ["cerberus"]=8025
        ["port-manager"]=8026
        ["gym-coach"]=8027
        ["nutritionist"]=8028
        ["meal-planner"]=8029
        ["academic-guide"]=8030
        ["eros"]=8031
        ["heracles"]=8032
        ["librarian"]=8033
        ["mentor"]=8034
        ["themis"]=8035
        ["plutus"]=8036
        ["procurement"]=8037
        ["iris"]=8038
        ["sentinel"]=8039
        ["varys"]=8040
    )

    # Start core agents first
    for agent in "${!CORE_AGENTS[@]}"; do
        start_agent "$agent" "${CORE_AGENTS[$agent]}" || ((failed++)) || true
    done

    # Give core agents time to initialize
    sleep 5

    # Start remaining agents
    for agent in "${!ALL_AGENTS[@]}"; do
        start_agent "$agent" "${ALL_AGENTS[$agent]}" || ((failed++)) || true
    done

    if [ $failed -gt 0 ]; then
        log_warn "$failed agents may have failed to start"
    else
        log_success "All agents started"
    fi

    return 0
}

#===============================================================================
# Run Health Checks
#===============================================================================
run_health_checks() {
    log_info "Running health verification..."

    local healthy=0
    local unhealthy=0

    # Check all agent health endpoints
    local -A ALL_SERVICES=(
        ["Event Bus"]=8099
        ["GAIA"]=8000
        ["HADES"]=8008
        ["CHRONOS"]=8010
        ["HEPHAESTUS"]=8011
        ["AEGIS"]=8012
        ["ATHENA"]=8013
        ["HERMES"]=8014
        ["ALOY"]=8015
        ["ARGUS"]=8016
        ["CHIRON"]=8017
        ["SCHOLAR"]=8018
    )

    for service in "${!ALL_SERVICES[@]}"; do
        local port="${ALL_SERVICES[$service]}"
        if curl -sf --max-time 3 "http://localhost:${port}/health" > /dev/null 2>&1; then
            log_success "$service (:$port) is healthy"
            ((healthy++))
        else
            log_warn "$service (:$port) not responding"
            ((unhealthy++))
        fi
    done

    log_info "Health check complete: $healthy healthy, $unhealthy unhealthy"

    # Return success even if some are unhealthy (they may start later)
    return 0
}

#===============================================================================
# Send Boot Notification via HERMES
#===============================================================================
send_boot_notification() {
    log_info "Sending boot notification via HERMES..."

    local hostname
    hostname=$(hostname)
    local boot_time
    boot_time=$(date '+%Y-%m-%d %H:%M:%S %Z')

    # Count running services
    local running_count=0
    for port in 8000 8008 8010 8011 8012 8013 8014 8015 8016 8017 8018 8099; do
        if curl -sf --max-time 2 "http://localhost:${port}/health" > /dev/null 2>&1; then
            ((running_count++))
        fi
    done

    # Create notification message
    local message="LeverEdge Fleet Started

Host: $hostname
Time: $boot_time
Active Services: $running_count

Boot sequence completed successfully."

    # Send via HERMES API
    if curl -sf --max-time 10 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$message\", \"priority\": \"normal\"}" \
        "http://localhost:8014/notify" > /dev/null 2>&1; then
        log_success "Boot notification sent via HERMES"
    else
        log_warn "Failed to send boot notification (HERMES may not be ready)"

        # Retry after delay
        sleep 10
        if curl -sf --max-time 10 \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"$message\", \"priority\": \"normal\"}" \
            "http://localhost:8014/notify" > /dev/null 2>&1; then
            log_success "Boot notification sent via HERMES (retry successful)"
        else
            log_error "Boot notification failed after retry"
        fi
    fi
}

#===============================================================================
# Main
#===============================================================================
main() {
    log_info "=============================================="
    log_info "LeverEdge Fleet Startup Sequence"
    log_info "=============================================="
    log_info "Started at: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    log_info "Hostname: $(hostname)"
    log_info ""

    # Step 1: Docker infrastructure
    start_docker_infrastructure

    # Step 2: Event Bus
    start_event_bus

    # Step 3: All agents
    start_all_agents

    # Step 4: Health checks
    sleep 10  # Give services time to fully initialize
    run_health_checks

    # Step 5: Boot notification
    send_boot_notification

    log_info ""
    log_info "=============================================="
    log_success "Fleet startup sequence complete"
    log_info "=============================================="

    exit 0
}

main "$@"
