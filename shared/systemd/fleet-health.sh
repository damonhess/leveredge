#!/bin/bash
#===============================================================================
# LeverEdge Fleet Health Check Script
# /opt/leveredge/shared/systemd/fleet-health.sh
#
# Comprehensive health check for all LeverEdge fleet components.
# Exit codes:
#   0 - All healthy
#   1 - Some services unhealthy
#   2 - Critical services down
#===============================================================================

set -euo pipefail

# Configuration
VERBOSE="${VERBOSE:-false}"
JSON_OUTPUT="${JSON_OUTPUT:-false}"
NOTIFY_ON_FAILURE="${NOTIFY_ON_FAILURE:-false}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
HEALTHY=0
UNHEALTHY=0
CRITICAL_DOWN=0

# Results storage for JSON output
declare -A RESULTS

#===============================================================================
# Utility Functions
#===============================================================================
print_header() {
    if [ "$JSON_OUTPUT" = "false" ]; then
        echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║              LEVEREDGE FLEET HEALTH CHECK                    ║${NC}"
        echo -e "${BLUE}║              $(date '+%Y-%m-%d %H:%M:%S')                            ║${NC}"
        echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
    fi
}

print_section() {
    if [ "$JSON_OUTPUT" = "false" ]; then
        echo -e "${CYAN}$1${NC}"
        echo "─────────────────────────────────────────────────────────────────"
    fi
}

check_service() {
    local name="$1"
    local port="$2"
    local is_critical="${3:-false}"
    local endpoint="${4:-/health}"

    local status="unknown"
    local response_time=""

    local start_time
    start_time=$(date +%s%N)

    if curl -sf --max-time 5 "http://localhost:${port}${endpoint}" > /dev/null 2>&1; then
        local end_time
        end_time=$(date +%s%N)
        response_time=$(( (end_time - start_time) / 1000000 ))
        status="healthy"
        ((HEALTHY++))

        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${GREEN}[OK]${NC} $name (:$port) - ${response_time}ms"
        fi
    else
        status="unhealthy"
        ((UNHEALTHY++))

        if [ "$is_critical" = "true" ]; then
            ((CRITICAL_DOWN++))
            if [ "$JSON_OUTPUT" = "false" ]; then
                echo -e "  ${RED}[CRITICAL]${NC} $name (:$port) - NOT RESPONDING"
            fi
        else
            if [ "$JSON_OUTPUT" = "false" ]; then
                echo -e "  ${YELLOW}[DOWN]${NC} $name (:$port) - NOT RESPONDING"
            fi
        fi
    fi

    RESULTS["$name"]="$status"
}

check_docker_container() {
    local name="$1"
    local is_critical="${2:-false}"

    local status="unknown"

    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${name}$"; then
        local container_status
        container_status=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "unknown")

        if [ "$container_status" = "running" ]; then
            status="running"
            ((HEALTHY++))
            if [ "$JSON_OUTPUT" = "false" ]; then
                echo -e "  ${GREEN}[OK]${NC} $name"
            fi
        else
            status="$container_status"
            ((UNHEALTHY++))
            if [ "$JSON_OUTPUT" = "false" ]; then
                echo -e "  ${YELLOW}[WARN]${NC} $name - Status: $container_status"
            fi
        fi
    else
        status="not_found"
        ((UNHEALTHY++))
        if [ "$is_critical" = "true" ]; then
            ((CRITICAL_DOWN++))
            if [ "$JSON_OUTPUT" = "false" ]; then
                echo -e "  ${RED}[CRITICAL]${NC} $name - NOT FOUND"
            fi
        else
            if [ "$JSON_OUTPUT" = "false" ]; then
                echo -e "  ${YELLOW}[DOWN]${NC} $name - NOT FOUND"
            fi
        fi
    fi

    RESULTS["container_$name"]="$status"
}

