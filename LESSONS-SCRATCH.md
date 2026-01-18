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

