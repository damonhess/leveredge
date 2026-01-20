# GSD: Comprehensive Loose Ends Cleanup - January 18, 2026

**Priority:** HIGH - Pre-Launch Cleanup
**Estimated Time:** 4-6 hours
**Created:** 2026-01-18
**Days to Launch:** 42

---

## OVERVIEW

Comprehensive cleanup covering:
1. ARIA password reset
2. Email/SMTP setup
3. PANOPTES medium issues
4. Technical debt
5. Documentation
6. Portfolio update
7. Git commit everything

---

## PART 1: ARIA PASSWORD RESET (5 min)

```bash
# Find user
cd /home/damon/stack
docker exec -it supabase-db psql -U postgres -d postgres -c "SELECT id, email FROM auth.users;"

# Reset password (replace EMAIL and PASSWORD)
docker exec -it supabase-db psql -U postgres -d postgres -c "
UPDATE auth.users 
SET encrypted_password = crypt('YOUR_NEW_PASSWORD', gen_salt('bf'))
WHERE email = 'damonhess@hotmail.com';
"

# Verify
echo "Password reset. Test login at https://dev.aria.leveredgeai.com"
```

---

## PART 2: FIX PANOPTES MEDIUM ISSUES (30 min)

### 2.1 Get Current Issues

```bash
curl http://localhost:8023/status | python3 -m json.tool
curl http://localhost:8023/issues | python3 -m json.tool > /tmp/panoptes-issues.json
cat /tmp/panoptes-issues.json | grep -E '"severity": "medium"' -A5 | head -50
```

### 2.2 Common Medium Issues and Fixes

**Health check URL errors (most common):**
- Cause: Registry URLs use container names but agents run via systemd
- Fix: Update registry URLs to use localhost

```bash
# Check which agents have URL issues
grep "http://" /opt/leveredge/config/agent-registry.yaml | grep -v localhost

# For each agent running via systemd, change:
#   url: http://agentname:PORT
# To:
#   url: http://localhost:PORT
```

**Missing systemd services:**
```bash
# List agents without systemd services
curl http://localhost:8023/issues | python3 -c "
import json, sys
data = json.load(sys.stdin)
for issue in data.get('issues', []):
    if issue.get('category') == 'missing_service':
        print(issue.get('affected', []))
"

# For each missing, check if service file exists in shared/systemd
ls /opt/leveredge/shared/systemd/leveredge-*.service

# Copy any missing to systemd
sudo cp /opt/leveredge/shared/systemd/leveredge-*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2.3 Update Registry URLs

Edit `/opt/leveredge/config/agent-registry.yaml`:

For ALL agents running via systemd (not Docker), change URLs to localhost:

```yaml
# Example - change FROM:
connection:
  url: http://panoptes:8023

# TO:
connection:
  url: http://localhost:8023
```

Agents that need localhost URLs (systemd-based):
- panoptes (8023)
- asclepius (8024)
- hermes (8014)
- chronos (8010)
- hades (8008)
- aegis (8012)
- argus (8016)
- aloy (8015)
- athena (8013)
- atlas (8007)
- sentinel (8019)
- event-bus (8099)

### 2.4 Rescan After Fixes

```bash
# Restart PANOPTES to pick up registry changes
sudo systemctl restart leveredge-panoptes

# Wait and rescan
sleep 5
curl -X POST http://localhost:8023/scan | python3 -m json.tool | grep -E "health_score|critical|high|medium"
```

**Target:** health_score > 90%, zero high, minimal medium

---

## PART 3: TECHNICAL DEBT CLEANUP (45 min)

### 3.1 Storage Bucket Orphan Cleanup

```sql
-- Run in Supabase SQL Editor (DEV)

-- Create cleanup function
CREATE OR REPLACE FUNCTION cleanup_orphaned_files()
RETURNS TABLE(deleted_count INTEGER, bucket TEXT) AS $$
DECLARE
  aria_deleted INTEGER := 0;
BEGIN
  -- Delete aria files without conversation reference
  WITH orphans AS (
    SELECT id FROM storage.objects 
    WHERE bucket_id = 'aria-uploads'
    AND created_at < NOW() - INTERVAL '7 days'
    AND name NOT IN (
      SELECT DISTINCT attachment_path FROM aria_messages 
      WHERE attachment_path IS NOT NULL
    )
  )
  DELETE FROM storage.objects WHERE id IN (SELECT id FROM orphans);
  GET DIAGNOSTICS aria_deleted = ROW_COUNT;
  
  RETURN QUERY SELECT aria_deleted, 'aria-uploads'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Run cleanup
SELECT * FROM cleanup_orphaned_files();
```

### 3.2 N8N Chat Memory Cleanup

```sql
-- Run in n8n database or via docker exec

