# SSL Certificate Monitor

Monitors SSL certificates for all LeverEdge domains and alerts before expiry.

**Port:** 8064

## Features

- **Daily scheduled checks** - Runs automatically at 6 AM UTC
- **14-day alert threshold** - Notifies when certificates expire within 14 days
- **Auto-renewal verification** - Detects Let's Encrypt certificates (auto-renew enabled)
- **HERMES integration** - Sends Telegram alerts for expiring certificates
- **CERBERUS integration** - Reports security events to the security agent
- **Web dashboard** - Visual status overview at `http://localhost:8064/`

## Monitored Domains

- n8n.leveredgeai.com
- dev.n8n.leveredgeai.com
- aria.leveredgeai.com
- dev-aria.leveredgeai.com
- control.n8n.leveredgeai.com
- api.leveredgeai.com

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with summary stats |
| `/` | GET | Web dashboard |
| `/api/certs` | GET | All certificate information |
| `/api/certs/{domain}` | GET | Specific domain certificate |
| `/api/check` | POST | Force check all domains |
| `/api/status` | GET | Monitoring status summary |
| `/api/expiring` | GET | Certificates expiring within threshold |

## Installation

```bash
cd /opt/leveredge/monitoring/ssl
pip install -r requirements.txt
```

## Running

### Direct

```bash
python ssl_monitor.py
```

### With Uvicorn

```bash
uvicorn ssl_monitor:app --host 0.0.0.0 --port 8064
```

### As Systemd Service

```bash
sudo cp ssl-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ssl-monitor
sudo systemctl start ssl-monitor
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_URL` | `http://localhost:8014` | HERMES notification endpoint |
| `CERBERUS_URL` | `http://localhost:8020` | CERBERUS security agent endpoint |
| `SSL_ALERT_DAYS` | `14` | Days before expiry to alert |
| `SSL_CHECK_HOUR` | `6` | Hour (UTC) for daily scheduled check |

## Alert Priorities

| Days Until Expiry | Priority | Action |
|-------------------|----------|--------|
| <= 3 days | CRITICAL | Immediate attention required |
| <= 7 days | HIGH | Urgent renewal needed |
| <= 14 days | NORMAL | Plan renewal soon |
| > 14 days | None | No alert |

## Integration with CERBERUS

The monitor reports SSL events to CERBERUS via POST `/events`:

```json
{
    "event_type": "ssl_certificate_alert",
    "source": "ssl_monitor",
    "severity": "high",
    "description": "SSL certificate for example.com expires in 7 days",
    "raw_data": {
        "domain": "example.com",
        "days_until_expiry": 7,
        "status": "expiring"
    }
}
```

## Integration with HERMES

Alerts are sent via POST `/notify`:

```json
{
    "message": "[SSL Monitor] WARNING: Certificate for example.com expires in 7 days!",
    "priority": "high",
    "channel": "telegram"
}
```

## Data Storage

Certificate data is persisted to `/opt/leveredge/monitoring/ssl/data/certificates.json` and survives restarts.

## Dashboard

Access the web dashboard at `http://localhost:8064/` to see:

- Total monitored domains
- Valid/invalid certificate counts
- Certificates expiring soon
- Detailed certificate information per domain
- Manual "Force Check All" button

## Troubleshooting

### Certificate check fails with "Connection refused"

The domain may not have HTTPS enabled or the server is down.

### DNS resolution failed

Check that the domain resolves correctly:
```bash
nslookup example.com
```

### SSL error

The certificate may be invalid, expired, or have a hostname mismatch.

### HERMES notification failed

Ensure HERMES is running at the configured URL:
```bash
curl http://localhost:8014/health
```
