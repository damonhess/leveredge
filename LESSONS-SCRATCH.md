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
