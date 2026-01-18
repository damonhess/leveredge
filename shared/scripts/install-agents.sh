#!/bin/bash
# install-agents.sh - Install and start all agent services
# Must be run with sudo

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

echo "=== Installing Agent Services ==="

# First generate all service files
/opt/leveredge/shared/scripts/deploy-all-agents.sh

# Copy to systemd
echo ""
echo "Copying service files to /etc/systemd/system/..."
cp /tmp/leveredge-*.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable and start all
echo ""
echo "Enabling and starting services..."

for svc in /tmp/leveredge-*.service; do
    name=$(basename $svc)
    svc_name=${name%.service}

    systemctl enable $svc_name 2>/dev/null || true
    systemctl start $svc_name 2>/dev/null || true

    if systemctl is-active --quiet $svc_name; then
        echo "  [OK] $svc_name"
    else
        echo "  [FAIL] $svc_name"
    fi
done

echo ""
echo "=== Done ==="
echo ""
echo "Check status: systemctl status leveredge-*"
echo "Check all: /opt/leveredge/shared/scripts/check-all-agents.sh"
