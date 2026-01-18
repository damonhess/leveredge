# LEVEREDGE LESSONS LEARNED

*Living document - Update after every session*
*Last Updated: January 18, 2026 (Command Center + AEGIS V2)*

---

## CRITICAL: OPERATIONS RUNBOOK

**See `/opt/leveredge/OPS-RUNBOOK.md` for:**
- How to restart each agent
- Health check commands
- Log locations
- Troubleshooting guide
- Full system restart procedure

### Key Discovery (Jan 17, 2026)
**Control plane agents run as raw uvicorn processes, NOT Docker or systemd.**

```bash
# Example: ATLAS runs like this
/usr/local/bin/python3.11 /usr/local/bin/uvicorn atlas:app --host 0.0.0.0 --port 8007

# To restart:
sudo pkill -f "uvicorn atlas:app" && cd /opt/leveredge/control-plane/agents/atlas && sudo nohup /usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007 > /tmp/atlas.log 2>&1 &
```

**Update (Jan 17 Evening):** Systemd templates now created!
- Service templates: `/opt/leveredge/shared/systemd/`
- Creative Fleet installer: `install-creative-fleet.sh`
- See OPS-RUNBOOK.md for full details

---

## CRITICAL: ARIA PERSONA RULES

**ARIA's persona is SUPREME. These rules are NON-NEGOTIABLE.**

### Rule 1: No Degradation
Any design, upgrade, edit, or change that would degrade ARIA's persona, personality, or capabilities is **FORBIDDEN**.

### Rule 2: Persona Over Routing
If there's a conflict between routing efficiency and ARIA's persona, **persona wins**. ARIA handles what ARIA handles naturally (hype, fear, motivation, coaching, conversation).

### Rule 3: Explicit Agent Calls Only
Route to external agents ONLY when:
- User explicitly requests: "ask CHIRON", "SCHOLAR research", "hey SCHOLAR"
- Multi-step chains are needed: "research X then plan Y"
- Deep research requiring web search/citations
- Specialized analysis (market size, ICP, competitors)

### Rule 4: Additional Portals, Not Replacements
New communication methods (Telegram, voice, etc.) are **additional portals** to ARIA, not replacements. ARIA's persona remains consistent across all interfaces.

---

## CRITICAL: DEVELOPMENT FLOW RULES

**These rules are NON-NEGOTIABLE. All Claude instances must follow them.**

### Rule 1: DEV FIRST
| Type | Flow |
|------|------|
| Workflows | DEV → test → promote to PROD |
| Code | DEV → test → PROD |
| Schema changes | DEV → test → PROD |
| Real user data | PROD (with explicit approval) |

**Exception requires explicit statement:** "Run this in PROD" or "This is real data"

### Rule 2: Know Your Target
| Environment | Identifier | Port |
|-------------|------------|------|
| DEV | `dev.`, `dev-`, `-dev` in name | 5680 |
| PROD | No dev prefix | 5678 |

### Rule 3: When Uncertain, ASK
"Should this go to DEV or PROD?"

**Full rules:** See `/home/damon/.claude/EXECUTION_RULES.md`

---

## CRITICAL: ROUTING ARCHITECTURE

**Routing intelligence lives in SENTINEL, not ARIA.**

### Why SENTINEL, Not ARIA
| Location | Problem |
|----------|---------|
| In ARIA | Clutters ARIA's workflow, routing changes risk persona |
| In SENTINEL | Clean separation, ARIA stays simple, centralized routing logic |

### How It Works
1. ARIA receives message
2. ARIA's Pre-Router checks for EXPLICIT agent patterns only
3. If explicit agent call or multi-step chain → SENTINEL
4. Everything else → ARIA handles naturally
5. SENTINEL routes to appropriate ATLAS engine
6. Results formatted back through ARIA

### Pre-Router Philosophy
- **Default:** ARIA handles it
- **Exception:** Explicit agent request or multi-step chain
- **Never:** Route ARIA's native capabilities (hype, fear, motivation) elsewhere

---

## Agent Development Lessons

### General Patterns