-- Clean old chat histories (older than 30 days, not linked to active conversations)
DELETE FROM n8n_chat_histories 
WHERE "createdAt" < NOW() - INTERVAL '30 days';
```

Or via command:
```bash
docker exec -it n8n-db psql -U postgres -d n8n -c "
DELETE FROM n8n_chat_histories WHERE \"createdAt\" < NOW() - INTERVAL '30 days';
"
```

### 3.3 Create Cleanup Cron Jobs

```bash
# Add to crontab
crontab -e
```

Add these lines:
```cron
# PANOPTES daily scan at 6 AM
0 6 * * * curl -X POST http://localhost:8023/scan > /dev/null 2>&1

# ASCLEPIUS auto-heal at 6:30 AM (after scan)
30 6 * * * curl -X POST http://localhost:8024/emergency/auto > /dev/null 2>&1

# Weekly storage cleanup (Sunday 3 AM)
0 3 * * 0 curl -X POST "http://localhost:54323/rest/v1/rpc/cleanup_orphaned_files" -H "apikey: ${SUPABASE_SERVICE_KEY}" > /dev/null 2>&1
```

### 3.4 Check Disk Space

```bash
df -h /opt/leveredge
du -sh /opt/leveredge/shared/backups/*
du -sh /opt/leveredge/archive/*

# Clean old backups (keep last 7 days)
find /opt/leveredge/shared/backups -type f -mtime +7 -delete
find /opt/leveredge/archive -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null
```

### 3.5 Docker Cleanup

```bash
cd /home/damon/stack
docker system prune -f
docker volume prune -f
```

---

## PART 4: DOCUMENTATION UPDATE (30 min)

### 4.1 Update LOOSE-ENDS.md

Create `/opt/leveredge/docs/LOOSE-ENDS-20260118.md`:

```markdown
# LeverEdge Status - January 18, 2026

*Updated: January 18, 2026*

---

## 🎯 LAUNCH TIMELINE

| Milestone | Date | Status |
|-----------|------|--------|
| Infrastructure Stable | Jan 18 | ✅ DONE |
| ARIA Frontend V3 | Jan 18 | ✅ DONE |
| PANOPTES + ASCLEPIUS | Jan 18 | ✅ DONE |
| Email/SMTP Setup | Jan 19 | 🟡 NEXT |
| Niche Research | Feb 1-7 | ⬜ UPCOMING |
| Outreach Module | Feb 8-14 | ⬜ UPCOMING |
| 10 Outreach Attempts | Feb 15-28 | ⬜ UPCOMING |
| **IN BUSINESS** | **March 1** | 🎯 TARGET |

---

## ✅ COMPLETED TODAY (January 18)

### Self-Healing Infrastructure
- PANOPTES integrity guardian (port 8023)
- ASCLEPIUS healing agent (port 8024)
- Reduced issues: 83 → 42
- Health score: 68% → 83%+
- Zero high-severity issues

### ARIA Frontend V3
- Deployed to dev.aria.leveredgeai.com
- New features: Council, Library, Cost Tracking
- Proper aria_* table naming
- Git-based deployment workflow

### Agent Fleet
- 35+ agents online
- Core agents on systemd with auto-restart
- Daily integrity scans scheduled

### Web Deployments
- command.leveredgeai.com (Command Center)
- aria.leveredgeai.com (ARIA)
- dev.aria.leveredgeai.com (ARIA DEV)

---

## 🔄 IN PROGRESS

### Email Setup (Required for password reset)
- Option: Google Workspace ($7/mo)
- Needed for: auth emails, outreach, invoicing

### ARIA Backend Wiring
- Frontend deployed, needs backend connections
- Tables created, need data flow

---

## 📋 REMAINING TASKS

### High Priority
1. Google Workspace setup
2. SMTP configuration for Supabase Auth
3. ARIA backend API connections
4. Test full ARIA flow end-to-end

### Medium Priority
5. DEV credential separation (Sheets, Telegram, Drive)
6. Portfolio dynamic injection to n8n
7. Cost tracking implementation

### Low Priority
8. Google Calendar OAuth integration
9. Right-click context menu in chat
10. Mobile long-press support

---

## 🛠️ INFRASTRUCTURE STATUS

### Agents Running
| Agent | Port | Status |
|-------|------|--------|
| Event Bus | 8099 | ✅ |
| ATLAS | 8007 | ✅ |
| SENTINEL | 8019 | ✅ |
| PANOPTES | 8023 | ✅ |
| ASCLEPIUS | 8024 | ✅ |
| HERMES | 8014 | ✅ |
| CHRONOS | 8010 | ✅ |
| HADES | 8008 | ✅ |
| AEGIS | 8012 | ✅ |
| ARGUS | 8016 | ✅ |

### Health
- PANOPTES Score: ~85%
- Critical Issues: 0
- High Issues: 0
- Automated healing: Active

---

## 📊 PORTFOLIO

Current: $58K - $117K across 28+ wins

### Today's Win
- PANOPTES + ASCLEPIUS: Self-healing infrastructure
- Value: $3K - $6K
- Anchoring: "DevOps team replacement"

---

## 🗂️ KEY FILES

| File | Purpose |
|------|---------|
| /opt/leveredge/config/agent-registry.yaml | Agent definitions |
| /opt/leveredge/docs/LOOSE-ENDS-20260118.md | This file |
| /opt/leveredge/specs/ | GSD build specs |
| /opt/leveredge/LESSONS-SCRATCH.md | Debug notes |

---

## ⚡ QUICK COMMANDS

```bash
# Check system health
curl http://localhost:8023/status

# Auto-heal issues
curl -X POST http://localhost:8024/emergency/auto

# Deploy ARIA frontend
cd /opt/leveredge/data-plane/dev/aria-frontend && git pull && npm run build

# Restart Caddy
cd /home/damon/stack && docker compose restart caddy
```
```

### 4.2 Update LESSONS-LEARNED.md

Consolidate from LESSONS-SCRATCH.md:

```bash
# Check scratch entries
cat /opt/leveredge/LESSONS-SCRATCH.md

# Move important ones to LESSONS-LEARNED.md
# Add January 18 section with:
# - PANOPTES deployment findings
# - URL format (localhost vs container name)
# - Frontend build/deploy workflow
```

### 4.3 Update agent-registry.yaml

Ensure all agents have correct:
- Ports
- URLs (localhost for systemd agents)
- Descriptions
- Actions

---

## PART 5: PORTFOLIO UPDATE (5 min)

```bash
# Add today's wins
/opt/leveredge/shared/scripts/add-win.sh \
  "Self-Healing Infrastructure (PANOPTES + ASCLEPIUS)" \
  "infrastructure" \
  "Built and deployed integrity monitoring and auto-healing agents. System detects issues automatically and heals them without manual intervention. Reduced issues from 83 to 42, achieved zero high-severity issues." \
  3000 6000 \
  "Enterprise DevOps teams charge $150K+/year for this level of automation"

/opt/leveredge/shared/scripts/add-win.sh \
  "ARIA Frontend V3" \
  "frontend" \
  "Deployed new ARIA personal assistant frontend with Council meetings, Library organization, cost tracking, and proper database integration." \
  2000 4000 \
  "Custom AI chat interfaces typically cost $20K-50K to build"
```

---

## PART 6: GIT COMMIT EVERYTHING (10 min)

```bash
cd /opt/leveredge

# Check status
git status

# Add all changes
git add -A

# Commit with detailed message
git commit -m "Jan 18: Major infrastructure upgrade + ARIA V3 frontend

INFRASTRUCTURE:
- Deployed PANOPTES integrity guardian (port 8023)
- Deployed ASCLEPIUS healing agent (port 8024)
- Health score improved: 68% → 85%+
- Zero high-severity issues
- Daily automated scans configured

ARIA FRONTEND V3:
- Complete redesign with Council, Library, Cost Tracking
- Proper aria_* table naming convention
- Git-based deployment workflow
- DEV/PROD separation

CLEANUP:
- Removed duplicate agent directories
- Fixed PANOPTES false positives
- Updated registry URLs to localhost
- Created systemd services for core agents
- Storage cleanup functions added
- Cron jobs for automated maintenance

DOCUMENTATION:
- Updated LOOSE-ENDS.md
- Updated LESSONS-LEARNED.md
- Portfolio wins added

Status: 42 days to launch, infrastructure stable"

# Push
git push origin main
```

---

## VERIFICATION CHECKLIST

After completing all parts:

```bash
# 1. ARIA login works
echo "Test: https://dev.aria.leveredgeai.com"

# 2. PANOPTES health score
curl http://localhost:8023/status | python3 -m json.tool | grep health_score

# 3. All core agents running
sudo systemctl is-active leveredge-{event-bus,atlas,sentinel,panoptes,asclepius,hermes,chronos,hades,aegis,argus}

# 4. Git is clean
cd /opt/leveredge && git status

# 5. Cron jobs installed
crontab -l | grep -E "panoptes|asclepius|cleanup"

# 6. Documentation updated
ls -la /opt/leveredge/docs/LOOSE-ENDS*.md
```

---

## SUCCESS CRITERIA

- [ ] ARIA password reset and can login
- [ ] PANOPTES health score > 85%
- [ ] Zero high-severity issues
- [ ] All core agents running on systemd
- [ ] Cron jobs for automated maintenance
- [ ] Git committed and pushed
- [ ] Documentation current
- [ ] Portfolio updated with today's wins

---

## WHAT'S NEXT (After This GSD)

1. **Google Workspace** - Manual setup by Damon
2. **SMTP for Supabase** - After email is working
3. **ARIA backend wiring** - Connect frontend to n8n webhooks
4. **Outreach prep** - Starts February 1

---

**42 days to launch. Infrastructure is solid. Time to monetize.**
