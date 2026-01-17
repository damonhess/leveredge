# Uptime Monitoring System

Port: **8063**

Real-time monitoring system for the Leveredge Agent Fleet. Tracks availability, response times, and historical uptime statistics for all agents.

## Features

- **Automated Monitoring**: Pings all agent endpoints every 5 minutes
- **Response Time Tracking**: Records response times for performance analysis
- **Downtime Alerts**: Sends alerts to HERMES (port 8014) when agents go down
- **Historical Statistics**: 24-hour, 7-day, and 30-day uptime percentages
- **Interactive Dashboard**: Real-time status visualization

## Monitored Agents

### Core Fleet (8007-8099)
- ATLAS (8007) - Central Orchestrator
- HADES (8008) - Storage & Persistence
- CHRONOS (8010) - Scheduler
- HEPHAESTUS (8011) - Code Forge
- AEGIS (8012) - Security Guardian
- ATHENA (8013) - Knowledge Base
- HERMES (8014) - Messenger
- ALOY (8015) - AI Assistant
- ARGUS (8016) - System Monitor
- CHIRON (8017) - Healer
- SCHOLAR (8018) - Research
- SENTINEL (8019) - Watchdog
- EVENT-BUS (8099) - Event System

### Security Fleet (8020-8021)
- CERBERUS (8020) - Access Control
- PORT-MANAGER (8021) - Port Registry

### Creative Fleet (8030-8034)
- MUSE (8030) - Creative Director
- CALLIOPE (8031) - Content Writer
- THALIA (8032) - Visual Designer
- ERATO (8033) - Video Producer
- CLIO (8034) - Asset Manager

### Personal Fleet (8101-8110)
- GYM-COACH (8110) - Fitness Training
- NUTRITIONIST (8101) - Nutrition Planning
- MEAL-PLANNER (8102) - Meal Planning
- ACADEMIC-GUIDE (8103) - Academic Advisor
- EROS (8104) - Relationship Coach

### Business Fleet (8200-8209)
- HERACLES (8200) - Project Manager
- LIBRARIAN (8201) - Document Manager
- DAEDALUS (8202) - Solution Architect
- THEMIS (8203) - Legal Advisor
- MENTOR (8204) - Career Coach
- PLUTUS (8205) - Financial Advisor
- PROCUREMENT (8206) - Procurement Agent
- HEPHAESTUS-SERVER (8207) - Server Manager
- ATLAS-INFRA (8208) - Infrastructure
- IRIS (8209) - Communications

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check for this service |
| `/` | GET | Dashboard HTML interface |
| `/api/status` | GET | Current status of all agents |
| `/api/history/{agent}` | GET | Historical data for specific agent |
| `/api/uptime` | GET | Overall uptime percentages |
| `/api/ping` | POST | Manually trigger a ping of all agents |
| `/api/agents` | GET | List all monitored agents |

## Installation

```bash
cd /opt/leveredge/monitoring/uptime
pip install -r requirements.txt
```

## Running

```bash
# Direct execution
python uptime.py

# Or with uvicorn
uvicorn uptime:app --host 0.0.0.0 --port 8063
```

## Configuration

Edit the following constants in `uptime.py`:

- `PORT`: Service port (default: 8063)
- `PING_INTERVAL_MINUTES`: How often to ping agents (default: 5)
- `REQUEST_TIMEOUT`: Timeout for health checks (default: 10 seconds)
- `HERMES_URL`: Alert destination (default: http://localhost:8014)

## Data Storage

Historical data is stored in `data/history.json`:
- Automatically pruned to keep 30 days of history
- Records timestamp, status, response time, and errors
- JSON format for easy inspection and backup

## Dashboard Features

- **Summary Cards**: Quick view of online/offline counts
- **Category Grouping**: Agents organized by fleet
- **Status Badges**: Visual up/down/unknown indicators
- **Response Times**: Per-agent response time display
- **Uptime Bars**: Visual uptime percentage indicators
- **Agent Details Modal**: Click any agent for history
- **Auto-refresh**: Updates every 30 seconds
- **Manual Refresh**: Force immediate status update

## Alert Integration

When an agent goes down, an alert is sent to HERMES at `/alert`:

```json
{
  "type": "uptime_alert",
  "severity": "warning",
  "agent": "ATLAS",
  "status": "down",
  "error": "Connection refused",
  "timestamp": "2024-01-15T10:30:00",
  "message": "Agent ATLAS is down: Connection refused"
}
```

Alerts are de-duplicated - only one alert per downtime event.

## Systemd Service (Optional)

Create `/etc/systemd/system/uptime-monitor.service`:

```ini
[Unit]
Description=Leveredge Uptime Monitor
After=network.target

[Service]
Type=simple
User=leveredge
WorkingDirectory=/opt/leveredge/monitoring/uptime
ExecStart=/usr/bin/python3 uptime.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable uptime-monitor
sudo systemctl start uptime-monitor
```
