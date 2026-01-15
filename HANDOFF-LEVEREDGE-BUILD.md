# HANDOFF: LEVEREDGE MULTI-AGENT ARCHITECTURE BUILD

*Handoff Created: January 16, 2026, ~8:30 AM PST*
*From: Claude Desktop (Launch Coach)*
*To: Claude Code (Builder)*

---

## IMMEDIATE CONTEXT

Damon is building a sophisticated multi-agent system for his AI automation agency. We just completed architecture planning and created the Phase 0 build spec. He's ready to execute.

**His current state:**
- Just created `/opt/leveredge/` directory (empty)
- Just created VS Code workspace: `/home/damon/leveredge-control.code-workspace`
- Ready to execute Phase 0 build
- Wants to move fast — context is getting long

---

## WHAT NEEDS TO HAPPEN RIGHT NOW

### Step 1: Create the Phase 0 Spec on Server

The spec file needs to be created at `/opt/leveredge/PHASE-0-GAIA-EVENT-BUS-SPEC.md`

**The full spec is attached as a separate file in this handoff.**

### Step 2: Execute Phase 0 Build

Run these commands in order:

```bash
# 1. Create Base Directory Structure
sudo mkdir -p /opt/leveredge/{gaia,control-plane,data-plane,shared,monitoring}
sudo mkdir -p /opt/leveredge/control-plane/{n8n,agents,workflows,dashboards,docs,event-bus}
sudo mkdir -p /opt/leveredge/data-plane/{prod,dev}
sudo mkdir -p /opt/leveredge/shared/{scripts,templates,backups,credentials}
sudo mkdir -p /opt/leveredge/shared/backups/{control-plane,prod,dev}/{hourly,daily,weekly,monthly}
sudo mkdir -p /opt/leveredge/monitoring/{prometheus,grafana}
sudo chown -R damon:damon /opt/leveredge
chmod 755 /opt/leveredge

# 2. Create GAIA files (see spec for full content)
# 3. Create Event Bus files (see spec for full content)
# 4. Set up systemd services
# 5. Verify everything works
```

### Step 3: Verify

```bash
ls -la /opt/leveredge/
ls -la /opt/leveredge/gaia/
/opt/leveredge/gaia/restore.sh list
curl http://localhost:8099/health
systemctl --user status event-bus
```

---

## THE ARCHITECTURE (APPROVED BY DAMON)

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   GAIA (Port 8000) - OUTSIDE EVERYTHING - Can rebuild entire system                     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               CONTROL PLANE                                              │
│                       control.n8n.leveredgeai.com                                       │
│                                                                                          │
│   n8n Instance (PostgreSQL) + FastAPI Agents + Event Bus + Web UIs                      │
│                                                                                          │
│   Agents: ATLAS, HEPHAESTUS, ATHENA, AEGIS, CHRONOS, HADES, HERMES, ARGUS, ALOY        │
│                                                                                          │
│   Every agent has:                                                                       │
│   - n8n Workflow (visual, debuggable)                                                   │
│   - FastAPI Backend (execution engine)                                                  │
│   - Grafana Monitoring                                                                  │
│                                                                                          │
│   All interactions logged to EVENT BUS                                                  │
│   Agents communicate via Event Bus subscriptions                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                     DATA PLANE                                           │
│                                                                                          │
│   PRODUCTION                              DEVELOPMENT                                   │
│   n8n.leveredgeai.com                     dev.n8n.leveredgeai.com                       │
│   aria.leveredgeai.com                    dev.aria.leveredgeai.com                      │
│   studio.leveredgeai.com                  dev.studio.leveredgeai.com                    │
│   api.leveredgeai.com                     dev.api.leveredgeai.com                       │
│                                                                                          │
│   IDENTICAL STRUCTURE - Only credentials differ                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Folder Structure

