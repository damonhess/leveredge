# LEVEREDGE OPS RUNBOOK

*Last Updated: January 17, 2026 (12:00 PM)*

**Purpose:** How to restart, monitor, and troubleshoot the LeverEdge infrastructure.

---

## SUPABASE ARCHITECTURE (Isolated DEV/PROD)

### Overview
DEV and PROD Supabase run on **completely isolated postgres containers**:

| Environment | Container | Port | Database | Path |
|-------------|-----------|------|----------|------|
| **PROD** | supabase-db-prod | 54322 | postgres | /opt/leveredge/data-plane/prod/supabase/ |
| **DEV** | supabase-db-dev | 54323 | postgres | /opt/leveredge/data-plane/dev/supabase/ |

### Connection Strings
```bash
# PROD
postgresql://postgres:PASSWORD@127.0.0.1:54322/postgres

# DEV
postgresql://postgres:PASSWORD@127.0.0.1:54323/postgres
```

### Services Connected to DEV Postgres (54323)
- aria-threading (systemd service)
- DEV n8n (Supabase Postgres DEV credential)
- DEV Supabase services (supabase-*-dev containers)

### Services Connected to PROD Postgres (54322)
- PROD n8n (Supabase Postgres server credential)
- PROD Supabase services (supabase-* containers)

### Schema Management
```bash
# Compare DEV and PROD schemas
/opt/leveredge/shared/scripts/promote-schema.sh

# Promote specific table from DEV to PROD
/opt/leveredge/shared/scripts/promote-schema.sh aria_new_table
```

### Restart Commands
```bash
# PROD Supabase (all services including postgres)
cd /opt/leveredge/data-plane/prod/supabase && docker compose down && docker compose up -d

# DEV Supabase (all services including postgres)
cd /opt/leveredge/data-plane/dev/supabase && docker compose down && docker compose up -d

# Just restart postgres containers
docker restart supabase-db-prod
docker restart supabase-db-dev
```

### Backup Commands
```bash
# PROD backup
docker exec supabase-db-prod pg_dump -U postgres -d postgres -F c -f /tmp/backup.dump
docker cp supabase-db-prod:/tmp/backup.dump ./prod_backup_$(date +%Y%m%d).dump

# DEV backup
docker exec supabase-db-dev pg_dump -U postgres -d postgres -F c -f /tmp/backup.dump
docker cp supabase-db-dev:/tmp/backup.dump ./dev_backup_$(date +%Y%m%d).dump
```

---

## QUICK REFERENCE - RESTART COMMANDS

### Control Plane Agents (FastAPI/Uvicorn)

