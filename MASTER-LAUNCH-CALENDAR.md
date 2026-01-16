# MASTER LAUNCH CALENDAR

*Last Updated: January 16, 2026*
*Launch: March 1, 2026 (45 days)*

---

## CURRENT STATE

### What's Built (Control Plane) ✅
| Agent | Port | Status |
|-------|------|--------|
| GAIA | 8000 | Ready (emergency restore) |
| Event Bus | 8099 | Running |
| ATLAS | n8n | Active (master orchestrator) |
| HEPHAESTUS | 8011 | Active (MCP server, Claude Web connected) |
| AEGIS | 8012 | Active (credential vault) |
| CHRONOS | Docker | Active (backup manager) |
| HADES | Docker | Active (rollback system) |
| HERMES | 8014 | Built (needs Telegram config) |
| ARGUS | 8016 | Built (needs Prometheus access) |
| ALOY | 8015 | Built (audit/anomaly) |
| ATHENA | 8013 | Built (documentation) |

### What's NOT Migrated Yet ❌
| Component | Current Location | Target Location |
|-----------|------------------|-----------------|
| ARIA workflows | Old n8n | /opt/leveredge/data-plane/prod/n8n |
| Dev n8n | /home/damon/environments/dev | /opt/leveredge/data-plane/dev/n8n |
| Prod n8n | /home/damon/stack | /opt/leveredge/data-plane/prod/n8n |
| ARIA frontend | aria.leveredgeai.com | Same (just backend move) |
| Supabase | /home/damon/stack | /opt/leveredge/data-plane/prod/supabase |

### Portfolio Status
**Current Value:** $57,500 - $109,500 across 8 wins
- Tracked in `aria_wins` and `aria_portfolio_summary` tables
- RPC functions working

---

## BLOCKING ISSUES

| Blocker | Impact | Effort |
|---------|--------|--------|
| ARIA not migrated | Can't demo | 2-3 days |
| No dev/prod mirror | Can't safely develop | 1 day |
| Old agent fleet running | Port conflicts, confusion | 1 hour |
| promote-to-prod.sh not working | Manual deployments | 2 hours |
| Credential separation incomplete | Google Sheets (9 refs), Telegram (14 refs), Drive (4 refs) | 4 hours |

---

## THE CALENDAR

### WEEK 1: Jan 16-22 (Infrastructure Complete)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Jan 16 | ✅ Control plane | Phase 0-4 complete |
| **Fri** | **Jan 17** | **Data plane setup** | Dev + Prod n8n in /opt/leveredge |
| Sat | Jan 18 | ARIA migration | Export → Import → Verify |
| Sun | Jan 19 | ARIA testing | All 7 modes working |
| Mon | Jan 20 | Dev workflow | promote-to-prod.sh working |
| Tue | Jan 21 | Credential separation | Finish Google/Telegram/Drive |
| **Wed** | **Jan 22** | **ARIA DEMO-READY** | ✓ Milestone |

### WEEK 2: Jan 23-29 (Outreach Prep)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| Thu | Jan 23 | Niche research | List 5 potential niches |
| Fri | Jan 24 | Niche selection | Pick ONE, document ICP |
| Sat | Jan 25 | TRW Outreach start | Begin module |
| Sun | Jan 26 | TRW Outreach | Continue |
| Mon | Jan 27 | TRW Outreach | Complete |
| Tue | Jan 28 | Outreach materials | Loom video, case studies |
| **Wed** | **Jan 29** | **OUTREACH READY** | ✓ Scripts, 50 targets |

### WEEK 3: Jan 30 - Feb 5 (First Outreach)

| Day | Date | Focus | Target |
|-----|------|-------|--------|
| Thu | Jan 30 | Outreach | 3 attempts |
| Fri | Jan 31 | Outreach | 3 attempts |
| Sat | Feb 1 | Outreach | 2 attempts |
| Sun | Feb 2 | Follow-up | Respond to replies |
| Mon | Feb 3 | Outreach | 2 attempts |
| **Tue** | **Feb 4** | **10 ATTEMPTS** | ✓ Milestone |
| Wed | Feb 5 | Refine | Adjust based on response |

### WEEK 4: Feb 6-12 (Discovery Calls)

| Day | Date | Focus | Target |
|-----|------|-------|--------|
| Thu-Fri | Feb 6-7 | Continue outreach | Warm leads |
| Sat | Feb 8 | Discovery call 1 | First sales call |
| Sun | Feb 9 | Debrief | Document lessons |
| Mon | Feb 10 | Discovery call 2 | Second call |
| Tue | Feb 11 | Discovery call 3 | Third call |
| **Wed** | **Feb 12** | **3 CALLS DONE** | ✓ Milestone |

