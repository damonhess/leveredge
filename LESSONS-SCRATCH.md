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

### 2026-01-17 00:35 - [OLYMPUS Unified Orchestration System]
**Status:** Deployed and verified
**Scope:** ATLAS (8007), SENTINEL (8019), Agent Registry

**Created:**
- `/opt/leveredge/config/agent-registry.yaml` - Single source of truth (1526 lines)
- `/opt/leveredge/control-plane/agents/atlas/` - FastAPI orchestration engine
- `/opt/leveredge/control-plane/agents/sentinel/` - Smart router with failover

**Architecture:**
```
ARIA/Telegram/CLI → SENTINEL (router) → ATLAS (orchestrator) → Agents
                                      ↓
                              n8n ATLAS (visual fallback)
```

**Agent Registry Contains:**
- 11 agents: SCHOLAR, CHIRON, HERMES, CHRONOS, HADES, AEGIS, ARGUS, ALOY, ATHENA, HEPHAESTUS, EVENT-BUS
- Full action definitions with params, returns, timeouts
- 7 pre-built chains: research-and-plan, validate-and-decide, comprehensive-market-analysis, niche-evaluation, weekly-planning, fear-to-action, safe-deployment
- Routing rules and intent patterns

**SENTINEL Features:**
- Smart routing (complexity-based: simple → direct, complex → ATLAS)
- Health monitoring with circuit breaker
- Auto-failover between n8n and FastAPI
- Sync validation endpoint

**ATLAS Features:**
- Chain execution with parallel/sequential steps
- Template rendering for dynamic params
- Retry logic with configurable attempts
- Cost tracking per execution
- Event bus publishing

**Container Setup:**
```bash
docker run -d --name atlas --network control-plane-net -p 8007:8007 \
  -v /opt/leveredge/config:/opt/leveredge/config:ro \
  -e REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml \
  -e EVENT_BUS_URL=http://event-bus:8099 \
  n8n-atlas:latest && docker network connect stack_net atlas

docker run -d --name sentinel --network control-plane-net -p 8019:8019 \
  -v /opt/leveredge/config:/opt/leveredge/config:ro \
  -e REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml \
  -e EVENT_BUS_URL=http://event-bus:8099 \
  -e FASTAPI_ATLAS_URL=http://atlas:8007 \
  n8n-sentinel:latest && docker network connect stack_net sentinel
```

**Test Commands:**
```bash
# Health checks
curl http://localhost:8007/health  # ATLAS
curl http://localhost:8019/health  # SENTINEL
curl http://localhost:8019/status  # Engine status

# Single agent via orchestration
curl -X POST http://localhost:8019/orchestrate -H "Content-Type: application/json" \
  -d '{"source":"test","type":"single","steps":[{"id":"t1","agent":"chiron","action":"hype","params":{}}]}'

# Direct routing (bypass orchestration)
curl -X POST http://localhost:8019/direct/argus/status

# Sync validation
curl http://localhost:8019/validate-sync

# List chains
curl http://localhost:8007/chains | jq '.chains[].name'
```

**Deferred Work:**
- n8n ATLAS workflow (FastAPI handles orchestration)
- ARIA integration (requires workflow updates)

### 2026-01-16 23:35 - [Universal Cost Tracking Infrastructure]
**Status:** Deployed and verified
**Scope:** CHIRON, SCHOLAR, ARGUS

**Created:**
- `/opt/leveredge/control-plane/shared/cost_tracker.py` - Universal cost tracking module
- `agent_usage_logs` table in PROD Supabase with indexes
- `agent_cost_summary` view for quick overview
- `get_agent_costs()` and `get_daily_costs()` SQL functions
- ARGUS `/costs`, `/costs/daily`, `/costs/summary` endpoints

**Integration Points:**
- CHIRON: `call_llm()` now logs usage automatically
- SCHOLAR: Both `call_llm()` and `call_llm_with_search()` log usage + web searches

**Tracked Metrics Per Request:**
- Agent name, endpoint, model
- Input tokens, output tokens
- Web searches count
- Input cost, output cost, feature cost, total cost
- Metadata (days_to_launch, etc.)
- Timestamp

