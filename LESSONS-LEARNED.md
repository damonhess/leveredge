# LEVEREDGE LESSONS LEARNED

*Living document - Update after every session*
*Last Updated: January 17, 2026 (11:20 AM)*

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

**Process improvements:**
- Always specify which MCP server in specs
- Format GSD dispatches as ready-to-paste blocks
- Symlink volumes, don't move them
- Preserve container names during migration
- Claude Code must update LESSONS-SCRATCH after every debug

---

## Technical Debt Tracker (Updated)

| Item | Priority | Effort | Status |
|------|----------|--------|--------|
| ~~Remove old systemd agent services~~ | ~~High~~ | ~~15 min~~ | ✅ Done |
| ~~HERMES Telegram config~~ | ~~Medium~~ | ~~30 min~~ | ✅ Done |
| ~~ARGUS Prometheus access~~ | ~~Medium~~ | ~~30 min~~ | ✅ Done |
| DEV supabase-storage-dev fix | Medium | 30 min | ⬜ |
| DEV supabase-studio-dev fix | Low | 30 min | ⬜ |
| promote-to-prod.sh API keys | Medium | 15 min | ⬜ |
| Cloudflare Access for control plane | Low | 2 hours | ⬜ |
| Push to GitHub remote | Low | 5 min | ⬜ |

---

## File Locations

| File | Purpose |
|------|---------|
| /opt/leveredge/MASTER-LAUNCH-CALENDAR.md | Launch timeline and milestones |
| /opt/leveredge/LESSONS-LEARNED.md | This file |
| /opt/leveredge/LESSONS-SCRATCH.md | Quick debug capture (consolidate here) |
| /opt/leveredge/FUTURE-VISION-AND-EXPLORATION.md | Architecture decisions |
| /opt/leveredge/data-plane/prod/n8n/ | Production n8n |
| /opt/leveredge/data-plane/dev/n8n/ | Development n8n |
| /opt/leveredge/data-plane/prod/supabase/ | Production Supabase |
| /opt/leveredge/data-plane/dev/supabase/ | Development Supabase |
| /opt/leveredge/control-plane/ | Control plane agents |
| /opt/leveredge/shared/scripts/ | CLI tools |
| /opt/leveredge/shared/backups/ | CHRONOS backups |