| Agent | Port | Restart Command |
|-------|------|-----------------|
| ATLAS | 8007 | `sudo pkill -f "uvicorn atlas:app" && cd /opt/leveredge/control-plane/agents/atlas && sudo nohup /usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007 > /tmp/atlas.log 2>&1 &` |
| HEPHAESTUS | 8011 | `sudo pkill -f "uvicorn.*8011" && cd /opt/leveredge/control-plane/agents/hephaestus && sudo nohup /usr/local/bin/python3.11 -m uvicorn hephaestus_mcp_server:app --host 0.0.0.0 --port 8011 > /tmp/hephaestus.log 2>&1 &` |
| CHRONOS | 8010 | `sudo pkill -f "uvicorn.*8010" && cd /opt/leveredge/control-plane/agents/chronos && sudo nohup /usr/local/bin/python3.11 -m uvicorn chronos:app --host 0.0.0.0 --port 8010 > /tmp/chronos.log 2>&1 &` |
| HADES | 8008 | `sudo pkill -f "uvicorn.*8008" && cd /opt/leveredge/control-plane/agents/hades && sudo nohup /usr/local/bin/python3.11 -m uvicorn hades:app --host 0.0.0.0 --port 8008 > /tmp/hades.log 2>&1 &` |
| AEGIS | 8012 | `sudo pkill -f "uvicorn.*8012" && cd /opt/leveredge/control-plane/agents/aegis && sudo nohup /usr/local/bin/python3.11 -m uvicorn aegis:app --host 0.0.0.0 --port 8012 > /tmp/aegis.log 2>&1 &` |
| ATHENA | 8013 | `sudo pkill -f "uvicorn.*8013" && cd /opt/leveredge/control-plane/agents/athena && sudo nohup /usr/local/bin/python3.11 -m uvicorn athena:app --host 0.0.0.0 --port 8013 > /tmp/athena.log 2>&1 &` |
| HERMES | 8014 | `sudo pkill -f "uvicorn.*8014" && cd /opt/leveredge/control-plane/agents/hermes && sudo nohup /usr/local/bin/python3.11 -m uvicorn hermes:app --host 0.0.0.0 --port 8014 > /tmp/hermes.log 2>&1 &` |
| ALOY | 8015 | `sudo pkill -f "uvicorn.*8015" && cd /opt/leveredge/control-plane/agents/aloy && sudo nohup /usr/local/bin/python3.11 -m uvicorn aloy:app --host 0.0.0.0 --port 8015 > /tmp/aloy.log 2>&1 &` |
| ARGUS | 8016 | `sudo pkill -f "uvicorn.*8016" && cd /opt/leveredge/control-plane/agents/argus && sudo nohup /usr/local/bin/python3.11 -m uvicorn argus:app --host 0.0.0.0 --port 8016 > /tmp/argus.log 2>&1 &` |
| SCHOLAR | 8018 | `sudo pkill -f "uvicorn.*8018" && cd /opt/leveredge/control-plane/agents/scholar && sudo nohup /usr/local/bin/python3.11 -m uvicorn scholar:app --host 0.0.0.0 --port 8018 > /tmp/scholar.log 2>&1 &` |
| CHIRON | 8017 | `sudo pkill -f "uvicorn.*8017" && cd /opt/leveredge/control-plane/agents/chiron && sudo nohup /usr/local/bin/python3.11 -m uvicorn chiron:app --host 0.0.0.0 --port 8017 > /tmp/chiron.log 2>&1 &` |
| SENTINEL | 8019 | `sudo pkill -f "uvicorn.*8019" && cd /opt/leveredge/control-plane/agents/sentinel && sudo nohup /usr/local/bin/python3.11 -m uvicorn sentinel:app --host 0.0.0.0 --port 8019 > /tmp/sentinel.log 2>&1 &` |
| EVENT BUS | 8099 | `sudo pkill -f "uvicorn.*8099" && cd /opt/leveredge/control-plane/event-bus && sudo nohup /usr/local/bin/python3.11 -m uvicorn event_bus:app --host 0.0.0.0 --port 8099 > /tmp/eventbus.log 2>&1 &` |
| GAIA | 8000 | `sudo pkill -f "uvicorn.*8000" && cd /opt/leveredge/gaia && sudo nohup /usr/local/bin/python3.11 -m uvicorn gaia:app --host 0.0.0.0 --port 8000 > /tmp/gaia.log 2>&1 &` |

### Security Fleet

| Agent | Port | Restart Command |
|-------|------|-----------------|
| CERBERUS | 8020 | `sudo pkill -f "uvicorn.*8020" && cd /opt/leveredge/control-plane/agents/cerberus && sudo nohup /usr/local/bin/python3.11 -m uvicorn cerberus:app --host 0.0.0.0 --port 8020 > /tmp/cerberus.log 2>&1 &` |
| PORT-MANAGER | 8021 | `sudo pkill -f "uvicorn.*8021" && cd /opt/leveredge/control-plane/agents/port-manager && sudo nohup /usr/local/bin/python3.11 -m uvicorn port_manager:app --host 0.0.0.0 --port 8021 > /tmp/port-manager.log 2>&1 &` |

### Creative Fleet

| Agent | Port | Restart Command |
|-------|------|-----------------|
| MUSE | 8030 | `sudo pkill -f "uvicorn.*8030" && cd /opt/leveredge/control-plane/agents/muse && sudo nohup /usr/local/bin/python3.11 -m uvicorn muse:app --host 0.0.0.0 --port 8030 > /tmp/muse.log 2>&1 &` |
| CALLIOPE | 8031 | `sudo pkill -f "uvicorn.*8031" && cd /opt/leveredge/control-plane/agents/calliope && sudo nohup /usr/local/bin/python3.11 -m uvicorn calliope:app --host 0.0.0.0 --port 8031 > /tmp/calliope.log 2>&1 &` |
| THALIA | 8032 | `sudo pkill -f "uvicorn.*8032" && cd /opt/leveredge/control-plane/agents/thalia && sudo nohup /usr/local/bin/python3.11 -m uvicorn thalia:app --host 0.0.0.0 --port 8032 > /tmp/thalia.log 2>&1 &` |
| ERATO | 8033 | `sudo pkill -f "uvicorn.*8033" && cd /opt/leveredge/control-plane/agents/erato && sudo nohup /usr/local/bin/python3.11 -m uvicorn erato:app --host 0.0.0.0 --port 8033 > /tmp/erato.log 2>&1 &` |
| CLIO | 8034 | `sudo pkill -f "uvicorn.*8034" && cd /opt/leveredge/control-plane/agents/clio && sudo nohup /usr/local/bin/python3.11 -m uvicorn clio:app --host 0.0.0.0 --port 8034 > /tmp/clio.log 2>&1 &` |