**Pricing (per 1M tokens):**
- Claude Sonnet 4: $3.00 input, $15.00 output
- Claude Opus 4: $15.00 input, $75.00 output
- Claude Haiku 4: $0.25 input, $1.25 output

**Container Setup Requirements:**
1. Containers must be on `stack_net` network to reach supabase-kong
2. `SUPABASE_SERVICE_KEY` env var must be set (from `/opt/leveredge/data-plane/prod/supabase/.env`)
3. Shared module copied to container at `/opt/leveredge/control-plane/shared/`

**Rebuild Command Pattern:**
```bash
SERVICE_ROLE_KEY="<key>" && \
docker stop <agent> && docker rm <agent> && \
docker run -d --name <agent> \
  --network control-plane-net \
  -p <port>:<port> \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e EVENT_BUS_URL="http://event-bus:8099" \
  -e SUPABASE_URL="http://supabase-kong:8000" \
  -e SUPABASE_SERVICE_KEY="$SERVICE_ROLE_KEY" \
  n8n-<agent>:latest && \
docker network connect stack_net <agent>
```

**Gotcha:** The `get_daily_costs()` function had ambiguous column reference error. Fixed by renaming return columns to `cost_date`, `day_total_cost`, `day_request_count`.

**Verification:**
```bash
curl -s http://localhost:8016/costs | jq .
# Returns costs by agent for last 30 days

docker exec supabase-db psql -U postgres -d postgres \
  -c "SELECT * FROM agent_usage_logs ORDER BY created_at DESC LIMIT 5;"
```

**Git Status:** Changes ready but blocked by root-owned directories in .git/objects. Need `sudo chown -R damon:damon /opt/leveredge/.git` before commit.

### 2026-01-16 21:55 - [SCHOLAR V2 Elite Market Research Upgrade]
**Upgrade:** SCHOLAR v1.0 → v2.0
**Container:** Rebuilt and deployed to control-plane-net

**New Endpoints (5):**
- `/deep-research` - Multi-source deep dive with web search
- `/competitor-profile` - Structured competitor analysis with web search
- `/market-size` - TAM/SAM/SOM calculation with sources
- `/pain-discovery` - Research and quantify pain points
- `/validate-assumption` - Test business assumptions with evidence

**New Frameworks (5):**
- TAM/SAM/SOM market sizing framework
- Competitive analysis framework with structured profiles
- ICP development framework with buyer profiles
- Pain point discovery framework (5 Whys, quantification)
- Research synthesis framework with confidence levels

**Enhanced System Prompt:**
- Elite research agent identity
- Damon's context with portfolio value
- Market sizing methodology
- Competitive intelligence gathering sources
- Research methodology checklists
- Output standards with confidence levels

**Web Search Capability:**
- Anthropic web_search tool enabled
- call_llm_with_search() function for live data
- Upgraded endpoints: /research, /niche, /competitors, /icp, /lead, /compare

**Bug Fix During Upgrade:**
- Issue: `can only concatenate str (not "NoneType") to str`
- Cause: Some web search response blocks have `text` attribute as None
- Fix: Added null check: `if hasattr(block, 'text') and block.text is not None`

**Deployment Note:** SCHOLAR container not in docker-compose.yml - runs standalone. Rebuild with:
```bash
cd /opt/leveredge/control-plane/agents/scholar
docker build -t n8n-scholar:latest .
docker stop scholar && docker rm scholar
docker run -d --name scholar --network control-plane-net -p 8018:8018 \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e EVENT_BUS_URL=http://event-bus:8099 \
  -e SUPABASE_URL=http://supabase-kong:8000 \
  -e SUPABASE_ANON_KEY="..." \
  n8n-scholar:latest
```

### 2026-01-16 21:35 - [CHIRON V2 Elite Business Mentor Upgrade]
**Upgrade:** CHIRON v1.0 → v2.0
**Container:** Rebuilt and deployed to control-plane-net

**New Endpoints (4):**
- `/sprint-plan` - ADHD-optimized sprint planning with time blocks
- `/pricing-help` - Value-based pricing strategy with ROI framing
- `/fear-check` - Rapid fear analysis with portfolio evidence
- `/weekly-review` - Structured accountability review

