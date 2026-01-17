# Google Tasks Two-Way Sync

Bidirectional synchronization between `aria_tasks` (local PostgreSQL) and Google Tasks API with conflict resolution.

## Features

- **Two-Way Sync**: Changes flow both directions - local to Google and Google to local
- **Conflict Resolution**: Configurable strategies (google_wins, local_wins, newest_wins)
- **Real-Time Webhooks**: Receive instant notifications when Google Tasks change
- **Full Sync**: Force complete reconciliation between systems
- **Audit Logging**: Track all sync operations for debugging
- **n8n Integration**: Workflow for processing webhooks

## Architecture

```
                                    +------------------+
                                    |   Google Tasks   |
                                    |       API        |
                                    +--------+---------+
                                             |
                                             v
+------------------+          +---------------------------+
|    aria_tasks    | <------> |    tasks-sync.py          |
|   (PostgreSQL)   |          |    FastAPI :8069          |
+------------------+          +---------------------------+
                                             ^
                                             |
                              +---------------------------+
                              |    n8n Workflow           |
                              |   (Webhook Handler)       |
                              +---------------------------+
```

## API Endpoints

### Health & Auth

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/auth/status` | GET | Authentication status |
| `/auth/url` | GET | Get OAuth authorization URL |
| `/auth/callback` | POST | Exchange OAuth code for tokens |
| `/auth/revoke` | POST | Revoke Google credentials |

### Task Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks/create` | POST | Create task (syncs to Google) |
| `/tasks/update` | POST | Update task |
| `/tasks/complete` | POST | Mark task complete |
| `/tasks/{id}` | GET | Get task with sync status |
| `/tasks/{id}` | DELETE | Delete task |
| `/tasks/pending` | GET | Get tasks pending sync |

### Sync Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sync/full` | POST | Force full bidirectional sync |
| `/sync/stats` | GET | Get sync statistics |
| `/sync/resolve-conflict` | POST | Manually resolve conflict |

### Webhooks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | Receive Google push notifications |
| `/webhook/n8n` | POST | Receive forwarded n8n webhooks |

### Task Lists

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasklists` | GET | List Google Task Lists |
| `/tasklists/{id}/tasks` | GET | List tasks in a Task List |

## Quick Start

```bash
# 1. Setup environment
cd /opt/leveredge/integrations/google-tasks
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your database URL

# 3. Add Google credentials
# Download from Google Cloud Console
cp client_secrets.json credentials/

# 4. Run database migration
psql -d your_db -f schema.sql

# 5. Start service
python tasks-sync.py

# 6. Authenticate
# Visit http://localhost:8069/auth/url?redirect_uri=http://localhost:8069/auth/callback
```

## Conflict Resolution

When both local and Google versions are modified since last sync:

| Strategy | Behavior |
|----------|----------|
| `google_wins` | Google version always takes precedence |
| `local_wins` | Local version always takes precedence |
| `newest_wins` | Most recently modified version wins (default) |
| `manual` | Mark as conflict, require manual resolution |

Configure via environment variable:
```bash
GOOGLE_TASKS_DEFAULT_CONFLICT_RESOLUTION=newest_wins
```

## Database Schema

### aria_tasks
Main task storage table with fields:
- `id` - UUID primary key
- `title` - Task title
- `notes` - Task description
- `due_date` - Due date/time
- `status` - needsAction or completed
- `priority` - low, normal, high, urgent
- `category` - Task category

### aria_tasks_sync
Sync tracking table:
- `local_task_id` - Reference to aria_tasks
- `google_task_id` - Google Tasks ID
- `sync_status` - synced, pending_push, pending_pull, conflict, error
- `last_synced_at` - Last successful sync timestamp

### aria_tasks_sync_log
Audit log of all sync operations for debugging.

## n8n Workflow

The included workflow (`tasks-webhook-workflow.json`) provides:

1. **Webhook Receiver** - Accepts Google push notifications
2. **Parse & Route** - Determines change type (create/update/delete)
3. **Sync Record Lookup** - Finds matching local task
4. **Apply Changes** - Updates local database or forwards to API
5. **Logging** - Records all sync operations
6. **Scheduled Sync** - Runs full sync every 15 minutes

Import into n8n:
1. Go to Workflows > Import from file
2. Select `tasks-webhook-workflow.json`
3. Configure Postgres credentials
4. Activate workflow

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_TASKS_DATABASE_URL` | (required) | PostgreSQL connection string |
| `GOOGLE_TASKS_DEFAULT_TASKLIST_ID` | `@default` | Default Google Task List |
| `GOOGLE_TASKS_DEFAULT_CONFLICT_RESOLUTION` | `newest_wins` | Conflict strategy |
| `GOOGLE_TASKS_HOST` | `0.0.0.0` | Server bind address |
| `GOOGLE_TASKS_PORT` | `8069` | Server port |
| `GOOGLE_TASKS_WEBHOOK_SECRET` | (optional) | Webhook verification secret |

## Files

```
/opt/leveredge/integrations/google-tasks/
├── tasks-sync.py           # FastAPI application
├── google_auth.py          # Google OAuth handler
├── sync_handler.py         # Sync logic & conflict resolution
├── schema.sql              # Database schema
├── tasks-webhook-workflow.json  # n8n workflow
├── requirements.txt        # Python dependencies
├── setup-guide.md          # Detailed setup instructions
├── README.md               # This file
├── .env                    # Environment config (create this)
└── credentials/            # OAuth credentials
    ├── client_secrets.json # Google OAuth client
    └── token.json          # Stored access token
```

## Integration with ARIA

This sync integrates with the ARIA coaching system's task management. Tasks created through ARIA or directly in aria_tasks will sync to Google Tasks, allowing:

- View/edit tasks in Google Tasks mobile app
- Use Google Assistant voice commands
- Sync across devices automatically
- Integrate with Google Calendar

## Troubleshooting

### Check service health
```bash
curl http://localhost:8069/health
```

### View pending syncs
```bash
curl http://localhost:8069/tasks/pending
```

### Force sync
```bash
curl -X POST http://localhost:8069/sync/full
```

### Check logs
```bash
# If running as systemd service
journalctl -u google-tasks-sync -f

# Or check n8n execution history
```

## See Also

- [Setup Guide](setup-guide.md) - Detailed installation instructions
- [Google Tasks API Docs](https://developers.google.com/tasks/reference/rest)
- [ARIA Coaching Tables](/opt/leveredge/data-plane/dev/supabase/migrations/20260117_aria_coaching_tables.sql)
