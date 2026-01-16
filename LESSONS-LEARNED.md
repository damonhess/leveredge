# LEVEREDGE LESSONS LEARNED

*Living document - Update after every session*
*Last Updated: January 15, 2026*

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
- AI Agent is expensive ($0.03/request with Sonnet)
- Dumb executor pattern: Claude Desktop reasons, HEPHAESTUS executes
- Keep execution tools atomic and composable

#### CHRONOS
- Backup directory must exist before first backup
- Checksum manifest for integrity verification
- Pre-deploy backups should be automatic before any HEPHAESTUS build

#### HADES
- Depends on CHRONOS for backup-based restores
- Version-based rollback requires n8n's internal history API
- Emergency actions require explicit confirmation flag

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

### Post-Update Verification
- [ ] GAIA health check passes
- [ ] Can list backups
- [ ] Emergency Telegram bot responds (if configured)
- [ ] Documented what changed and why

### GAIA Update History

| Date | Change | Reason | Tested By |
|------|--------|--------|-----------|
| 2026-01-15 | Initial creation | Phase 0 build | Claude Code |
| | | | |

---

## Autonomy Handoff Preparation

When upgrading from Option A (dumb executors) to Option B (autonomous agents):

### Per-Agent Handoff Checklist

#### HEPHAESTUS
- [ ] Add LLM node (Claude Haiku for simple, Sonnet for complex)
- [ ] Implement request interpretation logic
- [ ] Add design/planning phase before execution
- [ ] Test with vague requests
- [ ] Set cost alerts ($50/month warning)
- [ ] Document decision patterns for audit

#### ATLAS
- [ ] Upgrade from switch routing to LLM routing
- [ ] Add context awareness (what agents are busy, recent failures)
- [ ] Implement request prioritization
- [ ] Add "I don't know" fallback (ask human)

#### ATHENA
- [ ] Add LLM for automatic documentation
- [ ] Implement change detection (watch Event Bus)
- [ ] Auto-commit documentation updates
- [ ] Generate session summaries

#### ALOY
- [ ] Add anomaly detection LLM
- [ ] Pattern learning from Event Bus history
- [ ] Alert generation for suspicious patterns
- [ ] Integration with HERMES for notifications

### Global Handoff Tasks
- [ ] Implement TIER 2 approval queue
- [ ] HERMES Telegram integration complete
- [ ] Cost monitoring dashboard in Grafana
- [ ] Per-agent spending limits
- [ ] Kill switch for runaway costs
- [ ] Audit log retention policy (30 days? 90 days?)

### Handoff Trigger Criteria
- Revenue > $10K/month (can afford LLM costs)
- All Phase 4 agents deployed
- HERMES approval flow tested
- Cost monitoring verified
- Human comfortable with autonomy level

---

## Infrastructure Lessons

### Networking
- Cloudflare "Full" mode works, "Full (Strict)" requires origin cert
- Docker bridge IP: 172.17.0.1
- Service discovery within docker-compose: use service names
- External access: use Cloudflare Tunnel or exposed ports

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

**Process improvements:**
- Always test webhook accessibility after creating workflow
- Use `docker logs` immediately when things don't work
- Commit frequently, not in batches

---

## Technical Debt Tracker

| Item | Priority | Effort | Blocked By |
|------|----------|--------|------------|
| Service consolidation (hades-api → hades) | Low | 15 min | Nothing |
| n8n-troubleshooter rename | Low | 1 hour | Nothing |
| Cloudflare Access for control plane | Medium | 2 hours | Nothing |
| GAIA Telegram bot setup | Low | 30 min | Bot token |
| Push to GitHub remote | Medium | 5 min | Create repo |

---

## Future Investigation

Questions to answer later:
- Can Claude Code expose itself as MCP server?
- Best model for cost/capability balance per agent?
- How to share context between Claude Desktop and Claude Code?
- Supabase Realtime for Event Bus instead of SQLite?
- n8n community nodes for agent capabilities?
