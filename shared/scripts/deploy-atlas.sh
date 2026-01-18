#!/bin/bash
set -e

echo "Deploying ATLAS Orchestration Engine..."

# Verify directory exists
if [ ! -d "/opt/leveredge/control-plane/agents/atlas-orchestrator" ]; then
    echo "ERROR: ATLAS directory not found"
    exit 1
fi

# Install dependencies using shared venv
cd /opt/leveredge/control-plane/agents/atlas-orchestrator
echo "Installing dependencies..."
/opt/leveredge/shared/venv/bin/pip install -r requirements.txt -q

# Install systemd service
echo "Installing systemd service..."
sudo cp /opt/leveredge/shared/systemd/leveredge-atlas.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable leveredge-atlas

# Restart the service
echo "Starting ATLAS..."
sudo systemctl restart leveredge-atlas

# Wait for startup
sleep 3

# Check health
echo ""
echo "Checking health..."
if curl -s http://localhost:8007/health | grep -q "healthy"; then
    echo "ATLAS is healthy!"
    echo ""
    curl -s http://localhost:8007/status | python3 -m json.tool
else
    echo "ERROR: ATLAS health check failed"
    echo ""
    echo "Recent logs:"
    sudo journalctl -u leveredge-atlas -n 50 --no-pager
    exit 1
fi

echo ""
echo "ATLAS Orchestration Engine deployed successfully!"
echo "   Port: 8007"
echo "   Health: http://localhost:8007/health"
echo "   Chains: http://localhost:8007/chains"
echo "   Agents: http://localhost:8007/agents"
