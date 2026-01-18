# GSD: Loose Ends Cleanup - January 18, 2026

**Priority:** HIGH - System Stability & Launch Prep
**Estimated Time:** 4-6 hours
**Created:** 2026-01-18
**Days to Launch:** 42

---

## Overview

Comprehensive cleanup of infrastructure loose ends before moving to outreach prep.

---

## PART 1: CRITICAL (Do First)

### 1.1 Reset ARIA Password
**Problem:** Damon forgot password, no email recovery configured
**Fix:** Reset directly in Supabase

```bash
# Find Damon's user ID
cd /home/damon/stack
docker exec -it supabase-db psql -U postgres -d postgres -c "SELECT id, email FROM auth.users;"

# Reset password (replace YOUR_EMAIL and NEW_PASSWORD)
docker exec -it supabase-db psql -U postgres -d postgres -c "
UPDATE auth.users 
SET encrypted_password = crypt('NEW_PASSWORD_HERE', gen_salt('bf'))
WHERE email = 'YOUR_EMAIL_HERE';
"
```

**Verify:** Can log into aria.leveredgeai.com with new password

---

### 1.2 Verify Core Agents Running
**Check all are active:**

```bash
# Check status of all core agents
sudo systemctl status leveredge-event-bus leveredge-atlas leveredge-sentinel leveredge-panoptes leveredge-asclepius leveredge-hermes leveredge-chronos leveredge-hades leveredge-aegis leveredge-argus --no-pager

# Start any that aren't running
sudo systemctl start leveredge-event-bus
sudo systemctl start leveredge-atlas
sudo systemctl start leveredge-sentinel
# ... etc

# Enable all for auto-start
sudo systemctl enable leveredge-event-bus leveredge-atlas leveredge-sentinel leveredge-panoptes leveredge-asclepius leveredge-hermes leveredge-chronos leveredge-hades leveredge-aegis leveredge-argus
```

**Expected:** All services active and enabled

---

### 1.3 Git Commit Today's Work
**Commit all changes from today's session:**

```bash
cd /opt/leveredge
git add -A
git status  # Review changes
git commit -m "Jan 18: PANOPTES + ASCLEPIUS deployment, infrastructure cleanup

- Deployed PANOPTES integrity guardian (port 8023)
- Deployed ASCLEPIUS healing agent (port 8024)
- Reduced issues from 83 to 42 (zero high-severity)
- Cleaned up duplicate agent directories
- Fixed PANOPTES false positive detection
- Removed unimplemented agents from registry
- Created systemd services for core agents
- Deployed Command Center and ARIA frontend
- Health score: 68% → 83%"

git push origin main
```

---

## PART 2: EMAIL SETUP (Required for Password Recovery)

### 2.1 Option A: Google Workspace (Recommended)

**Why:** Professional email, Calendar, Drive integration, needed for outreach anyway

**Steps:**
1. Go to https://workspace.google.com
2. Sign up with leveredgeai.com domain
3. Verify domain ownership via Cloudflare DNS
4. Create damon@leveredgeai.com
5. Get SMTP credentials

**Cloudflare DNS records to add:**
```
Type: MX    Name: @    Value: aspmx.l.google.com    Priority: 1
Type: MX    Name: @    Value: alt1.aspmx.l.google.com    Priority: 5
Type: TXT   Name: @    Value: "v=spf1 include:_spf.google.com ~all"
```

### 2.2 Configure Supabase Auth SMTP

After email is set up, update Supabase:

```bash
# Edit Supabase config
nano /home/damon/stack/volumes/supabase/config.toml

# Add/update SMTP section:
[auth.email]
enable_signup = true
double_confirm_changes = true
enable_confirmations = true

[auth.email.smtp]
host = "smtp.gmail.com"
port = 587
user = "damon@leveredgeai.com"
pass = "YOUR_APP_PASSWORD"  # Generate from Google Account
admin_email = "damon@leveredgeai.com"
sender_name = "LeverEdge AI"
```

```bash
# Restart Supabase
cd /home/damon/stack
docker compose restart supabase-auth
```

---

## PART 3: ARIA BACKEND CONNECTION

### 3.1 Verify ARIA Webhook Endpoints

```bash
# Check ARIA workflow is active in n8n
curl -s http://localhost:5678/webhook/aria-chat -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "test-123"}' | head -100
```

### 3.2 Update Frontend API Config

When Bolt.new frontend is ready, update the API endpoint:

```javascript
// In frontend config/env
VITE_ARIA_API_URL=https://n8n.leveredgeai.com/webhook/aria-chat
VITE_SUPABASE_URL=https://studio.leveredgeai.com
VITE_SUPABASE_ANON_KEY=your_anon_key_here
```

### 3.3 CORS Configuration

Ensure n8n allows requests from aria.leveredgeai.com:

```bash
# Check n8n environment
docker exec n8n env | grep -i cors

# If needed, add to n8n docker-compose:
# N8N_CORS_ALLOW_ORIGIN=https://aria.leveredgeai.com
```

---

## PART 4: REMAINING PANOPTES ISSUES

### 4.1 Check Current Status

```bash
curl http://localhost:8023/status
```

### 4.2 Fix Medium Severity Issues

**Most are URL parsing issues in registry. Fix pattern:**

```bash
# Check which agents have bad URLs
curl http://localhost:8023/issues | python3 -m json.tool | grep -A5 "health_error"
```

