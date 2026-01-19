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
| **Creative content projects** | MUSE (8030) | Orchestrates creative fleet |
| **Writing/copy** | QUILL (8031) | Articles, scripts, social |
| **Design/presentations** | STAGE (8032) | Slides, charts, landing pages |
| **Media production** | REEL (8033) | Images, video, voiceover |
| **Content review/QA** | CRITIC (8034) | Brand compliance, fact-check |
| **Security gateway** | CERBERUS (8025) | Auth, rate limiting |
| **External PM/Projects** | CONSUL (8021) | Client projects, methodology |
| **Fitness guidance** | GYM-COACH (8110) | Workouts, progress |
| **Nutrition advice** | NUTRITIONIST (8101) | Diet, macros |
| **Meal planning** | MEAL-PLANNER (8102) | Recipes, grocery lists |
| **Learning paths** | ACADEMIC-GUIDE (8103) | Study planning |
| **Relationship advice** | EROS (8104) | Dating, communication |
| **Project management** | MAGNUS (8200) | Universal PM |
| **Knowledge ingestion** | LCIS-LIBRARIAN (8050) | Lessons, rules, playbooks |
| **Pre-action consultation** | LCIS-ORACLE (8052) | Rule checking, guidance |
| **Workflow building** | DAEDALUS (8202) | Automation design |
| **Legal guidance** | THEMIS (8203) | Contracts, compliance |
| **Business mentorship** | MENTOR (8204) | Career, leadership |
| **Professional coordination** | STEWARD (8220) | Meetings, advisors, action items |
| **Portfolio tracking** | MIDAS (8205) | Stocks, ETFs |
| **Crypto tracking** | SATOSHI (8206) | Wallets, DeFi |
| **Financial analysis** | PLUTUS (8207) | Budgets, ROI |
| **Cloud architecture** | ATLAS-INFRA (8208) | Scaling, costs |
| **Current events** | IRIS (8209) | News, trends |
| **Voice interface** | VOICE (8051) | Speech-to-text, TTS |
| **API gateway** | GATEWAY (8070) | Rate limiting, routing |
| **Memory consolidation** | MEMORY-V2 (8066) | Cross-conversation facts |
| **Manipulation detection** | SHIELD-SWORD (8067) | Influence patterns |
| **Agent status** | Fleet Dashboard (8060) | Health monitoring |
| **Cost tracking** | Cost Dashboard (8061) | LLM usage/costs |
| **Council meetings** | CONVENER (8300) | Multi-agent collaborative discussions |
| **Meeting transcription** | SCRIBE (8301) | Notes, summaries, action items |

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

### CONSUL (External Project Manager) - Port 8021
**Use for:**
- Client project management
- External PM tool integration (Leantime, OpenProject)
- Project methodology tracking
- Resource allocation
- Deliverable tracking

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health check |
| /projects | GET | List all projects |
| /projects/create | POST | Create new project |
| /projects/{id} | GET | Get project details |
| /projects/{id}/sync | POST | Sync with external PM |
| /connections | GET | List PM system connections |

**Team Integration:**
- Partners with VARYS (internal) for LeverEdge work
- Partners with CHIRON for strategic decisions
- Syncs with external PM tools (Leantime, OpenProject)
- Reports to Council for major decisions

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

## ALCHEMY CREATIVE FLEET (Content Production)

### MUSE (Creative Director) - Port 8030
**Use for:**
- Project coordination and task decomposition
- Storyboarding and workflow management
- Orchestrating other creative agents
- Creative brief definition

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /projects/create | POST | Create new creative project |
| /projects/{id} | GET | Get project status |
| /storyboard | POST | Create video storyboard |
| /fleet | GET | List creative fleet capabilities |

### QUILL (Writer) - Port 8031
**Use for:**
- Long-form content (articles, case studies, reports)
- Short-form copy (headlines, taglines, CTAs)
- Video scripts and slide decks
- Social media posts

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /write | POST | Generate content by type |
| /script/video | POST | Generate video script with scenes |
| /rewrite | POST | Revise content based on feedback |

