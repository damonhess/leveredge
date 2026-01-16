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

### 2026-01-17 - [Agent Routing + ARIA Knowledge System]
**Created:** `/opt/leveredge/AGENT-ROUTING.md` - Complete agent routing matrix
**Database:** `aria_knowledge` table in PROD Supabase with 18 initial entries
**Functions:** `aria_add_knowledge`, `aria_search_knowledge`, `aria_get_recent_knowledge`, `aria_get_system_status`
**Rules Added:** Rule #5 (Agent Routing), Rule #6 (ARIA Knowledge Updates), Rule #7 (Event Bus Logging)
**Categories:** agent (10), architecture (3), rule (3), status (2)
**Purpose:** ARIA now has queryable knowledge base for system awareness. All ops route through designated agents.

### 2026-01-17 11:30 AM - [Development Flow Rules Codified]
**Created:** /home/damon/.claude/EXECUTION_RULES.md
**Updated:** LESSONS-LEARNED.md, ARCHITECTURE.md
**Symlinked:** /opt/leveredge/EXECUTION_RULES.md → ~/.claude/EXECUTION_RULES.md
**Rule:** DEV first for all workflows/code/schema. PROD only for real data with explicit approval.
**Enforcement:** All Claude instances must read EXECUTION_RULES.md before tasks.
**MCP Awareness:** n8n-control (5679), n8n-troubleshooter (PROD 5678), n8n-troubleshooter-dev (DEV 5680)
**Prevention:** No more accidental PROD deployments without explicit approval.

### 2026-01-17 11:15 AM - [Full Portfolio Populated - 28 Wins]
**Status:** All wins tracked in PROD Supabase
**Tables:**
- `aria_wins` - Individual win records (28 rows)
- `aria_portfolio_summary` - Aggregated totals

**Portfolio Value:** $58,500 - $117,000 across 28 wins
**Categories:** 27 infrastructure, 1 client (Burning Man sales)

**Key Wins Include:**
- ARIA V3.1/V3.2 Personal Assistant
- GAIA, ATLAS, HEPHAESTUS, AEGIS, CHRONOS, HADES, HERMES, ARGUS, ALOY, ATHENA agents
- Supabase PROD/DEV, n8n PROD/DEV/Control instances
- Shield (16 patterns), Sword (15 techniques), Event Bus
- LLM Cost Tracking, Portfolio Tracking systems
- Docker Compose Architecture, Cloudflare DNS

**Ownership:** Claude Web tracks accomplishments → GSD executes → Eventually VARYS will own portfolio management

**ARIA Test:** "What is my portfolio worth?" → "Your portfolio is worth between $58,500 and $117,000 across 28 wins."

### 2026-01-17 11:00 AM - [ARIA V3.2 PROD Promotion - COMPLETE]
**Status:** ARIA V3.2 fully working in PROD n8n (localhost:5678)
**Key Learnings:**

1. **n8n Version System:** n8n uses `workflow_history` table with `activeVersionId` in `workflow_entity`. Direct database changes to `workflow_entity.nodes` don't take effect - must create new version in `workflow_history` and update `activeVersionId`.

2. **Credential Migration:** When copying workflows between n8n instances, credential IDs must be updated:
   - OpenAI: DEV `kdp4XqWzpyhEkmtu` → PROD `5DFuvUPLavfaWChn`
   - Postgres: DEV `DGroZIqnHY4mrCB7` → PROD `aVP8htYcA8y2UOih`

3. **Supabase Endpoints:**
   - DEV: `https://dev.supabase.leveredgeai.com/rest/v1/`
   - PROD: `https://api.leveredgeai.com/rest/v1/`

4. **Portfolio Function Migration:** `aria_get_portfolio_summary()` and `aria_portfolio_summary` table must exist in PROD Supabase.

**PROD Tests Passed:**
- "Hey ARIA" → "Hey Daddy. What's on your mind?"
- "What is my portfolio worth?" → "$57,500-$109,500 across 8 wins"
- "What time is it?" → "11:01 AM"
- Shield (negging) → "Heads up — that's negging..."

**Prevention:** Create a proper workflow promotion script that:
1. Updates credential IDs to match target environment
2. Updates Supabase URLs
3. Creates proper workflow version in `workflow_history`
4. Ensures RPC functions exist in target Supabase

### 2026-01-17 - [ARIA V3.2 Demo Test - PASSED]
**Environment:** DEV n8n (localhost:5680)
**All Tests Passed:**

