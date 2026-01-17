#!/bin/bash
#===============================================================================
# LeverEdge Fleet Service Installer
# /opt/leveredge/shared/systemd/install-fleet-service.sh
#
# Installs the LeverEdge fleet systemd service for automatic startup on boot.
# Requires: sudo privileges
#
# Usage:
#   sudo ./install-fleet-service.sh          # Install and enable
#   sudo ./install-fleet-service.sh --start  # Install, enable, and start
#   sudo ./install-fleet-service.sh --remove # Remove the service
#===============================================================================

set -euo pipefail

# Configuration
SYSTEMD_DIR="/etc/systemd/system"
LEVEREDGE_SYSTEMD="/opt/leveredge/shared/systemd"
SERVICE_NAME="leveredge-fleet.service"
LOG_DIR="/var/log/leveredge"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

#===============================================================================
# Utility Functions
#===============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_files() {
    local files=(
        "$LEVEREDGE_SYSTEMD/$SERVICE_NAME"
        "$LEVEREDGE_SYSTEMD/fleet-start.sh"
        "$LEVEREDGE_SYSTEMD/fleet-stop.sh"
        "$LEVEREDGE_SYSTEMD/fleet-health.sh"
    )

    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
}

#===============================================================================
# Install Function
#===============================================================================
install_service() {
    log_info "Installing LeverEdge Fleet Service..."

    # Check prerequisites
    check_root
    check_files

    # Create log directory
    log_info "Creating log directory..."
    mkdir -p "$LOG_DIR"
    chown damon:damon "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    log_success "Log directory created: $LOG_DIR"

    # Make scripts executable
    log_info "Setting script permissions..."
    chmod +x "$LEVEREDGE_SYSTEMD/fleet-start.sh"
    chmod +x "$LEVEREDGE_SYSTEMD/fleet-stop.sh"
    chmod +x "$LEVEREDGE_SYSTEMD/fleet-health.sh"
    log_success "Scripts are executable"

    # Copy service file
    log_info "Installing systemd service..."
    cp "$LEVEREDGE_SYSTEMD/$SERVICE_NAME" "$SYSTEMD_DIR/$SERVICE_NAME"
    log_success "Service file installed: $SYSTEMD_DIR/$SERVICE_NAME"

    # Install individual agent services if they exist
    if [ -d "$LEVEREDGE_SYSTEMD/agent-services" ]; then
        log_info "Installing individual agent services..."
        for service_file in "$LEVEREDGE_SYSTEMD/agent-services"/*.service; do
            if [ -f "$service_file" ]; then
                local base_name
                base_name=$(basename "$service_file")
                cp "$service_file" "$SYSTEMD_DIR/$base_name"
                log_info "  Installed: $base_name"
            fi
        done
        log_success "Agent services installed"
    fi

    # Reload systemd
    log_info "Reloading systemd daemon..."
    systemctl daemon-reload
    log_success "Systemd daemon reloaded"

    # Enable the service
    log_info "Enabling service for boot..."
    systemctl enable "$SERVICE_NAME"
    log_success "Service enabled: $SERVICE_NAME"

    echo ""
    log_success "Installation complete!"
    echo ""
    echo "Commands:"
    echo "  sudo systemctl start leveredge-fleet    # Start the fleet"
    echo "  sudo systemctl stop leveredge-fleet     # Stop the fleet"
    echo "  sudo systemctl status leveredge-fleet   # Check status"
    echo "  sudo journalctl -u leveredge-fleet -f   # View logs"
    echo ""
}

#===============================================================================
# Start Function
#===============================================================================
start_service() {
    log_info "Starting LeverEdge Fleet..."
    systemctl start "$SERVICE_NAME"

    # Wait a moment and check status
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Fleet started successfully"
        echo ""
        systemctl status "$SERVICE_NAME" --no-pager
    else
        log_error "Fleet failed to start"
        echo ""
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager
        exit 1
    fi
}

#===============================================================================
# Remove Function
#===============================================================================
remove_service() {
    check_root

    log_info "Removing LeverEdge Fleet Service..."

    # Stop if running
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_info "Stopping service..."
        systemctl stop "$SERVICE_NAME"
    fi

    # Disable
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_info "Disabling service..."
        systemctl disable "$SERVICE_NAME"
    fi

    # Remove service files
    if [ -f "$SYSTEMD_DIR/$SERVICE_NAME" ]; then
        log_info "Removing service file..."
        rm "$SYSTEMD_DIR/$SERVICE_NAME"
    fi

    # Remove agent services
    for service_file in "$SYSTEMD_DIR"/leveredge-*.service; do
        if [ -f "$service_file" ]; then
            local base_name
            base_name=$(basename "$service_file")
            log_info "Removing: $base_name"
            rm "$service_file"
        fi
    done

    # Reload systemd
    systemctl daemon-reload

    log_success "Service removed"
}

#===============================================================================
# Status Function
#===============================================================================
show_status() {
    echo ""
    echo "LeverEdge Fleet Service Status"
    echo "==============================="
    echo ""

    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_success "Service is RUNNING"
    else
        log_warn "Service is NOT RUNNING"
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_success "Service is ENABLED (will start on boot)"
    else
        log_warn "Service is DISABLED (will not start on boot)"
    fi

    echo ""
    echo "Recent logs:"
    echo "------------"
    journalctl -u "$SERVICE_NAME" -n 10 --no-pager 2>/dev/null || echo "(no logs yet)"
    echo ""
}

#===============================================================================
# Main
#===============================================================================
main() {
    case "${1:-install}" in
        install|--install)
            install_service
            ;;
        start|--start)
            install_service
            start_service
            ;;
        remove|--remove|uninstall|--uninstall)
            remove_service
            ;;
        status|--status)
            show_status
            ;;
        -h|--help)
            echo "LeverEdge Fleet Service Installer"
            echo ""
            echo "Usage: sudo $0 [OPTION]"
            echo ""
            echo "Options:"
            echo "  install   Install and enable the service (default)"
            echo "  --start   Install, enable, and start the service"
            echo "  --remove  Remove the service"
            echo "  --status  Show service status"
            echo "  --help    Show this help"
            echo ""
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

main "$@"
