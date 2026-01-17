#!/bin/bash
# =============================================================================
# LeverEdge Agent Fleet - Health Check Script
# =============================================================================
# Checks the health status of all agents in the fleet
#
# Usage:
#   ./fleet-health.sh           # Check all agents
#   ./fleet-health.sh --watch   # Continuous monitoring
#   ./fleet-health.sh --json    # Output as JSON
#   ./fleet-health.sh core      # Check only core agents
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.fleet.yml"
ENV_FILE="${SCRIPT_DIR}/.env.fleet"
TIMEOUT=5

# Agent definitions with ports
declare -A CORE_AGENTS=(
    ["event-bus"]="8099"
    ["chronos"]="8010"
    ["hades"]="8008"
    ["hermes"]="8014"
    ["argus"]="8016"
    ["aloy"]="8015"
    ["athena"]="8013"
    ["chiron"]="8017"
    ["scholar"]="8018"
    ["hephaestus-mcp"]="8011"
)

declare -A SECURITY_AGENTS=(
    ["aegis"]="8012"
    ["sentinel"]="8019"
    ["cerberus"]="8020"
    ["port-manager"]="8021"
    ["varys"]="8022"
)

declare -A CREATIVE_AGENTS=(
    ["muse"]="8030"
    ["calliope"]="8031"
    ["thalia"]="8032"
    ["erato"]="8033"
    ["clio"]="8034"
)

declare -A PERSONAL_AGENTS=(
    ["gym-coach"]="8100"
    ["nutritionist"]="8101"
    ["meal-planner"]="8102"
    ["academic-guide"]="8103"
    ["eros"]="8104"
)

declare -A BUSINESS_AGENTS=(
    ["heracles"]="8200"
    ["librarian"]="8201"
    ["workflow-builder"]="8202"
    ["themis"]="8203"
    ["mentor"]="8204"
    ["plutus"]="8205"
    ["procurement"]="8206"
    ["hephaestus-server"]="8207"
    ["atlas"]="8208"
    ["iris"]="8209"
)

# Parse arguments
PROFILE="all"
WATCH_MODE=""
JSON_OUTPUT=""
VERBOSE=""

for arg in "$@"; do
    case $arg in
        core|security|creative|personal|business|all)
            PROFILE="$arg"
            ;;
        --watch|-w)
            WATCH_MODE="true"
            ;;
        --json|-j)
            JSON_OUTPUT="true"
            ;;
        --verbose|-v)
            VERBOSE="true"
            ;;
        --help|-h)
            echo "Usage: $0 [profile] [options]"
            echo ""
            echo "Profiles:"
            echo "  core      - Check core infrastructure"
            echo "  security  - Check security agents"
            echo "  creative  - Check creative fleet"
            echo "  personal  - Check personal assistants"
            echo "  business  - Check business agents"
            echo "  all       - Check all agents (default)"
            echo ""
            echo "Options:"
            echo "  --watch   Continuous monitoring (refresh every 5s)"
            echo "  --json    Output results as JSON"
            echo "  --verbose Show detailed response info"
            echo "  --help    Show this help message"
            exit 0
            ;;
    esac
done

# Function to check agent health
check_agent_health() {
    local name=$1
    local port=$2
    local host=${3:-localhost}

    local url="http://${host}:${port}/health"
    local start_time=$(date +%s%N)

    # Try to get health endpoint
    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" --connect-timeout ${TIMEOUT} --max-time ${TIMEOUT} "${url}" 2>/dev/null) || true
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))

    if [ "$http_code" = "200" ]; then
        echo "healthy|${duration}|${body}"
    elif [ -z "$http_code" ] || [ "$http_code" = "000" ]; then
        echo "down|${duration}|Connection refused"
    else
        echo "unhealthy|${duration}|HTTP ${http_code}"
    fi
}

# Function to display agent status
display_status() {
    local name=$1
    local port=$2
    local result=$3

    local status=$(echo "$result" | cut -d'|' -f1)
    local duration=$(echo "$result" | cut -d'|' -f2)
    local detail=$(echo "$result" | cut -d'|' -f3-)

    local status_icon
    local status_color

    case $status in
        healthy)
            status_icon="[OK]"
            status_color="${GREEN}"
            ;;
        unhealthy)
            status_icon="[!!]"
            status_color="${YELLOW}"
            ;;
        down)
            status_icon="[XX]"
            status_color="${RED}"
            ;;
        *)
            status_icon="[??]"
            status_color="${GRAY}"
            ;;
    esac

    printf "  ${status_color}%-5s${NC} %-20s :%-5s  ${GRAY}%4dms${NC}" \
        "$status_icon" "$name" "$port" "$duration"

    if [ -n "$VERBOSE" ] && [ -n "$detail" ]; then
        echo -e "  ${GRAY}${detail}${NC}"
    else
        echo ""
    fi
}

# Function to check a group of agents
check_agent_group() {
    local group_name=$1
    shift
    local -n agents=$1

    echo -e "${CYAN}${group_name}:${NC}"

    local total=0
    local healthy=0
    local unhealthy=0
    local down=0

    for name in "${!agents[@]}"; do
        local port="${agents[$name]}"
        local result=$(check_agent_health "$name" "$port")
        local status=$(echo "$result" | cut -d'|' -f1)

        display_status "$name" "$port" "$result"

        ((total++))
        case $status in
            healthy) ((healthy++)) ;;
            unhealthy) ((unhealthy++)) ;;
            down) ((down++)) ;;
        esac
    done

    echo -e "${GRAY}  ─────────────────────────────────────────${NC}"
    echo -e "  ${GREEN}Healthy: ${healthy}${NC} | ${YELLOW}Unhealthy: ${unhealthy}${NC} | ${RED}Down: ${down}${NC} | Total: ${total}"
    echo ""

    # Return counts for summary
    echo "${healthy}:${unhealthy}:${down}:${total}"
}