### STAGE (Designer) - Port 8032
**Use for:**
- Presentation design (PowerPoint)
- Chart/graph generation
- Thumbnail creation
- Landing page design (Tailwind CSS)
- UI component generation
- Wireframe creation
- Website templates

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /design/presentation | POST | Create branded presentation |
| /design/chart | POST | Generate chart/graph |
| /design/thumbnail | POST | Create thumbnail |
| /design/landing-page | POST | Generate landing page HTML |
| /design/ui-component | POST | Generate UI component |
| /design/wireframe | POST | Generate wireframe mockup |
| /design/website-template | POST | Generate multi-page website |

### REEL (Media Producer) - Port 8033
**Use for:**
- AI image generation (DALL-E 3)
- Video production pipeline
- Voice synthesis (ElevenLabs)
- Stock footage/photo sourcing

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /generate/image | POST | Generate AI image |
| /generate/video | POST | Full video production |
| /generate/voiceover | POST | Generate voiceover |
| /source/stock | POST | Find stock assets |

### CRITIC (Reviewer) - Port 8034
**Use for:**
- Brand compliance checking
- Quality assurance
- Fact-checking via SCHOLAR
- Video quality review
- Accessibility checks

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /review | POST | Review any content type |
| /review/video | POST | Review video quality |
| /review/text | POST | Review text for grammar/tone |
| /fact-check | POST | Verify facts via SCHOLAR |

---

## SECURITY FLEET (SENTINELS)

### PANOPTES (Integrity Guardian) - Port 8023
**Use for:**
- System integrity monitoring
- Configuration drift detection
- File change detection
- Security baseline enforcement

### ASCLEPIUS (Auto-Healing) - Port 8024
**Use for:**
- Automatic service recovery
- Health-based restarts
- Self-healing workflows
- Incident response automation

### CERBERUS (Security Gateway) - Port 8025
**Use for:**
- Authentication and authorization
- Rate limiting and abuse prevention
- Security policy enforcement
- Access control decisions

---

## INFRASTRUCTURE AGENTS

### LCIS-LIBRARIAN (Knowledge Ingestion) - Port 8050
**Use for:**
- Learning from experiences (lessons, insights)
- Knowledge base growth
- Pattern detection and escalation
- Searchable lessons and rules

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /ingest | POST | Ingest new lesson (requires source_agent) |
| /lessons | GET | Retrieve lessons (supports ?limit=N) |
| /search | GET | Search lessons (?q=query) |
| /health | GET | Health check |

### LCIS-ORACLE (Pre-Action Consultation) - Port 8052
**Use for:**
- Pre-action rule checking
- Blocking dangerous operations
- Providing alternatives and guidance
- Claude Code context injection

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /consult | POST | Check action against rules |
| /rules | GET | List all active rules |
| /context/claude-code | GET | Get Claude Code context |
| /feedback/helpful | POST | Mark guidance as helpful |
| /feedback/ignored | POST | Report ignored guidance |
| /health | GET | Health check |

### VOICE (Voice Interface) - Port 8051
**Use for:**
- Speech-to-text via Whisper
- Text-to-speech via ElevenLabs
- Voice command processing
- Audio response generation

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /transcribe | POST | Audio to text |
| /synthesize | POST | Text to speech |
| /health | GET | Health check |

### GATEWAY (API Gateway) - Port 8070
**Use for:**
- API rate limiting
- Request routing
- Authentication verification
- Load balancing

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /route | POST | Route request to agent |
| /health | GET | Health check |
| /stats | GET | Request statistics |

### MEMORY-V2 (Unified Memory) - Port 8066
**Use for:**
- Cross-conversation fact extraction
- Semantic memory search
- Memory consolidation
- Context retrieval

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /remember | POST | Store fact |
| /recall | POST | Retrieve memories |
| /consolidate | POST | Merge memories |
| /health | GET | Health check |

