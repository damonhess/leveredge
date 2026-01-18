#!/bin/bash
# create-agent.sh - Generate a new agent from template
#
# Usage: create-agent.sh AGENT_NAME PORT "Description"

set -e

AGENT_NAME=$1
PORT=$2
DESCRIPTION=$3

if [ -z "$AGENT_NAME" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 AGENT_NAME PORT \"Description\""
    echo "Example: $0 MUSE 8030 \"Creative Director\""
    exit 1
fi

AGENT_DIR=$(echo "$AGENT_NAME" | tr '[:upper:]' '[:lower:]' | tr '-' '_')
AGENT_PATH="/opt/leveredge/control-plane/agents/$(echo "$AGENT_NAME" | tr '[:upper:]' '[:lower:]')"

# Create directory
mkdir -p "$AGENT_PATH"

# Copy and customize template
sed -e "s/TEMPLATE/$AGENT_NAME/g" \
    -e "s/8XXX/$PORT/g" \
    -e "s/Template agent description/$DESCRIPTION/g" \
    /opt/leveredge/shared/templates/agent_template.py > "$AGENT_PATH/${AGENT_DIR}.py"

# Create __init__.py
touch "$AGENT_PATH/__init__.py"

# Create requirements.txt
cat > "$AGENT_PATH/requirements.txt" << REQS
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pydantic>=2.5.0
REQS

# Create systemd service
MODULE=$AGENT_DIR
SERVICE_NAME="leveredge-$(echo "$AGENT_NAME" | tr '[:upper:]' '[:lower:]')"

cat > "/tmp/${SERVICE_NAME}.service" << SVCEOF
[Unit]
Description=LeverEdge $AGENT_NAME Agent
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=damon
WorkingDirectory=$AGENT_PATH
ExecStart=/usr/bin/python3 -m uvicorn ${MODULE}:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/leveredge/shared/lib

[Install]
WantedBy=multi-user.target
SVCEOF

echo "Created agent: $AGENT_NAME"
echo "  Directory: $AGENT_PATH"
echo "  Port: $PORT"
echo ""
echo "Next steps:"
echo "  1. Edit $AGENT_PATH/${AGENT_DIR}.py to add your logic"
echo "  2. sudo cp /tmp/${SERVICE_NAME}.service /etc/systemd/system/"
echo "  3. sudo systemctl daemon-reload"
echo "  4. sudo systemctl enable ${SERVICE_NAME}"
echo "  5. sudo systemctl start ${SERVICE_NAME}"
