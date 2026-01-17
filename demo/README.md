# ARIA Demo Environment

Sandboxed ARIA instance for demos at demo.leveredgeai.com

---

## Overview

This is a fully isolated demo environment that showcases ARIA's capabilities without affecting production data. Each demo session is:

- **Time-limited**: 15-minute session maximum
- **Rate-limited**: 10 messages per session
- **Memory-isolated**: No persistent storage (session memory only)
- **Auto-reset**: Clean slate between demos
- **Watermarked**: Responses clearly indicate demo mode

---

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Access to `/opt/leveredge/` directory
- Caddy reverse proxy configured (see caddy-config.txt)

### 2. Initialize Demo Environment

```bash
# Run initial setup
cd /opt/leveredge/demo
./reset-demo.sh --init

# This will:
# 1. Create demo database
# 2. Load demo data
# 3. Start demo n8n instance
# 4. Import demo workflow
```

### 3. Access Demo

- **Demo URL**: https://demo.leveredgeai.com
- **n8n Admin**: https://demo.n8n.leveredgeai.com (internal only)

---

## Architecture

```
                    Internet
                        |
                        v
              +-----------------+
              |     Caddy       |
              |  Reverse Proxy  |
              +-----------------+
                        |
         +--------------+--------------+
         |                             |
         v                             v
+------------------+          +------------------+
|   PROD ARIA      |          |   DEMO ARIA      |
| aria.leveredgeai |          | demo.leveredgeai |
|    Port 5678     |          |    Port 5681     |
+------------------+          +------------------+
         |                             |
         v                             v
+------------------+          +------------------+
|  PROD Supabase   |          |  Demo Database   |
|   (PostgreSQL)   |          |  (SQLite/Memory) |
+------------------+          +------------------+
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `demo-config.json` | Demo mode settings |
| `demo-data.sql` | Pre-loaded sample data |
| `reset-demo.sh` | Environment reset script |
| `caddy-config.txt` | Caddy configuration snippet |
| `n8n-demo-workflow.json` | Modified ARIA workflow |

---

## Demo Constraints

### Session Limits
- **Duration**: 15 minutes maximum
- **Messages**: 10 per session
- **Storage**: Session memory only (cleared on reset)

### Rate Limiting
- Prevents abuse during public demos
- Counter resets with each new session

### Watermark
All responses include:
```
---
[DEMO MODE] This is a demonstration of ARIA.
Start your free trial at leveredgeai.com
```

---

## Demo Data

Pre-loaded data showcases ARIA's capabilities:

### Sample Tasks
- "Review Q1 marketing strategy" (high priority, due tomorrow)
- "Prepare investor pitch deck" (medium priority, due in 3 days)
- "Send follow-up emails to prospects" (low priority, recurring)
- "Schedule team standup" (completed example)

### Sample Calendar Events
- "Team Standup" - Daily at 9:00 AM
- "Client Discovery Call" - Tomorrow at 2:00 PM
- "Product Review" - This Friday at 10:00 AM

### Sample Memories
- User prefers morning meetings
- Important client: Acme Corp (enterprise deal in progress)
- User's timezone: America/Los_Angeles
- Communication preference: Concise responses

### Demo User Preferences
```json
{
  "name": "Demo User",
  "timezone": "America/Los_Angeles",
  "response_style": "concise",
  "notification_preference": "important_only"
}
```

---

## Suggested Demo Script

### 1. Introduction (2 min)
"ARIA is your AI executive assistant. Let me show you what she can do."

### 2. Task Management (3 min)
```
"What's on my plate today?"
"Add a task: Call John about the partnership deal, high priority"
"What are my high priority items?"
```

### 3. Calendar Integration (3 min)
```
"What's my schedule tomorrow?"
"Do I have any conflicts this week?"
"Find me 30 minutes for a call with Sarah"
```

### 4. Memory & Context (3 min)
```
"What do you remember about Acme Corp?"
"Remember that Acme's decision maker is Sarah Chen, CFO"
"What's the status of my enterprise deals?"
```

### 5. Strategic Assistance (3 min)
```
"Help me prioritize my week"
"I'm feeling overwhelmed - what should I focus on?"
"Draft a follow-up email to Acme about our proposal"
```

### 6. Wrap Up (1 min)
"That's ARIA - your AI executive assistant. Ready to try it yourself?"

---

## Reset Between Demos

```bash
# Quick reset (30 seconds)
./reset-demo.sh

# Full reset with fresh data
./reset-demo.sh --full

# Check demo status
./reset-demo.sh --status
```

---

## Troubleshooting

### Demo not responding
```bash
# Check if demo container is running
docker ps | grep demo-n8n

# Restart demo environment
./reset-demo.sh --restart
```

### Session expired message
Normal behavior - demo session hit 15-minute limit. Run:
```bash
./reset-demo.sh
```

### Rate limit reached
Normal behavior - demo hit 10 message limit. Run:
```bash
./reset-demo.sh
```

---

## Security Considerations

1. **No Production Access**: Demo environment has zero access to production data
2. **Isolated Network**: Demo runs on separate Docker network
3. **No Real Credentials**: Demo uses mock integrations
4. **Session Isolation**: Each demo session is completely isolated
5. **Auto-Cleanup**: Data automatically purged between sessions

---

## Maintenance

### Daily
- Automatic reset via cron (runs every 4 hours)
- Log rotation

### Weekly
- Review demo analytics
- Update demo data if needed
- Check for workflow updates from prod

### Cron Setup
```bash
# Add to crontab
0 */4 * * * /opt/leveredge/demo/reset-demo.sh --quiet
```

---

## Contact

Issues with demo environment? Contact:
- **Slack**: #aria-demo
- **Email**: support@leveredgeai.com

---

*Last Updated: January 2026*