# Function to generate JSON output
generate_json() {
    local timestamp=$(date -Iseconds)

    echo "{"
    echo "  \"timestamp\": \"${timestamp}\","
    echo "  \"agents\": {"

    local first_group=true

    for group in "CORE" "SECURITY" "CREATIVE" "PERSONAL" "BUSINESS"; do
        if [ "$first_group" = false ]; then echo ","; fi
        first_group=false

        echo "    \"${group,,}\": {"

        local -n agents="${group}_AGENTS"
        local first_agent=true

        for name in "${!agents[@]}"; do
            if [ "$first_agent" = false ]; then echo ","; fi
            first_agent=false

            local port="${agents[$name]}"
            local result=$(check_agent_health "$name" "$port")
            local status=$(echo "$result" | cut -d'|' -f1)
            local duration=$(echo "$result" | cut -d'|' -f2)

            echo -n "      \"${name}\": {\"port\": ${port}, \"status\": \"${status}\", \"response_ms\": ${duration}}"
        done

        echo ""
        echo -n "    }"
    done

    echo ""
    echo "  }"
    echo "}"
}

# Main health check function
run_health_check() {
    if [ -n "$JSON_OUTPUT" ]; then
        generate_json
        return
    fi

    # Header
    clear 2>/dev/null || true
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "                    LeverEdge Agent Fleet - Health Check"
    echo "============================================================================="
    echo -e "${NC}"
    echo -e "${GRAY}Timestamp: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${GRAY}Profile: ${PROFILE}${NC}"
    echo ""

    local total_healthy=0
    local total_unhealthy=0
    local total_down=0
    local total_agents=0

    # Check requested groups
    case $PROFILE in
        core)
            result=$(check_agent_group "CORE INFRASTRUCTURE" CORE_AGENTS | tail -1)
            ;;
        security)
            result=$(check_agent_group "SECURITY AGENTS" SECURITY_AGENTS | tail -1)
            ;;
        creative)
            result=$(check_agent_group "CREATIVE FLEET" CREATIVE_AGENTS | tail -1)
            ;;
        personal)
            result=$(check_agent_group "PERSONAL ASSISTANTS" PERSONAL_AGENTS | tail -1)
            ;;
        business)
            result=$(check_agent_group "BUSINESS AGENTS" BUSINESS_AGENTS | tail -1)
            ;;
        all)
            # Check all groups and aggregate
            for group_data in \
                "CORE INFRASTRUCTURE:CORE_AGENTS" \
                "SECURITY AGENTS:SECURITY_AGENTS" \
                "CREATIVE FLEET:CREATIVE_AGENTS" \
                "PERSONAL ASSISTANTS:PERSONAL_AGENTS" \
                "BUSINESS AGENTS:BUSINESS_AGENTS"
            do
                group_name="${group_data%%:*}"
                group_var="${group_data##*:}"

                # Get the last line which contains the counts
                output=$(check_agent_group "$group_name" "$group_var")
                counts=$(echo "$output" | tail -1)

                # Print all but the last line
                echo "$output" | head -n -1

                # Parse counts
                h=$(echo "$counts" | cut -d':' -f1)
                u=$(echo "$counts" | cut -d':' -f2)
                d=$(echo "$counts" | cut -d':' -f3)
                t=$(echo "$counts" | cut -d':' -f4)

                ((total_healthy += h)) || true
                ((total_unhealthy += u)) || true
                ((total_down += d)) || true
                ((total_agents += t)) || true
            done
            ;;
    esac

    # Summary
    if [ "$PROFILE" = "all" ]; then
        echo -e "${CYAN}=============================================================================${NC}"
        echo -e "${CYAN}FLEET SUMMARY${NC}"
        echo -e "${CYAN}=============================================================================${NC}"

        local health_pct=0
        if [ "$total_agents" -gt 0 ]; then
            health_pct=$((total_healthy * 100 / total_agents))
        fi

        echo -e "  Total Agents:  ${total_agents}"
        echo -e "  ${GREEN}Healthy:       ${total_healthy}${NC}"
        echo -e "  ${YELLOW}Unhealthy:     ${total_unhealthy}${NC}"
        echo -e "  ${RED}Down:          ${total_down}${NC}"
        echo ""

        # Health bar
        echo -n "  Fleet Health: ["
        local bar_width=40
        local filled=$((health_pct * bar_width / 100))
        local empty=$((bar_width - filled))

        if [ "$health_pct" -ge 80 ]; then
            echo -n -e "${GREEN}"
        elif [ "$health_pct" -ge 50 ]; then
            echo -n -e "${YELLOW}"
        else
            echo -n -e "${RED}"
        fi

        printf '%0.s#' $(seq 1 $filled)
        echo -n -e "${GRAY}"
        printf '%0.s-' $(seq 1 $empty)
        echo -e "${NC}] ${health_pct}%"
        echo ""
    fi
}

# Main execution
if [ -n "$WATCH_MODE" ]; then
    echo -e "${BLUE}Watch mode enabled. Press Ctrl+C to exit.${NC}"
    sleep 2
    while true; do
        run_health_check
        echo -e "${GRAY}Refreshing in 5 seconds...${NC}"
        sleep 5
    done
else
    run_health_check
fi