### Personal Fleet

| Agent | Port | Restart Command |
|-------|------|-----------------|
| GYM-COACH | 8110 | `sudo pkill -f "uvicorn.*8110" && cd /opt/leveredge/control-plane/agents/gym-coach && sudo nohup /usr/local/bin/python3.11 -m uvicorn gym_coach:app --host 0.0.0.0 --port 8110 > /tmp/gym-coach.log 2>&1 &` |
| NUTRITIONIST | 8101 | `sudo pkill -f "uvicorn.*8101" && cd /opt/leveredge/control-plane/agents/nutritionist && sudo nohup /usr/local/bin/python3.11 -m uvicorn nutritionist:app --host 0.0.0.0 --port 8101 > /tmp/nutritionist.log 2>&1 &` |
| MEAL-PLANNER | 8102 | `sudo pkill -f "uvicorn.*8102" && cd /opt/leveredge/control-plane/agents/meal-planner && sudo nohup /usr/local/bin/python3.11 -m uvicorn meal_planner:app --host 0.0.0.0 --port 8102 > /tmp/meal-planner.log 2>&1 &` |
| ACADEMIC-GUIDE | 8103 | `sudo pkill -f "uvicorn.*8103" && cd /opt/leveredge/control-plane/agents/academic-guide && sudo nohup /usr/local/bin/python3.11 -m uvicorn academic_guide:app --host 0.0.0.0 --port 8103 > /tmp/academic-guide.log 2>&1 &` |
| EROS | 8104 | `sudo pkill -f "uvicorn.*8104" && cd /opt/leveredge/control-plane/agents/eros && sudo nohup /usr/local/bin/python3.11 -m uvicorn eros:app --host 0.0.0.0 --port 8104 > /tmp/eros.log 2>&1 &` |

### Business Fleet

| Agent | Port | Restart Command |
|-------|------|-----------------|
| HERACLES | 8200 | `sudo pkill -f "uvicorn.*8200" && cd /opt/leveredge/control-plane/agents/heracles && sudo nohup /usr/local/bin/python3.11 -m uvicorn heracles:app --host 0.0.0.0 --port 8200 > /tmp/heracles.log 2>&1 &` |
| LIBRARIAN | 8201 | `sudo pkill -f "uvicorn.*8201" && cd /opt/leveredge/control-plane/agents/librarian && sudo nohup /usr/local/bin/python3.11 -m uvicorn librarian:app --host 0.0.0.0 --port 8201 > /tmp/librarian.log 2>&1 &` |
| DAEDALUS | 8202 | `sudo pkill -f "uvicorn.*8202" && cd /opt/leveredge/control-plane/agents/daedalus && sudo nohup /usr/local/bin/python3.11 -m uvicorn daedalus:app --host 0.0.0.0 --port 8202 > /tmp/daedalus.log 2>&1 &` |
| THEMIS | 8203 | `sudo pkill -f "uvicorn.*8203" && cd /opt/leveredge/control-plane/agents/themis && sudo nohup /usr/local/bin/python3.11 -m uvicorn themis:app --host 0.0.0.0 --port 8203 > /tmp/themis.log 2>&1 &` |
| MENTOR | 8204 | `sudo pkill -f "uvicorn.*8204" && cd /opt/leveredge/control-plane/agents/mentor && sudo nohup /usr/local/bin/python3.11 -m uvicorn mentor:app --host 0.0.0.0 --port 8204 > /tmp/mentor.log 2>&1 &` |
| PLUTUS | 8205 | `sudo pkill -f "uvicorn.*8205" && cd /opt/leveredge/control-plane/agents/plutus && sudo nohup /usr/local/bin/python3.11 -m uvicorn plutus:app --host 0.0.0.0 --port 8205 > /tmp/plutus.log 2>&1 &` |
| PROCUREMENT | 8206 | `sudo pkill -f "uvicorn.*8206" && cd /opt/leveredge/control-plane/agents/procurement && sudo nohup /usr/local/bin/python3.11 -m uvicorn procurement:app --host 0.0.0.0 --port 8206 > /tmp/procurement.log 2>&1 &` |
| HEPHAESTUS-SERVER | 8207 | `sudo pkill -f "uvicorn.*8207" && cd /opt/leveredge/control-plane/agents/hephaestus-server && sudo nohup /usr/local/bin/python3.11 -m uvicorn hephaestus_server:app --host 0.0.0.0 --port 8207 > /tmp/hephaestus-server.log 2>&1 &` |
| ATLAS-INFRA | 8208 | `sudo pkill -f "uvicorn.*8208" && cd /opt/leveredge/control-plane/agents/atlas-infra && sudo nohup /usr/local/bin/python3.11 -m uvicorn atlas_infra:app --host 0.0.0.0 --port 8208 > /tmp/atlas-infra.log 2>&1 &` |
| IRIS | 8209 | `sudo pkill -f "uvicorn.*8209" && cd /opt/leveredge/control-plane/agents/iris && sudo nohup /usr/local/bin/python3.11 -m uvicorn iris:app --host 0.0.0.0 --port 8209 > /tmp/iris.log 2>&1 &` |

