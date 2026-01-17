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

### 2026-01-17 00:10 - [ARIA → OLYMPUS Integration]
**Status:** Deployed and verified in DEV
**Scope:** DEV ARIA workflow (aX8d9zWniCYaIDwc)

**Added Nodes:**
- `Pre-Router` - Code node that detects chain/agent patterns
- `Route Switch` - Routes to SENTINEL or AI Agent
- `SENTINEL Orchestrate` - HTTP Request to SENTINEL at 8019
- `Format Orchestration Response` - Formats multi-agent results

**Workflow Path:**
```
Webhook → Extract Input → Fetch Portfolio → SHIELD
    ↓
Pre-Router (pattern detection)
    ↓
Route Switch
    ├── SENTINEL path: SENTINEL Orchestrate → Format Orchestration Response → Format Response
    └── ARIA path: AI Agent → SWORD → Format Response
    ↓
Respond to Webhook
```

**Pattern Detection:**
- Chain patterns: "research X then plan Y" → research-and-plan chain
- CHIRON patterns: "hype me", "sprint plan", "pricing" → single CHIRON call
- SCHOLAR patterns: "research", "competitors", "market size" → single SCHOLAR call
- Default: ARIA handles normally

**Critical n8n Lessons:**

1. **activeVersionId vs versionId:**
   - `workflow_entity.versionId` = current draft version
   - `workflow_entity.activeVersionId` = version running in production
   - Direct SQL updates must update BOTH AND the workflow_history entry
   - n8n loads from activeVersionId, not versionId

2. **Switch v3 node format:**
   ```javascript
   {
     "rules": {
       "values": [
         {
           "conditions": {
             "options": {"caseSensitive": true, "typeValidation": "loose"},
             "combinator": "and",
             "conditions": [{"leftValue": "...", "rightValue": "...", "operator": {...}}]
           },
           "renameOutput": true,
           "outputKey": "SENTINEL"
         }
       ]
     },
     "options": {"fallbackOutput": "extra"}
   }
   ```
   NOT: `rules.rules` (causes "Could not find property option" error)

3. **Merge node limitations:**
   - `chooseBranch` mode waits for BOTH inputs
   - For conditional paths, connect directly to shared node
   - Use $json for incoming data, not $('NodeName') references

4. **$json vs $('NodeName'):**
   - Use `$json` when data comes from different paths
   - `$('NodeName')` fails if that node didn't execute in current path

**SENTINEL Fix:**
```python
# Before (fails when steps is None)
steps = intent.get("steps", [])

# After (handles None explicitly)
steps = intent.get("steps") or []
```

**Test Commands:**
```bash
# Test SENTINEL path (hype)
curl -X POST http://localhost:5680/webhook/assistant -H "Content-Type: application/json" -d '{"message": "hype me up"}'

# Test chain pattern
curl -X POST http://localhost:5680/webhook/assistant -H "Content-Type: application/json" -d '{"message": "research compliance automation then make me a plan"}'

# Test ARIA path (default)
curl -X POST http://localhost:5680/webhook/assistant -H "Content-Type: application/json" -d '{"message": "what time is it?"}'
```

**Success Criteria Met:**
- ✅ Pre-Router correctly detects chain patterns
- ✅ Pre-Router correctly detects single agent patterns
- ✅ Switch routes to SENTINEL vs ARIA correctly
- ✅ SENTINEL HTTP request succeeds
- ✅ Response formatter handles single agent results
- ✅ Response formatter handles chain results (2 steps)
- ✅ Default messages still handled by ARIA
- ✅ Cost and timing displayed in footer

**UPDATE: Pre-Router made less aggressive (2026-01-17 00:20)**

Original design routed too much to SENTINEL, bypassing ARIA's own capabilities.

**Now routes to SENTINEL only for:**
- Explicit agent requests: "ask CHIRON", "hey SCHOLAR"
- Multi-step chains: "research X then plan Y"
- Deep research needing web search/citations

**ARIA handles herself:**
- Motivation, hype (her HYPE mode)
- Fear/anxiety (her COACH mode + CBT tool)
- General strategy, pricing discussions
- Everything conversational

This preserves ARIA's personality and relationship while using agents for their specialized capabilities.

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

### 2026-01-17 00:35 - [HEPHAESTUS → OLYMPUS Bridge]
**Scope:** MCP server orchestration tools for Claude Web
**Changes:**
- Added `orchestrate` MCP tool with chain_name OR agent+action support
- Added `list_chains` and `list_agents` helper tools
- Routes through SENTINEL (8019) with automatic fallback to ATLAS (8007)
- Formats response for Claude Web consumption