check_systemd_service() {
    local name="$1"
    local is_critical="${2:-false}"

    local status="unknown"

    if systemctl is-active --quiet "$name" 2>/dev/null; then
        status="active"
        ((HEALTHY++))
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${GREEN}[OK]${NC} $name"
        fi
    elif systemctl is-enabled --quiet "$name" 2>/dev/null; then
        status="inactive"
        ((UNHEALTHY++))
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${YELLOW}[DOWN]${NC} $name - INACTIVE"
        fi
    else
        status="not_found"
        if [ "$JSON_OUTPUT" = "false" ] && [ "$VERBOSE" = "true" ]; then
            echo -e "  ${BLUE}[SKIP]${NC} $name - NOT INSTALLED"
        fi
    fi

    RESULTS["service_$name"]="$status"
}

#===============================================================================
# Check Docker Infrastructure
#===============================================================================
check_docker_infrastructure() {
    print_section "1. Docker Infrastructure"

    # Critical containers
    check_docker_container "supabase-db" true
    check_docker_container "supabase-kong" true

    # n8n instances
    check_docker_container "n8n-prod" true
    check_docker_container "n8n-dev" false
    check_docker_container "n8n-control" false

    # Other Supabase containers
    check_docker_container "supabase-auth" false
    check_docker_container "supabase-rest" false
    check_docker_container "supabase-storage" false
    check_docker_container "supabase-realtime" false

    echo ""
}

#===============================================================================
# Check Core Services
#===============================================================================
check_core_services() {
    print_section "2. Core Services (Critical)"

    check_service "Event-Bus" 8099 true
    check_service "HERMES" 8014 true
    check_service "AEGIS" 8012 true
    check_service "HADES" 8008 true
    check_service "GAIA" 8000 false

    echo ""
}

#===============================================================================
# Check Agent Services
#===============================================================================
check_agent_services() {
    print_section "3. Agent Services"

    check_service "CHRONOS" 8010 false
    check_service "HEPHAESTUS" 8011 false
    check_service "ATHENA" 8013 false
    check_service "ALOY" 8015 false
    check_service "ARGUS" 8016 false
    check_service "CHIRON" 8017 false
    check_service "SCHOLAR" 8018 false
    check_service "ATLAS" 8019 false

    echo ""
}

#===============================================================================
# Check Creative Fleet
#===============================================================================
check_creative_fleet() {
    print_section "4. Creative Fleet"

    check_service "CALLIOPE" 8020 false
    check_service "CLIO" 8021 false
    check_service "ERATO" 8022 false
    check_service "MUSE" 8023 false
    check_service "THALIA" 8024 false

    echo ""
}

#===============================================================================
# Check Specialized Agents
#===============================================================================
check_specialized_agents() {
    print_section "5. Specialized Agents"

    check_service "CERBERUS" 8025 false
    check_service "PORT-MANAGER" 8026 false
    check_service "GYM-COACH" 8027 false
    check_service "NUTRITIONIST" 8028 false
    check_service "MEAL-PLANNER" 8029 false
    check_service "ACADEMIC-GUIDE" 8030 false
    check_service "EROS" 8031 false
    check_service "HERACLES" 8032 false
    check_service "LIBRARIAN" 8033 false
    check_service "MENTOR" 8034 false
    check_service "THEMIS" 8035 false
    check_service "PLUTUS" 8036 false
    check_service "PROCUREMENT" 8037 false
    check_service "IRIS" 8038 false

    echo ""
}

