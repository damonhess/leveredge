# Client Onboarding Workflow

Automated n8n workflow for new client setup and onboarding.

## Overview

This workflow automates the entire client onboarding process from signup to kickoff call scheduling. When triggered via webhook, it creates all necessary records, generates credentials, sets up storage, sends welcome communications, and notifies the team.

## Architecture

```
Webhook Trigger
       |
       v
+------------------+
| Validate Input   |--- Invalid ---> Notify Error
+------------------+
       |
       v
+------------------+
| Set Client Data  |  Generate unique client_id
+------------------+
       |
       v
+------------------+
| Create Record    |  Supabase: clients table
+------------------+
       |
       v
+------------------+
| Generate API Key |  AEGIS credential vault
+------------------+
       |
       +----------------+
       |                |
       v                v
+---------------+  +-----------------+
| Create Root   |  | Create Subfolders|
| Folder        |  | (parallel loop) |
+---------------+  +-----------------+
       |                |
       +-------+--------+
               |
               v
      +------------------+
      | Merge & Prepare  |
      +------------------+
               |
               v
      +------------------+
      | Send Welcome     |  HERMES email service
      | Email            |
      +------------------+
               |
               v
      +------------------+
      | Schedule Kickoff |  Google Calendar
      | Call             |
      +------------------+
               |
               v
      +------------------+
      | Update Status    |  Mark client active
      +------------------+
               |
       +-------+-------+
       |               |
       v               v
+------------+  +--------------+
| Create     |  | Log to Event |
| Checklist  |  | Bus          |
+------------+  +--------------+
                       |
               +-------+-------+
               |               |
               v               v
        +----------+    +----------+
        | Telegram |    | Admin    |
        | Notify   |    | Email    |
        +----------+    +----------+
```

## Files

| File | Purpose |
|------|---------|
| `client-onboarding.json` | n8n workflow definition |
| `welcome-email.html` | Welcome email HTML template |
| `schema.sql` | Database schema for client tables |
| `checklist.md` | Manual onboarding checklist |
| `README.md` | This documentation |

## Webhook Endpoint

**URL:** `https://n8n.leveredgeai.com/webhook/client-onboarding`
**Method:** POST
**Content-Type:** application/json

### Request Body

```json
{
  "email": "client@company.com",
  "company_name": "Acme Corporation",
  "contact_name": "Jane Smith",
  "phone": "+1-555-0123",
  "plan_tier": "professional",
  "notes": "Referred by Partner XYZ"
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Primary contact email (unique) |
| `company_name` | string | Company/organization name |
| `contact_name` | string | Primary contact full name |

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `phone` | string | `""` | Contact phone number |
| `plan_tier` | string | `"starter"` | Plan: starter, professional, enterprise, custom |
| `notes` | string | `""` | Internal notes about the client |

### Response

**Success (202 Accepted):**
```json
{
  "status": "processing",
  "message": "Client onboarding initiated",
  "client_email": "client@company.com"
}
```

**Note:** The workflow processes asynchronously. The webhook returns immediately while onboarding continues in the background.

## What Gets Created

### 1. Client Record (Supabase)

A new row in the `clients` table with:
- Unique `client_id` (format: `cli_YYYYMMDD_xxxxxx`)
- Contact information
- Plan tier
- Status: `onboarding` (later updated to `active`)
- Timestamps

### 2. API Credentials (AEGIS)

- API key generated via AEGIS credential vault
- Scopes: `api:read`, `api:write`
- Expiry: 365 days
- Stored securely, never logged in plaintext

### 3. Project Folder Structure (Supabase Storage)

```
clients/
  cli_20260117_abc123/
    documents/
    contracts/
    reports/
    assets/
    communications/
```

### 4. Welcome Email

HTML email sent to client with:
- Account details (client_id, plan tier)
- API key (one-time delivery)
- Portal and documentation links
- Getting started steps

### 5. Kickoff Call (Google Calendar)

- Scheduled 3 business days out
- 1-hour meeting at 10:00 AM
- Google Meet link auto-generated
- Attendee: client email
- Standard agenda included

### 6. Onboarding Checklist

Tracked tasks in `client_onboarding_tasks` table:
- [x] Welcome email sent
- [x] API credentials generated
- [x] Project folders created
- [x] Kickoff call scheduled
- [ ] Service agreement signed
- [ ] Technical requirements gathered
- [ ] Integration configured
- [ ] Training completed

### 7. Admin Notifications

- **Telegram:** High-priority alert with client details
- **Email:** Full notification to admin@leveredgeai.com
- **Event Bus:** Logged for audit trail

## Setup Instructions

### 1. Database Setup

Run the schema in Supabase:

```bash
# Via psql
psql -h db.your-project.supabase.co -U postgres -d postgres -f schema.sql

