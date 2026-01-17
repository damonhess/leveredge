#!/bin/bash
# AEGIS V2 Installation Script
# Run with: sudo bash install_v2.sh

set -e

echo "=== AEGIS V2 Installation ==="

# Stop current service
echo "Stopping current AEGIS service..."
systemctl stop aegis 2>/dev/null || true

# Copy new service file
echo "Installing new service file..."
cp /opt/leveredge/control-plane/agents/aegis/aegis.service /etc/systemd/system/aegis.service

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Start service
echo "Starting AEGIS V2..."
systemctl start aegis

# Enable on boot
systemctl enable aegis

# Check status
echo ""
echo "=== Service Status ==="
systemctl status aegis --no-pager

echo ""
echo "=== Health Check ==="
sleep 2
curl -s http://localhost:8012/health | python3 -m json.tool

echo ""
echo "AEGIS V2 installation complete!"