### SHIELD-SWORD (Manipulation Detection) - Port 8067
**Use for:**
- Detecting manipulation patterns (Shield)
- Applying influence techniques (Sword)
- Pattern analysis
- Conversation safety

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /analyze | POST | Detect patterns |
| /apply | POST | Apply technique |
| /health | GET | Health check |

---

## DASHBOARDS & MONITORING

### Fleet Dashboard - Port 8060
**Use for:**
- Real-time agent health status
- Service uptime monitoring
- Quick restart controls
- Fleet overview

### Cost Dashboard - Port 8061
**Use for:**
- LLM API usage tracking
- Cost analysis and trends
- Budget alerts
- Per-agent cost breakdown

---

## COUNCIL FLEET - THE CONCLAVE (Multi-Agent Collaboration)

### CONVENER (Council Facilitator) - Port 8300
**Use for:**
- Convening multi-agent council meetings
- Facilitating collaborative discussions between agents
- Managing turn-based agent conversations
- Collecting decisions and action items
- Topic-based agent selection

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health check |
| /council/convene | POST | Create new council meeting |
| /council/{id}/start | POST | Start meeting with opening context |
| /council/{id}/turn | POST | Request next agent turn |
| /council/{id}/inject | POST | Inject directive/guidance |
| /council/{id}/decide | POST | Request formal decision |
| /council/{id}/action | POST | Assign action to agent |
| /council/{id}/adjourn | POST | End meeting, generate summary |
| /council/{id}/status | GET | Get meeting status |

**Auto-Selection:** CONVENER automatically selects relevant agents based on meeting topic keywords.

**Trigger Example:**
```bash
# Create a council meeting
curl -X POST http://localhost:8300/council/convene \
  -H "Content-Type: application/json" \
  -d '{"topic": "Market strategy for Q2 launch", "requested_agents": ["CHIRON", "SCHOLAR"]}'

# Start the meeting
curl -X POST http://localhost:8300/council/{meeting_id}/start \
  -H "Content-Type: application/json" \
  -d '{"opening_context": "We need to finalize our Q2 launch strategy"}'

# Request a turn
curl -X POST http://localhost:8300/council/{meeting_id}/turn

# Make a decision
curl -X POST http://localhost:8300/council/{meeting_id}/decide \
  -H "Content-Type: application/json" \
  -d '{"decision_prompt": "What should our primary marketing focus be?"}'

# Adjourn meeting
curl -X POST http://localhost:8300/council/{meeting_id}/adjourn
```

---

### SCRIBE (Council Secretary) - Port 8301
**Use for:**
- Recording council meeting transcripts
- Generating meeting summaries
- Extracting action items from discussions
- Searching meeting history
- Formatting meeting notes

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /health | GET | Health check |
| /scribe/record | POST | Record a meeting entry |
| /scribe/summarize/{id} | POST | Generate meeting summary |
| /scribe/notes/{id} | GET | Get formatted meeting notes |
| /scribe/actions/{id} | GET | Extract action items |
| /scribe/search | POST | Search meeting history |

**Trigger Example:**
```bash
# Generate meeting summary
curl -X POST http://localhost:8301/scribe/summarize/{meeting_id}

# Get meeting notes
curl http://localhost:8301/scribe/notes/{meeting_id}

# Get action items
curl http://localhost:8301/scribe/actions/{meeting_id}

# Search meetings
curl -X POST http://localhost:8301/scribe/search \
  -H "Content-Type: application/json" \
  -d '{"query": "marketing strategy"}'
```

---

## PERSONAL FLEET (Life Management)

### GYM-COACH (Fitness) - Port 8110
**Note:** Runs on 8110 (not 8100) due to port conflict with supabase-kong-dev.

**Use for:**
- Workout planning and tracking
- Exercise form guidance
- Fitness goal setting
- Progress monitoring

### NUTRITIONIST (Nutrition) - Port 8101
**Use for:**
- Nutrition advice and planning
- Macro/micro tracking
- Diet recommendations
- Supplement guidance

### MEAL-PLANNER (Meal Planning) - Port 8102
**Use for:**
- Weekly meal planning
- Recipe suggestions
- Grocery list generation
- Calorie/nutrition balancing

