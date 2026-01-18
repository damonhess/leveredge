#!/bin/bash
# deploy-all-agents.sh - Deploy all agents as systemd services
#
# This creates systemd service files for all agents and starts them.
# Requires sudo for systemd operations.

AGENTS_DIR="/opt/leveredge/control-plane/agents"
SERVICE_DIR="/etc/systemd/system"

# Agent definitions: directory:port:module
# Only deploy agents that have Python files
AGENTS=(
    "cerberus:8020:cerberus"
    "port-manager:8021:port_manager"
    "muse:8030:muse"
    "calliope:8031:calliope"
    "thalia:8032:thalia"
    "erato:8033:erato"
    "clio:8034:clio"
    "file-processor:8050:file_processor"
    "voice:8051:voice"
    "nutritionist:8101:nutritionist"
    "meal-planner:8102:meal_planner"
    "academic-guide:8103:academic_guide"
    "eros:8104:eros"
    "gym-coach:8110:gym_coach"
    "heracles:8200:heracles"
    "librarian:8201:librarian"
    "daedalus:8202:daedalus"
    "themis:8203:themis"
    "mentor:8204:mentor"
    "plutus:8205:plutus"
    "procurement:8206:procurement"
    "hephaestus-server:8207:hephaestus_server"
    "atlas-infra:8208:atlas_infra"
    "iris:8209:iris"
    "scribe:8301:scribe"
)

echo "=== Deploying All Agents ==="
echo ""

created=0
skipped=0

for entry in "${AGENTS[@]}"; do
    IFS=':' read -r agent port module <<< "$entry"

    # Check if agent file exists
    if [ ! -f "$AGENTS_DIR/$agent/${module}.py" ]; then
        echo "  SKIP: $agent - no Python file found"
        ((skipped++))
        continue
    fi

    echo "Creating service for $agent (port $port)..."

    # Create service file
    cat > "/tmp/leveredge-${agent}.service" << SVCEOF
[Unit]
Description=LeverEdge ${agent^^} Agent
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=damon
WorkingDirectory=$AGENTS_DIR/$agent
ExecStart=/usr/bin/python3 -m uvicorn ${module}:app --host 0.0.0.0 --port $port
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/leveredge/shared/lib:/opt/leveredge/control-plane/shared

[Install]
WantedBy=multi-user.target
SVCEOF

    ((created++))
done

echo ""
echo "Created $created service files in /tmp/"
echo "Skipped $skipped agents (no Python file)"
echo ""
echo "=== Installation Instructions ==="
echo ""
echo "Run the following commands with sudo:"
echo ""
echo "  # Copy all service files"
echo "  sudo cp /tmp/leveredge-*.service /etc/systemd/system/"
echo ""
echo "  # Reload systemd"
echo "  sudo systemctl daemon-reload"
echo ""
echo "  # Enable all services"
echo "  for svc in /tmp/leveredge-*.service; do"
echo "    name=\$(basename \$svc)"
echo "    sudo systemctl enable \${name%.service}"
echo "  done"
echo ""
echo "  # Start all services"
echo "  for svc in /tmp/leveredge-*.service; do"
echo "    name=\$(basename \$svc)"
echo "    sudo systemctl start \${name%.service}"
echo "  done"
echo ""
echo "Or run: sudo /opt/leveredge/shared/scripts/install-agents.sh"
