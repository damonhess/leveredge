# LEVEREDGE AGENT ROUTING RULES

**MANDATORY: All operations flow through designated agents.**
**NO floating commands. NO bypassing agents.**

---

## Quick Reference

| Task | Agent | How |
|------|-------|-----|
| File read/write/create | HEPHAESTUS | MCP tool or API |
| Run commands | HEPHAESTUS | MCP tool (whitelisted) |
| Complex multi-step tasks | GSD (Claude Code) | /gsd spec |
| Backup before changes | CHRONOS | API call or GSD |
| Rollback/recovery | HADES | API call |
| Credential management | AEGIS | API call |
| Send notifications | HERMES | API call or Event Bus |
| Check monitoring/metrics | ARGUS | API call |
| Audit logs/anomalies | ALOY | API call |
| Generate documentation | ATHENA | API call |
| Business decisions/accountability/ADHD planning | CHIRON V2 | API call (LLM-powered) |
| Market research/niche analysis | SCHOLAR V2 | API call (LLM-powered + web search) |
| Update portfolio | GSD → Supabase + Event Bus | Notify ARIA |
| Update knowledge base | GSD → aria_knowledge + Event Bus | Notify ARIA |
| Emergency restore | GAIA | Manual trigger only |
| Workflow orchestration | ATLAS | Via control n8n |

---

## Detailed Routing Rules

### HEPHAESTUS (Builder) - Port 8011
**Use for:**
- Reading files in /opt/leveredge/
- Creating/editing files
- Listing directories
- Git operations (status, log, diff, commit)
- Docker ps, docker logs
- Simple whitelisted commands

**DO NOT use for:**
- SQL/database operations → GSD
- HTTP requests to external services → GSD
- Complex multi-step tasks → GSD
- Credential values → AEGIS

**Claude Web Access:** ✅ Via MCP
**Claude Code Access:** ✅ Direct + MCP

---

### GSD (Claude Code)
**Use for:**
- Database operations (Supabase, PostgreSQL)
- Complex multi-step tasks
- HTTP requests
- Container exec operations
- Anything requiring full server access
- Tasks that need human-in-loop approval

**Format:** Always as copy-paste `/gsd` block with clear spec

**Claude Web Access:** ❌ (creates spec, user runs)
**Claude Code Access:** ✅ Direct execution

---

### CHRONOS (Backup) - Port 8010
**Use for:**
- Pre-change backups (ALWAYS before destructive ops)
- Scheduled backup verification
- Backup listing and status
- Restore point creation

**Trigger:**
```bash
curl -X POST http://localhost:8010/backup \
  -H "Content-Type: application/json" \
  -d '{"type": "pre-deploy", "component": "name"}'
```

**MANDATORY:** Call CHRONOS before:
- Database migrations
- Workflow changes
- Container modifications
- File deletions

---

### HADES (Rollback) - Port 8008
**Use for:**
- Rolling back failed deployments
- Restoring from CHRONOS backups
- Emergency recovery
- Version rollback in n8n

**Trigger:**
```bash
curl -X POST http://localhost:8008/rollback \
  -H "Content-Type: application/json" \
  -d '{"backup_id": "xxx", "component": "name"}'
```

---

### AEGIS (Credentials) - Port 8012
**Use for:**
- Creating credentials in n8n
- Syncing credential inventory
- Tracking expiration
- Rotation reminders
- Credential audits

**NEVER:**
- Log credential values
- Expose secrets in responses
- Bypass AEGIS for credential ops

**Trigger:**
```bash
# Sync credentials
curl -X POST http://localhost:8012/sync

# List credentials
curl http://localhost:8012/credentials

# Audit
curl http://localhost:8012/audit
```

---

### HERMES (Notifications) - Port 8014
**Use for:**
- Telegram notifications
- Event Bus publishing
- Alert routing
- Multi-channel notifications

**Trigger:**
```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{"channel": "telegram", "message": "text", "priority": "normal"}'
```

**Event Bus:**
```bash
curl -X POST http://localhost:8099/publish \
  -H "Content-Type: application/json" \
  -d '{"event": "type", "data": {...}}'
```

---

### ARGUS (Monitoring) - Port 8016
**Use for:**
- System health checks
- Prometheus metrics
- Container status
- Resource monitoring

**Trigger:**
```bash
curl http://localhost:8016/health
curl http://localhost:8016/metrics
```

---

