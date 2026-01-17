#!/bin/bash
# LeverEdge Security Hardening Installation Script
# /opt/leveredge/security/install.sh
#
# This script applies all security configurations for the LeverEdge platform.
# It must be run with root privileges (sudo).
#
# Usage: sudo ./install.sh [options]
#
# Options:
#   --dry-run     Show what would be done without making changes
#   --skip-ufw    Skip UFW configuration
#   --skip-fail2ban Skip Fail2ban configuration
#   --skip-docker Skip Docker network configuration
#   --skip-cerberus Skip CERBERUS configuration
#   --force       Skip confirmation prompts
#
# Version: 1.0.0

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/var/log/leveredge"
LOG_FILE="${LOG_DIR}/security-install.log"
BACKUP_DIR="/opt/leveredge/security/backups/$(date +%Y%m%d-%H%M%S)"

# Default options
DRY_RUN=false
SKIP_UFW=false
SKIP_FAIL2BAN=false
SKIP_DOCKER=false
SKIP_CERBERUS=false
FORCE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    mkdir -p "$LOG_DIR"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case "$level" in
        "INFO")  echo -e "${GREEN}[INFO]${NC} $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $message" ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} $message" ;;
        "DRY")   echo -e "${CYAN}[DRY-RUN]${NC} $message" ;;
    esac
}

print_banner() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                               ║${NC}"
    echo -e "${BLUE}║${NC}        ${GREEN}LeverEdge Security Hardening Installation${NC}              ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                      Version 1.0.0                           ${BLUE}║${NC}"
    echo -e "${BLUE}║                                                               ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR" "This script must be run as root. Use: sudo $0"
        exit 1
    fi
}

check_dependencies() {
    log "INFO" "Checking dependencies..."

    local deps=("ufw" "fail2ban-client" "docker" "curl")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log "WARN" "Missing dependencies: ${missing[*]}"
        log "INFO" "Installing missing dependencies..."

        if $DRY_RUN; then
            log "DRY" "Would run: apt-get install -y ${missing[*]}"
        else
            apt-get update
            apt-get install -y "${missing[@]}"
        fi
    fi

    log "INFO" "All dependencies satisfied"
}

create_backup() {
    log "INFO" "Creating backup of current configurations..."

    if $DRY_RUN; then
        log "DRY" "Would create backup at: $BACKUP_DIR"
        return
    fi

    mkdir -p "$BACKUP_DIR"

    # Backup Fail2ban configs
    if [[ -d /etc/fail2ban ]]; then
        cp -r /etc/fail2ban "$BACKUP_DIR/fail2ban" 2>/dev/null || true
    fi

    # Backup UFW rules
    if [[ -f /etc/ufw/user.rules ]]; then
        cp /etc/ufw/user.rules "$BACKUP_DIR/ufw-rules.backup" 2>/dev/null || true
    fi
    ufw status verbose > "$BACKUP_DIR/ufw-status.backup" 2>&1 || true

    # Backup iptables
    iptables-save > "$BACKUP_DIR/iptables.backup" 2>/dev/null || true

    log "INFO" "Backup created at: $BACKUP_DIR"
}

confirm_action() {
    local message="$1"

    if $FORCE; then
        return 0
    fi

    echo -e "${YELLOW}$message${NC}"
    read -p "Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "INFO" "Operation cancelled by user"
        exit 0
    fi
}

# ============================================================================
# FAIL2BAN INSTALLATION
# ============================================================================

install_fail2ban() {
    if $SKIP_FAIL2BAN; then
        log "INFO" "Skipping Fail2ban configuration (--skip-fail2ban)"
        return
    fi

    log "INFO" "Installing Fail2ban configuration..."

    if $DRY_RUN; then
        log "DRY" "Would copy jail.local to /etc/fail2ban/"
        log "DRY" "Would copy filter.d/leveredge.conf to /etc/fail2ban/filter.d/"
        log "DRY" "Would copy action.d/notify-hermes.conf to /etc/fail2ban/action.d/"
        log "DRY" "Would restart fail2ban service"
        return
    fi

    # Stop fail2ban before making changes
    systemctl stop fail2ban 2>/dev/null || true

    # Copy jail configuration
    log "INFO" "Installing jail.local..."
    cp "$SCRIPT_DIR/fail2ban/jail.local" /etc/fail2ban/jail.local
    chmod 644 /etc/fail2ban/jail.local

    # Copy custom filter
    log "INFO" "Installing custom filter..."
    cp "$SCRIPT_DIR/fail2ban/filter.d/leveredge.conf" /etc/fail2ban/filter.d/leveredge.conf
    chmod 644 /etc/fail2ban/filter.d/leveredge.conf

    # Copy HERMES action
    log "INFO" "Installing HERMES notification action..."
    cp "$SCRIPT_DIR/fail2ban/action.d/notify-hermes.conf" /etc/fail2ban/action.d/notify-hermes.conf
    chmod 644 /etc/fail2ban/action.d/notify-hermes.conf

    # Create log directories
    mkdir -p /var/log/leveredge
    mkdir -p /opt/leveredge/agents/logs
    mkdir -p /opt/leveredge/cerberus/logs
    mkdir -p /opt/leveredge/gateway/logs
    mkdir -p /opt/leveredge/supabase/logs

    # Set proper permissions
    chown -R root:adm /var/log/leveredge
    chmod 755 /var/log/leveredge

    # Start and enable fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban

    # Verify installation
    sleep 2
    if systemctl is-active --quiet fail2ban; then
        log "INFO" "Fail2ban installed and running successfully"
        fail2ban-client status
    else
        log "ERROR" "Fail2ban failed to start. Check: journalctl -u fail2ban"
        exit 1
    fi
}

