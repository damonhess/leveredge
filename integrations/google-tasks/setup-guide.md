# Google Tasks Two-Way Sync Setup Guide

This guide walks through setting up bidirectional sync between aria_tasks and Google Tasks.

## Prerequisites

- Python 3.10+
- PostgreSQL database (Supabase)
- Google Cloud Console account
- n8n instance (optional, for webhook workflow)

## Step 1: Google Cloud Console Setup

### 1.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** > **New Project**
3. Name it (e.g., "Leveredge Tasks Sync")
4. Click **Create**

### 1.2 Enable Google Tasks API

1. In your project, go to **APIs & Services** > **Library**
2. Search for "Tasks API"
3. Click **Google Tasks API**
4. Click **Enable**

### 1.3 Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User type: **External** (or Internal for Workspace)
   - App name: "Leveredge Tasks Sync"
   - User support email: your email
   - Developer contact: your email
   - Add scope: `https://www.googleapis.com/auth/tasks`
   - Add test users: your email
4. Back on Credentials, click **Create Credentials** > **OAuth client ID**
5. Application type: **Web application**
6. Name: "Tasks Sync API"
7. Authorized redirect URIs:
   - `http://localhost:8069/auth/callback`
   - `https://your-domain.com/auth/callback` (for production)
8. Click **Create**
9. Download the JSON file

### 1.4 Store Credentials

```bash
# Create credentials directory
mkdir -p /opt/leveredge/integrations/google-tasks/credentials

# Copy downloaded credentials
cp ~/Downloads/client_secret_*.json \
   /opt/leveredge/integrations/google-tasks/credentials/client_secrets.json

# Secure the file
chmod 600 /opt/leveredge/integrations/google-tasks/credentials/client_secrets.json
```

## Step 2: Database Setup

### 2.1 Run Schema Migration

```bash
# Connect to your PostgreSQL database
psql -h your-host -U postgres -d leveredge

# Run the schema
\i /opt/leveredge/integrations/google-tasks/schema.sql
```

Or via Supabase:

```bash
# Using Supabase CLI
supabase db push --db-url "postgresql://..." \
  < /opt/leveredge/integrations/google-tasks/schema.sql
```

### 2.2 Verify Tables Created

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'aria_tasks%';

-- Expected output:
-- aria_tasks
-- aria_tasks_sync
-- aria_tasks_sync_log
-- aria_google_tasklists
```

## Step 3: Python Environment Setup

### 3.1 Create Virtual Environment

```bash
cd /opt/leveredge/integrations/google-tasks

# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3.2 Configure Environment Variables

Create `.env` file:

```bash
cat > .env << 'EOF'
# Database
GOOGLE_TASKS_DATABASE_URL=postgresql://postgres:your-password@localhost:5432/leveredge

# Google Tasks
GOOGLE_TASKS_DEFAULT_TASKLIST_ID=@default
GOOGLE_TASKS_DEFAULT_CONFLICT_RESOLUTION=newest_wins

# Server
GOOGLE_TASKS_HOST=0.0.0.0
GOOGLE_TASKS_PORT=8069

# Optional: Webhook secret for verification
GOOGLE_TASKS_WEBHOOK_SECRET=your-secret-here
EOF
```

## Step 4: Initial Authentication

### 4.1 Start the Service

```bash
# Activate venv if not already
source venv/bin/activate

# Start the server
python tasks-sync.py
```

### 4.2 Authenticate with Google

1. Open browser to: `http://localhost:8069/health`
2. Check that `google_auth` shows `not_authenticated`
3. Get auth URL:
   ```bash
   curl "http://localhost:8069/auth/url?redirect_uri=http://localhost:8069/auth/callback"
   ```
4. Open the returned `authorization_url` in browser
5. Sign in and grant permissions
6. You'll be redirected back with a code
7. If redirect doesn't auto-complete, manually call:
   ```bash
   curl -X POST "http://localhost:8069/auth/callback" \
     -d "code=YOUR_CODE&redirect_uri=http://localhost:8069/auth/callback"
   ```

### 4.3 Verify Authentication

```bash
curl http://localhost:8069/auth/status

# Should show:
# {
#   "credentials_valid": true,
#   "has_refresh_token": true,
#   ...
# }
```

