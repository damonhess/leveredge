# Google Calendar Integration Setup Guide

This guide walks you through setting up the Google Calendar two-way sync integration for ARIA.

## Prerequisites

- Google Account with access to Google Cloud Console
- Domain with HTTPS support for webhooks
- PostgreSQL database access
- Python 3.10+

---

## Step 1: Create Google Cloud Project

### 1.1 Access Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account

### 1.2 Create New Project

1. Click the project dropdown at the top of the page
2. Click "New Project"
3. Enter project details:
   - **Project name**: `ARIA Calendar Integration`
   - **Organization**: Select your organization (if applicable)
   - **Location**: Select appropriate folder
4. Click "Create"
5. Wait for project creation (may take a minute)
6. Select the newly created project

### 1.3 Note Your Project ID

Save your Project ID for later use. You can find it on the project dashboard or in the URL.

---

## Step 2: Enable Google Calendar API

### 2.1 Navigate to API Library

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Or directly visit: `https://console.cloud.google.com/apis/library`

### 2.2 Enable Calendar API

1. Search for "Google Calendar API"
2. Click on "Google Calendar API" in the results
3. Click "Enable"
4. Wait for the API to be enabled

---

## Step 3: Create OAuth 2.0 Credentials

### 3.1 Configure OAuth Consent Screen

Before creating credentials, you must configure the consent screen:

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select User Type:
   - **Internal**: Only users in your organization (recommended for internal use)
   - **External**: Any Google user (requires app verification for production)
3. Click "Create"

### 3.2 Fill Consent Screen Details

**App Information:**
- **App name**: `ARIA Calendar Sync`
- **User support email**: Your email address
- **App logo**: (Optional) Upload your logo

**App Domain:**
- **Application home page**: `https://your-domain.com`
- **Application privacy policy link**: `https://your-domain.com/privacy`
- **Application terms of service link**: `https://your-domain.com/terms`

**Developer Contact:**
- **Email addresses**: Your email address

Click "Save and Continue"

### 3.3 Add Scopes

1. Click "Add or Remove Scopes"
2. Search and select these scopes:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/calendar.events`
3. Click "Update"
4. Click "Save and Continue"

### 3.4 Add Test Users (External Apps Only)

If you selected "External" user type:
1. Click "Add Users"
2. Enter email addresses of users who will test the app
3. Click "Add"
4. Click "Save and Continue"

### 3.5 Create OAuth Client ID

1. Go to **APIs & Services** > **Credentials**
2. Click "Create Credentials" > "OAuth client ID"
3. Select **Application type**: `Web application`
4. Enter **Name**: `ARIA Calendar Sync Client`
5. Add **Authorized JavaScript origins**:
   ```
   https://your-domain.com
   http://localhost:8068
   ```
6. Add **Authorized redirect URIs**:
   ```
   https://your-domain.com/auth/callback
   http://localhost:8068/auth/callback
   ```
7. Click "Create"

### 3.6 Download Credentials

1. In the OAuth 2.0 Client IDs list, find your newly created client
2. Click the download icon (Download JSON)
3. Rename the file to `client_secrets.json`
4. Move to credentials directory:
   ```bash
   mkdir -p /opt/leveredge/integrations/google-calendar/credentials
   mv client_secrets.json /opt/leveredge/integrations/google-calendar/credentials/
   chmod 600 /opt/leveredge/integrations/google-calendar/credentials/client_secrets.json
   ```

---

## Step 4: Set Up Webhook Domain Verification

Google requires domain verification for push notifications (webhooks).

### 4.1 Verify Domain Ownership

1. Go to [Google Search Console](https://search.google.com/search-console)
2. Add your domain
3. Follow verification steps (DNS TXT record or HTML file)

### 4.2 Register Domain for Push Notifications

1. Go to [Google Cloud Console Domain Verification](https://console.cloud.google.com/apis/credentials/domainverification)
2. Click "Add Domain"
3. Enter your webhook domain (e.g., `calendar.leveredge.ai`)
4. Verify ownership using the method provided

---

## Step 5: Database Setup

### 5.1 Run Schema Migration

```bash
cd /opt/leveredge/integrations/google-calendar
psql -U postgres -d leveredge -f schema.sql
```

### 5.2 Verify Tables Created

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'aria_calendar%';

-- Expected output:
-- aria_calendar_sync
-- aria_calendar_events
-- aria_calendar_metadata
-- aria_calendar_sync_history
```

---

## Step 6: Configure Environment

### 6.1 Create Environment File

```bash
cat > /opt/leveredge/integrations/google-calendar/.env << 'EOF'
# Database Configuration
CALENDAR_SYNC_DATABASE_URL=postgresql://postgres:your_password@localhost:5432/leveredge

# Google Calendar Settings
CALENDAR_SYNC_GOOGLE_CALENDAR_ID=primary
CALENDAR_SYNC_CONFLICT_RESOLUTION=google_wins

# Webhook Configuration
CALENDAR_SYNC_WEBHOOK_BASE_URL=https://calendar.leveredge.ai

# Server Settings
CALENDAR_SYNC_HOST=0.0.0.0
CALENDAR_SYNC_PORT=8068
EOF

chmod 600 /opt/leveredge/integrations/google-calendar/.env
```

### 6.2 Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `GOOGLE_CALENDAR_ID` | Calendar to sync with | `primary` |
| `CONFLICT_RESOLUTION` | How to resolve conflicts | `google_wins` |
| `WEBHOOK_BASE_URL` | Base URL for webhooks | Required |

