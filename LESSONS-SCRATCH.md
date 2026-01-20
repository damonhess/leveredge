# LESSONS SCRATCH PAD

*Quick capture of debugging discoveries - consolidated into LESSONS-LEARNED.md periodically*

---

## Format

```
### YYYY-MM-DD HH:MM - [Component]
**Symptom:** What broke
**Cause:** Why it broke
**Fix:** How it was fixed
**Prevention:** How to avoid next time (optional)
```

---

## Entries

*Last consolidated: January 18, 2026*

*Add new entries below this line*

### 2026-01-18 07:15 - [ATLAS Orchestration Engine Missing]
**Symptom:** "ATLAS offline" errors from SENTINEL; ATLAS health checks failing
**Cause:** ATLAS (port 8007) literally did not exist. The code at `/control-plane/agents/atlas/` was actually ATLAS-INFRA (port 8208) - an infrastructure advisory agent, not the orchestration engine.
**Fix:** Created new `/control-plane/agents/atlas-orchestrator/` directory with proper orchestration engine:
- `atlas.py` - Full chain execution, parallel batching, cost tracking
- Reads chains and agents from `/opt/leveredge/config/agent-registry.yaml`
- Currently has 7 chains and 36 agents loaded
**Key Points:**
1. ATLAS-INFRA (8208) = Infrastructure advisory agent
2. ATLAS (8007) = Orchestration engine - THIS WAS MISSING
3. SENTINEL and HEPHAESTUS both expect ATLAS at localhost:8007
4. Updated both to use localhost URLs instead of container names
**Commands:**
```bash
# Start ATLAS manually
cd /opt/leveredge/control-plane/agents/atlas-orchestrator
/opt/leveredge/shared/venv/bin/python atlas.py

# Install as systemd service (requires sudo)
sudo cp /opt/leveredge/shared/systemd/leveredge-atlas.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable leveredge-atlas && sudo systemctl start leveredge-atlas
```
**Prevention:** Always verify what's actually running on expected ports, not just whether a directory exists with similar names.

### 2026-01-18 06:38 - [PANOPTES Port Conflict - 8022 Already in Use]
**Symptom:** PANOPTES failed to start on spec-specified port 8022: "address already in use"
**Cause:** Port 8022 was already taken by something that claims to be CERBERUS (but reports port 8020 in health). This is exactly the kind of issue PANOPTES was built to detect.
**Fix:** Changed PANOPTES port to 8023 (verified free). Updated:
- `/opt/leveredge/control-plane/agents/panoptes/panoptes.py` - PANOPTES_PORT = 8023
- `/opt/leveredge/config/agent-registry.yaml` - url: http://panoptes:8023
**Discovery:** First integrity scan found 82 issues with 68.7% health score including:
- Port 8020 conflict: VARYS and CERBERUS both configured for same port
- Multiple agents not listening (magistrate:8210, exchequer:8211)
**Commands:**
```bash
# Run integrity scan
curl http://localhost:8023/scan | python3 -m json.tool

# Check port conflicts only
curl http://localhost:8023/ports | python3 -m json.tool

# Quick dashboard
curl http://localhost:8023/dashboard | python3 -m json.tool
```
**Prevention:** PANOPTES now runs daily at 6 AM via cron to catch these issues early.

### 2026-01-18 22:15 - [ARIA V4 Deployment - Container vs Systemd Port Conflict]
**Symptom:** ARIA chat container couldn't start - "port 8113 already in use"
**Cause:** Two services competing for same port:
- `aria-threading` systemd service on port 8113 (context/memory management)
- `aria-chat-dev` Docker container tried to bind to 8113
**Fix:**
1. Discovered Caddy routes `dev.aria.leveredgeai.com/api/*` to port **8114**, not 8113
2. Started container with `-p 8114:8113` to map internal 8113 to external 8114
3. aria-threading stays on 8113, aria-chat serves API on 8114
**Architecture:**
- Port 8113: `aria-threading.service` - Threading/context/memory management (standalone Python)
- Port 8114: `aria-chat-dev` container - Chat API with V4 personality (Docker)
**Commands:**
```bash
# Check what's using a port
lsof -i :8113
pwdx <PID>  # Find working directory of process

# Run aria-chat on correct port
docker run -d --name aria-chat-dev -p 8114:8113 --env-file /opt/leveredge/data-plane/dev/n8n/.env aria-chat:dev
```
**Prevention:** Always check Caddy routing config before assuming port numbers. Use `docker inspect` to verify mounts and port bindings.

