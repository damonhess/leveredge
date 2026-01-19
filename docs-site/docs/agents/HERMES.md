# HERMES

**Port:** 8014
**Domain:** THE_KEEP
**Status:** ✅ Operational

---

## Identity

**Name:** HERMES
**Title:** The Messenger
**Tagline:** "Swift as thought"

## Purpose

HERMES handles all notifications and alerts across the LeverEdge ecosystem. It provides multi-channel delivery for system alerts, user notifications, and inter-agent messages.

---

## API Endpoints

### Health
```
GET /health
```

### Send Notification
```
POST /notify
{
  "channel": "slack|email|sms|webhook",
  "recipient": "target",
  "message": "Notification content",
  "priority": "critical|high|normal|low",
  "metadata": {}
}
```

### Bulk Notify
```
POST /notify/bulk
{
  "notifications": [...]
}
```

### Templates
```
GET /templates
POST /templates
GET /templates/{id}
```

---

## Channels

| Channel | Description | Config Required |
|---------|-------------|-----------------|
| `slack` | Slack webhook | SLACK_WEBHOOK_URL |
| `email` | SMTP email | SMTP_* vars |
| `sms` | Twilio SMS | TWILIO_* vars |
| `webhook` | Custom webhook | Target URL |
| `push` | Browser push | VAPID keys |

---

## Priority Levels

| Priority | Behavior |
|----------|----------|
| `critical` | Immediate, all channels |
| `high` | Immediate, primary channel |
| `normal` | Queued, batch delivery |
| `low` | Digest, daily summary |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `hermes_notify` | Send notification |
| `hermes_alert` | Send system alert |
| `hermes_status` | Check delivery status |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `notifications` | Notification records |
| `notification_templates` | Message templates |
| `delivery_log` | Delivery history |

---

## Integration Points

### Calls To
- Slack API
- SMTP servers
- Twilio API
- Custom webhooks

### Called By
- All agents for alerts
- PANOPTES for monitoring alerts
- CHRONOS for backup notifications
- ASCLEPIUS for health alerts

---

## Configuration

Environment variables:
- `SLACK_WEBHOOK_URL` - Slack incoming webhook
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` - Email config
- `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM` - SMS config

---

## Deployment

```bash
docker run -d --name hermes \
  --network leveredge-network \
  -p 8014:8014 \
  -e SLACK_WEBHOOK_URL="$SLACK_WEBHOOK" \
  hermes:dev
```

---

## Changelog

- 2026-01-19: Documentation created
- 2026-01-16: Initial deployment
