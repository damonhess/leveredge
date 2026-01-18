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

