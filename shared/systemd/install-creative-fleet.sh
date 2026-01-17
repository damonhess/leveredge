#!/bin/bash
# Install systemd services for Creative Fleet
# Run with: sudo ./install-creative-fleet.sh

set -e

AGENTS="muse:8030 calliope:8031 thalia:8032 erato:8033 clio:8034"

echo "Creating systemd service files..."

for entry in $AGENTS; do
    NAME=$(echo $entry | cut -d: -f1)
    PORT=$(echo $entry | cut -d: -f2)
    UPPER=$(echo $NAME | tr '[:lower:]' '[:upper:]')

    cat > /etc/systemd/system/${NAME}.service << EOF
[Unit]
Description=${UPPER} Creative Agent (Port ${PORT})
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=damon
Group=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/${NAME}
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=/opt/leveredge/shared/llm-api-keys.env
ExecStart=/usr/local/bin/python3.11 -m uvicorn ${NAME}:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo "Created ${NAME}.service"
done

echo ""
echo "Reloading systemd..."
systemctl daemon-reload

echo ""
echo "Stopping any nohup processes..."
for entry in $AGENTS; do
    PORT=$(echo $entry | cut -d: -f2)
    pkill -f "uvicorn.*:${PORT}" 2>/dev/null || true
done
sleep 2

echo ""
echo "Enabling and starting services..."
for entry in $AGENTS; do
    NAME=$(echo $entry | cut -d: -f1)
    systemctl enable ${NAME}
    systemctl start ${NAME}
    echo "Started ${NAME}"
done

echo ""
echo "Status check:"
for entry in $AGENTS; do
    NAME=$(echo $entry | cut -d: -f1)
    PORT=$(echo $entry | cut -d: -f2)
    STATUS=$(systemctl is-active ${NAME})
    echo "  ${NAME} (${PORT}): ${STATUS}"
done

echo ""
echo "Done! Use 'journalctl -u <agent-name> -f' to view logs"