### ALOY (Audit) - Port 8015
**Use for:**
- Audit log queries
- Anomaly detection
- Activity history
- Compliance checks

**Trigger:**
```bash
curl http://localhost:8015/logs?since=1h
curl http://localhost:8015/anomalies
```

---

### ATHENA (Documentation) - Port 8013
**Use for:**
- Auto-generating docs from code
- Updating README files
- Creating API documentation
- Changelog generation

**Trigger:**
```bash
curl -X POST http://localhost:8013/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "readme", "path": "/opt/leveredge/"}'
```

---

### CHIRON V2 (Elite Business Mentor) - Port 8017
**Use for:**
- Strategic business decisions with embedded frameworks
- ADHD-optimized sprint planning
- Pricing strategy and value-based pricing
- Rapid fear analysis and reframing
- Weekly accountability reviews
- Pushing through procrastination with evidence
- Sales psychology and objection handling

**V2 Capabilities:**
- OODA Loop, Eisenhower Matrix, 10X Thinking, Inversion, First Principles
- ADHD Launch Framework with procrastination decoding
- Pricing psychology (anchoring, three-tier, ROI framing)
- Sales psychology (Trust Equation, pain > features, objection reframes)
- Hyperfocus trap detection

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health + time context |
| /time | GET | Current time awareness |
| /team | GET | Agent roster |
| /chat | POST | General conversation |
| /decide | POST | Decision framework |
| /accountability | POST | Accountability check |
| /challenge | POST | Challenge assumptions |
| /hype | POST | Evidence-based motivation |
| /framework/{type} | GET | Get frameworks (decision, accountability, strategic, fear, launch, adhd, pricing, sales, mvp) |
| /agent/call | POST | Call other agents |
| /upgrade-self | POST | Propose self-improvements |
| /sprint-plan | POST | **V2** ADHD-optimized sprint planning |
| /pricing-help | POST | **V2** Value-based pricing strategy |
| /fear-check | POST | **V2** Rapid fear analysis and reframe |
| /weekly-review | POST | **V2** Structured accountability review |

**Team Integration:**
- Time-aware (days to launch, current phase)
- Portfolio-aware (cites actual wins as evidence)
- Event Bus integration
- ARIA knowledge updates
- HERMES notifications (critical decisions)
- Inter-agent communication

**Trigger Example:**
```bash
# Create ADHD-optimized sprint plan
curl -X POST http://localhost:8017/sprint-plan \
  -H "Content-Type: application/json" \
  -d '{"goals": ["10 outreach messages", "1 demo call"], "time_available": "this weekend", "energy_level": "high"}'

# Get pricing strategy
curl -X POST http://localhost:8017/pricing-help \
  -H "Content-Type: application/json" \
  -d '{"service_description": "Compliance workflow automation", "value_delivered": "Saves 20 hours/month"}'

# Rapid fear check
curl -X POST http://localhost:8017/fear-check \
  -H "Content-Type: application/json" \
  -d '{"situation": "About to send cold outreach", "what_im_avoiding": "rejection"}'

# Weekly review
curl -X POST http://localhost:8017/weekly-review \
  -H "Content-Type: application/json" \
  -d '{"wins": ["Built 2 agents", "1 demo call"], "losses": ["Missed outreach target"]}'

# Get accountability check
curl -X POST http://localhost:8017/accountability \
  -H "Content-Type: application/json" \
  -d '{"commitment": "10 outreach messages", "deadline": "2026-01-17 5PM"}'

# Challenge a belief
curl -X POST http://localhost:8017/challenge \
  -H "Content-Type: application/json" \
  -d '{"assumption": "I need more features before outreach"}'

# Get hype boost
curl -X POST http://localhost:8017/hype

# Get ADHD framework
curl http://localhost:8017/framework/adhd
```

---

### SCHOLAR V2 (Elite Market Research) - Port 8018
**Use for:**
- Deep market research with web search (live data)
- TAM/SAM/SOM market sizing with sources
- Structured competitor profiling
- Niche analysis and evaluation
- ICP (Ideal Customer Profile) development
- Lead/prospect research
- Pain point discovery and quantification
- Business assumption validation
- Niche comparison