### Data Plane (Docker Compose)

| Service | Restart Command |
|---------|-----------------|
| Control n8n | `cd /opt/leveredge/control-plane/n8n && docker compose restart` |
| PROD n8n | `cd /opt/leveredge/data-plane/prod/n8n && docker compose restart` |
| DEV n8n | `cd /opt/leveredge/data-plane/dev/n8n && docker compose restart` |
| PROD Supabase | `cd /opt/leveredge/data-plane/prod/supabase && docker compose restart` |
| DEV Supabase | `cd /opt/leveredge/data-plane/dev/supabase && docker compose restart` |

---

## CHECK IF AGENT IS RUNNING

### Quick check all agents:
```bash
ps aux | grep uvicorn | grep -v grep
```

### Check specific agent:
```bash
ps aux | grep "uvicorn.*8007" | grep -v grep  # ATLAS
ps aux | grep "uvicorn.*8011" | grep -v grep  # HEPHAESTUS
# etc.
```

### Check Docker services:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Health check endpoints:
```bash
curl -s http://localhost:8007/health  # ATLAS
curl -s http://localhost:8011/health  # HEPHAESTUS
curl -s http://localhost:8099/health  # Event Bus
# etc.
```

---

## VIEW LOGS

### Uvicorn agents (if using nohup):
```bash
tail -f /tmp/atlas.log
tail -f /tmp/hephaestus.log
# etc.
```

### Docker services:
```bash
cd /opt/leveredge/control-plane/n8n && docker compose logs -f
cd /opt/leveredge/data-plane/prod/n8n && docker compose logs -f
```

---

## COMMON ISSUES & FIXES

### Agent won't start
1. Check if port is in use: `sudo lsof -i :8007`
2. Kill existing process: `sudo pkill -f "uvicorn.*8007"`
3. Check Python path: `which python3.11`
4. Check dependencies: `pip3.11 list | grep fastapi`

### Agent starts but immediately dies
1. Check logs: `tail -50 /tmp/atlas.log`
2. Run manually to see errors:
   ```bash
   cd /opt/leveredge/control-plane/agents/atlas
   /usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007
   ```

### Docker container won't start
1. Check logs: `docker compose logs`
2. Check disk space: `df -h`
3. Rebuild: `docker compose build --no-cache && docker compose up -d`

### n8n workflow not responding
1. Check n8n UI for errors
2. Check webhook is active (green indicator)
3. Check Event Bus for recent events

---

## FULL SYSTEM RESTART

If everything is broken, run in order:

```bash
# 1. Event Bus first (all agents depend on it)
cd /opt/leveredge/control-plane/event-bus
sudo nohup /usr/local/bin/python3.11 -m uvicorn event_bus:app --host 0.0.0.0 --port 8099 > /tmp/eventbus.log 2>&1 &
sleep 2

# 2. Core agents
cd /opt/leveredge/control-plane/agents/atlas
sudo nohup /usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007 > /tmp/atlas.log 2>&1 &

cd /opt/leveredge/control-plane/agents/hephaestus
sudo nohup /usr/local/bin/python3.11 -m uvicorn hephaestus_mcp_server:app --host 0.0.0.0 --port 8011 > /tmp/hephaestus.log 2>&1 &

# 3. Docker services
cd /opt/leveredge/control-plane/n8n && docker compose up -d
cd /opt/leveredge/data-plane/prod/n8n && docker compose up -d
cd /opt/leveredge/data-plane/prod/supabase && docker compose up -d

# 4. Supporting agents (as needed)
# ... repeat pattern for other agents
```

