#!/bin/bash
# LeverEdge UFW Firewall Rules
# /opt/leveredge/security/ufw/rules.sh
#
# Configures UFW firewall for the LeverEdge platform with strict
# security defaults and localhost-only access for internal services.
#
# Usage: sudo ./rules.sh [apply|test|reset]
#
# IMPORTANT: This script requires root privileges

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Script metadata
SCRIPT_NAME="LeverEdge UFW Firewall Configuration"
SCRIPT_VERSION="1.0.0"
LOG_FILE="/var/log/leveredge/ufw-config.log"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Network configuration
LOCALHOST="127.0.0.1"
LOCALHOST_RANGE="127.0.0.0/8"

# Trusted internal networks (customize as needed)
INTERNAL_NETWORKS=(
    "10.0.0.0/8"
    "172.16.0.0/12"
    "192.168.0.0/16"
)

# Docker networks (will be detected automatically)
DOCKER_NETWORK="172.17.0.0/16"

# ============================================================================
# PORT DEFINITIONS
# ============================================================================

# Public ports (accessible from anywhere)
declare -A PUBLIC_PORTS=(
    [SSH]=22
    [HTTP]=80
    [HTTPS]=443
)

# n8n ports (localhost only)
declare -A N8N_PORTS=(
    [N8N_MAIN]=5678
    [N8N_WEBHOOK]=5679
    [N8N_WORKER]=5680
)

# Supabase ports (localhost only)
declare -A SUPABASE_PORTS=(
    [SUPABASE_API]=8000
    [SUPABASE_STUDIO]=8001
    [POSTGRES]=5432
    [POSTGREST]=3000
    [REALTIME]=4000
    [STORAGE]=5000
    [AUTH]=9999
    [META]=8080
    [INBUCKET]=9000
)

# Agent port range (localhost only)
AGENT_PORT_START=8000
AGENT_PORT_END=8300

# Redis and other services (localhost only)
declare -A INTERNAL_PORTS=(
    [REDIS]=6379
    [MINIO]=9000
    [MINIO_CONSOLE]=9001
    [PROMETHEUS]=9090
    [GRAFANA]=3001
    [LOKI]=3100
    [VECTOR]=8686
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

    echo "[$timestamp] [$level] $message" >> "$LOG_FILE" 2>/dev/null || true

    case "$level" in
        "INFO")  echo -e "${GREEN}[INFO]${NC} $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $message" ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} $message" ;;
    esac
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR" "This script must be run as root"
        exit 1
    fi
}

check_ufw_installed() {
    if ! command -v ufw &> /dev/null; then
        log "ERROR" "UFW is not installed. Install with: apt-get install ufw"
        exit 1
    fi
}

backup_current_rules() {
    local backup_dir="/opt/leveredge/security/backups/ufw"
    local backup_file="$backup_dir/ufw-rules-$(date +%Y%m%d-%H%M%S).backup"

    mkdir -p "$backup_dir"

    log "INFO" "Backing up current UFW rules to $backup_file"
    ufw status verbose > "$backup_file" 2>&1 || true
    iptables-save >> "$backup_file" 2>&1 || true

    log "INFO" "Backup created: $backup_file"
}

# ============================================================================
# UFW RULE FUNCTIONS
# ============================================================================

reset_ufw() {
    log "INFO" "Resetting UFW to defaults..."

    # Disable UFW first
    ufw --force disable

    # Reset all rules
    ufw --force reset

    log "INFO" "UFW has been reset to defaults"
}

configure_defaults() {
    log "INFO" "Configuring UFW defaults..."

    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    ufw default deny routed

    # Enable logging
    ufw logging on
    ufw logging medium

    log "INFO" "Default policies configured: deny incoming, allow outgoing"
}