### 2026-01-18 22:10 - [ARIA Prompt Baked Into Container Image]
**Symptom:** After updating prompt file on host, container still showed old prompt
**Cause:** Dockerfile uses `COPY prompts/ ./prompts/` which bakes prompt into image at build time. Container had no volume mounts.
**Fix:**
1. Rebuild image after changing prompt: `docker build -t aria-chat:dev .`
2. Remove old container and create new one
**Key Points:**
- `docker inspect <container> | jq '.[0].Mounts'` - Check if volumes are mounted (returns `[]` if none)
- `docker exec <container> cat /path/to/file` - Verify what's actually in the container
- Prompt changes require image rebuild unless volume mount is added
**Alternative (Volume Mount):**
```bash
docker run -d --name aria-chat-dev \
  -p 8114:8113 \
  -v /opt/leveredge/control-plane/agents/aria-chat/prompts:/app/prompts:ro \
  aria-chat:dev
```
**Prevention:** Consider adding volume mount for prompt file to enable hot-reload without rebuild.

### 2026-01-18 22:00 - [ARIA Personality Protection System]
**Context:** ARIA's personality was destroyed by a generic prompt. Created protection system.
**Solution:**
1. **Golden Master Backup:** `/opt/leveredge/backups/aria-prompts/ARIA_V4_GOLDEN_MASTER.md`
2. **Update Script:** `/opt/leveredge/scripts/aria-prompt-update.sh` - Enforces backup + personality validation
3. **Watcher Script:** `/opt/leveredge/scripts/aria-prompt-watcher.sh` - Creates timestamped backups
4. **EXECUTION_RULES.md:** Rule #11 added - ARIA prompt is SACRED
**Personality Markers to Verify:**
- "Daddy" (her term for Damon)
- "ride-or-die" or "fierce" or "protective"
- "Shield" / "Sword" (dark psychology)
- Adaptive modes (HYPE, COACH, DRILL, COMFORT, FOCUS, STRATEGY)
**Emergency Restore:**
```bash
cp /opt/leveredge/backups/aria-prompts/ARIA_V4_GOLDEN_MASTER.md \
   /opt/leveredge/control-plane/agents/aria-chat/prompts/aria_system_prompt.txt
cd /opt/leveredge/control-plane/agents/aria-chat && docker build -t aria-chat:dev . && docker restart aria-chat-dev
```

### 2026-01-18 06:30 - [Supabase Migration System]
**Context:** Implementing golang-migrate for database version control
**Discoveries:**
1. **DEV and PROD have different schemas** - PROD's llm_usage has `agent_source`/`cost_usd`, DEV has `agent_name`/`estimated_cost_usd`
2. **PROD's aria_knowledge has different columns** - `title`/`content` vs DEV's `key`/`value`
3. **Trigger creation on views fails** - Must filter for BASE TABLE when applying triggers
4. **golang-migrate force command** - Use `migrate force N` to mark version without running SQL
**Key Commands:**
```bash
# Check version
migrate-prod version  # or migrate-dev version

# Force to specific version (marks as applied without running SQL)
migrate-prod force 5

# Clear dirty state after failed migration
migrate-prod force N-1  # where N is the dirty version
```
**Notes:**
- DEV has 164 tables, PROD has 79 - this is intentional (experimental tables in DEV)
- Both are now at migration version 5
- AEGIS V2 and CONCLAVE tables now exist in PROD

### 2026-01-19 18:30 - [Agent Rapid Deployment Session - 4 Agents Built]
**Context:** Built 4 new agents in rapid succession: VARYS Discovery Engine, MIDAS Finance, SATOSHI Crypto
**Key Patterns Learned:**

