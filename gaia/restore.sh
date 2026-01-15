#!/bin/bash
# /opt/leveredge/gaia/restore.sh
# Shell wrapper for GAIA operations

set -e

GAIA_DIR="/opt/leveredge/gaia"
GAIA_PY="$GAIA_DIR/gaia.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${GREEN}"
    echo "  ██████╗  █████╗ ██╗ █████╗ "
    echo " ██╔════╝ ██╔══██╗██║██╔══██╗"
    echo " ██║  ███╗███████║██║███████║"
    echo " ██║   ██║██╔══██║██║██╔══██║"
    echo " ╚██████╔╝██║  ██║██║██║  ██║"
    echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo " Genesis and Infrastructure Automation"
    echo ""
}

usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list [target]           List available backups"
    echo "  verify <backup_path>    Verify backup integrity"
    echo "  restore <target>        Restore from backup"
    echo "  health                  Check system health"
    echo "  full                    Full system restore (DANGEROUS)"
    echo ""
    echo "Targets: control-plane, prod, dev, full"
    echo ""
    echo "Options:"
    echo "  --backup <path>    Use specific backup file"
    echo "  --yes, -y          Skip confirmation prompts"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 restore control-plane --yes"
    echo "  $0 full --yes"
}

case "$1" in
    list)
        python3 "$GAIA_PY" list ${2:+--target $2}
        ;;
    verify)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: backup path required${NC}"
            exit 1
        fi
        python3 "$GAIA_PY" verify "$2"
        ;;
    restore)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: target required${NC}"
            exit 1
        fi
        print_banner
        shift
        python3 "$GAIA_PY" restore "$@"
        ;;
    health)
        python3 "$GAIA_PY" health
        ;;
    full)
        print_banner
        echo -e "${RED}+-----------------------------------------------------------+${NC}"
        echo -e "${RED}|           FULL SYSTEM RESTORE                             |${NC}"
        echo -e "${RED}|                                                           |${NC}"
        echo -e "${RED}|  This will restore EVERYTHING:                            |${NC}"
        echo -e "${RED}|  - Control plane n8n                                      |${NC}"
        echo -e "${RED}|  - All FastAPI agents                                     |${NC}"
        echo -e "${RED}|  - Production environment                                 |${NC}"
        echo -e "${RED}|  - Development environment                                |${NC}"
        echo -e "${RED}|                                                           |${NC}"
        echo -e "${RED}|  ALL CURRENT DATA WILL BE REPLACED                        |${NC}"
        echo -e "${RED}+-----------------------------------------------------------+${NC}"
        echo ""
        shift
        python3 "$GAIA_PY" restore full "$@"
        ;;
    *)
        print_banner
        usage
        exit 1
        ;;
esac
