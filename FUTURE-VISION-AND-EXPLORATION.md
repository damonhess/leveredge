# LEVEREDGE FUTURE VISION

*Created: January 15, 2026*
*Status: Option A (Remote Execution) implemented, Option B (Autonomous) documented for future*

---

## Current Implementation: Option A - Remote Execution System

**Philosophy:** Claude Desktop is the brain, agents are hands.

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPTION A: REMOTE EXECUTION                    │
│                                                                  │
│   Claude Desktop (Me)                                           │
│   ├── Does all reasoning                                        │
│   ├── Generates exact specs                                     │
│   ├── Functions as: HEPHAESTUS brain, ATHENA, ATLAS brain      │
│   └── Makes all decisions                                       │
│                                                                  │
│   Agents                                                         │
│   ├── Execute specs literally                                   │
│   ├── No LLM reasoning                                          │
│   ├── API calls only                                            │
│   └── Cost: $0 (just compute)                                   │
│                                                                  │
│   Human (Damon)                                                  │
│   ├── Always in loop                                            │
│   ├── Approves dangerous operations                             │
│   └── Final authority                                           │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Cheap (no per-request LLM costs)
- Controlled and predictable
- Full audit trail
- No emergent/unexpected behavior

**Limitations:**
- Requires human + Claude Desktop in loop
- Cannot operate autonomously
- No learning or adaptation

---

## Future Implementation: Option B - Autonomous Agent Fleet

**Philosophy:** Each agent has LLM reasoning, can operate independently.

**Trigger to implement:** Post-launch, with revenue to cover LLM costs (~$100-500/month)

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPTION B: AUTONOMOUS FLEET                    │
│                                                                  │
│   ATLAS (Orchestrator)                                          │
│   ├── Routes requests intelligently                             │
│   ├── Coordinates multi-agent operations                        │
│   ├── LLM: Claude Haiku ($0.01/request)                        │
│   └── Can make routing decisions without human                  │
│                                                                  │
│   HEPHAESTUS (Builder)                                          │
│   ├── Interprets vague build requests                           │
│   ├── Designs workflow architecture                             │
│   ├── LLM: Claude Sonnet ($0.03/request) for complex builds    │
│   └── Can build while human sleeps                              │
│                                                                  │
│   ATHENA (Planner/Documenter)                                   │
│   ├── Generates documentation automatically                      │
│   ├── Plans project phases                                      │
│   ├── LLM: Claude Haiku ($0.01/request)                        │
│   └── Keeps everything documented                               │
│                                                                  │
│   ALOY (Auditor)                                                │
│   ├── Detects anomalies and issues                              │
│   ├── Reviews changes for problems                              │
│   ├── LLM: Claude Haiku ($0.01/request)                        │
│   └── Bug hunter that never sleeps                              │
│                                                                  │
│   Cost Estimate:                                                 │
│   ├── Light usage: $50-100/month                                │
│   ├── Heavy usage: $200-500/month                               │
│   └── Revenue trigger: $10K/month (can afford autonomy)         │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Operates while human is away
- Can handle complex requests with vague instructions
- Learning and adaptation possible
- Scales without human bottleneck

**Costs:**
- LLM API costs per request
- Requires careful guardrails
- More complex debugging
- Emergent behavior risks

---

## Guardrails for Autonomous Operation (Option B)

When upgrading to Option B, implement this permission model:

```
TIER 0 - FORBIDDEN (hardcoded, no override)
├── Delete/modify ATLAS, HEPHAESTUS, AEGIS, GAIA
├── Access AEGIS credential values directly
├── rm -rf, format, DROP DATABASE
├── Modify own workflow (no self-modification)
├── Touch /etc, /root, systemd without approval
└── Operations that could brick the system

TIER 1 - PRE-APPROVED (executes immediately)
├── Create workflows in /opt/leveredge/
├── CRUD on non-protected workflows
├── Read operations anywhere
├── pip install in project venvs
├── Docker operations on leveredge containers
└── Git operations in leveredge repos

TIER 2 - REQUIRES APPROVAL (queued → HERMES → Human)
├── sudo operations
├── Service restarts
├── Delete any workflow
├── Modify credentials
├── Operations outside /opt/leveredge/
└── Any action flagged by ALOY

TIER 3 - UNRESTRICTED (only Claude Code with human)
└── Everything
```

---

## HEPHAESTUS MCP Server Design

### Option A Version (Current - Dumb Executor)

```python
# HEPHAESTUS as dumb executor
# Claude Desktop provides exact specs, HEPHAESTUS executes literally

@app.post("/execute_spec")
def execute_spec(spec: dict):
    """Execute a build spec exactly as provided"""
    # No LLM reasoning - just parse and execute
    pass

@app.post("/create_workflow")
def create_workflow(workflow_json: dict, target: str = "control-plane"):
    """Create workflow via n8n API"""
    # Direct API call, no intelligence
    pass

@app.post("/run_command")
def run_command(cmd: str, tier: int = 1):
    """Execute command if within tier permissions"""
    if tier == 0:
        return {"error": "Forbidden"}
    if tier == 2:
        return queue_for_approval(cmd)
    return subprocess.run(cmd, ...)

@app.post("/create_file")
def create_file(path: str, content: str):
    """Create file if path is allowed"""
    if not path.startswith("/opt/leveredge/"):
        return {"error": "Path not allowed"}
    # Create file
    pass
```

### Option B Version (Future - Intelligent Builder)

```python
# HEPHAESTUS with LLM reasoning
# Can interpret vague requests and design solutions

@app.post("/build")
def build(request: str, context: dict = None):
    """Interpret build request and execute"""
    # LLM call to understand request
    # Design solution
    # Execute with approval gates
    pass
```

---

