#!/bin/bash
# =============================================================================
# LeverEdge Agent Fleet - Stop Script
# =============================================================================
# Stops the LeverEdge agent fleet gracefully
#
# Usage:
#   ./fleet-stop.sh           # Stop all agents gracefully
#   ./fleet-stop.sh --force   # Force stop (kill containers)
#   ./fleet-stop.sh --clean   # Stop and remove volumes
#   ./fleet-stop.sh core      # Stop only core infrastructure
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.fleet.yml"
ENV_FILE="${SCRIPT_DIR}/.env.fleet"

# Parse arguments
PROFILE=""
FORCE_FLAG=""
CLEAN_FLAG=""
TIMEOUT=30

for arg in "$@"; do
    case $arg in
        core|security|creative|personal|business|all)
            PROFILE="$arg"
            ;;
        --force|-f)
            FORCE_FLAG="true"
            TIMEOUT=5
            ;;
        --clean|-c)
            CLEAN_FLAG="true"
            ;;
        --help|-h)
            echo "Usage: $0 [profile] [options]"
            echo ""
            echo "Profiles:"
            echo "  core      - Stop core infrastructure"
            echo "  security  - Stop security agents"
            echo "  creative  - Stop creative fleet"
            echo "  personal  - Stop personal assistants"
            echo "  business  - Stop business agents"
            echo "  all       - Stop all agents (default if no profile specified)"
            echo ""
            echo "Options:"
            echo "  --force   Force stop containers (kill rather than graceful stop)"
            echo "  --clean   Remove volumes after stopping (CAUTION: data loss)"
            echo "  --help    Show this help message"
            exit 0
            ;;
    esac
done

# Header
echo -e "${CYAN}"
echo "============================================================================="
echo "                    LeverEdge Agent Fleet - Stop"
echo "============================================================================="
echo -e "${NC}"

# Check for compose file
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: docker-compose.fleet.yml not found at ${COMPOSE_FILE}${NC}"
    exit 1
fi

# Use default env file if it exists
ENV_FLAG=""
if [ -f "$ENV_FILE" ]; then
    ENV_FLAG="--env-file ${ENV_FILE}"
fi

# Display what we're doing
echo -e "${BLUE}Configuration:${NC}"
echo "  Compose file: ${COMPOSE_FILE}"
echo "  Profile:      ${PROFILE:-all}"
echo "  Force:        ${FORCE_FLAG:-no}"
echo "  Clean:        ${CLEAN_FLAG:-no}"
echo "  Timeout:      ${TIMEOUT}s"
echo ""

# Show current status
echo -e "${BLUE}Current running containers:${NC}"
docker compose -f "${COMPOSE_FILE}" ${ENV_FLAG} ps 2>/dev/null || echo "  (none or compose not initialized)"
echo ""

# Confirm clean operation
if [ -n "$CLEAN_FLAG" ]; then
    echo -e "${RED}WARNING: --clean flag will remove all fleet volumes!${NC}"
    echo -e "${RED}This includes: event-bus-data, fleet-logs, fleet-data, shared-backups${NC}"
    read -p "Are you sure? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo -e "${YELLOW}Aborted.${NC}"
        exit 0
    fi
fi

# Build profile flag
PROFILE_FLAG=""
if [ -n "$PROFILE" ] && [ "$PROFILE" != "all" ]; then
    PROFILE_FLAG="--profile ${PROFILE}"
else
    # Stop all profiles
    PROFILE_FLAG="--profile all"
fi

# Stop containers
if [ -n "$FORCE_FLAG" ]; then
    echo -e "${YELLOW}Force stopping containers...${NC}"
    docker compose -f "${COMPOSE_FILE}" ${ENV_FLAG} ${PROFILE_FLAG} kill 2>/dev/null || true
else
    echo -e "${BLUE}Gracefully stopping containers (timeout: ${TIMEOUT}s)...${NC}"
    docker compose -f "${COMPOSE_FILE}" ${ENV_FLAG} ${PROFILE_FLAG} stop -t ${TIMEOUT} 2>/dev/null || true
fi

# Remove containers
echo -e "${BLUE}Removing containers...${NC}"
if [ -n "$CLEAN_FLAG" ]; then
    docker compose -f "${COMPOSE_FILE}" ${ENV_FLAG} ${PROFILE_FLAG} down -v --remove-orphans 2>/dev/null || true
else
    docker compose -f "${COMPOSE_FILE}" ${ENV_FLAG} ${PROFILE_FLAG} down --remove-orphans 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}Fleet stopped successfully!${NC}"

# Show remaining containers if any
REMAINING=$(docker compose -f "${COMPOSE_FILE}" ${ENV_FLAG} ps -q 2>/dev/null | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Note: Some containers may still be running (different profile):${NC}"
    docker compose -f "${COMPOSE_FILE}" ${ENV_FLAG} ps 2>/dev/null || true
fi

echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  ./fleet-start.sh       - Start the fleet again"
echo "  docker system prune    - Clean up unused Docker resources"
echo ""