```
/opt/leveredge/
├── gaia/                           # Tier 0 - Emergency restore
│   ├── gaia.py
│   ├── restore.sh
│   ├── emergency-telegram.py
│   └── config.yaml
│
├── control-plane/
│   ├── n8n/                        # Control plane n8n instance
│   ├── agents/                     # FastAPI backends
│   │   ├── atlas/
│   │   ├── hephaestus/
│   │   ├── athena/
│   │   ├── aegis/
│   │   ├── chronos/
│   │   ├── hades/
│   │   ├── hermes/
│   │   ├── argus/
│   │   └── aloy/
│   ├── workflows/                  # n8n workflow exports (git-tracked)
│   ├── dashboards/                 # Web UIs
│   ├── event-bus/                  # Event Bus API + SQLite
│   └── docs/
│
├── data-plane/
│   ├── prod/                       # Production environment
│   └── dev/                        # Development environment (mirror of prod)
│
├── shared/
│   ├── scripts/                    # CLI tools
│   ├── templates/
│   ├── backups/
│   └── credentials/
│
└── monitoring/
    ├── prometheus/
    └── grafana/
```

### Complete Agent Registry

#### Tier 0: Genesis
| Agent | Port | Purpose |
|-------|------|---------|
| GAIA | 8000 | Bootstrap/rebuild everything from nothing |

#### Tier 1: Control Plane
| Agent | Port | Purpose |
|-------|------|---------|
| ATLAS | 8007 | Master Orchestrator - routes all requests |
| HEPHAESTUS | 8011 | Builder - creates workflows, deploys containers |
| ATHENA | 8013 | Planner/Documenter - specs, architecture docs |
| AEGIS | 8012 | Credential Vault - audits, stores, applies credentials |
| CHRONOS | 8010 | Backup Manager - scheduled backups, retention |
| HADES | 8008 | Rollback/Destruction - recovery, nuclear option |
| HERMES | 8014 | Messenger - notifications, alerts |
| ARGUS | 8009 | Monitoring - health checks, anomaly detection |
| ALOY | 8015 | Auditor/Bug Hunter - post-deployment audits |

#### Tier 2: Data Plane
| Agent | Location | Purpose |
|-------|----------|---------|
| ARIA | prod + dev | Personal Assistant / Human Liaison |
| VARYS | prod + dev | Project Manager (future) |

#### Tier 3: Business Domain (Post-Launch)
| Agent | Purpose |
|-------|---------|
| SCHOLAR | Deep research, analysis |
| ORACLE | Geopolitical analysis |
| LIBRARIAN | Knowledge management, RAG |
| SCRIBE | Content creation |
| MERCHANT | Sales/outreach |

#### Tier 4: Personal Domain (Future)
| Agent | Purpose |
|-------|---------|
| APOLLO | Health/Fitness |
| DEMETER | Nutrition |
| MENTOR | Academic |
| EROS | Dating |

### Key Architecture Decisions

1. **Agents are a TEAM** - They communicate via Event Bus, not isolated tools

2. **AEGIS is ACTIVE** - When HEPHAESTUS builds, AEGIS applies credentials (HEPHAESTUS never sees values)

3. **ARIA is Human Liaison** - Informed of all events, relays human input requests, but doesn't build things

4. **ALOY hunts bugs** - Runs post-deployment audits after every change

5. **Every interaction logged** - Control plane watched like a hawk

6. **Multiple interaction channels:**
   - control.n8n.leveredgeai.com (primary)
   - Telegram bots (@LeveredgeControlBot, @GaiaEmergencyBot)
   - Web UIs (aegis, chronos, hades, aloy)
   - CLI (fallback)
   - MCP (programmatic)

7. **Native n8n nodes preferred** - Code nodes only when necessary

8. **Dev/Prod identical** - Same structure, different credentials

### Event Bus

All agents publish events. Relevant agents subscribe and react.

Example flow: HEPHAESTUS builds → CHRONOS backs up first → AEGIS applies creds → ALOY audits after → ATHENA documents → ARIA is informed → HERMES notifies

Human input requests have timeout + fallback. ARIA reminds Damon until resolved.

---

## CURRENT SERVER STATE

### What Already Exists

Located at `/home/damon/` (OLD structure - will be migrated):

- **n8n prod**: n8n.leveredgeai.com (working)
- **n8n dev**: dev.n8n.leveredgeai.com (working)
- **Supabase prod**: studio.leveredgeai.com (working)
- **Supabase dev**: dev.studio.leveredgeai.com (working)
- **ARIA prod**: aria.leveredgeai.com (working, V3.1)
- **ARIA dev**: dev-aria.leveredgeai.com (working)
- **Grafana**: grafana.leveredgeai.com (working)