#===============================================================================
# Check System Resources
#===============================================================================
check_system_resources() {
    print_section "6. System Resources"

    # Disk space
    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    local disk_avail
    disk_avail=$(df -h / | awk 'NR==2 {print $4}')

    if [ "$disk_usage" -lt 80 ]; then
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${GREEN}[OK]${NC} Disk: ${disk_usage}% used ($disk_avail available)"
        fi
    elif [ "$disk_usage" -lt 90 ]; then
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${YELLOW}[WARN]${NC} Disk: ${disk_usage}% used ($disk_avail available)"
        fi
    else
        ((CRITICAL_DOWN++))
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${RED}[CRITICAL]${NC} Disk: ${disk_usage}% used ($disk_avail available)"
        fi
    fi
    RESULTS["disk_usage"]="${disk_usage}%"

    # Memory
    local mem_pct
    mem_pct=$(free | awk '/^Mem:/ {printf("%.0f", $3/$2 * 100)}')
    local mem_used
    mem_used=$(free -h | awk '/^Mem:/ {print $3}')
    local mem_total
    mem_total=$(free -h | awk '/^Mem:/ {print $2}')

    if [ "$mem_pct" -lt 80 ]; then
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${GREEN}[OK]${NC} Memory: ${mem_used} / ${mem_total} (${mem_pct}%)"
        fi
    elif [ "$mem_pct" -lt 90 ]; then
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${YELLOW}[WARN]${NC} Memory: ${mem_used} / ${mem_total} (${mem_pct}%)"
        fi
    else
        ((CRITICAL_DOWN++))
        if [ "$JSON_OUTPUT" = "false" ]; then
            echo -e "  ${RED}[CRITICAL]${NC} Memory: ${mem_used} / ${mem_total} (${mem_pct}%)"
        fi
    fi
    RESULTS["memory_usage"]="${mem_pct}%"

    # Load average
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | xargs)
    local cpu_count
    cpu_count=$(nproc)

    if [ "$JSON_OUTPUT" = "false" ]; then
        echo -e "  ${BLUE}[INFO]${NC} Load: $load_avg (${cpu_count} CPUs)"
    fi
    RESULTS["load_average"]="$load_avg"

    echo ""
}

#===============================================================================
# Print Summary
#===============================================================================
print_summary() {
    if [ "$JSON_OUTPUT" = "true" ]; then
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"healthy\": $HEALTHY,"
        echo "  \"unhealthy\": $UNHEALTHY,"
        echo "  \"critical_down\": $CRITICAL_DOWN,"
        echo "  \"status\": \"$([ $CRITICAL_DOWN -eq 0 ] && [ $UNHEALTHY -eq 0 ] && echo "healthy" || ([ $CRITICAL_DOWN -gt 0 ] && echo "critical" || echo "degraded"))\""
        echo "}"
    else
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "Summary: ${GREEN}$HEALTHY healthy${NC}, ${YELLOW}$UNHEALTHY unhealthy${NC}, ${RED}$CRITICAL_DOWN critical${NC}"

        if [ $CRITICAL_DOWN -gt 0 ]; then
            echo -e "${RED}STATUS: CRITICAL - Core services are down!${NC}"
        elif [ $UNHEALTHY -gt 0 ]; then
            echo -e "${YELLOW}STATUS: DEGRADED - Some services unavailable${NC}"
        else
            echo -e "${GREEN}STATUS: HEALTHY - All systems operational${NC}"
        fi
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    fi
}

#===============================================================================
# Notify on Failure
#===============================================================================
notify_on_failure() {
    if [ "$NOTIFY_ON_FAILURE" = "true" ] && [ $UNHEALTHY -gt 0 ]; then
        local message="Fleet Health Alert

Status: $([ $CRITICAL_DOWN -gt 0 ] && echo "CRITICAL" || echo "DEGRADED")
Healthy: $HEALTHY
Unhealthy: $UNHEALTHY
Critical: $CRITICAL_DOWN

Time: $(date '+%Y-%m-%d %H:%M:%S')"

        curl -sf --max-time 5 \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"$message\", \"priority\": \"high\"}" \
            "http://localhost:8014/notify" > /dev/null 2>&1 || true
    fi
}

#===============================================================================
# Main
#===============================================================================
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -j|--json)
                JSON_OUTPUT="true"
                shift
                ;;
            -n|--notify)
                NOTIFY_ON_FAILURE="true"
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  -v, --verbose   Show all services including skipped"
                echo "  -j, --json      Output in JSON format"
                echo "  -n, --notify    Send notification on failure"
                echo "  -h, --help      Show this help"
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done

    print_header
    check_docker_infrastructure
    check_core_services
    check_agent_services
    check_creative_fleet
    check_specialized_agents
    check_system_resources
    print_summary
    notify_on_failure

    # Exit code based on status
    if [ $CRITICAL_DOWN -gt 0 ]; then
        exit 2
    elif [ $UNHEALTHY -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

main "$@"