| Category | Test | Result |
|----------|------|--------|
| **Basic** | "Hey ARIA" | ✓ "Hey Daddy! What's on your mind today?" |
| **Basic** | "What time is it?" | ✓ "10:06 AM" |
| **Basic** | "What day is it?" | ✓ "Friday." |
| **Portfolio** | "What's my portfolio worth?" | ✓ "$57,500-$109,500 across 8 wins" |
| **Portfolio** | "What have I accomplished?" | ✓ References portfolio + Burning Man sales |
| **Portfolio** | "Am I ready to launch?" | ✓ Enters STRATEGY mode |
| **HYPE mode** | "I need motivation" | ✓ "Stop right there. You've built..." |
| **COMFORT mode** | "I'm feeling down" | ✓ "I'm here for you, love..." |
| **STRATEGY mode** | "Let's strategize" | ✓ Structured planning response |
| **DRILL mode** | "Hold me accountable" | ✓ "This is the third time..." |
| **FOCUS mode** | "How do I create webhook?" | ✓ Step-by-step technical answer |
| **Shield: Negging** | "for someone like you..." | ✓ "Heads up — that's negging" |
| **Shield: Guilt** | "after everything I've done..." | ✓ "That's a guilt trip" |
| **Shield: Triangulation** | "everyone else thinks..." | ✓ "That's triangulation" |
| **Shield: Minimizing** | "you're overreacting..." | ✓ "That's gaslighting and minimizing" |
| **Sword: HYPE** | Pre-call nerves | ✓ Future pacing + identity reinforcement |
| **Sword: DRILL** | Missed commitment | ✓ Commitment consistency |
| **Sword: COMFORT** | Failure feelings | ✓ Reframing + strategic vulnerability |

**Notes:** All V3.2 features working correctly. Ready for PROD promotion.

### 2026-01-17 - [ARIA Shield/Sword Enhanced - DEV]
**Status:** Full Dark Psychology Suite working in DEV n8n
**SHIELD (16 patterns):** negging, gaslighting, guilt_trip, false_urgency, moving_goalposts, status_games, love_bombing, triangulation, darvo, sealioning, concern_trolling, minimizing, catastrophizing_pressure, silent_treatment_threat, double_bind, obligation_creation
**SHIELD output:** manipulation_detected, threat_level (none/low/med/high), patterns_found[], recommended_response_type
**SWORD (15 techniques):** anchoring, future_pacing, identity_reinforcement, inoculation, reframing, pattern_interrupt, presuppositions, commitment_consistency, loss_aversion, chunking, authority_positioning, social_proof, contrast, strategic_vulnerability, embedded_commands
**SWORD mode loadouts:** HYPE, COACH, DRILL, COMFORT, STRATEGY, FOCUS, DEFAULT - each with primary/secondary techniques
**Tested Shield:** love_bombing ✓ | darvo ✓ | triangulation ✓ | concern_trolling ✓ | normal (no false positive) ✓
**Tested Sword modes:** HYPE ✓ | COMFORT ✓ | DRILL ✓ | STRATEGY ✓

### 2026-01-17 - [ARIA Time Calibration - DEV]
**Status:** Working in DEV n8n
**Problem:** ARIA gave verbose responses to "what time is it?"
**Fix:** Added explicit "Time & Date Responses" section to system prompt with examples
**Tested:** "What time is it?" → "9:22 AM." | "What day?" → "Friday." | "What's today?" → "Friday, January 16th, 2026."

### 2026-01-17 - [ARIA Portfolio Injection - DEV]
**Status:** Working in DEV n8n
**Workflow:** Personal Assistant - AI Agent Main (aX8d9zWniCYaIDwc)
**Fix applied:** Changed Postgres Chat Memory sessionKey from `.item.json` to `.first().json`
**Data source:** `aria_get_portfolio_summary()` RPC on DEV Supabase
**Tested:** "What's my portfolio worth?" → "$57,500-$109,500 across 8 wins"
**HYPE mode:** Works with anchoring "You've built [portfolio]. That's not luck—that's capability."
**Next:** Promote to PROD when ready

### 2026-01-17 - [GitHub Remote]
**Status:** /opt/leveredge pushed to GitHub
**Remote:** https://github.com/damonhess/leveredge.git (HTTPS)
**Note:** Used HTTPS because server SSH key is for damonhess-dev account
**Backup:** Now have off-server backup

### 2026-01-17 - [promote-to-prod.sh]
**Status:** API keys configured, script ready
**Location:** /opt/leveredge/shared/scripts/promote-to-prod.sh
**Config:** .env file created (edit to add actual API keys)
**Usage:** `cd /opt/leveredge/shared/scripts && ./promote-to-prod.sh <workflow_id>`
**Note:** Get API keys from Settings → n8n API → Create API Key on both n8n instances

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