**New Environment Variables:**
- `SENTINEL_URL` (default: http://sentinel:8019)
- `ATLAS_URL` (default: http://atlas:8007)

**Usage Pattern:**
```python
# Chain execution
{"chain_name": "research-and-plan", "input": {"topic": "compliance automation"}}

# Single agent call
{"agent": "chiron", "action": "chat", "params": {"message": "..."}}
```

**Key Lesson:** HEPHAESTUS is MCP server (not FastAPI), so spec endpoints become MCP tools instead. Same logic, different interface.

---

*Add new entries above this line*

### 2026-01-17 01:10 - [VARYS Mission Guardian]
**Status:** Deployed and running
**Components:** FastAPI agent (port 8020), n8n scheduler workflow

**What Was Built:**
- VARYS agent: Mission guardian with drift detection
- Sacred texts: /opt/leveredge/mission/ with MISSION, LAUNCH-DATE, REVENUE-GOAL, BOUNDARIES, PORTFOLIO-TARGET
- n8n workflow: VARYS Scheduler (daily briefs 6 AM, weekly reviews Sunday 8 PM)
- Agent registry entry added to config/agent-registry.yaml

**Key Endpoints:**
- `/health` - Health check
- `/days-to-launch` - 42 days remaining (HIGH urgency)
- `/todays-focus` - Extract focus from MASTER-LAUNCH-CALENDAR
- `/scan-drift` - Detect scope creep in git commits
- `/validate-decision` - Check decisions against mission alignment
- `/daily-brief` - Generate daily accountability brief (sends via HERMES)
- `/weekly-review` - Comprehensive weekly review (triggers CHIRON)
- `/mission/{doc}` - Retrieve sacred mission documents

**Drift Detection Patterns:**
- "quick (addition|fix|change)"
- "small (enhancement|tweak|update)"
- "while we're at it", "one more thing", "might as well"
- "real quick", "shouldn't take long", "just need to add"

**Integrations:**
- HERMES for notifications
- CHIRON for weekly reviews
- Event Bus for logging
- n8n scheduler for automation

**Container:** varys on control-plane-net, volumes /opt/leveredge readonly

### 2026-01-17 01:44 - [ARIA Life Coaching Tools - Phase 1]
**Status:** Deployed to DEV
**Components:** 12 database tables, 4 n8n workflow tools, ARIA integration

**What Was Built:**
- Database schema: 12 coaching tables (aria_wheel_of_life, aria_values, aria_goals, aria_daily_checkins, aria_grow_sessions, aria_habits, aria_habit_completions, aria_decisions, aria_resistance_patterns, aria_commitments, aria_coaching_sessions, aria_tool_analytics)
- Helper functions: aria_record_tool_usage, aria_get_latest_wheel, aria_compare_wheels, aria_goal_stats, aria_habit_streak, aria_complete_habit, aria_check_commitments, aria_checkin_patterns
- n8n workflows: 17 - Wheel of Life, 18 - Values Clarifier, 19 - Progress Tracker, 20 - Goal Architect
- ARIA integration: Tools connected to AI Agent, system prompt updated

**Tools Implemented:**
1. **wheel_of_life**: Assess life balance across 8 dimensions with trend tracking
2. **values_clarifier**: Identify, rank, and check alignment of core values
3. **progress_tracker**: Daily check-ins with pattern analysis
4. **goal_architect**: Transform vague goals into SMART goals with DARN-C motivation scoring

**Key Database Functions:**
- `aria_get_latest_wheel(user_id)` - Get most recent wheel assessment
- `aria_compare_wheels(user_id)` - Compare current vs previous assessment
- `aria_checkin_patterns(user_id, days)` - Analyze mood/energy trends
- `aria_goal_stats(user_id)` - Goal completion statistics

**Technical Notes:**
- Tools added to ARIA workflow via direct database update (nodes + connections)
- n8n workflow import script created: data-plane/dev/n8n/workflows-to-import/import-v2.sh
- All tables in postgres_dev (supabase), workflows in n8n_dev

**Remaining Phases (Not Yet Built):**
- Phase 2: grow_session, habit_designer, energy_optimizer, decision_accelerator, resistance_decoder
- Phase 3: coaching_insights, system_architect, identity_shifter

### 2026-01-17 02:57 - [ARIA Coaching Tools - Tier 2]
**Status:** Deployed to DEV
**Scope:** DEV n8n workflows + ARIA AI Agent

**Tier 2 Tools Added:**
1. **grow_session** (21 - GROW Session) - GROW model coaching (Goal → Reality → Options → Will)
2. **habit_designer** (22 - Habit Designer) - Habit stacking, cue-routine-reward loops, 2-minute rule
3. **energy_optimizer** (23 - Energy Optimizer) - Energy pattern mapping, ADHD support, optimal task matching
4. **decision_accelerator** (24 - Decision Accelerator) - OODA Loop, Eisenhower Matrix, 10-10-10, Regret Minimization
5. **resistance_decoder** (25 - Resistance Decoder) - Procrastination root cause analysis (fear, overwhelm, perfectionism, boredom)

**Database Tables Created:**
- aria_wheel_of_life, aria_values, aria_daily_checkins, aria_goals (Tier 1)
- aria_grow_sessions, aria_habits, aria_habit_completions (Tier 2)
- aria_energy_logs, aria_decisions, aria_resistance_patterns (Tier 2)
- aria_commitments, aria_coaching_sessions, aria_tool_analytics (Shared)

**Helper Functions:**
- aria_get_latest_wheel() - Get most recent wheel of life assessment
- aria_compare_wheels() - Compare current vs previous assessments
- aria_record_tool_usage() - Track tool usage analytics

**Lesson Learned:**
- n8n import:workflow command requires workflow ID field, otherwise fails with FK constraint
- Direct SQL inserts work better than n8n CLI for bulk workflow imports
- Tool nodes use @n8n/n8n-nodes-langchain.toolWorkflow type with ai_tool connection

**Trigger Phrases:**
- grow_session: "coach me", "I'm stuck", "help me figure out"
- habit_designer: "build a habit", "be more consistent", "daily routine"
- energy_optimizer: "I'm tired", "no energy", "when am I most productive"
- decision_accelerator: "I can't decide", "I'm torn between", "should I"
- resistance_decoder: "I should probably", "I'll get to it later", "I don't feel like"

### 2026-01-17 - [ARIA Async Multitasking]
**Built:** Complete async task system with privacy controls

**Components:**
1. Database:
   - `aria_async_tasks` - Task storage with privacy fields
   - `aria_task_progress` - Step-by-step progress tracking
   - `aria_cleanup_tasks()` - Auto-delete function
   
2. n8n Workflows (DEV):
   - `30 - Task Dispatcher` (task-dispatcher-001) - Privacy detection + all CRUD operations
   - `31 - Task Listener` (task-listener-001) - Event Bus subscriber for task lifecycle
   - `32 - Task Cleanup Scheduler` (task-cleanup-001) - Hourly cleanup job
   
3. ARIA Tools (7 new):
   - `dispatch_task` - Background task dispatch with privacy options
   - `check_tasks` - Status check with include_private flag
   - `get_task_result` - Retrieve completed task output
   - `delete_task` - Permanent task deletion
   - `get_task_privacy` - Check privacy settings
   - `set_task_privacy` - Modify privacy level
   - `clear_task_history` - Bulk delete old tasks

**Privacy Levels:**
- 📊 Normal: Saved, Telegram notifications OK
- 🔒 Private: Hidden from history, no external notifications
- 💨 Ephemeral: Auto-delete after delivery

**Auto-Detection:** Sensitive patterns (salary, health, legal, financial) auto-upgrade to private

**Key Patterns:**
- Privacy detection uses regex patterns in Code node
- Tasks connect to AI Agent via ai_tool connections
- Event Bus integration for task lifecycle events
- Delete_at column enables scheduled deletion


### 2026-01-17 07:20 - [Unified Memory Elite - Complete Implementation]
**Status:** COMPLETE - All core components working in DEV

**What Was Built:**
1. **Unified Memory V2 Schema** - Full schema with embeddings, source tracking, confidence decay
2. **Memory Functions** - aria_store_memory, aria_search_memory, aria_hybrid_search_memory, aria_find_conflicts, aria_merge_memories, aria_decay_confidence
3. **Memory Service** - Python service at `/home/damon/environments/dev/aria-threading/services/memory_service.py`
4. **Context Assembler Elite** - Combines recent messages + unified memory + semantic chunks + async tasks
5. **REST API Endpoints** - /memory/store, /memory/search, /memory/update, /memory/forget, /memory/list, /memory/stats, /memory/duplicates, /memory/merge, /memory/decay, /context/elite

**Key Implementation Details:**
- Memory embeddings use OpenAI text-embedding-ada-002 (1536 dimensions)
- PostgreSQL pgvector with IVFFlat index for efficient similarity search
- Source tracking: every memory knows where it came from (conversation, task, manual)
- Conflict detection: automatically finds similar memories when storing new ones
- Budget-based context assembly: allocates tokens across sources (45% recent, 30% memory, 15% semantic, 10% tasks)

**API Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /memory/store | POST | Store memory with auto-embedding |
| /memory/search | POST | Semantic search |
| /memory/list | GET | List by type/category |
| /memory/stats | GET | Memory statistics |
| /memory/forget/{id} | POST | Soft delete |
| /context/elite | POST | Assemble context from all sources |

**Gotchas Found:**
1. **OpenAI key loading**: When running via nohup, env vars don't pass properly. Added fallback to load from .env file in embedding_service.py
2. **aria_memory_stats GROUP BY error**: Original function used "GROUP BY TRUE" which PostgreSQL rejected. Fixed with subqueries.
3. **aria_messages missing columns**: Added token_count, input_tokens, output_tokens columns

**Testing Commands:**
```bash
# Store a memory
curl -X POST http://localhost:8113/memory/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "memory_type": "fact", "category": "test"}'

# Search memories
curl -X POST http://localhost:8113/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is LeverEdge?", "limit": 5}'

# Get elite context
curl -X POST http://localhost:8113/context/elite \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about the project"}'
```

**Files Created/Modified:**
- `/home/damon/environments/dev/aria-threading/schema/001-unified-memory-elite.sql` - Complete schema
- `/home/damon/environments/dev/aria-threading/services/memory_service.py` - New service
- `/home/damon/environments/dev/aria-threading/services/context_assembler.py` - Added elite context
- `/home/damon/environments/dev/aria-threading/services/embedding_service.py` - Added .env fallback
- `/home/damon/environments/dev/aria-threading/api.py` - Added memory endpoints

**Still TODO (Future):**
- n8n workflows: 33-Task Result Extractor, 34-Memory Consolidation
- Automatic memory extraction after conversation turns
- Event Bus integration for memory events
- Privacy enforcement across interfaces

### 2026-01-17 06:45 - [aria-threading Database Connectivity Fix]
**Symptom:** `socket.gaierror: [Errno -3] Temporary failure in name resolution`
**Cause:** aria-threading running on host tried to connect to `supabase-db` hostname (Docker internal DNS). Host system can't resolve Docker container hostnames.

**Solution:** Option B - Expose PostgreSQL port to localhost only
1. Added `ports: ["127.0.0.1:54322:5432"]` to supabase-db service in docker-compose.yml
2. Updated aria-threading .env, run.sh, and systemd service to use `127.0.0.1:54322`
3. Password must be URL-encoded in connection string (+ → %2B, / → %2F)

**Why This Approach:**
- Simple and production-reliable
- Secure: only localhost can access (127.0.0.1 binding)
- Compatible with systemd service model
- No need to containerize Python service
- Standard pattern for host-to-container DB access

**Key Files Changed:**
- `/opt/leveredge/data-plane/prod/supabase/docker-compose.yml` - Added ports section to db service
- `/home/damon/environments/dev/aria-threading/.env` - Updated DATABASE_URL
- `/home/damon/environments/dev/aria-threading/run.sh` - Updated default DATABASE_URL
- `/home/damon/environments/dev/aria-threading/aria-threading.service` - Updated systemd env (note: %% escaping for systemd)

**URL Encoding Gotcha:** asyncpg parses DSN as URL, so special characters in password need URL encoding. Raw password fails with cryptic port parsing errors.

**Verification Commands:**
```bash
# Check port binding
ss -tlnp | grep 54322
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep supabase-db

# Test connection
python3 -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('postgresql://postgres:i%2BNKWrdGrBsHu2n%2FLGzNMY84Avry2RhNOY2QYksldLtX7GEuxdyASrpv3n0IRinS@127.0.0.1:54322/postgres_dev'))"
```

### 2026-01-17 05:30 - [ARIA Unified Threading]
**Status:** Database schema deployed to DEV Supabase
**Scope:** Unified conversation stream with semantic retrieval

**Key Design Decisions:**
1. **Extend, don't replace**: Existing aria_conversations/aria_messages tables extended with chunk_id, sequence_num, threading_settings
2. **Unified stream via session_id**: Uses 'unified-{user_id}' session pattern for ONE stream per user
3. **Chunk embeddings separate table**: aria_chunk_embeddings keeps vector storage efficient and allows cascade deletes
4. **Column naming in RETURNS TABLE**: PostgreSQL function returns can conflict with column names - use aliases like `conv_id` instead of `conversation_id`

**Function Gotchas:**
- Return type NUMERIC vs DOUBLE PRECISION for EXTRACT() results
- Column name ambiguity in PL/pgSQL: Use table aliases (m.conversation_id, c.conversation_id)
- BIGINT vs INT: COUNT(*) returns BIGINT, need explicit cast

**Database Connectivity:**
- Supabase DB in Docker: Connect via container network (supabase-db:5432), not localhost
- No external port exposed - use docker exec for CLI testing
- Python service needs to run on same Docker network or expose port

**Service Architecture:**
- Port 8113 for aria-threading API
- Follows aria-reminders pattern (FastAPI + asyncpg)
- Tools endpoint format matches n8n HTTP Request node expectations

### 2026-01-17 07:45 - [ARIA Integration Validation]
**Context:** Validated all ARIA systems work together after January 2026 upgrades
**Status:** Complete - all smoke tests pass

**Components Validated:**
- Unified Memory Elite (port 8113): ✓ store, search, update, forget working
- Async Tasks: ✓ Table created, privacy controls in place
- Coaching tools (17-28): ✓ Already imported
- Task Dispatcher (30): ✓ Active with privacy detection
- Task Listener (31), Cleanup (32): ✓ Active
- NEW Task Result Extractor (33): Extracts memories from completed tasks
- NEW Memory Consolidation Engine (34): Daily dedup/decay at 3 AM

**Key Additions:**
1. `/health/full` endpoint in aria-threading - comprehensive health check
2. ARIA system prompt updated with 33+ tools and routing guide
3. update_memory and forget_memory tools added
4. VARYS daily brief now includes ARIA health status
5. aria_unified_memory got privacy_level, category, keywords columns

**Discovery:** The aria_async_tasks table didn't exist. Created with full schema including privacy controls from spec.

**Pattern:** When validating integrations, check that database tables actually exist - the workflows reference tables that may not have been created yet.


### 2026-01-17 08:15 - Supabase Isolation Migration
**Context:** DEV and PROD Supabase shared a single postgres container (supabase-db) with two databases (postgres, postgres_dev). This was fragile.

**Solution:** Created fully isolated environments:
- PROD: supabase-db-prod (port 54322) with postgres database
- DEV: supabase-db-dev (port 54323) with postgres database

**Key Steps:**
1. Backup both databases before migration
2. Update PROD docker-compose to rename db container to supabase-db-prod
3. Create new DEV docker-compose with its own db container (supabase-db-dev)
4. PROD uses existing volume (data preserved), DEV uses new volume (data restored from backup)
5. Update aria-threading systemd to use DEV postgres (54323)
6. Sync schemas between environments using pg_dump

**Gotchas:**
- Supabase storage-api migration can fail if old functions exist (storage.foldername) - drop with CASCADE
- Realtime DB_ENC_KEY must be exactly 16 bytes for AES-128
- postgres-meta container healthcheck needs node (no curl/wget available)
- n8n credentials are encrypted - update via UI, not database

**New Tools:**
- /opt/leveredge/shared/scripts/promote-schema.sh - Compare and promote schemas DEV→PROD

**Prevention:** Always use isolated environments from the start. Never share database containers between environments.

### 2026-01-17 08:15 - [ATLAS Parallel Execution]
**Context:** Built parallel batch execution for ATLAS
**Discovery:** 
- Semaphore-based concurrency control works well for limiting parallel API calls
- In-memory batch storage is sufficient for tracking (100 batch limit with LRU eviction)
- Event Bus integration enables ARIA awareness of batch progress
- Different Docker networks can block agent-to-agent communication

**Implementation Notes:**
- BatchTask dataclass tracks individual task status/results
- Batch dataclass aggregates stats (completed_count, failed_count, progress_percent)
- BatchExecutor uses asyncio.Semaphore for concurrency limiting
- BackgroundTasks for non-blocking batch execution
- Optional webhook callback for completion notification

**Testing Note:** When testing parallel execution, ensure agents (SCHOLAR, CHIRON) are on same Docker network as ATLAS. Different networks = HTTP timeouts.