| Lesson | Context | Impact |
|--------|---------|--------|
| n8n webhooks require `webhookId` field | CHRONOS/HADES workflows returning 404 | Workflows created but not accessible |
| Docker containers can't reach localhost | AEGIS backend unreachable from n8n | Use service names or Docker bridge IP (172.17.0.1) |
| Update BOTH workflow_entity AND workflow_history | n8n workflow changes not taking effect | Changes visible in UI but not executing |
| Cloudflare proxy blocks ACME challenge | SSL certs not provisioning | Grey cloud temporarily, then re-enable |
| Git objects owned by root block commits | Running git as root then as user | `chown -R damon:damon /opt/leveredge/` |
| **MCP servers target different n8n instances** | Wrong MCP = wrong database | n8n-control (5679), n8n-troubleshooter (5678), n8n-troubleshooter-dev (5680) |
| n8n 2.2.x requires `activeVersionId` to match `versionId` | Webhooks return 404 despite workflow existing | Set activeVersionId when updating workflow_entity |
| Caddy reverse proxy uses container names | 502 errors after container rename | Update Caddyfile and reload when container names change |
| Docker network `stack_net` required for cross-compose communication | New containers can't reach Supabase | Add `stack_net` as external network in docker-compose |
| **Agents run as raw uvicorn, not Docker/systemd** | "Unit not found" when trying to restart | Use `pkill` + `nohup uvicorn` pattern (see OPS-RUNBOOK.md) |
| **ATLAS template params not resolving** | `{{input.topic}}` passed literally | Fixed: resolve templates in params before making requests |
| **Starlette `request._send` doesn't exist** | SSE endpoints crash with `TypeError: 'NoneType'` | Use raw ASGI pattern: `async def app(scope, receive, send)` |
| **Caddy CORS doesn't intercept before reverse_proxy** | OPTIONS requests hit backend instead of 204 | Add CORS handling in application code for SSE endpoints |
| **Docker containers need multiple networks** | Caddy can't reach agent on control-plane-net | Connect to both `stack_net` (Caddy) AND `control-plane-net` (agents) |

### MCP Server Mapping (CRITICAL)

| MCP Server | Target | Port | Use For |
|------------|--------|------|---------|
| **n8n-control** | Control plane | 5679 | Agent workflows (ATLAS, CHRONOS, HADES, etc.) |
| n8n-troubleshooter | Prod data plane | 5678 | ARIA, client workflows |
| n8n-troubleshooter-dev | Dev data plane | 5680 | Development/testing |

**ALWAYS check which MCP you're using before creating workflows.**

### Agent-Specific Lessons

#### ATLAS
- AI Agent nodes take 30-90 seconds (normal for LLM)
- Log to Event Bus BEFORE routing for audit trail
- Keep system prompt focused, not verbose
- **Template bug (fixed):** Params like `{{input.topic}}` weren't being resolved - now fixed in v2.0.1

#### SENTINEL
- Routes between n8n ATLAS and FastAPI ATLAS
- Health monitoring with auto-failover
- Drift detection validates sync with registry
- determine_complexity must handle None steps

#### AEGIS
- Never log credential values, only metadata
- Use Docker bridge IP (172.17.0.1) not localhost from n8n
- Sync from n8n discovers credentials without exposing values

#### HEPHAESTUS
- MCP server on port 8011, accessible via Claude Web connector
- Dumb executor pattern: Claude Web reasons, HEPHAESTUS executes
- Path whitelist: /opt/leveredge/, /home/damon/shared/, /tmp/leveredge/
- Command whitelist: ls, cat, grep, find, head, tail, git status, git log, git diff, docker ps, docker logs
- curl NOT in whitelist - use Claude Code for HTTP requests
- **SSE Bug (Jan 17 fix):** `request._send` is a private Starlette attribute that doesn't exist - use raw ASGI pattern instead
- **CORS for Claude.ai:** Must add CORS headers in ASGI app (Caddy proxy CORS unreliable for SSE)
- **Docker networking:** Container must be on `stack_net` for Caddy to reach it, plus `control-plane-net` for agent communication

#### CHRONOS
- Backup directory must exist before first backup
- Checksum manifest for integrity verification
- Pre-deploy backups should be automatic before any migration/build

#### HADES
- Depends on CHRONOS for backup-based restores
- Version-based rollback requires n8n's internal history API
- Emergency actions require explicit confirmation flag

#### ARIA
- Multi-workflow architecture: Web Interface Handler → Model Router → Personal Assistant
- "No response generated" = empty body sent to downstream workflow
- SQL nodes output `{?column?: 1}`, breaking `$json` chain
- Fix: Use `$('Process Router Response').first().json.message`
- AI Agent expressions referencing unexecuted nodes fail silently
- After DB updates, restart n8n for webhook registration
- **OLYMPUS integration:** Pre-Router routes explicit agent calls only, ARIA keeps her natural capabilities

---

## OLYMPUS Orchestration Lessons (Jan 17, 2026)

