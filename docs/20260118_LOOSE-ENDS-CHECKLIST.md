# LOOSE ENDS CHECKLIST - January 18, 2026 Evening

**From this chat session. Nothing forgotten.**

---

## ✅ COMPLETED THIS SESSION

- [x] DEV/PROD isolation system implemented
- [x] Updated guidance docs (LOOSE-ENDS, FUTURE-VISION, ARCHITECTURE)
- [x] Agent registry corrected (VARYS → ARIA SANCTUM, ALCHEMY names fixed)
- [x] ARIA Supremacy architecture documented
- [x] Pipeline tables SQL created
- [x] PM tool comparison (Leantime vs OpenProject)
- [x] CONSUL added as external PM agent
- [x] Creative team renamed: MUSE, QUILL, STAGE, REEL, CRITIC

---

## 🔄 IN PROGRESS

- [ ] Google Workspace setup (waiting for propagation)
  - Then: MX records, SPF/DKIM, Supabase SMTP, Instantly connect

---

## 📋 NEXT ACTIONS (Priority Order)

### Immediate (Today/Tonight)

1. **Run pipeline SQL in DEV Supabase**
   ```
   File: /opt/leveredge/specs/pipeline-aria-supremacy-tables.sql
   ```

2. **Git commit all new docs**
   ```bash
   cd /opt/leveredge
   git add docs/ specs/
   git commit -m "Jan 18: Strategic decisions, ARIA supremacy, pipeline tables, PM comparison"
   git push
   ```

3. **Cloudflare DNS for Google Workspace**
   - Add MX records when Google provides them
   - Add SPF, DKIM, DMARC TXT records

### This Week

4. **Deploy Leantime + OpenProject**
   - Add to Docker stack
   - Configure Caddy
   - Add DNS records
   - Initialize admin accounts

5. **AEGIS page in Command Center**
   - New Bolt.new project for Command Center
   - AEGIS page first
   - Built-in chat with agent

6. **CONSUL Phase 1 build**
   - Basic PM operations
   - OpenProject adapter first
   - Leantime adapter second

---

## 📦 CAPTURED REQUIREMENTS

### AEGIS Page (Bolt.new Prompt)
```
Add AEGIS Credentials Management page at route /agents/aegis

Database tables (Supabase):
- aegis_credentials
- aegis_audit_log

Sections:
1. Header: 🛡️ AEGIS "Guardian of Secrets" + status
2. Dashboard: Health score gauge, Expiring Soon, Total, Failed Auth cards
3. Credentials list with filters (project, provider, type, status)
4. Actions: [Add Credential] [Bulk Health Check] [Rotate Expiring]
5. Built-in chat with AEGIS agent

Design: ADHD-friendly, one primary metric prominent, color-coded status
```

### Command Center (New Bolt.new Project)
- Separate from ARIA
- Has own chat per agent
- 8 domains navigation (GAIA, THE KEEP, PANTHEON, etc.)
- Agent pages with Dashboard + Actions + Chat pattern

### Frontend Projects (Separate)
| Project | Purpose |
|---------|---------|
| ARIA | Personal assistant |
| Command Center | Infrastructure + agent chat |
| Customer Portal | Client dashboards (future) |
| Public Website | Marketing (future) |

---

## 📊 DATABASE TABLES TO CREATE

### Already in SQL file ready to run:
- pipeline_definitions
- pipeline_executions
- pipeline_stage_logs
- aria_knowledge
- council_decisions
- council_decision_impacts
- agent_skills
- agent_skill_gaps
- agent_audits
- consul_pm_connections
- consul_projects
- consul_project_sync

### Also fixes:
- ALCHEMY agent names (quill, stage, reel, critic)
- VARYS domain (ARIA_SANCTUM)
- Adds CONSUL

---

## 🔧 TECHNICAL TASKS

### DNS Records Needed
- [ ] dev.command.leveredgeai.com → A record
- [ ] leantime.leveredgeai.com → A record
- [ ] openproject.leveredgeai.com → A record
- [ ] MX records for leveredgeai.com (Google Workspace)

### Password Reset (Still pending)
```bash
docker exec -it supabase-db psql -U postgres -d postgres -c "
UPDATE auth.users 
SET encrypted_password = crypt('NEW_PASSWORD', gen_salt('bf'))
WHERE email = 'damonhess@hotmail.com';
"
```

---

## 🏛️ DECISIONS MADE TODAY

| Decision | Rationale |
|----------|-----------|
| ARIA + Command Center separate | Isolation, redundancy |
| Command Center has built-in agent chat | No ARIA dependency |
| VARYS = internal PM (ARIA SANCTUM) | Eyes and ears of LeverEdge project |
| CONSUL = external PM (CHANCERY) | Client projects, methodology |
| STAGE owns design/aesthetics | Clear ownership |
| ALOY handles agent audits | Extends audit role |
| Use BOTH Leantime + OpenProject | Different strengths |
| DEV/PROD isolation mandatory | Safety after accident |
| Google Workspace Starter | $6/mo, Instantly handles email features |

---

## 🔗 KEY FILES CREATED TODAY

| File | Purpose |
|------|---------|
| `/opt/leveredge/docs/20260118_LOOSE-ENDS.md` | Current status |
| `/opt/leveredge/docs/20260118_FUTURE-VISION.md` | Roadmap |
| `/opt/leveredge/docs/20260118_ARCHITECTURE.md` | System design |
| `/opt/leveredge/docs/20260118_STRATEGIC-DECISIONS.md` | Decisions from chat |
| `/opt/leveredge/docs/20260118_AGENT-REGISTRY-CORRECTED.md` | Fixed agents |
| `/opt/leveredge/docs/20260118_ARIA-SUPREMACY.md` | Info architecture |
| `/opt/leveredge/docs/20260118_PM-TOOL-COMPARISON.md` | Leantime vs OpenProject |
| `/opt/leveredge/specs/dev-prod-isolation-system.md` | Isolation spec |
| `/opt/leveredge/specs/pipeline-aria-supremacy-tables.sql` | Database tables |

---

## ⚠️ DON'T FORGET

1. **ALOY audits CONSUL** - First pipeline test after CONSUL built
2. **All pipelines supervised until reliable** - VARYS watches, ARIA informed
3. **Council decisions memorialized** - Use council_decisions table
4. **ARIA knows all** - Event bus subscriptions, knowledge base updates
5. **42 days to launch** - March 1, 2026

---

*Last updated: January 18, 2026 ~11:00 PM*
