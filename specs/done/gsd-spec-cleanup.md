# GSD: Spec Cleanup & Agent Fixes

**Priority:** MEDIUM
**Time:** ~10 min
**Purpose:** Archive dead specs, fix ASCLEPIUS, resolve PLUTUS port conflict

---

## PHASE 1: ARCHIVE DEAD SPECS

Create archive directory and move superseded specs:

```bash
mkdir -p /opt/leveredge/specs/archive

# CONSUL specs - superseded by MAGNUS
mv /opt/leveredge/specs/CONSUL-PM-SPEC.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/CONSUL-UNIVERSAL-PM-SPEC.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/gsd-consul-pm.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/gsd-consul-universal-pm.md /opt/leveredge/specs/archive/

# MAGNUS specs - completed
mv /opt/leveredge/specs/MAGNUS-UNIVERSAL-PM-SPEC.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/gsd-magnus-universal-pm.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/gsd-magnus-adapters.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/gsd-magnus-heracles-merge.md /opt/leveredge/specs/archive/

# Mega GSDs - too big, individual approach better
mv /opt/leveredge/specs/MEGA-GSD-JANUARY-SPRINT.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/mega-gsd-dashboard-aegis-v2.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/mega-gsd-full-dashboard-build.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/mega-gsd-infrastructure-hardening.md /opt/leveredge/specs/archive/
mv /opt/leveredge/specs/gsd-mega-build-jan18.md /opt/leveredge/specs/archive/

# Superseded loose ends
mv /opt/leveredge/specs/gsd-loose-ends-jan18.md /opt/leveredge/specs/archive/

# Completed GSDs - move to done
mkdir -p /opt/leveredge/specs/done
mv /opt/leveredge/specs/gsd-midas-finance.md /opt/leveredge/specs/done/
mv /opt/leveredge/specs/gsd-satoshi-crypto.md /opt/leveredge/specs/done/
mv /opt/leveredge/specs/gsd-varys-fleet-audit.md /opt/leveredge/specs/done/
mv /opt/leveredge/specs/gsd-varys-discovery.md /opt/leveredge/specs/done/
mv /opt/leveredge/specs/gsd-magnus-unified-command-center.md /opt/leveredge/specs/done/
```

---

## PHASE 2: FIX ASCLEPIUS

ASCLEPIUS exists but has no Dockerfile:

```bash
cat > /opt/leveredge/control-plane/agents/asclepius/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    anthropic \
    pydantic

COPY asclepius.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

EXPOSE 8024

CMD ["uvicorn", "asclepius:app", "--host", "0.0.0.0", "--port", "8024"]
EOF
```

Verify ASCLEPIUS is in docker-compose:

```bash
grep -A5 "asclepius:" /opt/leveredge/docker-compose.fleet.yml
```

If missing, add:

```yaml
  asclepius:
    build:
      context: ./control-plane/agents/asclepius
      dockerfile: Dockerfile
    container_name: asclepius
    hostname: asclepius
    profiles: ["security", "all"]
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - EVENT_BUS_URL=http://event-bus:8099
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "8024:8024"
    networks:
      - fleet-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8024/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    labels:
      - "leveredge.agent=ASCLEPIUS"
      - "leveredge.domain=OLYMPUS"
      - "leveredge.port=8024"
```

---

## PHASE 3: RESOLVE PLUTUS PORT CONFLICT

**Issue:** Both MIDAS and PLUTUS claim port 8205

**Decision:** MIDAS wins (newer, more comprehensive). Move PLUTUS to 8207.

```bash
# Check current PLUTUS port
grep -E "port.*820" /opt/leveredge/control-plane/agents/plutus/plutus.py

# Update PLUTUS to 8207
sed -i 's/8205/8207/g' /opt/leveredge/control-plane/agents/plutus/plutus.py
```

Update docker-compose if PLUTUS entry exists:

```yaml
  plutus:
    # ... 
    ports:
      - "8207:8207"  # Changed from 8205
```

**Alternative:** If PLUTUS functionality is fully covered by MIDAS, consider deprecating PLUTUS:

```bash
# Option B: Deprecate PLUTUS
mv /opt/leveredge/control-plane/agents/plutus /opt/leveredge/control-plane/agents/_deprecated_plutus
# Comment out plutus in docker-compose.fleet.yml
```

---

## PHASE 4: UPDATE AGENT-ROUTING.md

Add/update entries:

```markdown
## Port Assignments (Updated)

| Port | Agent | Domain | Status |
|------|-------|--------|--------|
| 8024 | ASCLEPIUS | OLYMPUS | Active |
| 8205 | MIDAS | THE_KEEP | Active |
| 8206 | SATOSHI | THE_KEEP | Active |
| 8207 | PLUTUS | THE_KEEP | Active (or Deprecated) |
| 8210 | SOLON | THE_KEEP | Active |
| 8211 | QUAESTOR | THE_KEEP | Active |
| 8220 | STEWARD | THE_KEEP | Active |

## Deprecated Agents

| Agent | Replaced By | Notes |
|-------|-------------|-------|
| CONSUL | MAGNUS | Universal PM |
| CROESUS | QUAESTOR | Renamed |
| HERACLES | MAGNUS | Merged |
```

---

## PHASE 5: VERIFY CREATIVE FLEET

Check if creative agents have Dockerfiles and are in compose:

```bash
for agent in muse calliope thalia erato clio; do
  echo "=== $agent ==="
  ls /opt/leveredge/control-plane/agents/$agent/ 2>/dev/null || \
  ls /opt/leveredge/control-plane/agents/creative-fleet/$agent/ 2>/dev/null || \
  echo "NOT FOUND"
done
```

Creative fleet may be in a subdirectory. Verify structure matches docker-compose.

---

## DELIVERABLES

- [ ] Archive 15+ dead/superseded specs
- [ ] Move completed GSDs to /done
- [ ] Add ASCLEPIUS Dockerfile
- [ ] Verify ASCLEPIUS in docker-compose
- [ ] Resolve PLUTUS port (move to 8207 or deprecate)
- [ ] Update AGENT-ROUTING.md
- [ ] Verify creative fleet structure
- [ ] Commit

---

## SPEC INVENTORY AFTER CLEANUP

**Active GSDs (to run):**
- gsd-command-center.md → Council page
- gsd-pipeline-system.md → Multi-agent workflows
- gsd-advisory-upgrades.md → If not yet run
- gsd-agent-documentation.md → Auto-doc

**Active Specs (reference):**
- MASTER-CONTROL-CENTER-SPEC.md
- LCIS-COLLECTIVE-INTELLIGENCE.md
- chiron-v2-upgrade.md
- scholar-v2-upgrade.md
- atlas-orchestration-v2.md
- conclave-v2-smart-councils.md

**Archived:**
- All CONSUL specs
- All mega-GSDs
- Superseded loose ends

---

## COMMIT MESSAGE

```
chore: Spec cleanup and agent fixes

ARCHIVED:
- CONSUL specs (superseded by MAGNUS)
- Mega-GSDs (individual approach better)
- Superseded loose ends

FIXED:
- ASCLEPIUS Dockerfile added
- PLUTUS port conflict resolved (→ 8207)

ORGANIZED:
- /specs/archive/ for superseded
- /specs/done/ for completed
- Updated AGENT-ROUTING.md

Clean house, clear mind.
```