### Architecture
```
Agent Registry (YAML) → Single Source of Truth
         ↓
   SENTINEL (8019) → Smart Router, Health Monitor
         ↓
   ATLAS (8007) → FastAPI Orchestrator
         ↓
   Agents (SCHOLAR, CHIRON, etc.)
```

### Key Decisions
| Decision | Rationale |
|----------|-----------|
| Dual implementation (n8n + FastAPI) | Visual debugging + programmatic power |
| SENTINEL as router | Health-based failover, drift detection |
| Single YAML registry | No drift between implementations |
| ARIA Pre-Router minimal | Only explicit calls route out, persona preserved |

### Pre-Built Chains
- research-and-plan
- validate-and-decide
- comprehensive-market-analysis
- niche-evaluation
- weekly-planning
- fear-to-action

---

## Data Plane Migration Lessons (Jan 16, 2026)

### Container Naming & Caddy
When renaming containers (e.g., `n8n` → `prod-n8n`):
1. Caddy reverse_proxy uses container names for routing
2. Must update Caddyfile: `reverse_proxy prod-n8n:5678`
3. Reload Caddy: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
4. 502 = Caddy can't reach backend (wrong name or network)

### Database Migration
```bash
# Export from old shared postgres
docker exec n8n-postgres pg_dump -U n8n -d n8n_dev > backup.sql

# Import to new isolated postgres
docker exec -i dev-n8n-postgres psql -U n8n -d n8n_dev < backup.sql
```