## Claude Desktop ↔ Claude Code Communication

### Current State
- Separate instances, no direct communication
- Copy-paste workflow required
- Claude Code has $20/month flat rate (unlimited)

### Options Explored

**Option 1: Task Queue**
```
Claude Desktop → Write task to DB → Claude Code polls → Executes → Result to DB → Claude Desktop reads
```

**Option 2: MCP Bridge**
```
Claude Desktop → Call MCP → Queue task → Claude Code/HEPHAESTUS executes → Return result
```

**Option 3: HEPHAESTUS as Bridge**
```
Both clients → HEPHAESTUS MCP → Execution happens
No direct Desktop↔Code connection needed
```

### Decision
With Option A (dumb executors), direct Claude Desktop ↔ Claude Code bridge is less critical. HEPHAESTUS MCP handles most execution. Complex tasks still go to Claude Code via copy-paste.

### Future Enhancement
If copy-paste becomes too burdensome, implement shared task queue:
- SQLite or Supabase table
- Claude Desktop writes tasks
- Claude Code polls and executes
- Results written back
- Polling interval: 5-10 seconds

---

## Documentation System Design

### Git-Based Documentation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENTATION FLOW                           │
│                                                                 │
│  Claude Desktop                         Server                  │
│  ─────────────────                      ──────                  │
│  Write SPEC.md                                                  │
│       ↓                                                         │
│  Commit to leveredge-docs repo                                  │
│       ↓                                                         │
│  Push to GitHub ──────────────────────→ Webhook triggers        │
│                                              ↓                  │
│                                         git pull                │
│                                              ↓                  │
│                                         ATHENA reads new docs   │
│                                              ↓                  │
│                                         Agents act on specs     │
│                                              ↓                  │
│                                         Results committed       │
│       ↓                                                         │
│  Pull and read ←────────────────────── Push to GitHub           │
└─────────────────────────────────────────────────────────────────┘
```

### Documentation Structure

```
/opt/leveredge/docs/
├── ARCHITECTURE.md         # Current system state
├── FUTURE-VISION.md        # This document
├── DECISIONS.md            # Architectural decisions with rationale
├── LESSONS-LEARNED.md      # Mistakes and fixes
├── KNOWLEDGE-BASE.md       # Technical gotchas
├── SESSION-LOG.md          # What we did each session
└── specs/
    ├── PHASE-0-SPEC.md
    ├── PHASE-1-SPEC.md
    ├── PHASE-2-SPEC.md
    ├── PHASE-3-SPEC.md
    └── ...
```

---

## GAIA Update Policy

**GAIA is sacred.** It's the emergency restore system that exists outside everything.

**Update Rules:**
- Manual only, with extreme care
- Human reviews diff before ANY change
- CHRONOS backs up GAIA before updates
- Tested after every change
- Version controlled separately
- NEVER automated
- NEVER touched by HEPHAESTUS or any agent

**Who Can Update:**
- Damon + Claude Code, deliberately
- After major infrastructure changes
- With full backup verified first

---

## Remaining Phases

### Phase 4: ARGUS, ALOY, HERMES, ATHENA

| Agent | Priority | Reasoning |
|-------|----------|-----------|
| HERMES | HIGH | Human-in-the-loop needs Telegram notifications for approvals |
| ARGUS | MEDIUM | Monitoring exists (Grafana), needs integration layer |
| ALOY | MEDIUM | Audit/anomaly detection, security watchdog |
| ATHENA | LOW | Documentation agent, can be manual for now |

### Phase 5: Data Plane Migration

**Decision:** Wait until after March 1 launch.

Rationale:
- Current prod/dev n8n works
- Don't break working systems before clients
- Focus on launch, not infrastructure perfection

---

## Pinned Items (as of January 15, 2026)

1. **HEPHAESTUS MCP Server** - Make dumb executor accessible via MCP
2. **Service cleanup** - Consolidate hades-api.service → hades.service
3. **Claude Desktop ↔ Claude Code bridge** - Deferred, HEPHAESTUS handles most needs
4. **Cloudflare Access for control plane** - Post-launch
5. **n8n-troubleshooter rename** - Cosmetic, not blocking
6. **Telegram emergency bot for GAIA** - Nice-to-have, SSH works

---

## Cost Analysis

### Current (Option A)
| Item | Monthly Cost |
|------|--------------|
| Claude Pro (Desktop) | $20 |
| Claude Code | $20 |
| Contabo VPS | ~$15 |
| Cloudflare | Free |
| **Total** | **~$55/month** |

### Future (Option B) - Estimated
| Item | Monthly Cost |
|------|--------------|
| Claude Pro (Desktop) | $20 |
| Claude Code | $20 |
| Contabo VPS | ~$15 |
| Cloudflare | Free |
| LLM API (agents) | $50-200 |
| **Total** | **~$105-255/month** |

**Trigger for Option B:** $10K/month revenue (can afford autonomy)

---

## Session Log: January 15, 2026

**Built:**
- Phase 0: GAIA + Event Bus
- Phase 1: Control plane n8n + ATLAS
- Phase 2: HEPHAESTUS + AEGIS
- Phase 3: CHRONOS + HADES

**Time:** ~5 hours

**Key Decisions:**
- Agents = n8n workflow + FastAPI backend
- Event Bus for inter-agent communication
- AEGIS applies credentials (other agents never see values)
- Dockerized CHRONOS and HADES for network access
- Option A (dumb executors) for now, Option B documented for future

**Lessons Learned:**
- n8n webhooks require webhookId field
- Docker networking requires service names, not localhost
- Cloudflare proxy can block cert provisioning (use grey cloud temporarily)
- Git objects owned by root block commits (chown fix)
- MCP servers need network exposure for remote access