configure_public_ports() {
    log "INFO" "Configuring public ports..."

    # SSH - Allow from anywhere but with rate limiting
    log "INFO" "Allowing SSH (port ${PUBLIC_PORTS[SSH]}) with rate limiting"
    ufw limit ${PUBLIC_PORTS[SSH]}/tcp comment 'SSH with rate limiting'

    # HTTP - Allow from anywhere
    log "INFO" "Allowing HTTP (port ${PUBLIC_PORTS[HTTP]})"
    ufw allow ${PUBLIC_PORTS[HTTP]}/tcp comment 'HTTP'

    # HTTPS - Allow from anywhere
    log "INFO" "Allowing HTTPS (port ${PUBLIC_PORTS[HTTPS]})"
    ufw allow ${PUBLIC_PORTS[HTTPS]}/tcp comment 'HTTPS'
}

configure_n8n_ports() {
    log "INFO" "Configuring n8n ports (localhost only)..."

    for name in "${!N8N_PORTS[@]}"; do
        local port="${N8N_PORTS[$name]}"
        log "INFO" "Allowing n8n port $port from localhost only"
        ufw allow from $LOCALHOST to any port $port proto tcp comment "n8n $name - localhost only"
        ufw allow from $LOCALHOST_RANGE to any port $port proto tcp comment "n8n $name - localhost range"
    done
}

configure_supabase_ports() {
    log "INFO" "Configuring Supabase ports (localhost only)..."

    for name in "${!SUPABASE_PORTS[@]}"; do
        local port="${SUPABASE_PORTS[$name]}"
        log "INFO" "Allowing Supabase port $port from localhost only"
        ufw allow from $LOCALHOST to any port $port proto tcp comment "Supabase $name - localhost only"
        ufw allow from $LOCALHOST_RANGE to any port $port proto tcp comment "Supabase $name - localhost range"
    done
}

configure_agent_ports() {
    log "INFO" "Configuring agent ports ${AGENT_PORT_START}-${AGENT_PORT_END} (localhost only)..."

    # Allow agent port range from localhost
    ufw allow from $LOCALHOST to any port ${AGENT_PORT_START}:${AGENT_PORT_END} proto tcp comment 'Agent ports - localhost only'
    ufw allow from $LOCALHOST_RANGE to any port ${AGENT_PORT_START}:${AGENT_PORT_END} proto tcp comment 'Agent ports - localhost range'
}

configure_internal_services() {
    log "INFO" "Configuring internal service ports (localhost only)..."

    for name in "${!INTERNAL_PORTS[@]}"; do
        local port="${INTERNAL_PORTS[$name]}"
        log "INFO" "Allowing internal service port $port from localhost only"
        ufw allow from $LOCALHOST to any port $port proto tcp comment "$name - localhost only"
        ufw allow from $LOCALHOST_RANGE to any port $port proto tcp comment "$name - localhost range"
    done
}

configure_docker_networking() {
    log "INFO" "Configuring Docker network access..."

    # Allow Docker bridge network
    if command -v docker &> /dev/null; then
        # Get Docker bridge network
        local docker_bridge=$(docker network inspect bridge --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "$DOCKER_NETWORK")

        log "INFO" "Allowing Docker bridge network: $docker_bridge"
        ufw allow from $docker_bridge to any comment 'Docker bridge network'

        # Get custom leveredge network if exists
        local leveredge_net=$(docker network inspect leveredge-network --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || true)
        if [[ -n "$leveredge_net" ]]; then
            log "INFO" "Allowing LeverEdge Docker network: $leveredge_net"
            ufw allow from $leveredge_net to any comment 'LeverEdge Docker network'
        fi
    else
        log "WARN" "Docker not found, using default network: $DOCKER_NETWORK"
        ufw allow from $DOCKER_NETWORK to any comment 'Docker network (default)'
    fi
}

configure_icmp() {
    log "INFO" "Configuring ICMP rules..."

    # Allow ping from localhost and internal networks
    ufw allow from $LOCALHOST_RANGE proto icmp comment 'ICMP from localhost'

    # Optional: Allow ping from anywhere (useful for monitoring)
    # Uncomment the following line if needed:
    # ufw allow proto icmp comment 'ICMP from anywhere'
}