### WEEK 5-6: Feb 13-26 (Close & Pipeline)

- Follow up on interested leads
- Send proposals
- Continue outreach (target 20+ attempts)
- Close first deal

### WEEK 7: Feb 27 - Mar 1 (LAUNCH)

| Day | Date | Focus |
|-----|------|-------|
| Thu | Feb 27 | Final prep |
| Fri | Feb 28 | Soft launch |
| **Sat** | **Mar 1** | **🚀 LAUNCH DAY** |

---

## PHASE 5: DATA PLANE MIGRATION (Jan 17-21)

### Step 1: Stop Old Environment
```bash
# Stop old agents (they conflict with new)
sudo systemctl stop atlas-api hades-api heimdall-api chronos-api
sudo systemctl disable atlas-api hades-api heimdall-api chronos-api

# Stop old n8n stack temporarily
cd /home/damon/stack
docker compose stop n8n n8n-postgres
```

### Step 2: Create Data Plane Structure
```
/opt/leveredge/data-plane/
├── prod/
│   ├── n8n/
│   │   ├── docker-compose.yml
│   │   ├── data/
│   │   │   ├── n8n/
│   │   │   └── postgres/
│   │   └── .env
│   └── supabase/  (later)
└── dev/
    ├── n8n/
    │   ├── docker-compose.yml
    │   ├── data/
    │   │   ├── n8n/
    │   │   └── postgres/
    │   └── .env
    └── supabase/  (later)
```

### Step 3: Prod n8n (port 5678)
```yaml
# /opt/leveredge/data-plane/prod/n8n/docker-compose.yml
version: '3.8'

services:
  prod-n8n-postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - prod-net

  prod-n8n:
    image: n8nio/n8n:latest
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=prod-n8n-postgres
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
      - DB_POSTGRESDB_USER=${POSTGRES_USER}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_HOST=${N8N_HOST}
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.leveredgeai.com
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
    volumes:
      - ./data/n8n:/home/node/.n8n
    ports:
      - "5678:5678"
    networks:
      - prod-net
      - stack_net  # For Caddy access
    depends_on:
      - prod-n8n-postgres

networks:
  prod-net:
    driver: bridge
  stack_net:
    external: true
```

### Step 4: Dev n8n (port 5680)
```yaml
# /opt/leveredge/data-plane/dev/n8n/docker-compose.yml
# Same structure, different ports and credentials
ports:
  - "5680:5678"
WEBHOOK_URL=https://dev.n8n.leveredgeai.com
```

### Step 5: ARIA Workflow Migration
1. Export ARIA workflows from old n8n
2. Import to new prod-n8n
3. Clone to dev-n8n
4. Update Supabase connections
5. Verify all 7 modes work

### Step 6: Caddy Updates
```
n8n.leveredgeai.com {
    reverse_proxy localhost:5678
}

dev.n8n.leveredgeai.com {
    reverse_proxy localhost:5680
}
```

### Step 7: promote-to-prod.sh
```bash
#!/bin/bash
# Promote workflow from dev to prod

WORKFLOW_ID=$1
SOURCE="http://localhost:5680"
TARGET="http://localhost:5678"

# 1. Backup prod (via CHRONOS)
curl -X POST http://localhost:8010/backup -d '{"type":"pre-deploy"}'

# 2. Export from dev
n8n-troubleshooter export-workflow --id $WORKFLOW_ID --source dev

# 3. Import to prod
n8n-troubleshooter import-workflow --source prod

# 4. Activate
n8n-troubleshooter activate-workflow --id $WORKFLOW_ID --source prod

echo "Promoted $WORKFLOW_ID from dev to prod"
```

---

## ARIA V3.1 FEATURES (Already Built)

- ✅ Full personality (warm, sharp, witty)
- ✅ 7 adaptive modes (DEFAULT, COACH, HYPE, COMFORT, FOCUS, DRILL, STRATEGY)
- ✅ Mode auto-decay
- ✅ Dark psychology offense/defense
- ✅ User profile learning
- ✅ Portfolio tracking integration
- ✅ Time-aware responses

### ARIA V3.2 (Post-Migration)
- [ ] Dynamic portfolio injection
- [ ] Shield/Sword separation
- [ ] Improved time calibration

