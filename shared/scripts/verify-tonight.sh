#!/bin/bash
# VERIFICATION SCRIPT - Run after GSD completes
# Created: January 16, 2026

echo "=== PHASE 4 AGENT WEBHOOKS ==="
echo "HERMES:"
curl -s -X POST https://control.n8n.leveredgeai.com/webhook/hermes -H "Content-Type: application/json" -d '{"action":"health"}' || echo "FAIL"

echo ""
echo "ARGUS:"
curl -s -X POST https://control.n8n.leveredgeai.com/webhook/argus -H "Content-Type: application/json" -d '{"action":"health"}' || echo "FAIL"

echo ""
echo "ALOY:"
curl -s -X POST https://control.n8n.leveredgeai.com/webhook/aloy -H "Content-Type: application/json" -d '{"action":"health"}' || echo "FAIL"

echo ""
echo "ATHENA:"
curl -s -X POST https://control.n8n.leveredgeai.com/webhook/athena -H "Content-Type: application/json" -d '{"action":"health"}' || echo "FAIL"

echo ""
echo "=== DATA PLANE ==="
echo "PROD n8n:"
curl -s https://n8n.leveredgeai.com/healthz || echo "FAIL"

echo ""
echo "DEV n8n:"
curl -s https://dev.n8n.leveredgeai.com/healthz || echo "FAIL"

echo ""
echo "=== CONTROL PLANE WORKFLOWS ==="
curl -s -u admin:$N8N_BASIC_AUTH_PASSWORD "https://control.n8n.leveredgeai.com/api/v1/workflows" | jq '.data[] | {name, active}'

echo ""
echo "=== VERIFICATION COMPLETE ==="