**Conflict Resolution Options:**
- `google_wins`: Google Calendar changes take precedence
- `aria_wins`: ARIA changes take precedence
- `most_recent`: Most recently modified version wins
- `manual`: Flag for manual resolution

---

## Step 7: Install and Run

### 7.1 Create Virtual Environment

```bash
cd /opt/leveredge/integrations/google-calendar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 7.2 Start the Service

```bash
# Development
python calendar-sync.py

# Production (with uvicorn)
uvicorn calendar-sync:app --host 0.0.0.0 --port 8068 --workers 4
```

### 7.3 Create Systemd Service (Production)

```bash
cat > /etc/systemd/system/aria-calendar-sync.service << 'EOF'
[Unit]
Description=ARIA Google Calendar Sync Service
After=network.target postgresql.service

[Service]
Type=simple
User=leveredge
Group=leveredge
WorkingDirectory=/opt/leveredge/integrations/google-calendar
Environment=PATH=/opt/leveredge/integrations/google-calendar/venv/bin
ExecStart=/opt/leveredge/integrations/google-calendar/venv/bin/uvicorn calendar-sync:app --host 0.0.0.0 --port 8068 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aria-calendar-sync
systemctl start aria-calendar-sync
```

---

## Step 8: Complete OAuth Authorization

### 8.1 Get Authorization URL

```bash
curl "http://localhost:8068/auth/url?redirect_uri=http://localhost:8068/auth/callback"
```

Response:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "random_state_string"
}
```

### 8.2 Authorize in Browser

1. Open the `authorization_url` in your browser
2. Sign in with your Google account
3. Grant requested permissions
4. You'll be redirected to the callback URL with a `code` parameter

### 8.3 Exchange Code for Credentials

```bash
curl -X POST "http://localhost:8068/auth/callback" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "CODE_FROM_CALLBACK",
    "redirect_uri": "http://localhost:8068/auth/callback"
  }'
```

### 8.4 Verify Authentication

```bash
curl "http://localhost:8068/auth/status"
```

Expected response:
```json
{
  "client_secrets_configured": true,
  "token_exists": true,
  "credentials_valid": true,
  "has_refresh_token": true
}
```

---

## Step 9: Set Up Webhook

### 9.1 Register Webhook with Google

```bash
curl -X POST "http://localhost:8068/webhook/setup" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://calendar.leveredge.ai/webhook",
    "expiration_hours": 168
  }'
```

### 9.2 Configure Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name calendar.leveredge.ai;

    ssl_certificate /etc/letsencrypt/live/calendar.leveredge.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calendar.leveredge.ai/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8068;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Step 10: Import n8n Workflow

### 10.1 Import Workflow

1. Open n8n at `http://localhost:5678`
2. Go to **Settings** > **Import from File**
3. Select `calendar-webhook-workflow.json`
4. Click "Import"

### 10.2 Configure Credentials

1. Open the imported workflow
2. Click on any PostgreSQL node
3. Create/select your PostgreSQL credentials
4. Save the workflow

### 10.3 Activate Workflow

1. Toggle the workflow to "Active"
2. Copy the webhook URLs for use

---

## Step 11: Test the Integration

### 11.1 Health Check

```bash
curl http://localhost:8068/health
```

### 11.2 Create Test Event

```bash
curl -X POST "http://localhost:8068/events/create" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Event from ARIA",
    "description": "This is a test event",
    "start_time": "2024-01-15T10:00:00Z",
    "end_time": "2024-01-15T11:00:00Z",
    "location": "Conference Room A"
  }'
```

### 11.3 Get Today's Events

```bash
curl "http://localhost:8068/events/today"
```

### 11.4 Check Sync Status

```bash
curl "http://localhost:8068/sync/status"
```

---

## Troubleshooting

### Common Issues

**1. "Client secrets not configured"**
- Ensure `client_secrets.json` is in the credentials directory
- Check file permissions (should be 600)

**2. "Invalid grant" error**
- Authorization code may have expired
- Restart the OAuth flow from Step 8

**3. Webhook not receiving notifications**
- Verify domain is registered in Google Cloud Console
- Check HTTPS certificate is valid
- Ensure firewall allows inbound traffic on port 443

**4. Token refresh failing**
- Check refresh token is stored
- Verify OAuth consent screen scopes include offline access

### Logs

```bash
# View service logs
journalctl -u aria-calendar-sync -f

# Check n8n workflow executions
# In n8n UI: Go to Executions tab
```

---

## Maintenance

### Renew Webhook (Weekly)

Webhooks expire after the configured time. Set up a cron job:

```bash
# Add to crontab
0 0 * * 0 curl -X POST "http://localhost:8068/webhook/setup" -H "Content-Type: application/json" -d '{"expiration_hours": 168}'
```

### Monitor Sync Health

```bash
# Check for conflicts
curl "http://localhost:8068/sync/conflicts"

# View sync statistics
curl "http://localhost:8068/sync/status"
```

### Database Cleanup

```sql
-- Clean old sync history (run monthly)
SELECT cleanup_old_sync_history();

-- Clean soft-deleted events
SELECT cleanup_deleted_events();
```

---

## Security Considerations

1. **Credentials Storage**: Never commit `client_secrets.json` or `token.json` to version control
2. **HTTPS Required**: Google requires HTTPS for webhook endpoints
3. **Token Security**: Store tokens securely, restrict file permissions
4. **Domain Verification**: Only verified domains can receive push notifications
5. **Scope Limitation**: Only request necessary scopes
