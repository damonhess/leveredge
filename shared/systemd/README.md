# LeverEdge Fleet Systemd Configuration

Auto-start on boot configuration for the entire LeverEdge fleet.

## Overview

This configuration enables automatic startup of all LeverEdge services when the system boots:

- Docker infrastructure (Supabase, n8n instances)
- Event Bus (central message router)
- All agent services (30+ agents)
- Health verification after startup
- Boot notification via HERMES

## Quick Start

### Installation

```bash
# Install and enable (requires sudo)
sudo ./install-fleet-service.sh

# Install, enable, AND start immediately
sudo ./install-fleet-service.sh --start
```

### Management Commands

```bash
# Start the fleet
sudo systemctl start leveredge-fleet

# Stop the fleet
sudo systemctl stop leveredge-fleet

# Check status
sudo systemctl status leveredge-fleet

# View logs
sudo journalctl -u leveredge-fleet -f

# Disable auto-start on boot
sudo systemctl disable leveredge-fleet

# Enable auto-start on boot
sudo systemctl enable leveredge-fleet
```

## Files

| File | Description |
|------|-------------|
| `leveredge-fleet.service` | Master systemd service file |
| `fleet-start.sh` | Startup script - starts all services in order |
| `fleet-stop.sh` | Shutdown script - graceful shutdown |
| `fleet-health.sh` | Health check script - verify all services |
| `install-fleet-service.sh` | Installer script (requires sudo) |
| `agent-services/` | Individual agent service files |

## Startup Sequence

The fleet starts in this order to respect dependencies:

1. **Docker Infrastructure**
   - Supabase (PostgreSQL, Kong, Auth, etc.)
   - n8n instances (prod, dev, control)

2. **Event Bus** (port 8099)
   - Central message router
   - Must be up before agents

3. **Core Agents**
   - HERMES (8014) - Notifications
   - AEGIS (8012) - Credentials
   - HADES (8008) - System admin
   - GAIA (8000) - Orchestration

4. **All Other Agents**
   - Started in parallel for speed

5. **Health Verification**
   - All endpoints checked
   - Results logged

6. **Boot Notification**
   - Telegram message via HERMES
   - Includes status summary

## Health Check

Run health check manually:

```bash
# Basic health check
./fleet-health.sh

# Verbose output (shows all services)
./fleet-health.sh --verbose

# JSON output (for automation)
./fleet-health.sh --json

# Notify on failure
./fleet-health.sh --notify
```

Exit codes:
- `0` - All healthy
- `1` - Some services unhealthy
- `2` - Critical services down

## Logs

Logs are stored in:
- `/var/log/leveredge/fleet-start.log` - Startup logs
- `/var/log/leveredge/fleet-stop.log` - Shutdown logs
- `journalctl -u leveredge-fleet` - Systemd journal

View logs for specific agents:
```bash
journalctl -u hermes -f
journalctl -u aegis -f
journalctl -u event-bus -f
```

## Agent Services

Individual agent services can be managed separately:

```bash
# Start specific agent
sudo systemctl start hermes

# Stop specific agent
sudo systemctl stop hermes

# Restart specific agent
sudo systemctl restart hermes

# View agent status
sudo systemctl status hermes
```

### Available Agent Services

| Service | Port | Description |
|---------|------|-------------|
| event-bus | 8099 | Central message router |
| gaia | 8000 | Central orchestration |
| hades | 8008 | System administrator |
| chronos | 8010 | Time & scheduling |
| hephaestus | 8011 | Code builder |
| aegis | 8012 | Credential management |
| athena | 8013 | Strategy & decisions |
| hermes | 8014 | Notifications & approvals |
| aloy | 8015 | Memory & context |
| argus | 8016 | Monitoring |
| chiron | 8017 | Health & wellness |
| scholar | 8018 | Research & learning |
| atlas | 8019 | Infrastructure |
| calliope | 8020 | Creative content |
| clio | 8021 | History & documentation |
| erato | 8022 | Poetry & lyrics |
| muse | 8023 | Creative inspiration |
| thalia | 8024 | Web/UI design |
| cerberus | 8025 | Security & access |
| port-manager | 8026 | Investment portfolio |
| gym-coach | 8027 | Fitness & training |
| nutritionist | 8028 | Nutrition & diet |
| meal-planner | 8029 | Meal planning |
| academic-guide | 8030 | Education & study |
| eros | 8031 | Relationships |
| heracles | 8032 | Physical tasks |
| librarian | 8033 | Knowledge management |
| mentor | 8034 | Coaching & guidance |
| themis | 8035 | Legal & compliance |
| plutus | 8036 | Finance & budgeting |
| procurement | 8037 | Purchasing |
| iris | 8038 | Communication |
| sentinel | 8039 | Security monitoring |
| varys | 8040 | Intelligence gathering |

## Uninstallation

```bash
# Remove the service
sudo ./install-fleet-service.sh --remove
```

This will:
- Stop the service if running
- Disable auto-start
- Remove service files from systemd

## Troubleshooting

### Service won't start

1. Check logs:
   ```bash
   journalctl -u leveredge-fleet -n 50
   ```

2. Verify Docker is running:
   ```bash
   sudo systemctl status docker
   ```

3. Check disk space:
   ```bash
   df -h /
   ```

### Agent not responding

1. Check individual agent status:
   ```bash
   sudo systemctl status <agent-name>
   ```

2. View agent logs:
   ```bash
   journalctl -u <agent-name> -f
   ```

3. Restart the agent:
   ```bash
   sudo systemctl restart <agent-name>
   ```

### Docker containers not starting

1. Check Docker status:
   ```bash
   docker ps -a
   ```

2. View container logs:
   ```bash
   docker logs <container-name>
   ```

3. Restart Docker:
   ```bash
   sudo systemctl restart docker
   ```

### HERMES notifications not working

1. Verify HERMES is running:
   ```bash
   curl http://localhost:8014/health
   ```

2. Check Telegram token is configured:
   ```bash
   # Token should be in environment or /opt/leveredge/control-plane/agents/hermes/.telegram_token
   ```

## Configuration

### Environment Variables

The fleet scripts use these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LEVEREDGE_HOME` | `/opt/leveredge` | Base directory |
| `HEALTH_TIMEOUT` | `120` | Health check timeout (seconds) |
| `GRACEFUL_TIMEOUT` | `30` | Shutdown timeout (seconds) |

### Customizing Startup

Edit `fleet-start.sh` to:
- Change startup order
- Add/remove agents
- Modify health check endpoints
- Adjust timeouts

### Customizing Notifications

Edit the `send_boot_notification` function in `fleet-start.sh` to customize:
- Message format
- Priority level
- Additional metadata

## Security Notes

- Service files run as user `damon` (not root)
- Scripts have restricted permissions
- Credentials are loaded from secure locations
- Health endpoints are localhost-only

## Maintenance

### Updating Service Files

After modifying service files:

```bash
# Copy updated files
sudo cp agent-services/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Restart affected services
sudo systemctl restart <service-name>
```

### Backup Before Changes

Always backup before making changes:

```bash
# Backup all service files
cp -r /etc/systemd/system/leveredge-*.service /tmp/backup/
```