# Or paste into Supabase SQL Editor
```

### 2. Import Workflow

1. Open n8n at `https://n8n.leveredgeai.com`
2. Go to Workflows > Import from File
3. Select `client-onboarding.json`
4. Click Import

### 3. Configure Credentials

Replace placeholder credential IDs in the workflow:

| Node | Credential | ID to Replace |
|------|------------|---------------|
| Create Client Record | Supabase | `REPLACE_WITH_SUPABASE_CREDENTIAL_ID` |
| Update Client Status | Supabase | `REPLACE_WITH_SUPABASE_CREDENTIAL_ID` |
| Create Onboarding Checklist | Supabase | `REPLACE_WITH_SUPABASE_CREDENTIAL_ID` |
| Schedule Kickoff Call | Google Calendar | `REPLACE_WITH_GOOGLE_CREDENTIAL_ID` |

### 4. Configure AEGIS

Ensure AEGIS has the `/credentials/generate` endpoint enabled:

```bash
# Test AEGIS
curl http://aegis:8012/health
```

### 5. Configure HERMES

Verify HERMES email capability:

```bash
# Test notification
curl -X POST http://hermes:8014/notify \
  -H "Content-Type: application/json" \
  -d '{"channel": "telegram", "message": "Test", "priority": "normal"}'
```

### 6. Activate Workflow

1. Open the workflow in n8n
2. Toggle the "Active" switch
3. Verify webhook URL is accessible

## Testing

### Manual Test

```bash
curl -X POST https://n8n.leveredgeai.com/webhook/client-onboarding \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "company_name": "Test Company",
    "contact_name": "Test User",
    "plan_tier": "starter"
  }'
```

### Verify Results

1. Check Supabase `clients` table for new record
2. Check `client_onboarding_tasks` for checklist
3. Verify Telegram notification received
4. Check Google Calendar for kickoff event
5. Verify welcome email in test inbox

## Error Handling

The workflow includes:

1. **Input Validation:** Checks for required fields before processing
2. **Error Trigger:** Catches any workflow errors
3. **Error Notification:** Sends critical alert via Telegram with error details
4. **Execution Logging:** All steps logged to Event Bus

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Missing required fields | Incomplete webhook payload | Ensure email, company_name, contact_name are provided |
| Duplicate client | Email already exists | Use unique email or update existing client |
| AEGIS unreachable | Service down | Check AEGIS container health |
| Calendar auth failed | Token expired | Re-authorize Google Calendar credential |

## Customization

### Email Template

Edit `welcome-email.html` to customize:
- Branding (colors, logo)
- Content sections
- CTA buttons
- Footer information

Template variables:
- `{{contact_name}}`
- `{{company_name}}`
- `{{client_id}}`
- `{{api_key}}`
- `{{plan_tier}}`
- `{{portal_url}}`
- `{{docs_url}}`

### Folder Structure

Modify the "Folder List" node to change default folders:

```javascript
// Current folders
["documents", "contracts", "reports", "assets", "communications"]

// Add more as needed
["documents", "contracts", "reports", "assets", "communications", "invoices", "support"]
```

### Kickoff Timing

Adjust the "Calculate Kickoff Date" node:
- Default: 3 days from signup
- Change `duration` parameter for different timing

## Monitoring

### Workflow Executions

Monitor via n8n:
- Executions tab shows all runs
- Filter by status (success/error)
- Click execution for detailed logs

### Event Bus

Query onboarding events:

```bash
curl "http://event-bus:8099/events?source_agent=CLIENT_ONBOARDING"
```

### Database Views

Check onboarding pipeline:

```sql
SELECT * FROM v_onboarding_pipeline;
SELECT * FROM v_active_clients;
```

## Integration Points

| Service | Purpose | Endpoint |
|---------|---------|----------|
| Supabase | Database & Storage | api.leveredgeai.com |
| AEGIS | Credential vault | aegis:8012 |
| HERMES | Notifications | hermes:8014 |
| Event Bus | Audit logging | event-bus:8099 |
| Google Calendar | Scheduling | OAuth2 API |

## Security Considerations

1. **API Keys:** Generated keys are only sent in the welcome email, never logged
2. **Credentials:** All sensitive data managed by AEGIS, never in workflow
3. **Validation:** Input validation prevents injection attacks
4. **Audit Trail:** All actions logged to Event Bus
5. **RLS:** Enable Row Level Security in Supabase for production

## Support

For issues or enhancements:
1. Check workflow execution logs
2. Review Event Bus for error details
3. Contact platform team via Telegram

---

*Last Updated: January 2026*
*Version: 1.0.0*