# ============================================================================
# UFW INSTALLATION
# ============================================================================

install_ufw() {
    if $SKIP_UFW; then
        log "INFO" "Skipping UFW configuration (--skip-ufw)"
        return
    fi

    log "INFO" "Installing UFW configuration..."

    if $DRY_RUN; then
        log "DRY" "Would run: $SCRIPT_DIR/ufw/rules.sh apply"
        return
    fi

    # Make rules script executable
    chmod +x "$SCRIPT_DIR/ufw/rules.sh"

    # Apply UFW rules
    "$SCRIPT_DIR/ufw/rules.sh" apply

    log "INFO" "UFW configuration complete"
}

# ============================================================================
# DOCKER NETWORK INSTALLATION
# ============================================================================

install_docker_networks() {
    if $SKIP_DOCKER; then
        log "INFO" "Skipping Docker network configuration (--skip-docker)"
        return
    fi

    log "INFO" "Configuring Docker networks..."

    if $DRY_RUN; then
        log "DRY" "Would create Docker networks: leveredge-dmz, leveredge-app, leveredge-agents, leveredge-data, leveredge-monitor"
        return
    fi

    # Create networks (ignore errors if they already exist)
    local networks=(
        "leveredge-dmz:172.20.0.0/24"
        "leveredge-app:172.21.0.0/24"
        "leveredge-agents:172.22.0.0/24"
        "leveredge-data:172.23.0.0/24"
        "leveredge-monitor:172.24.0.0/24"
    )

    for network_spec in "${networks[@]}"; do
        local network_name="${network_spec%%:*}"
        local subnet="${network_spec##*:}"

        if docker network ls --format '{{.Name}}' | grep -q "^${network_name}$"; then
            log "INFO" "Network $network_name already exists, skipping"
        else
            log "INFO" "Creating network: $network_name ($subnet)"

            local extra_opts=""
            if [[ "$network_name" == "leveredge-data" ]]; then
                extra_opts="--internal"
            fi

            docker network create \
                --driver bridge \
                --subnet "$subnet" \
                $extra_opts \
                --label "com.leveredge.network=$network_name" \
                "$network_name" || log "WARN" "Failed to create network $network_name"
        fi
    done

    log "INFO" "Docker networks configured"
    docker network ls | grep leveredge
}

# ============================================================================
# CERBERUS CONFIGURATION
# ============================================================================

install_cerberus_config() {
    if $SKIP_CERBERUS; then
        log "INFO" "Skipping CERBERUS configuration (--skip-cerberus)"
        return
    fi

    log "INFO" "Installing CERBERUS monitoring configuration..."

    if $DRY_RUN; then
        log "DRY" "Would copy monitoring-config.yaml to /opt/leveredge/cerberus/config/"
        return
    fi

    # Create CERBERUS directories
    mkdir -p /opt/leveredge/cerberus/config
    mkdir -p /opt/leveredge/cerberus/logs
    mkdir -p /opt/leveredge/cerberus/data

    # Copy configuration
    cp "$SCRIPT_DIR/cerberus/monitoring-config.yaml" /opt/leveredge/cerberus/config/monitoring-config.yaml
    chmod 644 /opt/leveredge/cerberus/config/monitoring-config.yaml

    # Create empty threat log if it doesn't exist
    touch /opt/leveredge/cerberus/logs/threats.log
    chmod 644 /opt/leveredge/cerberus/logs/threats.log

    log "INFO" "CERBERUS configuration installed"

    # If CERBERUS container is running, trigger config reload
    if docker ps --format '{{.Names}}' | grep -q cerberus; then
        log "INFO" "Signaling CERBERUS to reload configuration..."
        docker exec cerberus kill -HUP 1 2>/dev/null || log "WARN" "Could not signal CERBERUS"
    fi
}