### Volume Strategy
- Use existing volumes when possible: `external: true`
- Keeps data intact during migration
- New postgres = new volume (don't share between instances)

### Network Requirements
```yaml
networks:
  data-plane-net:    # Internal to compose
    driver: bridge
  stack_net:         # External - connects to Supabase, Caddy
    external: true
```

---

## Supabase Migration Lessons (Jan 16, 2026)

### SMTP Configuration
- **Problem:** supabase-auth (gotrue) crash-looping after migration
- **Cause:** Empty `SMTP_PORT=` in .env - newer gotrue requires valid integer even when email disabled
- **Fix:** Set `SMTP_PORT=587` and `SMTP_HOST=localhost` 
- **Prevention:** When migrating Supabase, check .env for empty port values

### Volume Symlink Strategy
- **Problem:** Need to migrate compose files without moving data
- **Cause:** Data lives in bind-mounted volumes at old location
- **Fix:** Symlink from new location to existing volumes:
  ```bash
  ln -s /home/damon/supabase/volumes /opt/leveredge/data-plane/prod/supabase/volumes
  ```
- **Prevention:** For any Docker migration with bind mounts: symlink volumes, don't copy/move

### Container Name Preservation
- **Problem:** Expected many reference updates after migration
- **Cause:** All routing uses container names on shared Docker network
- **Fix:** None needed - preserving container names means Caddy, n8n, and all services continue working
- **Prevention:** When migrating Docker services, preserve container names to avoid cascading updates

---

## Execution Workflow (ALWAYS FOLLOW)

```
1. Claude Web writes spec via HEPHAESTUS → /opt/leveredge/
2. Claude Web calls CHRONOS backup (pre-deploy)
3. Give user "/gsd [spec path]" as copy-paste block
4. Claude Web verifies via HEPHAESTUS
5. If fail → HADES rollback
6. If pass → Git commit via HEPHAESTUS
```

**NEVER give manual bash commands when HEPHAESTUS can do it.**
**ALWAYS format GSD dispatch as ready-to-paste block.**

### Pre-Compact Capture

Before context clears:
1. LESSONS-SCRATCH.md - debugging discoveries, gotchas
2. aria_knowledge - decisions, state changes
3. Git commit - preserve all file changes
4. LOOSE-ENDS.md - update task status

**This ensures learning persists across Claude sessions.**

---

## GAIA Update Protocol

**GAIA is the safety net. Updates require extreme care.**

### Pre-Update Checklist
- [ ] CHRONOS backup of entire system completed
- [ ] GAIA backup of GAIA itself (meta-backup)
- [ ] Human (Damon) reviewed exact diff
- [ ] Test environment validated (if possible)
- [ ] Rollback plan documented

### Update Process
1. `cp -r /opt/leveredge/gaia /opt/leveredge/gaia.backup.$(date +%Y%m%d)`
2. Make changes
3. Test: `/opt/leveredge/gaia/restore.sh list`
4. Test: `/opt/leveredge/gaia/gaia.py status`
5. If tests fail: `rm -rf /opt/leveredge/gaia && mv /opt/leveredge/gaia.backup.* /opt/leveredge/gaia`
6. Commit with detailed message

---

## Infrastructure Lessons

### Networking
- Cloudflare "Full" mode works, "Full (Strict)" requires origin cert
- Docker bridge IP: 172.17.0.1
- Service discovery within docker-compose: use service names
- External access: use Cloudflare Tunnel or exposed ports
- WireGuard VPN: server 10.8.0.1, laptop 10.8.0.2
- `stack_net` is the shared network for all services needing Supabase/Caddy access
- Prometheus on host network can't be reached from Docker bridge - connect to shared network instead

### Persistence
- SQLite fine for low-volume agent DBs
- Supabase for anything needing concurrent access
- Mount volumes for container data persistence
- Backup SQLite DBs to /opt/leveredge/shared/backups/

### Security
- Basic auth is temporary, Cloudflare Access is target
- Never log credential values
- Whitelist allowed paths for file operations
- Audit everything via Event Bus
- UFW rules: allow 8011 from 10.8.0.0/24 (HEPHAESTUS via VPN)

---

## Session Learnings

### January 15, 2026 (5 hours)
**What worked:**
- Phase-by-phase approach with specs
- FastAPI + n8n workflow pattern for agents
- Event Bus for audit trail
- Dockerizing agents that need network access

**What didn't:**
- Assuming localhost works from Docker containers
- Creating n8n workflows without webhookId
- Running as root (permission issues later)

### January 16, 2026 (6.5 hours - JUGGERNAUT MODE)
**Accomplished (13 tasks):**
1. HEPHAESTUS converted from REST to proper MCP protocol
2. Claude Web command center established
3. Phase 4 agents built (HERMES, ARGUS, ALOY, ATHENA)
4. Phase 4 n8n workflows created
5. n8n PROD migration
6. n8n DEV migration
7. ARIA debugged and fixed
8. promote-to-prod.sh created
9. Lesson capture system implemented
10. Old systemd services removed
11. HERMES Telegram + multi-channel
12. ARGUS Prometheus connected
13. Supabase PROD + DEV migration

**What worked:**
- GSD for parallel task execution
- CHRONOS backup before migrations
- Symlink strategy for volume preservation
- Container name preservation avoiding cascade updates

**What didn't:**
- GSD initially used wrong MCP
- Built HEPHAESTUS as REST instead of MCP initially
- Caddy 502 after container rename
- Over-verifying instead of moving fast
- Forgetting to update LESSONS-SCRATCH after debugging

### January 17, 2026 (OLYMPUS + Coaching Session)
**Accomplished:**
1. OLYMPUS unified orchestration system designed and deployed
2. Agent Registry (YAML single source of truth)
3. FastAPI ATLAS on port 8007
4. SENTINEL smart router on port 8019
5. 7 pre-built chains defined
6. ARIA → OLYMPUS integration
7. Pre-Router fixed to preserve ARIA's persona
8. ARIA Coaching TIER 1 (4 tools) built
9. ARIA Coaching TIER 2 (5 tools) built
10. ATLAS template bug fixed (v2.0.1)
11. Unified Threading spec created
12. **OPS-RUNBOOK.md created** - operational documentation

**Key Discoveries:**
- Agents run as raw uvicorn processes (no docker, no systemd)
- `docker-compose` → `docker compose` (no hyphen in newer Docker)
- ATLAS params weren't resolving templates - fixed

### January 17, 2026 (Fleet Expansion + PROD Promotion)
**Accomplished:**
1. Updated ARIA to know about 35+ agents across all categories
2. Started Creative Fleet agents (MUSE 8030, CALLIOPE 8031, THALIA 8032, ERATO 8033, CLIO 8034)
3. Built Security Fleet (CERBERUS 8020, PORT-MANAGER 8021)
4. Built Personal Fleet (GYM-COACH 8110, NUTRITIONIST 8101, MEAL-PLANNER 8102, ACADEMIC-GUIDE 8103, EROS 8104)
5. Built Business Fleet (HERACLES 8200, LIBRARIAN 8201, DAEDALUS 8202, THEMIS 8203, MENTOR 8204, PLUTUS 8205, PROCUREMENT 8206, HEPHAESTUS-SERVER 8207, ATLAS-INFRA 8208, IRIS 8209)
6. AEGIS V2 deployed with PostgreSQL backend and AES-256 encryption
7. Promoted ARIA to PROD

**Key Discoveries:**
- **GYM-COACH port conflict:** Port 8100 occupied by supabase-kong-dev → uses 8110 instead
- **n8n PUT /workflows API:** Requires exactly 4 fields: name, nodes, connections, settings (extra fields cause 400)
- **THALIA import fix:** `RgbColor` → `RGBColor` in pptx.dml.color
- **Creative Fleet dependencies:** pillow, python-pptx, python-docx, matplotlib
- **ARIA Supabase issue:** "Get User Preferences" node failing (credential or RPC function issue - needs fix)

**Fleet Health Summary:**
| Fleet | Status | Agents |
|-------|--------|--------|
| Core Infrastructure | All healthy | 12 agents (8007-8099) |
| Research | All healthy | SCHOLAR 8018, CHIRON 8017, SENTINEL 8019 |
| Creative | All healthy | 5 agents (8030-8034) |
| Security | All healthy | CERBERUS 8020, PORT-MANAGER 8021 |
| Personal | 4/5 healthy | GYM-COACH on 8110 (not 8100) |
| Business | All healthy | 10 agents (8200-8209) |

### January 17, 2026 (Overnight Mega-Build - 28+ Parallel Agents)
**Accomplished (massive overnight build):**

| Category | Items Built | Files | Lines |
|----------|-------------|-------|-------|
| Infrastructure Agents | FILE-PROCESSOR (8050), VOICE (8051), GATEWAY (8070), MEMORY-V2 (8066), SHIELD-SWORD (8067), REMINDERS-V2 | ~30 | ~4,500 |
| Dashboards | Fleet Dashboard (8060), Cost Dashboard (8061), Log Aggregation (8062), Uptime Monitor (8063), SSL Monitor (8064) | ~25 | ~3,800 |
| Docker | Full fleet docker-compose.yml (35 services, 5 profiles) | 1 | 1,392 |
| Documentation | MkDocs site with Material theme | ~15 | ~2,200 |
| Testing | pytest integration suite for all fleets | ~12 | ~2,100 |
| Integrations | Google Calendar sync, Google Tasks sync, Telegram bot, Email (SendGrid) | ~20 | ~3,500 |
| Maintenance | Storage cleanup, n8n chat memory cleanup | ~8 | ~1,200 |
| Security | fail2ban, UFW rules, Docker network isolation | ~10 | ~800 |
| Frontend | ARIA Frontend V2 (React components) | ~15 | ~2,800 |
| Client Portal | Next.js 14 with Supabase auth | ~20 | ~3,500 |
| Demo | Demo environment setup | ~8 | ~1,100 |
| Billing | Invoice & usage tracking system | ~10 | ~1,500 |
| Auto-start | Systemd service templates | ~5 | ~300 |
| **TOTAL** | 28+ components | ~245 | ~66,600 |

**Key Pattern - Parallel Agent Building:**
1. Launched 28+ Task agents in parallel batches
2. Each agent ran independently with full context
3. No blocking - all built simultaneously
4. Monitored completion via task notifications
5. Compiled results after all completed

**What Worked:**
- Parallel Task agents with clear specs = massive throughput
- Breaking work into independent, well-defined units
- Overnight execution while sleeping = productive use of time
- Each agent had complete context (no dependencies on other agents)

**What Didn't:**
- Some agents needed dependency installation (pillow, pptx, etc.)
- A few port conflicts (GYM-COACH 8100 → 8110)
- Some agents reference each other - would benefit from shared types

**Infrastructure Additions:**
| Directory | Purpose |
|-----------|---------|
| `/opt/leveredge/monitoring/` | uptime, ssl, logs, prometheus, grafana |
| `/opt/leveredge/integrations/` | google-calendar, google-tasks, telegram, email |
| `/opt/leveredge/maintenance/` | storage-cleanup, chat-cleanup |
| `/opt/leveredge/billing/` | Invoice & usage tracking |
| `/opt/leveredge/security/` | fail2ban, ufw, docker hardening |
| `/opt/leveredge/tests/` | pytest integration suite |
| `/opt/leveredge/docs-site/` | MkDocs documentation |
| `/opt/leveredge/demo/` | Demo environment |
| `/opt/leveredge/aria-frontend-v2/` | React component library |
| `/opt/leveredge/client-portal/` | Next.js client portal |

**Agent Count Summary:**
| Before Mega-Build | After Mega-Build |
|-------------------|------------------|
| 13 agents | 40+ agents |
| 4 fleets | 5 fleets + dashboards |
| No tests | Full pytest suite |
| No docs site | MkDocs with Material |
| No integrations | Google, Telegram, Email |

---

## Technical Debt Tracker (Updated Post-Mega-Build)

| Item | Priority | Effort | Status |
|------|----------|--------|--------|
| ~~Remove old systemd agent services~~ | ~~High~~ | ~~15 min~~ | ✅ Done |
| ~~HERMES Telegram config~~ | ~~Medium~~ | ~~30 min~~ | ✅ Done |
| ~~ARGUS Prometheus access~~ | ~~Medium~~ | ~~30 min~~ | ✅ Done |
| ~~OLYMPUS orchestration system~~ | ~~High~~ | ~~2 hours~~ | ✅ Done |
| ~~ARIA → OLYMPUS integration~~ | ~~High~~ | ~~30 min~~ | ✅ Done |
| ~~OPS-RUNBOOK.md~~ | ~~High~~ | ~~30 min~~ | ✅ Done |
| ~~Fleet Expansion (35+ agents)~~ | ~~High~~ | ~~4 hours~~ | ✅ Done (40+ now) |
| ~~ARIA PROD promotion~~ | ~~High~~ | ~~30 min~~ | ✅ Done |
| ~~AEGIS V2 PostgreSQL migration~~ | ~~High~~ | ~~2 hours~~ | ✅ Done |
| ~~Systemd service templates~~ | ~~High~~ | ~~2 hours~~ | ✅ Done - `/opt/leveredge/shared/systemd/` |
| ~~File upload system~~ | ~~Medium~~ | ~~4 hours~~ | ✅ Done - FILE-PROCESSOR (8050) |
| ~~Telegram interface~~ | ~~Medium~~ | ~~2 hours~~ | ✅ Done - `/opt/leveredge/integrations/telegram/` |
| ~~Voice interface~~ | ~~Medium~~ | ~~3 hours~~ | ✅ Done - VOICE (8051) |
| ~~Memory consolidation~~ | ~~Medium~~ | ~~3 hours~~ | ✅ Done - MEMORY-V2 (8066) |
| ~~Two-way Google sync~~ | ~~Medium~~ | ~~2 hours~~ | ✅ Done - `/opt/leveredge/integrations/` |
| ~~Email/SMTP config~~ | ~~Medium~~ | ~~1 hour~~ | ✅ Done - SendGrid integration |
| ~~Storage cleanup automation~~ | ~~Medium~~ | ~~1 hour~~ | ✅ Done - `/opt/leveredge/maintenance/` |
| ~~n8n chat memory cleanup~~ | ~~Medium~~ | ~~1 hour~~ | ✅ Done - `/opt/leveredge/maintenance/` |
| ~~Documentation site~~ | ~~Medium~~ | ~~2 hours~~ | ✅ Done - MkDocs at `/opt/leveredge/docs-site/` |
| ~~Integration test suite~~ | ~~Medium~~ | ~~3 hours~~ | ✅ Done - `/opt/leveredge/tests/` |
| ~~CONVENER V2 with Robert's Rules~~ | ~~High~~ | ~~3 hours~~ | ✅ Done - smart meeting facilitator |
| ~~Command Center Dashboard~~ | ~~High~~ | ~~4 hours~~ | ✅ Done - Next.js 14, 8 domains, 40+ agents |
| ~~AEGIS V2 database schema~~ | ~~High~~ | ~~1 hour~~ | ✅ Done - DEV Supabase tables |
| ~~Cost tracking library~~ | ~~High~~ | ~~1 hour~~ | ✅ Done - `/opt/leveredge/shared/lib/cost_tracker.py` |
| ~~Encryption module for AEGIS~~ | ~~High~~ | ~~30 min~~ | ✅ Done - Fernet AES-256 |
| ~~n8n workflow templates for AEGIS~~ | ~~Medium~~ | ~~30 min~~ | ✅ Done - 3 workflows |
| ~~GitHub SSH verification~~ | ~~Low~~ | ~~5 min~~ | ✅ Done - damonhess-dev account |
| **Fix ARIA Supabase credential** | High | 30 min | ⬜ Get User Preferences node failing |
| **Wire cost tracking into CHIRON/SCHOLAR** | High | 1 hour | ⬜ Library built, needs integration |
| **Deploy new agents to production** | High | 2 hours | ⬜ 35 services designed, need deployment |
| **Install agent dependencies** | Medium | 30 min | ⬜ pillow, pptx, etc. for Creative Fleet |
| **Convert agents to native n8n nodes** | High | 4 hours | ⬜ Currently Code nodes, need visibility |
| HEPHAESTUS → OLYMPUS bridge | Medium | 30 min | ⬜ Spec ready |
| DEV supabase-storage-dev fix | Medium | 30 min | ⬜ |
| DEV supabase-studio-dev fix | Low | 30 min | ⬜ |
| Cloudflare Access for control plane | Low | 2 hours | ⬜ Needs manual dashboard config |
| PROD database schema sync | Medium | 30 min | ⬜ AEGIS V2 tables only in DEV |
| Import all credentials to AEGIS | Medium | 1 hour | ⬜ 6 registered, need full inventory |
| Generate Midjourney assets | Medium | 2 hours | ⬜ 9 domain backgrounds + hub |
| CRM system (lead tracking) | Low | 4 hours | ⬜ |
| Public website (leveredgeai.com) | Low | 8 hours | ⬜ |

---

## File Locations

### Documentation
| File | Purpose |
|------|---------|
| /opt/leveredge/README.md | Project overview |
| /opt/leveredge/ARCHITECTURE.md | System design overview |
| /opt/leveredge/OPS-RUNBOOK.md | **Operational procedures - restart, logs, troubleshooting** |
| /opt/leveredge/AGENT-ROUTING.md | Who does what, routing rules |
| /opt/leveredge/LOOSE-ENDS.md | Current tasks and status |
| /opt/leveredge/FUTURE-VISION.md | Business roadmap |
| /opt/leveredge/LESSONS-LEARNED.md | This file |
| /opt/leveredge/LESSONS-SCRATCH.md | Quick debug capture |
| /opt/leveredge/docs-site/ | MkDocs documentation site |

### Core Infrastructure
| Directory | Purpose |
|-----------|---------|
| /opt/leveredge/control-plane/agents/ | 40+ FastAPI agents |
| /opt/leveredge/control-plane/event-bus/ | Inter-agent communication |
| /opt/leveredge/config/agent-registry.yaml | OLYMPUS single source of truth |
| /opt/leveredge/gaia/ | Emergency bootstrap |

### Data Plane
| Directory | Purpose |
|-----------|---------|
| /opt/leveredge/data-plane/prod/n8n/ | Production n8n |
| /opt/leveredge/data-plane/dev/n8n/ | Development n8n |
| /opt/leveredge/data-plane/prod/supabase/ | Production Supabase |
| /opt/leveredge/data-plane/dev/supabase/ | Development Supabase |

### New Infrastructure (Post-Mega-Build)
| Directory | Purpose |
|-----------|---------|
| /opt/leveredge/monitoring/ | Prometheus, Grafana, uptime, SSL, logs |
| /opt/leveredge/integrations/ | Google Calendar, Google Tasks, Telegram, Email |
| /opt/leveredge/maintenance/ | Storage cleanup, chat memory cleanup |
| /opt/leveredge/billing/ | Invoice & usage tracking |
| /opt/leveredge/security/ | fail2ban, UFW, Docker hardening |
| /opt/leveredge/tests/ | pytest integration suite |
| /opt/leveredge/demo/ | Demo environment |
| /opt/leveredge/aria-frontend-v2/ | React component library |
| /opt/leveredge/client-portal/ | Next.js client portal |
| /opt/leveredge/ui/command-center/ | Command Center Dashboard (Next.js 14) |
| /opt/leveredge/workflows/aegis/ | AEGIS n8n workflow templates |
| /opt/leveredge/shared/lib/ | Shared Python libraries (cost_tracker) |
| /opt/leveredge/secrets/ | Encryption keys (aegis_master.key) |

### Shared Resources
| Directory | Purpose |
|-----------|---------|
| /opt/leveredge/shared/scripts/ | CLI tools |
| /opt/leveredge/shared/backups/ | CHRONOS backups |
| /opt/leveredge/shared/systemd/ | Service templates |
| /opt/leveredge/shared/llm-api-keys.env | API keys for LLM agents |

---

## Key Pattern: Parallel Agent Building

The overnight mega-build demonstrated a powerful pattern for massive throughput:

### Recipe for Parallel Builds
1. **Define independent units** - Each component should be buildable without waiting for others
2. **Create clear specs** - Each Task agent needs complete context in its prompt
3. **Launch in batches** - Send multiple Task tool calls in single message
4. **Monitor via notifications** - System reminders tell you when agents complete
5. **Compile after completion** - Aggregate results once all done

### When to Use This Pattern
- Multiple independent features/components
- Large-scale infrastructure buildout
- Documentation across multiple files
- Test suites for different modules

### When NOT to Use
- Sequential dependencies (A must finish before B starts)
- Components that share state or types
- When you need to iterate based on first result

### Example Prompt Structure for Build Agents
```
Build [COMPONENT_NAME] at [PATH]:
- Purpose: [what it does]
- Port: [if applicable]
- Dependencies: [libraries needed]
- Key features: [bullet list]
- Create: [files to create]
- Follow pattern from: [existing similar component]
```

### Results from Jan 17 Mega-Build
- 28+ components built in parallel
- ~245 files created
- ~66,600 lines of code
- Completed while sleeping (overnight)

---

## Session Learnings (Continued)

### January 18, 2026 (Command Center + AEGIS V2)
**Accomplished:**

| Category | Items Built | Details |
|----------|-------------|---------|
| CONVENER V2 | Smart meeting facilitator | Robert's Rules, LLM-powered, signal parsing |
| Command Center | Next.js 14 dashboard | Hub, 8 domain pages, 40+ agent pages, council UI |
| AEGIS V2 Schema | PostgreSQL tables | aegis_credentials_v2, aegis_providers (12 providers) |
| Encryption | Fernet (AES-256) module | Master key generated, encryption.py created |
| Cost Tracking | Python library + views | cost_tracker.py, llm_cost_summary view |
| n8n Workflows | 3 AEGIS templates | health-monitor, rotation-scheduler, daily-report |

**Command Center Dashboard:**
- `/opt/leveredge/ui/command-center/` - Full Next.js 14 App Router implementation
- Hub with key metrics (agent status, meeting activity)
- 8 domain pages with agent grids (GAIA, PANTHEON, SENTINELS, THE SHIRE, THE KEEP, CHANCERY, ALCHEMY, ARIA SANCTUM)
- 40+ agent detail pages with status, actions, API endpoints
- Council meeting UI (create, run, summon, vote)
- React Query hooks for real-time data fetching

**Key Errors and Fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `Engine "node" incompatible (18.19.1 vs >=20.9.0)` | Next.js 16 requires Node 20+ | Downgraded to Next.js 14.2.21 + React 18 |
| ESLint peer dependency conflict | eslint ^9 incompatible with Next.js 14 | Downgraded to eslint ^8 |
| `next.config.ts not supported` | Next.js 14 uses .js/.mjs | Renamed to next.config.mjs |
| `Unknown font 'geist'` | Geist font not in Next.js 14 | Changed to Inter font |
| `HealthStatus type mismatch` | Missing status/message fields | Updated types.ts with full interface |
| `useSearchParams should be wrapped in Suspense` | Next.js 14 requirement | Wrapped NewMeetingContent in Suspense boundary |
| `params: Promise<{...}>` syntax error | Next.js 14 params not Promise (unlike 15/16) | Changed to `params: {...}`, removed async/await |

**Next.js 14 vs 16 Differences Learned:**
- Node.js: 14 works with 18.x, 16 requires 20.9+
- Config: 14 uses .mjs, 16 supports .ts
- Fonts: 14 uses next/font/google manually, 16 has built-in Geist
- Params: 14 params are sync objects, 15/16 are Promises
- ESLint: 14 requires eslint ^8, 16 uses ^9

**AEGIS V2 Implementation:**
- Database schema in DEV Supabase (port 54323)
- 12 providers pre-loaded (anthropic, openai, telegram, slack, etc.)
- Environment column for DEV/PROD credential separation
- Fernet encryption with master key at `/opt/leveredge/secrets/aegis_master.key`

**Cost Tracking:**
- Library at `/opt/leveredge/shared/lib/cost_tracker.py`
- Pricing for claude-3-5-sonnet, gpt-4o, gpt-4o-mini, gpt-3.5-turbo
- Views: `llm_cost_summary` (by model), `llm_daily_costs` (daily breakdown)
- Tested successfully with test entry

**Documentation Updates:**
- LOOSE-ENDS.md - Removed completed items, updated session log
- FUTURE-VISION.md - Marked CONCLAVE V2 and Command Center as BUILT

**What Worked:**
- Downgrading Next.js 14 instead of upgrading Node.js (faster)
- Using React Query for data fetching hooks
- Fernet encryption for credential security
- Separating DEV/PROD credentials via environment column

**What Didn't:**
- Initially tried Next.js 16 without checking Node version
- Missed Suspense boundary for useSearchParams (Next.js 14 strict)
- Assumed params were Promises like Next.js 15/16

**CONVENER V2 Database Mapping:**
When designing V2 APIs, existing DB constraints limit valid values. CONVENER V2 wanted CONVENED/IN_SESSION/ADJOURNED but DB had scheduled/active/completed.
- **Solution:** Map V2 status names in API responses while using DB-compatible values internally
- CONVENED → stored as "scheduled"
- IN_SESSION → stored as "active"
- ADJOURNED → stored as "completed"
- **Prevention:** Check existing DB constraints first when designing V2 APIs
