# Installation Guide

This guide covers installing and deploying LeverEdge infrastructure.

## Prerequisites

### System Requirements

- **OS**: Ubuntu 22.04+ or compatible Linux distribution
- **RAM**: Minimum 16GB (32GB recommended)
- **Storage**: 100GB+ SSD
- **CPU**: 4+ cores

### Software Requirements

- Docker 24.0+
- Docker Compose 2.0+
- Python 3.11+
- Node.js 18+ (for n8n)
- Git

## Directory Structure

```
/opt/leveredge/
├── gaia/                    # Tier 0 - Emergency restore
├── control-plane/
│   ├── n8n/                 # Control plane n8n (5679)
│   ├── agents/              # FastAPI agent backends
│   │   ├── atlas/
│   │   ├── hephaestus/
│   │   ├── aegis/
│   │   ├── chronos/
│   │   └── ...
│   ├── workflows/           # n8n workflow exports
│   └── event-bus/           # SQLite message bus
├── data-plane/
│   ├── prod/
│   │   ├── n8n/            # Production n8n (5678)
│   │   └── supabase/       # Production database
│   └── dev/
│       ├── n8n/            # Development n8n (5680)
│       └── supabase/       # Development database
├── shared/
│   ├── scripts/            # CLI tools
│   └── backups/            # CHRONOS backup destination
├── config/                  # Configuration files
└── monitoring/              # Prometheus + Grafana
```

## Installation Steps

### 1. Clone the Repository

```bash
sudo mkdir -p /opt/leveredge
sudo chown $USER:$USER /opt/leveredge
cd /opt/leveredge
git clone https://github.com/leveredge/leveredge.git .
```

### 2. Install Python Dependencies

```bash
# Install Python 3.11
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip

# Create virtual environment for shared modules
python3.11 -m venv /opt/leveredge/control-plane/shared/venv
source /opt/leveredge/control-plane/shared/venv/bin/activate
pip install fastapi uvicorn httpx anthropic
```

### 3. Configure Environment Variables

Create environment files for each component:

```bash
# Control plane n8n
cp /opt/leveredge/control-plane/n8n/.env.example /opt/leveredge/control-plane/n8n/.env

# Production n8n
cp /opt/leveredge/data-plane/prod/n8n/.env.example /opt/leveredge/data-plane/prod/n8n/.env

# Agent configuration
cp /opt/leveredge/config/agent-registry.yaml.example /opt/leveredge/config/agent-registry.yaml
```

Edit each `.env` file with your specific configuration.

### 4. Start Docker Services

```bash
# Start control plane n8n
cd /opt/leveredge/control-plane/n8n
docker compose up -d

# Start production n8n
cd /opt/leveredge/data-plane/prod/n8n
docker compose up -d

# Start Supabase
cd /opt/leveredge/data-plane/prod/supabase
docker compose up -d
```

### 5. Start Control Plane Agents

Start the Event Bus first (all agents depend on it):

```bash
cd /opt/leveredge/control-plane/event-bus
sudo nohup /usr/local/bin/python3.11 -m uvicorn event_bus:app --host 0.0.0.0 --port 8099 > /tmp/eventbus.log 2>&1 &
```

Then start core agents:

```bash
# ATLAS - Orchestration
cd /opt/leveredge/control-plane/agents/atlas
sudo nohup /usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007 > /tmp/atlas.log 2>&1 &

# HEPHAESTUS - Builder/MCP
cd /opt/leveredge/control-plane/agents/hephaestus
sudo nohup /usr/local/bin/python3.11 -m uvicorn hephaestus_mcp_server:app --host 0.0.0.0 --port 8011 > /tmp/hephaestus.log 2>&1 &

# Continue for other agents...
```

!!! tip "Use Systemd for Production"
    For production deployments, convert agents to systemd services for auto-restart and better management. See [Operations Guide](../operations/monitoring.md) for systemd configuration.

### 6. Verify Installation

Check that all services are running:

```bash
# Check Docker containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check agent health
curl -s http://localhost:8007/health  # ATLAS
curl -s http://localhost:8011/health  # HEPHAESTUS
curl -s http://localhost:8099/health  # Event Bus
```

## Post-Installation

### Initialize Database Schema

Run the Supabase migrations:

```bash
cd /opt/leveredge/data-plane/prod/supabase
docker exec -it supabase-db-prod psql -U postgres -d postgres -f /migrations/init.sql
```

### Import n8n Workflows

Import the agent workflows into control plane n8n:

1. Access control.n8n.leveredgeai.com
2. Import workflows from `/opt/leveredge/control-plane/workflows/`

### Configure Credentials

Use AEGIS to manage credentials:

```bash
# Sync credentials from n8n
curl -X POST http://localhost:8012/sync

# List credentials
curl http://localhost:8012/credentials
```

## Troubleshooting Installation

### Port Conflicts

Check for port conflicts:

```bash
sudo lsof -i :8007  # ATLAS
sudo lsof -i :5678  # PROD n8n
```

### Agent Won't Start

1. Check logs: `tail -50 /tmp/atlas.log`
2. Run manually to see errors:
   ```bash
   cd /opt/leveredge/control-plane/agents/atlas
   /usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007
   ```

### Docker Issues

```bash
# Check Docker status
sudo systemctl status docker

# Check container logs
docker compose logs -f
```

## Next Steps

- [Configure the system](configuration.md)
- [Explore agent capabilities](../agents/core.md)
- [Set up monitoring](../operations/monitoring.md)