# ============================================================================
# POST-INSTALLATION VERIFICATION
# ============================================================================

verify_installation() {
    log "INFO" "Verifying installation..."

    local errors=0

    # Check Fail2ban
    if ! $SKIP_FAIL2BAN; then
        if systemctl is-active --quiet fail2ban; then
            log "INFO" "Fail2ban: OK"
        else
            log "ERROR" "Fail2ban: FAILED"
            ((errors++))
        fi
    fi

    # Check UFW
    if ! $SKIP_UFW; then
        if ufw status | grep -q "Status: active"; then
            log "INFO" "UFW: OK"
        else
            log "ERROR" "UFW: FAILED"
            ((errors++))
        fi
    fi

    # Check Docker networks
    if ! $SKIP_DOCKER; then
        local required_networks=("leveredge-dmz" "leveredge-app" "leveredge-agents" "leveredge-data" "leveredge-monitor")
        local missing_networks=()

        for net in "${required_networks[@]}"; do
            if ! docker network ls --format '{{.Name}}' | grep -q "^${net}$"; then
                missing_networks+=("$net")
            fi
        done

        if [[ ${#missing_networks[@]} -eq 0 ]]; then
            log "INFO" "Docker networks: OK"
        else
            log "ERROR" "Docker networks: MISSING - ${missing_networks[*]}"
            ((errors++))
        fi
    fi

    # Check CERBERUS config
    if ! $SKIP_CERBERUS; then
        if [[ -f /opt/leveredge/cerberus/config/monitoring-config.yaml ]]; then
            log "INFO" "CERBERUS config: OK"
        else
            log "ERROR" "CERBERUS config: FAILED"
            ((errors++))
        fi
    fi

    echo ""
    if [[ $errors -eq 0 ]]; then
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║               INSTALLATION COMPLETED SUCCESSFULLY              ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║          INSTALLATION COMPLETED WITH $errors ERROR(S)              ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    fi
    echo ""

    return $errors
}

print_next_steps() {
    echo ""
    echo -e "${CYAN}Next Steps:${NC}"
    echo ""
    echo "1. Review Fail2ban status:"
    echo "   sudo fail2ban-client status"
    echo ""
    echo "2. Check UFW rules:"
    echo "   sudo ufw status verbose"
    echo ""
    echo "3. Verify Docker networks:"
    echo "   docker network ls | grep leveredge"
    echo ""
    echo "4. Apply Docker security overlay:"
    echo "   docker-compose -f docker-compose.yml -f $SCRIPT_DIR/docker/docker-compose.security.yml up -d"
    echo ""
    echo "5. Configure HERMES API key for notifications:"
    echo "   export HERMES_API_KEY='your-api-key'"
    echo ""
    echo "6. Test SSH access before closing current session!"
    echo ""
    echo -e "${YELLOW}IMPORTANT:${NC} Verify you can still SSH into the server before"
    echo "closing your current session. If locked out, use the"
    echo "backup at: $BACKUP_DIR"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-ufw)
                SKIP_UFW=true
                shift
                ;;
            --skip-fail2ban)
                SKIP_FAIL2BAN=true
                shift
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --skip-cerberus)
                SKIP_CERBERUS=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --dry-run       Show what would be done without making changes"
                echo "  --skip-ufw      Skip UFW configuration"
                echo "  --skip-fail2ban Skip Fail2ban configuration"
                echo "  --skip-docker   Skip Docker network configuration"
                echo "  --skip-cerberus Skip CERBERUS configuration"
                echo "  --force         Skip confirmation prompts"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

main() {
    parse_args "$@"

    print_banner

    if $DRY_RUN; then
        log "INFO" "Running in DRY-RUN mode - no changes will be made"
        echo ""
    fi

    check_root
    check_dependencies

    echo ""
    echo "This script will install security hardening for LeverEdge:"
    echo ""
    [[ $SKIP_FAIL2BAN == false ]] && echo "  - Fail2ban intrusion prevention"
    [[ $SKIP_UFW == false ]] && echo "  - UFW firewall rules"
    [[ $SKIP_DOCKER == false ]] && echo "  - Docker network isolation"
    [[ $SKIP_CERBERUS == false ]] && echo "  - CERBERUS monitoring configuration"
    echo ""

    confirm_action "This will modify system security settings."

    create_backup

    install_fail2ban
    install_ufw
    install_docker_networks
    install_cerberus_config

    if ! $DRY_RUN; then
        verify_installation
        print_next_steps
    else
        log "DRY" "Dry run complete. No changes were made."
    fi
}

main "$@"
