# Leveredge Infrastructure

The Leveredge automation platform with agent-based architecture.

## Architecture Overview

```
+---------------------------+
|      CONTROL PLANE        |
|  (n8n @ port 5679)       |
|                          |
|  +-------------------+   |
|  |   Agent Fleet     |   |
|  | ATLAS, HEPHAESTUS |   |
|  | ATHENA, AEGIS     |   |
|  | CHRONOS, HADES    |   |
|  | HERMES, ARGUS     |   |
|  | ALOY, ARIA        |   |
|  +-------------------+   |
|           |              |
|  +-------------------+   |
|  |    EVENT BUS      |   |
|  |   (port 8099)     |   |
|  +-------------------+   |
+-----------|--------------+
            |
+-----------v--------------+
|       DATA PLANE         |
|                          |
|  +----------+ +-------+  |
|  |   PROD   | |  DEV  |  |
|  | n8n:5678 | |n8n:5680| |
|  +----------+ +-------+  |
+--------------------------+
            |
+-----------v--------------+
|         GAIA             |
|  (Emergency Recovery)    |
|  Can rebuild everything  |
+--------------------------+
```

## Directory Structure

```
/opt/leveredge/
+-- gaia/                   # Emergency recovery system
|   +-- gaia.py            # Main GAIA logic
|   +-- restore.sh         # Shell wrapper
|   +-- emergency-telegram.py  # Standalone emergency bot
|   +-- config.yaml        # Configuration
|   +-- .telegram_token    # Bot token (configure manually)
|   +-- .2fa_secret        # 2FA secret (auto-generated)
|   +-- .authorized_users  # Telegram user IDs (configure manually)
|
+-- control-plane/          # Control plane components
|   +-- n8n/               # Control n8n instance
|   +-- agents/            # FastAPI agent services
|   +-- workflows/         # n8n workflow definitions
|   +-- dashboards/        # Agent web dashboards
|   +-- docs/              # Documentation
|   +-- event-bus/         # Event bus service
|       +-- event_bus.py   # FastAPI event bus
|       +-- events.db      # SQLite database
|
+-- data-plane/             # Data plane environments
|   +-- prod/              # Production environment
|   +-- dev/               # Development environment
|
+-- shared/                 # Shared resources
|   +-- scripts/           # Utility scripts
|   +-- templates/         # Configuration templates
|   +-- backups/           # Backup storage
|   |   +-- control-plane/ # Control plane backups
|   |   +-- prod/          # Production backups
|   |   +-- dev/           # Development backups
|   +-- credentials/       # Credential storage
|
+-- monitoring/             # Monitoring stack
    +-- prometheus/        # Prometheus configuration
    +-- grafana/           # Grafana dashboards
```

## Quick Start

### Check System Health
```bash
/opt/leveredge/gaia/restore.sh health
```

### List Available Backups
```bash
/opt/leveredge/gaia/restore.sh list
```

### Check Event Bus
```bash
curl http://localhost:8099/health
curl http://localhost:8099/events
```

## Emergency Procedures

### Full System Restore (from server)
```bash
/opt/leveredge/gaia/restore.sh full --yes
```

### Restore Specific Component
```bash
/opt/leveredge/gaia/restore.sh restore control-plane --yes
/opt/leveredge/gaia/restore.sh restore prod --yes
/opt/leveredge/gaia/restore.sh restore dev --yes
```

### Emergency Telegram Restore
1. Message @GaiaEmergencyBot
2. Use /restore <target> or /fullrestore
3. Enter 2FA code when prompted

## Services

| Service | Port | Description |
|---------|------|-------------|
| Event Bus | 8099 | Agent communication bus |
| Control n8n | 5679 | Control plane workflow engine |
| Prod n8n | 5678 | Production workflow engine |
| Dev n8n | 5680 | Development workflow engine |

## Configuration

### GAIA Emergency Bot
1. Get bot token from @BotFather
2. Add to `/opt/leveredge/gaia/.telegram_token`
3. Add your Telegram user ID to `/opt/leveredge/gaia/.authorized_users`
4. Start service: `systemctl --user start gaia-emergency`

### Event Bus
The event bus runs automatically as a systemd user service.
```bash
systemctl --user status event-bus
```

## Phase 0 Complete

This installation includes:
- GAIA emergency recovery system
- Event Bus for agent communication
- Directory structure for all components

Next phases will add:
- Phase 1: Control plane n8n + ATLAS
- Phase 2: HEPHAESTUS + AEGIS
- Phase 3: CHRONOS + HADES
- Phase 4: Remaining agents
- Phase 5: Data plane sync
