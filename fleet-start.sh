#!/bin/bash
# =============================================================================
# LeverEdge Agent Fleet - Start Script
# =============================================================================
# Starts the LeverEdge agent fleet with proper dependency ordering
#
# Usage:
#   ./fleet-start.sh           # Start all agents
#   ./fleet-start.sh core      # Start only core infrastructure
#   ./fleet-start.sh security  # Start security agents
#   ./fleet-start.sh creative  # Start creative fleet
#   ./fleet-start.sh personal  # Start personal assistants
#   ./fleet-start.sh business  # Start business agents
#   ./fleet-start.sh --build   # Rebuild images before starting
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
ENV_EXAMPLE="${SCRIPT_DIR}/.env.fleet.example"

# Parse arguments
PROFILE="all"
BUILD_FLAG=""
DETACH_FLAG="-d"

for arg in "$@"; do
    case $arg in
        core|security|creative|personal|business|all)
            PROFILE="$arg"
            ;;
        --build)
            BUILD_FLAG="--build"
            ;;
        --foreground|-f)
            DETACH_FLAG=""
            ;;
        --help|-h)
            echo "Usage: $0 [profile] [options]"
            echo ""
            echo "Profiles:"
            echo "  core      - Start core infrastructure (event-bus, chronos, hades, etc.)"
            echo "  security  - Start security agents (aegis, cerberus, sentinel, etc.)"
            echo "  creative  - Start creative fleet (muse, calliope, thalia, etc.)"
            echo "  personal  - Start personal assistants (gym-coach, nutritionist, etc.)"
            echo "  business  - Start business agents (heracles, plutus, atlas, etc.)"
            echo "  all       - Start all agents (default)"
            echo ""
            echo "Options:"
            echo "  --build       Rebuild Docker images before starting"
            echo "  --foreground  Run in foreground (don't detach)"
            echo "  --help        Show this help message"
            exit 0
            ;;
    esac
done

# Header
echo -e "${CYAN}"
echo "============================================================================="
echo "                    LeverEdge Agent Fleet - Start"
echo "============================================================================="
echo -e "${NC}"

# Check for compose file
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: docker-compose.fleet.yml not found at ${COMPOSE_FILE}${NC}"
    exit 1
fi

# Check for environment file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: .env.fleet not found${NC}"
    if [ -f "$ENV_EXAMPLE" ]; then
        echo -e "${YELLOW}Creating .env.fleet from .env.fleet.example...${NC}"
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo -e "${YELLOW}Please edit .env.fleet with your API keys and settings${NC}"
    else
        echo -e "${RED}Error: Neither .env.fleet nor .env.fleet.example found${NC}"
        exit 1
    fi
fi

# Check for external networks
echo -e "${BLUE}Checking external networks...${NC}"
if ! docker network ls | grep -q "control-plane-net"; then
    echo -e "${YELLOW}Creating control-plane-net network...${NC}"
    docker network create control-plane-net || true
fi
if ! docker network ls | grep -q "stack_net"; then
    echo -e "${YELLOW}Creating stack_net network...${NC}"
    docker network create stack_net || true
fi
echo -e "${GREEN}Networks ready${NC}"

# Display startup info
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Compose file: ${COMPOSE_FILE}"
echo "  Environment:  ${ENV_FILE}"
echo "  Profile:      ${PROFILE}"
echo "  Build:        ${BUILD_FLAG:-no}"
echo "  Detached:     ${DETACH_FLAG:+yes}"
echo ""

# Start the fleet
echo -e "${BLUE}Starting ${PROFILE} agents...${NC}"
echo ""

# Build docker compose command
CMD="docker compose -f ${COMPOSE_FILE} --env-file ${ENV_FILE}"

if [ "$PROFILE" != "all" ]; then
    CMD="${CMD} --profile ${PROFILE}"
else
    CMD="${CMD} --profile all"
fi

CMD="${CMD} up ${BUILD_FLAG} ${DETACH_FLAG}"

echo -e "${CYAN}Running: ${CMD}${NC}"
echo ""

# Execute
eval $CMD

# If detached, show status
if [ -n "$DETACH_FLAG" ]; then
    echo ""
    echo -e "${GREEN}Fleet started successfully!${NC}"
    echo ""
    echo -e "${BLUE}Quick status:${NC}"
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo "  ./fleet-health.sh      - Check health of all agents"
    echo "  ./fleet-stop.sh        - Stop the fleet"
    echo "  docker compose -f docker-compose.fleet.yml logs -f [service]  - View logs"
    echo ""
fi