---

## AGENT PORT MAP

### Core Infrastructure (8000-8099)
| Port | Agent | Type | Description |
|------|-------|------|-------------|
| 8000 | GAIA | FastAPI | Emergency rebuild |
| 8007 | ATLAS | FastAPI | Orchestration engine |
| 8008 | HADES | FastAPI | Rollback/recovery |
| 8010 | CHRONOS | FastAPI | Backup management |
| 8011 | HEPHAESTUS | FastAPI (MCP) | File ops/commands |
| 8012 | AEGIS | FastAPI | Credential vault |
| 8013 | ATHENA | FastAPI | Documentation |
| 8014 | HERMES | FastAPI | Notifications |
| 8015 | ALOY | FastAPI | Audit/anomalies |
| 8016 | ARGUS | FastAPI | Monitoring |
| 8017 | CHIRON | FastAPI | Business mentor (LLM) |
| 8018 | SCHOLAR | FastAPI | Market research (LLM) |
| 8019 | SENTINEL | FastAPI | Smart router |
| 8099 | Event Bus | FastAPI | Event publishing |

### Security Fleet (8020-8021)
| Port | Agent | Type | Description |
|------|-------|------|-------------|
| 8020 | CERBERUS | FastAPI | Security gateway |
| 8021 | PORT-MANAGER | FastAPI | Port allocation |

### Creative Fleet (8030-8034)
| Port | Agent | Type | Description |
|------|-------|------|-------------|
| 8030 | MUSE | FastAPI | Creative director |
| 8031 | CALLIOPE | FastAPI | Writer (LLM) |
| 8032 | THALIA | FastAPI | Designer |
| 8033 | ERATO | FastAPI | Media producer |
| 8034 | CLIO | FastAPI | Reviewer (LLM) |

### Personal Fleet (8100-8110)
| Port | Agent | Type | Description |
|------|-------|------|-------------|
| 8110 | GYM-COACH | FastAPI | Fitness (LLM) - **Note: 8110 not 8100** |
| 8101 | NUTRITIONIST | FastAPI | Nutrition (LLM) |
| 8102 | MEAL-PLANNER | FastAPI | Meals (LLM) |
| 8103 | ACADEMIC-GUIDE | FastAPI | Learning (LLM) |
| 8104 | EROS | FastAPI | Relationships (LLM) |

### Business Fleet (8200-8209)
| Port | Agent | Type | Description |
|------|-------|------|-------------|
| 8200 | HERACLES | FastAPI | Project manager (LLM) |
| 8201 | LIBRARIAN | FastAPI | Knowledge manager (LLM) |
| 8202 | DAEDALUS | FastAPI | Workflow builder (LLM) |
| 8203 | THEMIS | FastAPI | Legal advisor (LLM) |
| 8204 | MENTOR | FastAPI | Business coach (LLM) |
| 8205 | PLUTUS | FastAPI | Financial analyst (LLM) |
| 8206 | PROCUREMENT | FastAPI | Procurement expert (LLM) |
| 8207 | HEPHAESTUS-SERVER | FastAPI | Server admin (LLM) |
| 8208 | ATLAS-INFRA | FastAPI | Infrastructure advisor (LLM) |
| 8209 | IRIS | FastAPI | World events (LLM) |

### n8n Instances
| Port | Service | Type |
|------|---------|------|
| 5678 | PROD n8n | Docker |
| 5679 | Control n8n | Docker |
| 5680 | DEV n8n | Docker |

---

## TODO: SYSTEMD SERVICES

These agents should be converted to systemd services for:
- Auto-restart on crash
- Auto-start on boot
- Proper logging via journald
- Better process management

Example service file (`/etc/systemd/system/atlas.service`):
```ini
[Unit]
Description=ATLAS Orchestration Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/leveredge/control-plane/agents/atlas
ExecStart=/usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then: `sudo systemctl enable atlas && sudo systemctl start atlas`

---

## MAINTENANCE WINDOWS

- **Backups:** CHRONOS runs daily at 2 AM UTC
- **Log rotation:** Weekly (TODO: implement)
- **Database vacuum:** Monthly (TODO: implement)

---

*When in doubt, check the logs first.*
