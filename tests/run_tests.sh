#!/bin/bash
# =============================================================================
# Leveredge Integration Test Runner
# =============================================================================
#
# Usage:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh health             # Run only health checks
#   ./run_tests.sh core               # Run core agent tests
#   ./run_tests.sh creative           # Run creative fleet tests
#   ./run_tests.sh security           # Run security fleet tests
#   ./run_tests.sh quick              # Run quick tests (no slow tests)
#   ./run_tests.sh coverage           # Run with coverage report
#   ./run_tests.sh <test_file.py>     # Run specific test file
#
# Environment Variables:
#   LEVEREDGE_BASE_URL   - Base URL for agents (default: http://localhost)
#   LEVEREDGE_TEST_TIMEOUT - Default timeout in seconds (default: 10)
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default settings
PYTEST_ARGS=""
RUN_MODE="all"

# Parse arguments
case "${1:-all}" in
    health)
        RUN_MODE="health"
        PYTEST_ARGS="-m health"
        echo -e "${BLUE}Running health check tests only...${NC}"
        ;;
    core)
        RUN_MODE="core"
        PYTEST_ARGS="-m core"
        echo -e "${BLUE}Running core agent tests...${NC}"
        ;;
    creative)
        RUN_MODE="creative"
        PYTEST_ARGS="-m creative"
        echo -e "${BLUE}Running creative fleet tests...${NC}"
        ;;
    security)
        RUN_MODE="security"
        PYTEST_ARGS="-m security"
        echo -e "${BLUE}Running security fleet tests...${NC}"
        ;;
    personal)
        RUN_MODE="personal"
        PYTEST_ARGS="-m personal"
        echo -e "${BLUE}Running personal fleet tests...${NC}"
        ;;
    business)
        RUN_MODE="business"
        PYTEST_ARGS="-m business"
        echo -e "${BLUE}Running business fleet tests...${NC}"
        ;;
    integration)
        RUN_MODE="integration"
        PYTEST_ARGS="-m integration"
        echo -e "${BLUE}Running integration tests...${NC}"
        ;;
    quick)
        RUN_MODE="quick"
        PYTEST_ARGS='-m "not slow"'
        echo -e "${BLUE}Running quick tests (excluding slow tests)...${NC}"
        ;;
    coverage)
        RUN_MODE="coverage"
        PYTEST_ARGS="--cov=. --cov-report=html --cov-report=term"
        echo -e "${BLUE}Running tests with coverage report...${NC}"
        ;;
    all)
        RUN_MODE="all"
        PYTEST_ARGS=""
        echo -e "${BLUE}Running all tests...${NC}"
        ;;
    *.py)
        RUN_MODE="file"
        PYTEST_ARGS="$1"
        echo -e "${BLUE}Running tests from $1...${NC}"
        ;;
    -h|--help|help)
        echo "Leveredge Integration Test Runner"
        echo ""
        echo "Usage: ./run_tests.sh [command]"
        echo ""
        echo "Commands:"
        echo "  (none)       Run all tests"
        echo "  health       Run only health check tests"
        echo "  core         Run core agent tests"
        echo "  creative     Run creative fleet tests"
        echo "  security     Run security fleet tests"
        echo "  personal     Run personal fleet tests"
        echo "  business     Run business fleet tests"
        echo "  integration  Run integration tests"
        echo "  quick        Run quick tests (excludes slow tests)"
        echo "  coverage     Run with coverage report"
        echo "  <file.py>    Run specific test file"
        echo "  help         Show this help"
        echo ""
        echo "Environment Variables:"
        echo "  LEVEREDGE_BASE_URL      Base URL (default: http://localhost)"
        echo "  LEVEREDGE_TEST_TIMEOUT  Timeout in seconds (default: 10)"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh health"
        echo "  ./run_tests.sh test_atlas.py"
        echo "  LEVEREDGE_BASE_URL=http://192.168.1.100 ./run_tests.sh"
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

# Check if Python virtual environment exists
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Install/upgrade dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -q -r requirements.txt

# Print configuration
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Base URL: ${LEVEREDGE_BASE_URL:-http://localhost}"
echo "  Timeout:  ${LEVEREDGE_TEST_TIMEOUT:-10}s"
echo "  Mode:     $RUN_MODE"
echo ""

# Run tests
echo -e "${BLUE}Running pytest...${NC}"
echo "============================================================"

# Build pytest command
PYTEST_CMD="python -m pytest $PYTEST_ARGS -v"

# Add color output if terminal supports it
if [ -t 1 ]; then
    PYTEST_CMD="$PYTEST_CMD --color=yes"
fi

# Execute tests
if eval $PYTEST_CMD; then
    echo ""
    echo "============================================================"
    echo -e "${GREEN}All tests passed!${NC}"
    EXIT_CODE=0
else
    echo ""
    echo "============================================================"
    echo -e "${RED}Some tests failed!${NC}"
    EXIT_CODE=1
fi

# Coverage report location
if [ "$RUN_MODE" = "coverage" ]; then
    echo ""
    echo -e "${BLUE}Coverage report generated:${NC}"
    echo "  HTML report: $SCRIPT_DIR/htmlcov/index.html"
fi

# Deactivate virtual environment
deactivate

exit $EXIT_CODE