### FastAPI Agents (Currently at /home/damon/)

These exist but are "invisible" - CLI only, no n8n integration yet:

- ATLAS: 8007 (working but limited)
- HADES: 8008 (working)
- HEIMDALL: 8009 (working) → becomes ARGUS
- CHRONOS: 8010 (working)
- AEGIS: 8012 (working, just built yesterday)

### What Needs Migration

After Phase 0, these will be migrated to `/opt/leveredge/data-plane/`:
- All docker-compose files
- All n8n instances
- All Supabase instances
- All agent code

---

## DAMON'S CONTEXT

### Who He Is
- Civil engineer with law degree
- Works in government water rights enforcement
- Has ADHD - needs structure + encouragement
- Building AI automation agency
- Launch date: March 1, 2026
- Revenue goal: $30K/month to leave job

### What He Values
- **Visibility** - Hates invisible systems, wants to SEE everything working
- **Control** - Doesn't want to be "at Claude's mercy"
- **Native nodes** - Prefers n8n native over Code nodes
- **Production quality** - Builds real systems, not tutorials
- **Speed** - Context is getting long, wants to move fast

### His Current State
- Just completed major architecture planning session
- Excited about the vision
- Ready to build
- Needs to hand off because context is long

---

## BUILD PHASES

### Phase 0: GAIA + Event Bus (NOW)
- GAIA bootstrap scripts
- Event Bus (SQLite + FastAPI)
- Directory structure
- Emergency Telegram bot

### Phase 1: Control Plane n8n + ATLAS
- Deploy control.n8n.leveredgeai.com
- ATLAS workflow (orchestrator)
- Cloudflare Access setup

### Phase 2: HEPHAESTUS + AEGIS
- Builder workflow
- Active credential management
- AEGIS web UI

### Phase 3: CHRONOS + HADES
- Backup management + web UI
- Rollback system + web UI

### Phase 4: ARGUS + ALOY + HERMES + ATHENA
- Monitoring integration
- Auditor/bug hunter
- Notifications
- Documentation

### Phase 5: Data Plane Sync
- Migrate prod to new structure
- Mirror to dev
- Integration testing

---

## FILES TO CREATE

The Phase 0 spec contains all file contents for:

1. `/opt/leveredge/gaia/gaia.py` - Main GAIA script
2. `/opt/leveredge/gaia/restore.sh` - Shell wrapper
3. `/opt/leveredge/gaia/emergency-telegram.py` - Standalone bot
4. `/opt/leveredge/gaia/config.yaml` - Configuration
5. `/opt/leveredge/control-plane/event-bus/event_bus.py` - FastAPI
6. `/opt/leveredge/control-plane/event-bus/event-bus-schema.sql` - SQLite schema
7. Systemd service files for event-bus and gaia-emergency

---

## IMPORTANT NOTES

1. **Read EXECUTION_RULES.md** at `/home/damon/.claude/EXECUTION_RULES.md` before running bash commands

2. **Use ATLAS for privileged operations** when it's operational

3. **Never update n8n workflows via direct SQL** - Use n8n API

4. **Dev-first workflow** - All changes go to dev first, test, then promote

5. **The old agents at /home/damon/** still work - don't break them during migration

---

## VERIFICATION CHECKLIST

After Phase 0 build, verify:

- [ ] `/opt/leveredge/` directory structure complete
- [ ] GAIA scripts executable
- [ ] `gaia restore.sh list` works (will show empty but no errors)
- [ ] Event Bus running on port 8099
- [ ] `curl http://localhost:8099/health` returns healthy
- [ ] Event Bus can receive events
- [ ] Systemd services enabled

---

## CONTACT

If questions arise that require human input:
- Damon is available via this Claude session
- He prefers direct action over extensive explanations
- He's technical - don't over-explain basics
- He values speed and results

---

## GO BUILD IT

Start with creating the Phase 0 spec file, then execute the build commands.

The user is waiting. Move fast.
