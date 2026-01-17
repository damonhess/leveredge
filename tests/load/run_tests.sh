#!/bin/bash
# =============================================================================
# Leveredge Load Testing Runner
# =============================================================================
#
# Usage:
#   ./run_tests.sh [profile] [options]
#
# Profiles:
#   light   - 10 users, light load (default)
#   medium  - 50 users, moderate load
#   heavy   - 200 users, stress test
#   custom  - Use custom options
#
# Examples:
#   ./run_tests.sh light
#   ./run_tests.sh medium --tags health
#   ./run_tests.sh heavy --time 30m
#   ./run_tests.sh custom --users 25 --spawn-rate 5
#
# =============================================================================

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE="${1:-light}"
HOST="${HOST:-http://localhost}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create directories
mkdir -p reports logs

# Function to print banner
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║            LEVEREDGE LOAD TESTING SUITE                       ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║  Profile: $PROFILE"
    echo "║  Host: $HOST"
    echo "║  Timestamp: $TIMESTAMP"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: Python 3 is required${NC}"
        exit 1
    fi

    # Check Locust
    if ! command -v locust &> /dev/null; then
        echo -e "${YELLOW}Locust not found. Installing...${NC}"
        pip install -r requirements.txt
    fi

    # Check if host is reachable (basic check)
    if ! curl -s --connect-timeout 5 "$HOST:8007/health" > /dev/null 2>&1; then
        echo -e "${YELLOW}WARNING: ATLAS ($HOST:8007) may not be reachable${NC}"
        echo -e "${YELLOW}Continue anyway? (y/n)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    echo -e "${GREEN}Prerequisites OK${NC}"
}

# Function to run tests with profile
run_with_profile() {
    local profile=$1
    shift
    local extra_args="$@"

    case $profile in
        light)
            echo -e "${GREEN}Running LIGHT load test (10 users, 1/s spawn)${NC}"
            locust -f locustfile.py \
                --config configs/light.conf \
                --host "$HOST" \
                --html "reports/light_${TIMESTAMP}.html" \
                --csv "reports/light_${TIMESTAMP}" \
                --logfile "logs/light_${TIMESTAMP}.log" \
                $extra_args
            ;;

        medium)
            echo -e "${YELLOW}Running MEDIUM load test (50 users, 5/s spawn)${NC}"
            locust -f locustfile.py \
                --config configs/medium.conf \
                --host "$HOST" \
                --html "reports/medium_${TIMESTAMP}.html" \
                --csv "reports/medium_${TIMESTAMP}" \
                --logfile "logs/medium_${TIMESTAMP}.log" \
                $extra_args
            ;;

        heavy)
            echo -e "${RED}Running HEAVY load test (200 users, 20/s spawn)${NC}"
            echo -e "${RED}WARNING: This may impact system performance!${NC}"
            sleep 3
            locust -f locustfile.py \
                --config configs/heavy.conf \
                --host "$HOST" \
                --html "reports/heavy_${TIMESTAMP}.html" \
                --csv "reports/heavy_${TIMESTAMP}" \
                --logfile "logs/heavy_${TIMESTAMP}.log" \
                $extra_args
            ;;

        custom)
            echo -e "${BLUE}Running CUSTOM load test${NC}"
            locust -f locustfile.py \
                --host "$HOST" \
                --html "reports/custom_${TIMESTAMP}.html" \
                --csv "reports/custom_${TIMESTAMP}" \
                --logfile "logs/custom_${TIMESTAMP}.log" \
                $extra_args
            ;;

        web)
            echo -e "${GREEN}Starting Locust Web UI at http://localhost:8089${NC}"
            locust -f locustfile.py --host "$HOST"
            ;;

        health-only)
            echo -e "${GREEN}Running health check tests only${NC}"
            locust -f locustfile.py \
                --config configs/light.conf \
                --host "$HOST" \
                --tags health \
                --html "reports/health_${TIMESTAMP}.html" \
                --csv "reports/health_${TIMESTAMP}" \
                --logfile "logs/health_${TIMESTAMP}.log" \
                $extra_args
            ;;

        event-bus-only)
            echo -e "${GREEN}Running Event Bus tests only${NC}"
            locust -f locustfile.py \
                --config configs/medium.conf \
                --host "$HOST" \
                --tags event-bus \
                --html "reports/event_bus_${TIMESTAMP}.html" \
                --csv "reports/event_bus_${TIMESTAMP}" \
                --logfile "logs/event_bus_${TIMESTAMP}.log" \
                $extra_args
            ;;

        chat-only)
            echo -e "${GREEN}Running ARIA chat tests only${NC}"
            locust -f locustfile.py \
                --config configs/light.conf \
                --host "$HOST" \
                --tags chat \
                --html "reports/chat_${TIMESTAMP}.html" \
                --csv "reports/chat_${TIMESTAMP}" \
                --logfile "logs/chat_${TIMESTAMP}.log" \
                $extra_args
            ;;

        stress)
            echo -e "${RED}Running STRESS test (maximum throughput)${NC}"
            echo -e "${RED}WARNING: This WILL impact system performance!${NC}"
            sleep 5
            locust -f locustfile.py \
                --host "$HOST" \
                --users 500 \
                --spawn-rate 50 \
                --run-time 5m \
                --headless \
                --tags stress,throughput \
                --html "reports/stress_${TIMESTAMP}.html" \
                --csv "reports/stress_${TIMESTAMP}" \
                --logfile "logs/stress_${TIMESTAMP}.log" \
                $extra_args
            ;;

        *)
            echo -e "${RED}Unknown profile: $profile${NC}"
            echo "Available profiles: light, medium, heavy, custom, web, health-only, event-bus-only, chat-only, stress"
            exit 1
            ;;
    esac
}

# Function to show help
show_help() {
    echo "Leveredge Load Testing Runner"
    echo ""
    echo "Usage: ./run_tests.sh [profile] [options]"
    echo ""
    echo "Profiles:"
    echo "  light          10 users, 1/s spawn rate, 5 min"
    echo "  medium         50 users, 5/s spawn rate, 10 min"
    echo "  heavy          200 users, 20/s spawn rate, 15 min"
    echo "  custom         Custom configuration (pass Locust args)"
    echo "  web            Start Locust Web UI"
    echo "  health-only    Run only health check tests"
    echo "  event-bus-only Run only Event Bus tests"
    echo "  chat-only      Run only ARIA chat tests"
    echo "  stress         Maximum throughput stress test"
    echo ""
    echo "Options (pass to Locust):"
    echo "  --users N      Number of concurrent users"
    echo "  --spawn-rate N Users to spawn per second"
    echo "  --run-time T   Test duration (e.g., 5m, 1h)"
    echo "  --tags TAG     Run only tests with specific tag"
    echo ""
    echo "Environment Variables:"
    echo "  HOST           Target host (default: http://localhost)"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh light"
    echo "  ./run_tests.sh medium --tags health"
    echo "  HOST=http://staging.leveredge.ai ./run_tests.sh heavy"
    echo "  ./run_tests.sh custom --users 25 --spawn-rate 5 --run-time 10m"
}

# Main execution
main() {
    case "$1" in
        -h|--help|help)
            show_help
            exit 0
            ;;
    esac

    print_banner
    check_prerequisites

    # Shift to get extra args
    shift 2>/dev/null || true

    run_with_profile "$PROFILE" "$@"

    echo ""
    echo -e "${GREEN}Test completed!${NC}"
    echo -e "Reports: ${BLUE}reports/${NC}"
    echo -e "Logs: ${BLUE}logs/${NC}"
}

main "$@"