configure_additional_security() {
    log "INFO" "Applying additional security rules..."

    # Block common attack ports
    local blocked_ports=(23 25 135 137 138 139 445 1433 1434 3306 3389)

    for port in "${blocked_ports[@]}"; do
        ufw deny $port comment "Block common attack port $port"
    done

    # Block invalid packets (requires iptables)
    log "INFO" "Note: Advanced packet filtering requires direct iptables rules"
}

# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

verify_rules() {
    log "INFO" "Verifying UFW configuration..."

    echo ""
    echo "============================================"
    echo "Current UFW Status"
    echo "============================================"
    ufw status verbose

    echo ""
    echo "============================================"
    echo "Numbered Rules"
    echo "============================================"
    ufw status numbered
}

test_mode() {
    log "INFO" "Running in TEST mode - no changes will be applied"

    echo ""
    echo "============================================"
    echo "TEST MODE - Rules that would be applied:"
    echo "============================================"
    echo ""
    echo "Default Policies:"
    echo "  - Deny incoming"
    echo "  - Allow outgoing"
    echo "  - Deny routed"
    echo ""
    echo "Public Ports (allow from anywhere):"
    for name in "${!PUBLIC_PORTS[@]}"; do
        echo "  - $name: ${PUBLIC_PORTS[$name]}/tcp"
    done
    echo "  - SSH will use rate limiting"
    echo ""
    echo "n8n Ports (localhost only):"
    for name in "${!N8N_PORTS[@]}"; do
        echo "  - $name: ${N8N_PORTS[$name]}/tcp"
    done
    echo ""
    echo "Supabase Ports (localhost only):"
    for name in "${!SUPABASE_PORTS[@]}"; do
        echo "  - $name: ${SUPABASE_PORTS[$name]}/tcp"
    done
    echo ""
    echo "Agent Ports (localhost only):"
    echo "  - Range: ${AGENT_PORT_START}-${AGENT_PORT_END}/tcp"
    echo ""
    echo "Internal Services (localhost only):"
    for name in "${!INTERNAL_PORTS[@]}"; do
        echo "  - $name: ${INTERNAL_PORTS[$name]}/tcp"
    done
    echo ""
    echo "Docker Networks: Will be auto-detected"
    echo ""
    echo "Run './rules.sh apply' to apply these rules"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

print_header() {
    echo "============================================"
    echo "$SCRIPT_NAME"
    echo "Version: $SCRIPT_VERSION"
    echo "============================================"
    echo ""
}

apply_rules() {
    check_root
    check_ufw_installed

    print_header

    log "INFO" "Starting UFW configuration..."

    # Backup current rules
    backup_current_rules

    # Reset to clean state
    reset_ufw

    # Configure all rules
    configure_defaults
    configure_public_ports
    configure_n8n_ports
    configure_supabase_ports
    configure_agent_ports
    configure_internal_services
    configure_docker_networking
    configure_icmp
    configure_additional_security

    # Enable UFW
    log "INFO" "Enabling UFW..."
    ufw --force enable

    # Verify configuration
    verify_rules

    log "INFO" "UFW configuration complete!"
    echo ""
    echo "============================================"
    echo "IMPORTANT: Verify SSH access before closing"
    echo "your current session!"
    echo "============================================"
}

show_help() {
    print_header
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  apply   - Apply all firewall rules (requires root)"
    echo "  test    - Show rules that would be applied without changes"
    echo "  reset   - Reset UFW to defaults (requires root)"
    echo "  status  - Show current UFW status"
    echo "  help    - Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0 apply   # Apply all rules"
    echo "  $0 test         # Preview rules"
    echo "  sudo $0 reset   # Reset to defaults"
}

# Parse command line arguments
case "${1:-help}" in
    apply)
        apply_rules
        ;;
    test)
        test_mode
        ;;
    reset)
        check_root
        check_ufw_installed
        print_header
        backup_current_rules
        reset_ufw
        ;;
    status)
        check_ufw_installed
        ufw status verbose
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log "ERROR" "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