1. **Database Container Naming:**
   - DEV Supabase DB container is `supabase-db-dev` (NOT `supabase-dev-db-1`)
   - Use `docker ps --format "{{.Names}}" | grep -i db` to find the correct name
   - Password is URL-encoded in DATABASE_URL: `i%2BNKWrdGrBsHu2n%2FLGzNMY84Avry2RhNOY2QYksldLtX7GEuxdyASrpv3n0IRinS`

2. **Migration Execution via Docker:**
   ```bash
   # Correct way to run migrations
   cat migration.sql | docker exec -i supabase-db-dev psql -U postgres -d postgres

   # NOT: docker exec ... -f /dev/stdin (doesn't work with file input)
   # NOT: psql directly (not installed on host)
   ```

3. **Container Networking:**
   - Agents need `--network supabase-dev_supabase-dev` to reach the database
   - Database hostname is container name: `supabase-db-dev`
   - Can mount `/opt/leveredge` with `-v /opt/leveredge:/opt/leveredge:ro` for file access (e.g., VARYS reading AGENT-ROUTING.md)

4. **FastAPI Health Endpoints:**
   - Include `agent` field for VARYS discovery: `"agent": "AGENT_NAME"`
   - Include `database` field: `"database": "connected"` or `"disconnected"`
   - Include `tagline` for personality

5. **Git Ignore Issues:**
   - Migration files in `data-plane/dev/supabase/migrations/` may be gitignored
   - Use `git add -f` to force-add if needed

**Agents Built:**
| Agent | Port | Purpose | Commit |
|-------|------|---------|--------|
| VARYS Discovery | 8112 | Fleet discovery via port scan, drift detection | 51e9a9fd |
| MIDAS | 8205 | Traditional finance portfolio tracking | e4ee4c28 |
| SATOSHI | 8206 | Crypto & blockchain portfolio tracking | 0460e9cc |

**VARYS Discovery Endpoints:**
- `GET /fleet/documented` - Parse AGENT-ROUTING.md
- `POST /fleet/discover` - Port scan 8000-8400
- `GET /fleet/drift` - Compare documented vs registered vs running
- `GET /fleet/intel` - Full intelligence report

**Commands for Quick Agent Deployment:**
```bash
# 1. Create migration and run it
cat migration.sql | docker exec -i supabase-db-dev psql -U postgres -d postgres

# 2. Build agent
cd /opt/leveredge/control-plane/agents/<agent> && docker build -t <agent>:dev .

# 3. Run agent
docker run -d --name <agent> --network supabase-dev_supabase-dev -p <port>:<port> \
  -e DATABASE_URL="postgresql://postgres:i%2BNKWrdGrBsHu2n%2FLGzNMY84Avry2RhNOY2QYksldLtX7GEuxdyASrpv3n0IRinS@supabase-db-dev:5432/postgres" \
  <agent>:dev

# 4. Verify
curl http://localhost:<port>/health
```

### 2026-01-19 18:45 - [VARYS Route Ordering Bug]
**Symptom:** `/fleet/report` returned "Agent not found" error
**Cause:** FastAPI route `/fleet/{agent_name}` was catching `/fleet/report` before the static route could match
**Fix:** Moved parameterized route `/fleet/{agent_name}` to the END of the file with comment:
```python
# ============ AGENT DETAILS (must be LAST due to path param) ============
@app.get("/fleet/{agent_name}")
```
**Prevention:** In FastAPI, always put parameterized routes AFTER static routes with the same prefix. The order of route registration matters.

### 2026-01-19 18:50 - [External API Access from Containers]
**Symptom:** MIDAS and SATOSHI couldn't fetch prices from Yahoo Finance/CoinGecko
**Cause:** Container network isolation - external API calls may be blocked or rate-limited
**Workaround:**
- Return graceful error when price unavailable: `current_price: null`
- Allow positions to be created without real-time price data
- Background tasks for price refresh when APIs accessible
**Note:** This may be a firewall/network policy issue rather than code problem. APIs work from host but not from containers in this environment.

