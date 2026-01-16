# HERMES TELEGRAM CONFIGURATION

*Execute NOW - January 16, 2026*

## Credentials

```
TELEGRAM_BOT_TOKEN=8461818832:AAGIJajYqsF_j8aPA5B5zSes20TaLhOqKY4
TELEGRAM_CHAT_ID=5024815534
```

## Tasks

### 1. Update HERMES FastAPI with Telegram credentials

File: `/opt/leveredge/control-plane/agents/hermes/hermes.py`

Add environment variables and actual Telegram sending:

```python
import os
import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram(message: str, chat_id: str = None):
    """Send message via Telegram bot"""
    if not TELEGRAM_BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not configured"}
    
    target_chat = chat_id or TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "chat_id": target_chat,
            "text": message,
            "parse_mode": "Markdown"
        })
        return response.json()
```

### 2. Update HERMES Docker container with env vars

File: `/opt/leveredge/control-plane/n8n/docker-compose.yml`

Add to hermes service:
```yaml
hermes:
  environment:
    - TELEGRAM_BOT_TOKEN=8461818832:AAGIJajYqsF_j8aPA5B5zSes20TaLhOqKY4
    - TELEGRAM_CHAT_ID=5024815534
```

### 3. Rebuild and restart HERMES

```bash
cd /opt/leveredge/control-plane/n8n
docker compose up -d --build hermes
```

### 4. Test Telegram notification

```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{"message": "🚀 HERMES is alive! LeverEdge notifications working.", "channel": "telegram"}'
```

### 5. Test via n8n webhook

```bash
curl -X POST https://control.n8n.leveredgeai.com/webhook/hermes \
  -H "Content-Type: application/json" \
  -d '{"action": "notify", "message": "Test from HERMES n8n workflow"}'
```

## Verification

You should receive a Telegram message on your phone.

## Security Note

These credentials are now in docker-compose.yml. Future improvement: move to AEGIS vault.
