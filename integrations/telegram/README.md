# ARIA Telegram Bot Integration

Complete setup guide for the ARIA Telegram bot, enabling voice, text, and image interaction with ARIA from Telegram.

## Overview

This integration provides:
- Text message support with full ARIA context
- Voice message transcription and processing
- Image analysis and description
- Bot commands for quick actions
- Session continuity with the web interface

## Prerequisites

1. Telegram account
2. n8n instance running (prod-n8n or dev-n8n)
3. Access to Supabase/PostgreSQL database
4. OpenAI API key (for voice transcription and vision)

---

## Step 1: Create Bot with @BotFather

1. Open Telegram and search for `@BotFather`
2. Start a conversation and send `/newbot`
3. Follow the prompts:
   - Enter a name for your bot (e.g., "ARIA Assistant")
   - Enter a username (must end in `bot`, e.g., `aria_leveredge_bot`)
4. Save the **API Token** provided - you'll need this for n8n

### Configure Bot Settings

Send these commands to @BotFather:

```
/setcommands
```

Then select your bot and paste:

```
status - Check ARIA and system status
tasks - View and manage your tasks
remind - Set a reminder (e.g., /remind 30m Call John)
workout - Get today's workout or log exercise
meals - Get meal suggestions or log food
help - Show available commands
```

Additional settings:

```
/setdescription
```
> ARIA - Your personal AI assistant. Send text, voice, or images.

```
/setabouttext
```
> ARIA helps you stay organized, healthy, and productive. Part of the LeverEdge system.

```
/setuserpic
```
> Upload an ARIA avatar/logo

### Privacy Settings (Important)

```
/setprivacy
```
> Select DISABLE to allow the bot to receive all messages in groups (if needed)

For personal use only, leave privacy ENABLED.

---

## Step 2: Database Setup

Run the following SQL to create the telegram_sessions table:

```sql
-- See: telegram_sessions.sql in this directory

-- Quick create:
CREATE TABLE IF NOT EXISTS telegram_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,           -- Telegram user ID
    chat_id BIGINT NOT NULL,           -- Telegram chat ID
    username TEXT,                      -- Telegram username
    first_name TEXT,                    -- User's first name
    web_session_id TEXT,               -- Links to web ARIA session for continuity
    leveredge_user_id TEXT DEFAULT 'damon',  -- LeverEdge user mapping
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    message_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_authorized BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}'::JSONB,
    UNIQUE(user_id, chat_id)
);

CREATE INDEX idx_telegram_sessions_user ON telegram_sessions(user_id);
CREATE INDEX idx_telegram_sessions_chat ON telegram_sessions(chat_id);
CREATE INDEX idx_telegram_sessions_web ON telegram_sessions(web_session_id);
```

---

## Step 3: n8n Workflow Setup

### Import the Workflow

1. Open n8n (https://your-n8n-instance)
2. Go to Workflows > Import from File
3. Select `telegram-workflow.json` from this directory
4. The workflow will be imported as "ARIA Telegram Bot"

### Configure Credentials

1. **Telegram Bot API**
   - Go to Credentials > Add Credential > Telegram API
   - Name: `ARIA Telegram Bot`
   - Access Token: (paste the token from @BotFather)

2. **OpenAI API** (for voice and vision)
   - Go to Credentials > Add Credential > OpenAI
   - API Key: (your OpenAI API key)

3. **PostgreSQL**
   - Ensure your Supabase/Postgres credential is configured
   - Should be named: `Supabase Postgres PROD` or `Supabase Postgres DEV`

### Set Webhook URL

After activating the workflow, n8n will provide a webhook URL. Configure it with Telegram:

**Option A: Use n8n's Telegram trigger** (Recommended)
- The workflow uses n8n's built-in Telegram trigger which handles this automatically

**Option B: Manual webhook setup**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-n8n-domain/webhook/aria-telegram"}'
```

Verify webhook:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

---

## Step 4: Authorization Setup

By default, the bot requires users to be authorized. To authorize yourself:

1. Send any message to the bot
2. The bot will respond with your Telegram user ID
3. Run this SQL to authorize:

```sql
UPDATE telegram_sessions
SET is_authorized = TRUE,
    leveredge_user_id = 'your_user_id'
WHERE user_id = YOUR_TELEGRAM_USER_ID;
```

Or add authorized users directly:

```sql
INSERT INTO telegram_sessions (user_id, chat_id, is_authorized, leveredge_user_id)
VALUES (YOUR_TELEGRAM_USER_ID, YOUR_CHAT_ID, TRUE, 'damon');
```

---

## Step 5: Testing

1. **Text Message**: Send "Hello ARIA" - should get a response
2. **Voice Message**: Record a voice note - should be transcribed and processed
3. **Image**: Send a photo - should be analyzed and described
4. **Commands**: Try `/status`, `/tasks`, `/workout`

---

## Architecture

```
Telegram App
    |
    v
Telegram API (webhook)
    |
    v
n8n Telegram Trigger
    |
    +-- Text Message --> Direct to ARIA
    |
    +-- Voice Message --> OpenAI Whisper --> ARIA
    |
    +-- Image --> OpenAI Vision --> ARIA
    |
    +-- Commands --> Command Router --> Specialized Handlers
    |
    v
ARIA Core (via HTTP request to ARIA webhook)
    |
    v
Response back to Telegram
    |
    v
Log to telegram_sessions
```

---

## Session Continuity

The bot maintains session continuity with the web interface:

1. **Session Linking**: When a user first messages the bot, a session is created
2. **Web Session ID**: The `web_session_id` field can be set to link Telegram to a web session
3. **Shared Context**: ARIA uses the same user context regardless of interface
4. **Message History**: All messages are logged and can be retrieved

To link a web session:

```sql
UPDATE telegram_sessions
SET web_session_id = 'unified-damon'
WHERE user_id = YOUR_TELEGRAM_USER_ID;
```

---

## Troubleshooting

### Bot not responding
1. Check n8n workflow is active
2. Verify webhook is set correctly: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
3. Check n8n execution logs

### Voice messages not working
1. Verify OpenAI API key is valid
2. Check OpenAI has Whisper access
3. Voice files must be < 25MB

### Images not analyzed
1. Verify OpenAI API key has GPT-4 Vision access
2. Image must be accessible URL or base64

### "Unauthorized" message
1. Check `is_authorized` is TRUE in telegram_sessions
2. Verify your Telegram user ID matches

### Session not linking to web
1. Ensure `web_session_id` matches the ARIA conversation session
2. Check `leveredge_user_id` is set correctly

---

## Security Considerations

1. **Token Protection**: Never expose your bot token in public repos
2. **Authorization**: Only authorized users can interact with ARIA
3. **Rate Limiting**: Consider implementing rate limits for production
4. **Data Privacy**: Voice and images are sent to OpenAI for processing
5. **Webhook Security**: Use HTTPS only, consider IP whitelisting

---

## Environment Variables

For deployment, set these environment variables:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_key_here
ARIA_WEBHOOK_URL=http://prod-n8n:5678/webhook/aria-chat
DATABASE_URL=postgresql://user:pass@host:5432/db
```

---

## Files in This Directory

- `README.md` - This setup guide
- `telegram-workflow.json` - n8n workflow for import
- `commands.md` - Detailed command documentation
- `telegram_sessions.sql` - Database schema

---

## Support

For issues with this integration:
1. Check n8n execution logs
2. Review this documentation
3. Check the Telegram Bot API documentation: https://core.telegram.org/bots/api