### ACADEMIC-GUIDE (Education) - Port 8103
**Use for:**
- Learning path recommendations
- Study planning and optimization
- Skill development guidance
- Course recommendations

### EROS (Relationships) - Port 8104
**Use for:**
- Dating advice and coaching
- Relationship guidance
- Communication strategies
- Social skill development

---

## BUSINESS FLEET (Professional Services)

### MAGNUS (Universal Project Manager) - Port 8200
**Use for:**
- Multi-platform project management (OpenProject, Asana, Jira, Monday, Notion, Linear)
- Task breakdown and estimation
- Sprint management with adapter system
- Resource allocation
- Background sync with external PM tools
- Unified API across all platforms

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /projects | GET/POST | List/create projects |
| /tasks | GET/POST | Manage tasks |
| /sync | POST | Sync with external platform |
| /status | GET | Dashboard with active projects |
| /health | GET | Health check |

> Note: MAGNUS supersedes HERACLES. The adapter system supports multiple PM tools.

### DAEDALUS (Workflow Builder) - Port 8202
**Use for:**
- Workflow design and automation
- Process optimization
- Integration planning
- N8n workflow creation

### THEMIS (Legal Advisor) - Port 8203
**Use for:**
- Contract review and analysis
- Legal compliance guidance
- Risk assessment
- Policy recommendations

### MENTOR (Business Coach) - Port 8204
**Use for:**
- Business mentorship
- Career guidance
- Leadership development
- Professional growth planning

### STEWARD (Professional Coordination) - Port 8220
**Use for:**
- Tracking professional advisors (CPA, attorney, financial advisor)
- Meeting preparation with AI-generated questions and context
- Recording advice received from professionals
- Managing action items with deadlines
- Document tracking for professional needs
- Synthesizing advice across multiple advisors and AI agents

**Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| /professionals | GET/POST | Manage your professional advisors |
| /professionals/{id} | GET | Get professional with meetings, advice |
| /meetings | GET/POST | Schedule and list meetings |
| /meetings/{id} | GET | Get meeting details with questions |
| /meetings/{id}/prep | POST | Generate AI meeting prep |
| /meetings/{id}/complete | POST | Record meeting outcomes |
| /advice | GET/POST | List/add advice from professionals |
| /advice/actions | GET | Get pending action items |
| /questions | GET/POST | Manage questions for professionals |
| /documents | GET/POST | Track needed documents |
| /synthesize | POST | Synthesize advice on a topic |
| /status | GET | Dashboard with upcoming meetings |
| /health | GET | Health check |

### MIDAS (Traditional Finance) - Port 8205
**Use for:**
- Portfolio tracking (stocks, ETFs, mutual funds)
- Transaction recording
- Watchlist and price alerts
- Dividend tracking
- Performance reporting

### SATOSHI (Crypto & Blockchain) - Port 8206
**Use for:**
- Multi-wallet tracking (EVM, Solana, Bitcoin)
- DeFi position monitoring
- NFT portfolio
- Gas tracking
- Crypto market data

### PLUTUS (Financial Analyst) - Port 8207
**Use for:**
- AI-powered financial analysis
- Budget planning
- Investment guidance
- ROI calculations

### ATLAS-INFRA (Infrastructure Advisor) - Port 8208
**Use for:**
- Cloud architecture guidance
- Infrastructure planning
- Scaling recommendations
- Cost optimization

### IRIS (World Events Reporter) - Port 8209
**Use for:**
- News and current events
- Industry trend analysis
- Market updates
- Competitive intelligence

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

---

## Deprecated Agents

| Agent | Port | Replaced By | Notes |
|-------|------|-------------|-------|
| HERACLES | 8200 | MAGNUS | Merged into universal PM |
| CONSUL | - | MAGNUS | Superseded by MAGNUS adapters |
| CROESUS | 8211 | QUAESTOR | Renamed for clarity |
| LIBRARIAN | 8201 | LCIS-LIBRARIAN (8050) | Ghost entry removed |

> These agents should not be used directly. Use their replacements instead.