### ARIA V4.0 (Future)
- [ ] Multi-modal files (PDF with citations)
- [ ] Proactive reminders
- [ ] Cross-device sync
- [ ] Telegram interface
- [ ] Voice interface

---

## INCOMPLETE CREDENTIAL SEPARATION

| Credential | Refs | Priority |
|------------|------|----------|
| Google Sheets DEV | 9 workflows | HIGH |
| Telegram DEV | 14 workflows | HIGH |
| Google Drive DEV | 4 workflows | HIGH |
| Pinecone | misc | LOW |
| MCP servers | misc | LOW |
| Fal AI | misc | LOW |
| WhatsApp | misc | LOW |

---

## TECHNICAL DEBT TO ADDRESS

| Item | Impact | When |
|------|--------|------|
| Storage bucket cleanup | Orphaned files | After Feb 15 |
| n8n chat memory cleanup | DB bloat | After Feb 15 |
| Cost tracking (llm_usage table) | Scaling risk | After first client |
| SMTP configuration | Auth emails | After first client |
| GitHub repo audit | Backup risk | After Feb 15 |

---

## CLIENT SERVICE TIERS (For Sales)

| Tier | Price | What They Get |
|------|-------|---------------|
| Tier 1 | $500-2K/mo | Lead capture, email sequences, CRM integration |
| Tier 2 | $2K-5K/mo | Document processing, compliance tracking, reporting |
| Tier 3 | $5K-15K/mo | Custom AI agents, NLP interfaces, decision support |
| Tier 4 | $15K+/mo | Multi-tenant, custom dev, dedicated support |

---

## SUCCESS METRICS

### By Jan 22 (ARIA Demo-Ready)
- [ ] Data plane migrated
- [ ] ARIA workflows in new prod n8n
- [ ] Dev/prod mirror working
- [ ] promote-to-prod.sh functional
- [ ] All 7 ARIA modes tested

### By Jan 29 (Outreach Ready)
- [ ] ONE niche selected
- [ ] ICP documented
- [ ] TRW module complete
- [ ] Loom demo video
- [ ] 50 target list

### By Feb 4 (10 Attempts)
- [ ] 10 outreach messages sent
- [ ] Tracking responses
- [ ] Adjusting approach

### By Feb 12 (3 Calls)
- [ ] 3 discovery calls completed
- [ ] Lessons documented
- [ ] Pipeline started

### March 1 (LAUNCH)
- [ ] First paying client OR
- [ ] Active pipeline with warm leads

---

## DECISIONS MADE (DO NOT REVISIT)

| Decision | Rationale |
|----------|-----------|
| No LinkedIn until first clients | Protecting reputation |
| Direct outreach via TRW | More targeted than social |
| ARIA is personal, not product | Sell outcomes, not tools |
| Credential manager waits | Outreach takes priority |
| Autonomous ATLAS deferred | Wait for revenue |
| Dev-first deployment | Never direct to prod |
| Greek/mythology naming | Consistency |

---

## KEY COMMANDS

```bash
# Operations (via ATLAS - free)
atlas "restart hades"
atlas "check disk space"
atlas "show container logs for n8n"
atlas "rollback last operation"
atlas "list backups"

# Portfolio
add-win.sh "Title" "category" "description" low high "anchoring"
add-win.sh --summary

# HEPHAESTUS (Claude Web command center)
# I can now: create files, read files, list dirs, call agents, git commit
```

---

## FILE LOCATIONS

| File | Purpose |
|------|---------|
| /opt/leveredge/LAUNCH-CALENDAR.md | This file |
| /opt/leveredge/GSD-PHASE-4-AGENTS.md | Agent build spec |
| /opt/leveredge/LESSONS-LEARNED.md | Technical gotchas |
| /opt/leveredge/FUTURE-VISION-AND-EXPLORATION.md | Architecture decisions |
| /home/damon/.claude/EXECUTION_RULES.md | Claude Code rules |
| /home/damon/environments/dev/aria-assistant/prompts/ARIA_SYSTEM_PROMPT_V3.md | ARIA personality |

---

## TOMORROW'S FOCUS: Jan 17

**Goal:** Data plane setup (dev + prod n8n)

1. Stop old agent services
2. Create /opt/leveredge/data-plane structure
3. Deploy prod n8n (5678)
4. Deploy dev n8n (5680)
5. Update Caddy routes
6. Test both accessible
7. Git commit

**Do NOT do tomorrow:**
- ARIA migration (that's Saturday)
- Credential separation (that's Tuesday)
- Any new features