**Common fix:** Registry URLs should be `http://localhost:PORT` not `http://agentname:PORT` for agents running via systemd (not Docker).

### 4.3 Update Registry URLs

```yaml
# In /opt/leveredge/config/agent-registry.yaml
# Change from:
connection:
  url: http://panoptes:8023

# To:
connection:
  url: http://localhost:8023
```

Apply to all systemd-based agents.

---

## PART 5: PORTFOLIO DYNAMIC INJECTION

### 5.1 Add HTTP Request Node to ARIA Workflow

In DEV n8n, add node before AI Agent:

**Node: HTTP Request**
- Method: POST
- URL: `{{ $env.SUPABASE_URL }}/rest/v1/rpc/aria_get_portfolio_summary`
- Headers:
  - apikey: `{{ $env.SUPABASE_SERVICE_KEY }}`
  - Authorization: `Bearer {{ $env.SUPABASE_SERVICE_KEY }}`
  - Content-Type: application/json
- Body: `{}`

**Merge into system prompt:**
```
DAMON'S PORTFOLIO:
{{ $json.portfolio_summary }}
```

---

## PART 6: TECHNICAL DEBT CLEANUP

### 6.1 Storage Bucket Cleanup

Create cleanup function:

```sql
-- In Supabase SQL editor
CREATE OR REPLACE FUNCTION cleanup_orphaned_files()
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  -- Delete files without conversation reference
  WITH orphans AS (
    SELECT id FROM storage.objects 
    WHERE bucket_id = 'aria-uploads'
    AND (metadata->>'conversation_id') IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM aria_conversations 
      WHERE id = (metadata->>'conversation_id')::uuid
    )
  )
  DELETE FROM storage.objects WHERE id IN (SELECT id FROM orphans);
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

### 6.2 Chat Memory Cleanup

```sql
-- Clean old n8n chat histories
DELETE FROM n8n_chat_histories 
WHERE created_at < NOW() - INTERVAL '30 days'
AND session_id NOT IN (
  SELECT DISTINCT session_id FROM aria_conversations
);
```

### 6.3 Create Cleanup Cron Job

```bash
# Add to crontab
crontab -e

# Add line (runs Sunday 3 AM):
0 3 * * 0 curl -X POST http://localhost:8023/scan && curl -X POST http://localhost:8024/emergency/auto
```

---

## PART 7: DEV CREDENTIAL SEPARATION

### 7.1 Remaining Credentials to Separate

| Credential | PROD Refs | DEV Refs | Status |
|------------|-----------|----------|--------|
| Google Sheets | ? | 9 | Needs DEV version |
| Telegram | ? | 14 | Needs DEV version |
| Google Drive | ? | 4 | Needs DEV version |

### 7.2 Create DEV Credentials via AEGIS

```bash
# Use AEGIS CLI or API
curl -X POST http://localhost:8012/credentials/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "google-sheets-dev",
    "provider": "google-sheets",
    "environment": "dev",
    "data": {...}
  }'
```

---

## PART 8: DOCUMENTATION UPDATE

### 8.1 Update LOOSE-ENDS.md

Create new version at `/opt/leveredge/docs/LOOSE-ENDS.md` with:
- Today's completions
- Updated priorities
- Current system status

### 8.2 Update Portfolio

```bash
# Add today's wins
/opt/leveredge/shared/scripts/add-win.sh \
  "PANOPTES & ASCLEPIUS Deployment" \
  "infrastructure" \
  "Built and deployed integrity monitoring and auto-healing system. Reduced issues from 83 to 42, achieved zero high-severity issues." \
  3000 6000 \
  "Self-healing infrastructure typically requires dedicated DevOps team"
```

---

## VERIFICATION CHECKLIST

After completing all parts:

```bash
# 1. Can log into ARIA
curl -I https://aria.leveredgeai.com

# 2. All core agents running
sudo systemctl is-active leveredge-{event-bus,atlas,sentinel,panoptes,asclepius,hermes,chronos,hades,aegis,argus}

# 3. PANOPTES health score
curl http://localhost:8023/status | python3 -m json.tool | grep health_score

# 4. Git is clean
cd /opt/leveredge && git status

# 5. Email configured (test)
# Send test email from Google Workspace

# 6. ARIA responds
curl -X POST https://n8n.leveredgeai.com/webhook/aria-chat \
  -H "Content-Type: application/json" \
  -d '{"message":"ping","session_id":"test"}'
```

---

## GSD COMMAND

```
/gsd /opt/leveredge/specs/gsd-loose-ends-jan18.md

CONTEXT: Comprehensive loose ends cleanup after PANOPTES/ASCLEPIUS deployment.
Focus on: password reset, email setup, agent verification, git commits, documentation.

PRIORITY ORDER:
1. Reset ARIA password (CRITICAL - blocking)
2. Verify all agents running
3. Git commit today's work
4. Email/SMTP setup (needed for production)
5. Fix remaining PANOPTES issues
6. Technical debt cleanup
7. Documentation update

After completion: curl http://localhost:8023/scan to verify health score improved.
```

---

## SUCCESS CRITERIA

- [ ] Can log into ARIA with new password
- [ ] All 10 core agents running and enabled
- [ ] Git repo committed and pushed
- [ ] Email sending works (test password reset)
- [ ] PANOPTES health score > 85%
- [ ] Zero high-severity issues
- [ ] Portfolio updated with today's wins
- [ ] LOOSE-ENDS.md current

---

**42 days to launch. Clean infrastructure = confident outreach.**
