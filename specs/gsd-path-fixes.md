# GSD: Path Fixes & Agent Renames

**Priority:** CRITICAL (blocks other agents)
**Time:** 5 min
**Purpose:** Fix directory names to match docker-compose, rename CROESUS → QUAESTOR

---

## THE PROBLEM

| Agent | Current Directory | Docker Expects | Issue |
|-------|------------------|----------------|-------|
| SOLON | `magistrate/` | `solon/` | Wrong path |
| QUAESTOR | `exchequer/` (as croesus.py) | `quaestor/` | Wrong path + wrong name |
| PLUTUS | `littlefinger/plutus.py` | `plutus/` | Stuck in wrong dir |

---

## EXECUTION

### Step 1: Rename Directories

```bash
cd /opt/leveredge/control-plane/agents

# SOLON - magistrate → solon
mv magistrate solon

# QUAESTOR - exchequer → quaestor  
mv exchequer quaestor

# Rename croesus.py → quaestor.py inside
mv quaestor/croesus.py quaestor/quaestor.py
```

### Step 2: Update QUAESTOR Code

In `quaestor/quaestor.py`, change:
- All references from "CROESUS" to "QUAESTOR"
- Port stays 8211
- Update docstring, app title, health endpoint

```python
# OLD
"""
CROESUS - AI-Powered Tax & Wealth Advisor Agent
Port: 8211
Named after Croesus, King of Lydia renowned for his vast wealth.
"""

# NEW  
"""
QUAESTOR - AI-Powered Tax Advisor Agent
Port: 8211
Named after the Quaestors, Roman financial magistrates who managed the treasury.
Provides tax INFORMATION (not advice) with authoritative citations.
"""
```

Update FastAPI app:
```python
# OLD
app = FastAPI(
    title="CROESUS",
    description="AI-Powered Tax & Wealth Advisor (READ-ONLY)",
    version="1.0.0"
)

# NEW
app = FastAPI(
    title="QUAESTOR",
    description="AI-Powered Tax Advisor - Tax Information Only",
    version="1.0.0"
)
```

Update health endpoint:
```python
# OLD
return {
    "status": "healthy",
    "service": "CROESUS - Tax & Wealth Advisor",
    ...
}

# NEW
return {
    "status": "healthy",
    "service": "QUAESTOR - Tax Advisor",
    "port": 8211,
    "tagline": "The treasury knows all debts owed to Caesar."
}
```

### Step 3: Fix PLUTUS Location

```bash
# Create plutus directory
mkdir -p /opt/leveredge/control-plane/agents/plutus

# Move plutus.py
mv /opt/leveredge/control-plane/agents/littlefinger/plutus.py \
   /opt/leveredge/control-plane/agents/plutus/plutus.py

# Create Dockerfile for PLUTUS
cat > /opt/leveredge/control-plane/agents/plutus/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    anthropic \
    pydantic

COPY plutus.py .

EXPOSE 8205

CMD ["uvicorn", "plutus:app", "--host", "0.0.0.0", "--port", "8205"]
EOF
```

Wait - MIDAS is now on 8205. Check PLUTUS port:

```bash
grep -E "port.*820" /opt/leveredge/control-plane/agents/plutus/plutus.py
```

If PLUTUS is also 8205, we have a conflict. Options:
- Remove PLUTUS (MIDAS does the job)
- Move PLUTUS to 8207

### Step 4: Update docker-compose.fleet.yml

Verify entries point to correct directories:

```yaml
  solon:
    build:
      context: ./control-plane/agents/solon
      dockerfile: Dockerfile
    container_name: solon
    hostname: solon
    # ... rest stays same

  quaestor:
    build:
      context: ./control-plane/agents/quaestor
      dockerfile: Dockerfile
    container_name: quaestor
    hostname: quaestor
    ports:
      - "8211:8211"
    # ... rest same as croesus entry, just renamed
```

### Step 5: Update AGENT-ROUTING.md

Change CROESUS → QUAESTOR throughout.

### Step 6: Test

```bash
# Rebuild affected containers
docker compose -f docker-compose.fleet.yml build solon quaestor

# Start them
docker compose -f docker-compose.fleet.yml up -d solon quaestor

# Test
curl http://localhost:8210/health
curl http://localhost:8211/health
```

---

## DELIVERABLES

- [ ] mv magistrate → solon
- [ ] mv exchequer → quaestor
- [ ] Rename croesus.py → quaestor.py
- [ ] Update all CROESUS references → QUAESTOR in code
- [ ] Fix PLUTUS location or remove (port conflict with MIDAS)
- [ ] Update docker-compose if needed
- [ ] Update AGENT-ROUTING.md
- [ ] Test both agents

---

## COMMIT MESSAGE

```
fix: Agent path corrections and CROESUS → QUAESTOR rename

RENAMES:
- magistrate/ → solon/
- exchequer/ → quaestor/
- CROESUS → QUAESTOR (Roman tax magistrate)

FIXES:
- Docker-compose paths now match directories
- PLUTUS location resolved

The treasury knows all debts owed to Caesar.
```
