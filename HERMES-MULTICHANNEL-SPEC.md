# HERMES Multi-Channel Routing

*Quick enhancement - January 16, 2026*

## Current State
- `channel` parameter exists but is ignored
- Always sends to Telegram

## Target State
Route notifications by channel:
- `telegram` → Telegram Bot API
- `event-bus` → Event Bus (for agent-to-agent)
- `slack` → Slack webhook (future)
- `email` → SMTP (future)

## Update /opt/leveredge/control-plane/agents/hermes/hermes.py

Replace the `/notify` endpoint with:

```python
@app.post("/notify")
async def notify(req: NotifyRequest):
    """Send a notification to specified channel"""
    notification_id = str(uuid.uuid4())[:8]
    emoji = get_priority_emoji(req.priority)
    formatted_message = f"{emoji} <b>LeverEdge Alert</b>\n\n{req.message}"
    
    success = False
    
    # Route by channel
    if req.channel == "telegram":
        success = await send_telegram_message(formatted_message)
    elif req.channel == "event-bus":
        try:
            await log_to_event_bus(
                "notification",
                target="broadcast",
                details={"message": req.message, "priority": req.priority}
            )
            success = True
        except:
            success = False
    elif req.channel == "slack":
        # TODO: Implement Slack webhook
        success = False
    elif req.channel == "email":
        # TODO: Implement SMTP
        success = False
    else:
        # Default to telegram
        success = await send_telegram_message(formatted_message)
    
    # Record in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO notifications (notification_id, message, priority, channel, status, delivered_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        notification_id,
        req.message,
        req.priority,
        req.channel,
        "delivered" if success else "failed",
        datetime.utcnow().isoformat() if success else None
    ))
    conn.commit()
    conn.close()

    await log_to_event_bus(
        "notification_sent",
        target=req.channel,
        details={"notification_id": notification_id, "priority": req.priority, "success": success}
    )

    return {
        "notification_id": notification_id,
        "status": "delivered" if success else "failed",
        "channel": req.channel
    }
```

## After Update

```bash
cd /opt/leveredge/control-plane/n8n
docker compose up -d --build hermes
```

## Test

```bash
# Telegram
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{"message": "Telegram test", "channel": "telegram"}'

# Event Bus
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{"message": "Event bus test", "channel": "event-bus"}'
```