**New Frameworks (4):**
- `adhd` - ADHD Launch Framework (10 principles)
- `pricing` - Pricing Framework (10 principles)
- `sales` - Sales Framework (10 principles)
- `mvp` - MVP-to-Scale Framework (10 principles)

**Enhanced System Prompt:**
- Strategic frameworks: OODA Loop, Eisenhower Matrix, 10X Thinking, Inversion, First Principles
- ADHD-optimized patterns with procrastination decoder
- Pricing psychology (anchoring, three-tier, ROI framing)
- Sales psychology (Trust Equation, pain > features, objection reframes)
- Hyperfocus trap detection with immediate callouts
- Red flags section with specific responses

**Deployment Note:** CHIRON container not in docker-compose.yml - runs standalone. Rebuild with:
```bash
cd /opt/leveredge/control-plane/agents/chiron
docker build -t n8n-chiron:latest .
docker stop chiron && docker rm chiron
docker run -d --name chiron --network control-plane-net -p 8017:8017 \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e EVENT_BUS_URL=http://event-bus:8099 \
  -e SUPABASE_URL=http://supabase-kong:8000 \
  -e SUPABASE_ANON_KEY="..." \
  n8n-chiron:latest
```

### 2026-01-17 - [SCHOLAR Agent Built - CHIRON's Research Partner]
**Port:** 8018
**Container:** scholar (n8n-scholar:latest)
**Model:** Claude claude-sonnet-4-20250514
**Role:** Market Research
**Partner:** CHIRON (sends findings for strategic interpretation)
**Features:**
- Time-aware (knows days to launch: 44, current phase)
- Niche analysis with 6-criteria scoring framework
- ICP development framework
- Competitive intelligence
- Lead research
- Niche comparison side-by-side

**Endpoints:**
- /health, /time, /team - Standard status
- /research - General research (quick/standard/deep)
- /niche - Deep niche analysis with scoring
- /competitors - Competitive intelligence
- /icp - Ideal Customer Profile development
- /lead - Research specific company
- /compare - Compare multiple niches
- /send-to-chiron - Send findings to CHIRON
- /upgrade-self - Propose self-improvements

**Research Frameworks:**
- TAM/SAM/SOM market sizing
- 6-criteria niche scoring (Pain, Pay, Access, Competition, Expertise, Growth)
- ICP template with 8 sections
- Competitor profiles template

**Team Pattern:** Research -> SCHOLAR -> CHIRON -> Decision -> ARIA knowledge

### 2026-01-17 - [CHIRON Agent Built - Full Team Integration]
**Port:** 8017
**Container:** chiron (n8n-chiron:latest)
**Model:** Claude claude-sonnet-4-20250514
**Features:**
- Time-aware (knows days to launch: 44, current phase)
- Portfolio-aware (cites actual wins from aria_portfolio)
- Team-integrated (Event Bus, ARIA knowledge, HERMES notifications)
- Inter-agent communication capability
- Self-upgrade endpoint for proposing improvements

**Endpoints:**
- /health - Health + time context
- /time - Full time context
- /team - Agent roster
- /chat - General conversation with context
- /decide - Decision framework with scoring
- /accountability - Commitment tracking
- /challenge - Challenge assumptions with evidence
- /hype - Evidence-based motivation
- /framework/{type} - decision, accountability, strategic, fear, launch
- /upgrade-self - Propose self-improvements

**Integration:**
- Logs all decisions to aria_knowledge (ARIA sees everything)
- Publishes events to Event Bus
- Critical decisions notify HERMES -> Telegram
- Can call other agents via /agent/call

**First LLM Agent:** Template for future agents (SCHOLAR will be similar)

**Git Note:** AGENT-ROUTING.md committed. Chiron files need `sudo chown -R damon:damon /opt/leveredge/.git/objects` before commit (some root-owned directories).

### 2026-01-17 - [Pre-Compact Learning Rules]
**Added:** Rules #8 (pre-compact capture) and #9 (session handoff)
**Purpose:** Knowledge persists across Claude context windows
**Flow:** Work → Capture → Compact → Next session reads captures
**Locations:** LESSONS-SCRATCH.md, aria_knowledge, Git commits
**Triggers:** Context pressure, session end, major task complete, switching work areas

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