**V2 Capabilities:**
- Live web search via Anthropic web_search tool
- TAM/SAM/SOM market sizing framework
- Competitive analysis framework with structured profiles
- ICP development framework
- Pain point discovery framework (5 Whys, quantification)
- Research synthesis framework with confidence levels

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health + time context + V2 status |
| /time | GET | Current time awareness |
| /team | GET | Agent roster |
| /research | POST | General research (web search for standard/deep) |
| /niche | POST | Deep niche analysis with web search |
| /competitors | POST | Competitive intelligence with web search |
| /icp | POST | Develop Ideal Customer Profile with web search |
| /lead | POST | Research specific company with web search |
| /compare | POST | Compare multiple niches with web search |
| /send-to-chiron | POST | Send findings to CHIRON |
| /upgrade-self | POST | Propose self-improvements |
| /deep-research | POST | **V2** Multi-source deep dive with web search |
| /competitor-profile | POST | **V2** Structured competitor analysis |
| /market-size | POST | **V2** TAM/SAM/SOM calculation with sources |
| /pain-discovery | POST | **V2** Research and quantify pain points |
| /validate-assumption | POST | **V2** Test business assumptions with evidence |

**Team Integration:**
- Time-aware (days to launch, current phase)
- Partners with CHIRON for strategy
- Event Bus integration
- ARIA knowledge updates
- HERMES notifications

**Partner Relationship:**
- SCHOLAR does research with web search -> sends to CHIRON
- CHIRON interprets strategically -> makes decision
- Both log to ARIA knowledge

**Trigger Example:**
```bash
# Deep research with web search
curl -X POST http://localhost:8018/deep-research \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 compliance automation software companies in 2025-2026?"}'

# Competitor profiling
curl -X POST http://localhost:8018/competitor-profile \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Hyperproof", "website": "https://hyperproof.io"}'

# Market sizing
curl -X POST http://localhost:8018/market-size \
  -H "Content-Type: application/json" \
  -d '{"market": "compliance automation software", "geography": "United States", "segment": "water utilities"}'

# Pain discovery
curl -X POST http://localhost:8018/pain-discovery \
  -H "Content-Type: application/json" \
  -d '{"role": "Compliance Officer", "industry": "water utilities"}'

# Validate assumption
curl -X POST http://localhost:8018/validate-assumption \
  -H "Content-Type: application/json" \
  -d '{"assumption": "Water utilities spend over $50K/year on compliance software", "importance": "high"}'

# Niche comparison (upgraded)
curl -X POST http://localhost:8018/compare \
  -H "Content-Type: application/json" \
  -d '{"niches": ["water utilities", "environmental permits", "municipal government"]}'
```

---

### GAIA (Emergency) - Port 8000
**Use for:**
- Complete system rebuild
- Disaster recovery
- Bootstrap from nothing

**NEVER trigger automatically. Human decision only.**

---

### ATLAS (Orchestrator) - Control n8n
**Use for:**
- Complex workflow chains
- Multi-agent coordination
- Request routing

**Access:** Via control.n8n.leveredgeai.com

---

## ARIA Knowledge Updates

**ARIA must be informed of:**
- Every portfolio update
- Every major deployment
- Every agent status change
- Every system event

**Mechanism:** Event Bus + aria_knowledge table

### Adding Knowledge
```sql
SELECT aria_add_knowledge(
  'category',      -- agent, deployment, decision, lesson, project, event
  'Title',
  'Content description',
  'subcategory',   -- optional
  '{}',            -- metadata JSON
  'source',        -- claude_web, gsd, agent_name
  'importance'     -- critical, high, normal, low
);
```

### Searching Knowledge
```sql
SELECT * FROM aria_search_knowledge('query text', 'category', 10);
```

### Getting Recent Knowledge
```sql
SELECT * FROM aria_get_recent_knowledge('category', 20);
```

### System Status Overview
```sql
SELECT * FROM aria_get_system_status();
```

---

## Knowledge Persistence Flow

```
Work Session
    ↓
Discoveries/Learnings
    ↓
┌─────────────────────────────────────┐
│ LESSONS-SCRATCH.md (quick capture)  │
│ aria_knowledge (ARIA awareness)     │
│ Git commit (file changes)           │
└─────────────────────────────────────┘
    ↓
Context Compacts/Clears
    ↓
New Session Reads:
- LESSONS-LEARNED.md (consolidated)
- aria_knowledge (queryable)
- LOOSE-ENDS.md (current state)
    ↓
Continuity Preserved ✓
```

Periodic consolidation: LESSONS-SCRATCH.md → LESSONS-LEARNED.md