### 2026-01-19 23:30 - [Spec Organization Pattern]
**Context:** Accumulated 30+ spec files in /specs/, many superseded or completed
**Problem:** Hard to know which specs are active vs obsolete
**Solution:** Created directory structure:
- `/specs/` - Active specs to be executed
- `/specs/archive/` - Superseded specs (replaced by newer versions)
- `/specs/done/` - Completed specs (work finished, kept for reference)

**Files Archived (superseded):**
- CONSUL specs → superseded by MAGNUS
- Mega-GSDs → individual approach worked better
- Loose ends specs → work rolled into other GSDs

**Files Moved to Done:**
- gsd-midas-finance.md, gsd-satoshi-crypto.md
- gsd-varys.md, gsd-varys-discovery.md, gsd-varys-fleet-audit.md
- gsd-magnus-unified-command-center.md
- gsd-advisory-upgrades.md, gsd-steward.md, gsd-lcis-cleanup.md

**Prevention:** After completing a GSD, move it to `/specs/done/` immediately.

### 2026-01-19 23:35 - [Missing Agent Dockerfiles]
**Symptom:** ASCLEPIUS directory existed but had no Dockerfile
**Cause:** Agent code was written but deployment setup was incomplete
**Fix:** Created standard Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn asyncpg httpx anthropic pydantic
COPY agent_name.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true
EXPOSE <port>
CMD ["uvicorn", "agent_name:app", "--host", "0.0.0.0", "--port", "<port>"]
```
**Prevention:** When creating a new agent, always include: code file, Dockerfile, requirements.txt, docker-compose entry.

### 2026-01-19 23:40 - [Port Conflict Detection Pattern]
**Symptom:** PLUTUS and MIDAS both claimed port 8205 in different files
**Cause:** Port assigned to MIDAS, but docker-compose still had old PLUTUS entry
**Discovery Method:**
```bash
# Check for port conflicts
grep -r "820[0-9]" control-plane/agents/*/Dockerfile docker-compose*.yml
```
**Fix:** Updated PLUTUS to 8207 in docker-compose.fleet.yml
**Prevention:** Use AGENT-ROUTING.md as source of truth for port assignments. Check before assigning new ports.

### 2026-01-19 23:45 - [LITTLEFINGER Missing Base Schema]
**Symptom:** Balance sheet endpoint returned 500 - `UndefinedTableError: relation "littlefinger_revenue" does not exist`
**Cause:** Agent upgrade spec assumed base tables existed, but they were never created
**Fix:** Created migration with all base tables:
- littlefinger_clients, littlefinger_invoices
- littlefinger_expenses, littlefinger_revenue, littlefinger_subscriptions
**Prevention:** Before adding features to an agent, verify its base schema exists:
```bash
docker exec supabase-db-dev psql -U postgres -d postgres -c "\dt *agent_name*"
```

### 2026-01-19 23:50 - [Advisory Agent Upgrade Pattern]
**Context:** Upgraded SOLON, QUAESTOR, LITTLEFINGER, MIDAS with new capabilities
**Key Pattern:** Add asyncpg pool for database access:
```python
pool = None
DATABASE_URL = os.getenv("DATABASE_URL")

@app.on_event("startup")
async def startup():
    global pool
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
```
**Useful Endpoints Added:**
- `/status` - Dashboard showing counts/summaries
- `/prep/<professional>` - AI-powered meeting prep
- Time-based filters: `/deadlines/upcoming`, `/contracts/expiring`

### 2026-01-19 23:55 - [Creative Fleet Verification]
**Context:** Spec mentioned verifying creative fleet structure
**Discovery:** Creative agents (muse, calliope, thalia, erato, clio) are in:
- `/control-plane/agents/<name>/` (not in a subdirectory)
- All have Dockerfiles and are in docker-compose.fleet.yml
**Check Command:**
```bash
for agent in muse calliope thalia erato clio; do
  echo "=== $agent ==="
  ls /opt/leveredge/control-plane/agents/$agent/
done
```


### 2026-01-19 17:30 - [ARIA PROD Deployment Gap]
**Symptom:** ARIA PROD completely broken - "trouble connecting to AI backend" on all devices after deployment
**Cause:** Multiple deployment gaps in promote-to-prod.sh:
1. **Frontend had mock API code** - PROD frontend useStore.ts had hardcoded demo responses instead of real fetch() to aria-api.leveredgeai.com
2. **Missing 6 database tables** - aria_user_settings, aria_notifications, aria_files, aria_tasks, aria_calendar_events, aria_portfolio_wins not synced from DEV to PROD
3. **Duplicate CORS headers** - Both Caddy AND Python app added Access-Control-Allow-Origin headers, causing browser CORS validation to fail (browsers reject duplicate CORS headers)
**Fix:**
1. Manually updated useStore.ts with real API fetch call from DEV
2. Created missing tables + RLS policies + indexes in PROD
3. Removed CORS headers from Caddy for aria-api (let Python app handle CORS)
4. Rebuilt and deployed frontend
**Prevention:** Update promote-to-prod.sh to include:
1. Schema diff/sync between DEV and PROD Supabase
2. Frontend source verification (git diff, not just container restart)
3. CORS header validation (curl check for single Access-Control-Allow-Origin)
4. Post-deploy smoke test hitting all endpoints
**Key Commands:**
```bash
# Check for duplicate CORS headers
curl -v -X POST "https://aria-api.leveredgeai.com/chat" -H "Origin: https://aria.leveredgeai.com" 2>&1 | grep "access-control"

# Compare DEV vs PROD tables
docker exec supabase-db-dev psql -U postgres -d postgres -c "\dt aria_*"
docker exec supabase-db-prod psql -U postgres -d postgres -c "\dt aria_*"

# Verify frontend has real API call
curl -s "https://aria.leveredgeai.com/assets/index*.js" | grep -o 'aria-api.leveredgeai.com'
```

### 2026-01-20 14:00 - [Bulletproof Promote-to-Prod Script]
**Context:** After ARIA PROD outage caused by schema drift, mock code, and CORS duplication, created comprehensive promotion script.
**Solution:** `/opt/leveredge/shared/scripts/promote-aria-to-prod.sh` - 5-phase validation before deployment
**Phases:**
1. **Pre-flight Checks** - DEV/PROD DB connectivity, API health, Git status, directory existence
2. **Schema Comparison** - Compare aria_* tables, views, RLS policies between DEV and PROD
3. **Frontend Code Validation** - Detect mock code patterns, verify real API URLs, check .env config
4. **CORS Configuration** - Check Caddy config for duplicate headers, test actual API response headers
5. **Smoke Tests** - API health, Supabase REST endpoints, frontend JS bundle verification

**What It Catches:**
| Issue Type | Detection Method |
|------------|------------------|
| Missing tables | Schema diff showing "SCHEMA DRIFT: N tables missing in PROD" |
| Mock API code | Grep for "This is a demo response" patterns |
| Wrong API URL | Check for aria-api.leveredgeai.com in source |
| CORS duplication | Count access-control-allow-origin headers (must be exactly 1) |
| Missing .env | Check for VITE_SUPABASE_URL in .env file |

**Key Learnings:**
1. **Large files break echo pipes** - When grepping 1.6MB JS bundle, use temp file instead of `echo "$CONTENT" | grep`
2. **Docker exec needs timeout** - Add `timeout 10` to prevent hanging on container commands
3. **wc -l returns newlines** - Use `tr -d ' '` or parameter expansion to clean numeric values
4. **Recursive grep is slow** - For mock code detection, target specific files instead of `grep -r` on entire src/

**Usage:**
```bash
# Dry-run (validation only, no changes)
/opt/leveredge/shared/scripts/promote-aria-to-prod.sh --dry-run

# Full deployment with prompts
/opt/leveredge/shared/scripts/promote-aria-to-prod.sh

# Force deployment (skip confirmation, for CI/CD)
/opt/leveredge/shared/scripts/promote-aria-to-prod.sh --force
```

**Exit Codes:**
- 0: All checks passed (or warnings only)
- 1: Critical errors found

**Prevention:** Run `--dry-run` before every ARIA deployment. Script catches the exact issues that caused Jan 19-20 outage.