## Step 5: n8n Workflow Setup

### 5.1 Import Workflow

1. Open n8n at `http://localhost:5678`
2. Go to **Workflows** > **Import from file**
3. Select `/opt/leveredge/integrations/google-tasks/tasks-webhook-workflow.json`
4. Click **Import**

### 5.2 Configure Credentials

1. In the workflow, click on any Postgres node
2. Click **Create New** under Credentials
3. Configure with your database connection:
   - Host: your-db-host
   - Database: leveredge
   - User: postgres
   - Password: your-password
4. Save and name it "Supabase Dev"

### 5.3 Activate Workflow

1. Toggle the workflow **Active** switch on
2. Note the webhook URL shown (e.g., `https://n8n.your-domain.com/webhook/google-tasks-webhook`)

## Step 6: Google Push Notifications (Optional)

For real-time updates, set up Google Push Notifications:

### 6.1 Register Webhook with Google

This requires a publicly accessible HTTPS endpoint.

```python
# Using the Tasks API to watch a task list
from googleapiclient.discovery import build

service = build('tasks', 'v1', credentials=creds)

# Register webhook
watch_request = {
    'id': 'unique-channel-id',
    'type': 'web_hook',
    'address': 'https://your-domain.com/webhook/google-tasks-webhook',
    'expiration': int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
}

response = service.tasklists().watch(
    tasklist='@default',
    body=watch_request
).execute()
```

Note: Google Push Notifications require:
- HTTPS endpoint
- Valid SSL certificate
- Domain verification in Google Cloud Console

## Step 7: Test the Integration

### 7.1 Create a Test Task

```bash
# Create task locally (syncs to Google)
curl -X POST http://localhost:8069/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Task from API",
    "notes": "This should sync to Google Tasks",
    "due_date": "2024-12-31T23:59:59Z"
  }'
```

### 7.2 Check Google Tasks

Open Google Tasks (tasks.google.com) and verify the task appears.

### 7.3 Trigger Full Sync

```bash
curl -X POST http://localhost:8069/sync/full \
  -H "Content-Type: application/json" \
  -d '{"conflict_resolution": "newest_wins"}'
```

### 7.4 Check Sync Stats

```bash
curl http://localhost:8069/sync/stats
```

## Step 8: Production Deployment

### 8.1 Systemd Service

Create `/etc/systemd/system/google-tasks-sync.service`:

```ini
[Unit]
Description=Google Tasks Sync Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/leveredge/integrations/google-tasks
Environment=PATH=/opt/leveredge/integrations/google-tasks/venv/bin
EnvironmentFile=/opt/leveredge/integrations/google-tasks/.env
ExecStart=/opt/leveredge/integrations/google-tasks/venv/bin/python tasks-sync.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable google-tasks-sync
sudo systemctl start google-tasks-sync
sudo systemctl status google-tasks-sync
```

### 8.2 Nginx Reverse Proxy

Add to nginx config:

```nginx
location /tasks-sync/ {
    proxy_pass http://127.0.0.1:8069/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
}
```

## Troubleshooting

### Common Issues

**"No valid credentials" error**
- Re-run authentication flow
- Check that `token.json` exists in credentials folder
- Verify refresh token is present

**"Task not found in Google"**
- The task may have been deleted from Google
- Run full sync to reconcile

**Sync conflicts**
- Check `/tasks/pending` for conflict details
- Resolve manually or adjust conflict resolution strategy

**Webhook not receiving notifications**
- Verify HTTPS endpoint is accessible
- Check Google Cloud Console for webhook errors
- Ensure domain is verified

### Logs

```bash
# Service logs
sudo journalctl -u google-tasks-sync -f

# n8n workflow logs
# Check n8n execution history in UI
```

### Health Checks

```bash
# API health
curl http://localhost:8069/health

# Database connectivity
curl http://localhost:8069/health | jq '.components.database'

# Auth status
curl http://localhost:8069/auth/status
```

## Support

For issues:
1. Check logs for error messages
2. Verify all environment variables are set
3. Ensure database tables exist
4. Confirm Google API is enabled and credentials are valid
