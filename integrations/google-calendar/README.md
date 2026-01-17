# Google Calendar Two-Way Sync

Two-way synchronization between ARIA and Google Calendar with real-time webhook notifications.

## Features

- **Event Creation from ARIA**: Create calendar events through API calls
- **Calendar Changes Update ARIA**: Google Calendar changes automatically sync to ARIA
- **Real-time Webhooks**: Instant notifications when calendar changes occur
- **Conflict Resolution**: Configurable strategy (Google wins, ARIA wins, most recent, manual)
- **OAuth 2.0 Authentication**: Secure credential management with automatic token refresh

## Architecture

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│    ARIA     │◄─────►│  Calendar Sync   │◄─────►│ Google Calendar │
│  (Events)   │       │   API (8068)     │       │      API        │
└─────────────┘       └──────────────────┘       └─────────────────┘
       ▲                      ▲                          │
       │                      │                          │
       │              ┌───────┴───────┐                  │
       │              │    n8n        │◄─────────────────┘
       └──────────────│   Workflow    │     (Webhook notifications)
                      └───────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd /opt/leveredge/integrations/google-calendar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database and webhook URLs
```

### 3. Set Up Database

```bash
psql -U postgres -d leveredge -f schema.sql
```

### 4. Add Google Credentials

Follow the [Setup Guide](setup-guide.md) to create OAuth credentials and place `client_secrets.json` in the `credentials/` directory.

### 5. Start the Service

```bash
python calendar-sync.py
```

### 6. Complete OAuth Flow

Visit `http://localhost:8068/auth/url?redirect_uri=http://localhost:8068/auth/callback` and authorize.

## API Reference

### Health Check

```http
GET /health
```

Returns service status and component health.

### Authentication

```http
GET /auth/status
GET /auth/url?redirect_uri={uri}
POST /auth/callback
POST /auth/revoke
```

### Events

```http
POST /events/create
POST /events/update
DELETE /events/{id}
GET /events/{id}
GET /events/today
GET /events/upcoming?days=7&max_results=50
```

### Webhook

```http
POST /webhook          # Receive Google notifications
POST /webhook/setup    # Register webhook with Google
POST /webhook/stop     # Stop webhook notifications
```

### Sync Status

```http
GET /sync/status
GET /sync/conflicts
POST /sync/resolve/{google_event_id}?resolution=google_wins
```

## Event Creation Example

```bash
curl -X POST "http://localhost:8068/events/create" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Meeting",
    "description": "Weekly sync",
    "start_time": "2024-01-15T14:00:00Z",
    "end_time": "2024-01-15T15:00:00Z",
    "location": "Conference Room A",
    "attendees": ["alice@example.com", "bob@example.com"],
    "local_event_id": 123
  }'
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `CALENDAR_SYNC_DATABASE_URL` | PostgreSQL connection | Required |
| `CALENDAR_SYNC_GOOGLE_CALENDAR_ID` | Calendar to sync | `primary` |
| `CALENDAR_SYNC_CONFLICT_RESOLUTION` | Conflict strategy | `google_wins` |
| `CALENDAR_SYNC_WEBHOOK_BASE_URL` | Webhook domain | Required |
| `CALENDAR_SYNC_PORT` | API port | `8068` |

### Conflict Resolution Strategies

- `google_wins`: Google Calendar is the source of truth
- `aria_wins`: ARIA changes take precedence
- `most_recent`: Most recently modified version wins
- `manual`: Flag conflicts for manual resolution

## Database Schema

### Core Tables

- `aria_calendar_events`: ARIA-side event storage
- `aria_calendar_sync`: Sync state tracking
- `aria_calendar_metadata`: Sync tokens, webhook channels
- `aria_calendar_sync_history`: Audit log

### Useful Views

- `v_events_pending_to_google`: Events needing Google sync
- `v_events_with_conflicts`: Events with sync conflicts
- `v_today_events`: Today's events
- `v_upcoming_events`: Next 7 days
- `v_sync_statistics`: Sync health metrics

## n8n Workflow

The included `calendar-webhook-workflow.json` provides:

1. **Google Calendar Webhook Handler**: Receives notifications from Google
2. **ARIA Notification Handler**: Receives events from ARIA for sync to Google
3. **Sync Logging**: Records all sync operations in history table

### Webhook Endpoints

- `POST /webhook/google-calendar-webhook` - Google notifications
- `POST /webhook/aria-calendar-notify` - ARIA to Google sync

## Files

```
google-calendar/
├── calendar-sync.py              # FastAPI application
├── google_auth.py                # OAuth handling
├── sync_handler.py               # Sync logic
├── schema.sql                    # Database schema
├── calendar-webhook-workflow.json # n8n workflow
├── setup-guide.md                # Detailed setup instructions
├── requirements.txt              # Python dependencies
├── README.md                     # This file
└── credentials/                  # OAuth credentials (gitignored)
    ├── client_secrets.json       # Google OAuth client
    └── token.json                # Access/refresh tokens
```

## Security

- OAuth 2.0 with automatic token refresh
- Credentials stored with restricted permissions (600)
- HTTPS required for webhooks
- Domain verification required by Google

## Monitoring

```bash
# Check service health
curl http://localhost:8068/health

# View sync statistics
curl http://localhost:8068/sync/status

# Check for conflicts
curl http://localhost:8068/sync/conflicts
```

## Maintenance

### Webhook Renewal

Webhooks expire periodically. Renew with:

```bash
curl -X POST http://localhost:8068/webhook/setup
```

### Database Cleanup

```sql
-- Clean old history (90+ days)
SELECT cleanup_old_sync_history();

-- Clean deleted events (30+ days)
SELECT cleanup_deleted_events();
```

## Troubleshooting

See [Setup Guide](setup-guide.md#troubleshooting) for common issues and solutions.

## License

Proprietary - Leveredge AI
