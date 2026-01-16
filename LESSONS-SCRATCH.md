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

*Last consolidated: January 17, 2026 12:45 AM*

### 2026-01-17 OVERNIGHT - [Cost Tracking Infrastructure]
**Created:** llm_usage, llm_usage_daily, llm_budget_alerts tables in PROD Supabase
**Functions:** log_llm_usage, get_usage_summary, get_conversation_cost, get_daily_costs, get_usage_by_model, get_usage_by_agent, check_budget_alerts, calculate_llm_cost
**Also:** Added input_tokens, output_tokens, model, cost_usd, latency_ms columns to aria_messages
**Status:** Ready for ARIA integration - workflows need to call log_llm_usage() after each LLM call

### 2026-01-16 11:00 - [Supabase Storage DEV]
**Symptom:** supabase-storage-dev crash-looping with "column path_tokens already exists"
**Cause:** Storage image version mismatch (v0.43.11) vs database schema (created by newer image). Migration table had old format, couldn't recognize already-applied migrations.
**Fix:** 1) Copy migrations table from PROD postgres to DEV postgres_dev, 2) Upgrade storage image to v1.32.0 (match PROD)
**Prevention:** Keep DEV and PROD Supabase image versions in sync

### 2026-01-16 11:02 - [Supabase Studio DEV]
**Symptom:** supabase-studio-dev marked "unhealthy" despite working
**Cause:** Next.js 15+ binds to container hostname by default, not localhost. Healthcheck uses localhost:3000 which fails.
**Fix:** Add `HOSTNAME: "::"` env var to force binding to all interfaces (same as PROD)
**Prevention:** Always include `HOSTNAME: "::"` in Supabase Studio container configs

---

*Add new entries above this line*
