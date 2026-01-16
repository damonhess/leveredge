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

### 2026-01-16 10:45 - [Supabase Migration]
**Symptom:** supabase-auth container crash-looping after migration
**Cause:** Empty `SMTP_PORT=` in .env causes gotrue to fail parsing (newer gotrue requires valid int)
**Fix:** Set `SMTP_PORT=587` and `SMTP_HOST=localhost` even when email is disabled
**Prevention:** When migrating Supabase, check .env for empty port values that newer images require

### 2026-01-16 10:30 - [Supabase Migration]
**Symptom:** Need to migrate Supabase to /opt/leveredge/data-plane/ without data loss
**Cause:** Data lives in bind-mounted volumes at old location
**Fix:** Use symlinks from new compose location to existing volume directories. Don't move data.
**Prevention:** For any Docker migration with bind mounts: symlink volumes, don't copy/move them

### 2026-01-16 10:35 - [Supabase Migration]
**Symptom:** Expected to need many reference updates after migration
**Cause:** All routing uses container names (supabase-kong, supabase-db) on shared Docker network
**Fix:** No fixes needed - preserving container names means Caddy, n8n, and all services continue working
**Prevention:** When migrating Docker services, preserve container names to avoid cascading reference updates

### 2026-01-16 22:45 - [ARIA]
**Symptom:** "No response generated" from ARIA
**Cause:** `$json.message` after SQL node got `{?column?: 1}` instead of upstream data
**Fix:** Use explicit reference: `$('Process Router Response').first().json.message`
**Prevention:** Always use explicit node references when data must pass through SQL nodes

### 2026-01-16 22:30 - [Caddy]
**Symptom:** 502 Bad Gateway after migration
**Cause:** Caddy config still referenced old container name `n8n` instead of `prod-n8n`
**Fix:** Update Caddyfile, `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
**Prevention:** Container renames require Caddyfile updates

### 2026-01-16 21:00 - [n8n MCP]
**Symptom:** GSD created workflows in wrong n8n instance
**Cause:** Used n8n-troubleshooter (prod) instead of n8n-control (control plane)
**Fix:** Specify correct MCP in spec, updated LESSONS-LEARNED with MCP mapping table
**Prevention:** Always specify which MCP server in specs

---

*Add new entries above this line*
