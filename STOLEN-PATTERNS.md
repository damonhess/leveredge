# STOLEN PATTERNS - From CA-AIDev & AI Development Stack

*Captured: January 17, 2026*
*Source: Buddy's California government AI projects*
*Scale context: 40M residents, 170 departments - patterns apply to SMB compliance*

---

## 1. BIZBOT PRODUCT PATTERN (Tier 1 Product Blueprint)

### The Model
```
USER FILLS FORM
       ↓
SUPERVISOR AGENT (orchestrates)
       ↓
┌──────┬──────┬──────┬──────┬──────┐
│Entity│State │Local │Indus-│Renew-│  ← 5-6 domain experts (parallel)
│Form  │Licen-│Licen-│try   │al &  │
│      │sing  │sing  │Spec  │Compl │
└──────┴──────┴──────┴──────┴──────┘
       ↓
PDF GUIDE EMAILED (2-5 minutes)
```

### Metrics
- Processing time: 2-5 minutes
- Cost per request: ~$0.36
- Daily capacity: 1,000-2,000 requests

### LeverEdge Application
**Water Utilities Compliance Guide Product:**
1. Prospect fills intake form (utility size, location, current systems)
2. Agents analyze: Federal regs, State regs, Local requirements, Industry specifics
3. PDF delivered: "Your Water Utility Compliance Checklist"
4. Lead capture → Discovery call → Paid engagement

**This becomes Tier 0.5:** Free/low-cost lead magnet before Tier 1 ($500-2,500)

---

## 2. MULTI-LLM ROUTING PATTERN

### Their Model Routing
| Task Type | Model | Why |
|-----------|-------|-----|
| Orchestration/Synthesis | GPT-4o | Good at coordination |
| Legal/Regulatory Analysis | Claude 3.5 Sonnet | Best at nuanced reasoning |
| Scientific/Research | Gemini 1.5 Pro | Best at web synthesis |
| Fast Responses | Claude Haiku | Cost efficiency |

### LeverEdge Application
| Agent | Current | Consider |
|-------|---------|----------|
| CHIRON | Claude Sonnet | Keep (reasoning) |
| SCHOLAR | Claude Sonnet | Gemini (research synthesis) |
| ARIA | Claude Sonnet | Keep (personality) |
| ATLAS | None (rule-based) | Haiku when AI needed |
| Fast ops | Sonnet | Haiku (10x cheaper) |

### Implementation
```python
# llm-gateway pattern
def route_request(task_type):
    routing = {
        "reasoning": "claude-sonnet",
        "research": "gemini-1.5-pro", 
        "fast": "claude-haiku",
        "coding": "claude-sonnet",
        "legal": "claude-sonnet"
    }
    return routing.get(task_type, "claude-sonnet")
```

---

## 3. WISEBOT KNOWLEDGE INGESTION (LIBRARIAN Blueprint)

### Architecture
```
EMAIL/UPLOAD TRIGGER
        ↓
┌─────────────────────────────────────┐
│         PARSE & NORMALIZE           │
│  PDF │ DOCX │ MD │ MP3 │ IMG │ CSV  │
│      │      │    │     │     │      │
│  ───────────────────────────────    │
│  Whisper │ OCR │ Vision │ Extract   │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│         DEDUP & HASH                │
│  • Content hash (exact match)       │
│  • Embedding similarity (semantic)  │
│  • Skip if >95% similar             │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│         EMBED & STORE               │
│  • Generate embeddings              │
│  • Store in pgvector                │
│  • Index metadata                   │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│      KNOWLEDGE GATEWAY API          │
│  • Semantic search                  │
│  • RAG retrieval                    │
│  • Unified query interface          │
└─────────────────────────────────────┘
```

### Key Features to Steal
1. **Multi-format support:** PDF, DOCX, MD, MP3, images, CSV, XLSX
2. **Audio transcription:** Whisper integration
3. **Image processing:** OCR + Vision AI for context
4. **Smart deduplication:** Hash + embedding similarity
5. **Unified gateway:** Single API for all knowledge queries

### LIBRARIAN Spec (based on WiseBot)
```
LIBRARIAN Agent
├── /ingest - Process new document
│   ├── Detect format
│   ├── Extract content (Whisper, OCR, parsers)
│   ├── Check dedup (hash + embeddings)
│   └── Store with metadata
├── /search - Semantic search
│   ├── Query embedding
│   ├── Vector similarity
│   └── Return ranked results
├── /query - RAG retrieval
│   ├── Search relevant chunks
│   ├── Build context
│   └── Return formatted for LLM
└── /recall - "What did I decide about X?"
    ├── Search decisions
    ├── Find related context
    └── Summarize history
```

---

## 4. COMMENTBOT ANALYSIS PATTERN

### Their Approach
Multi-agent analysis of public comments:
- Legal Agent: Regulatory/statutory analysis, citation validation
- Scientific Agent: Evidence evaluation, claim assessment
- Sentiment Agent: Urgency detection, tone analysis
- Database Writer: Structured storage

### LeverEdge Application: Compliance Document Analyzer
```
COMPLIANCE DOCUMENT ANALYZER
├── Regulatory Agent - Identify applicable regulations
├── Gap Agent - Find compliance gaps
├── Risk Agent - Assess violation severity
├── Recommendation Agent - Suggest remediation
└── Report Generator - Produce compliance report
```

---

## 5. SUPERVISOR-SUBORDINATE PATTERN (Formalized)

### Clean Architecture
```
                 ┌─────────────┐
                 │ SUPERVISOR  │
                 │ (ATLAS?)    │
                 │             │
                 │ • Routes    │
                 │ • Tracks    │
                 │ • Synth-    │
                 │   esizes    │
                 └──────┬──────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Expert  │    │ Expert  │    │ Expert  │
   │    A    │    │    B    │    │    C    │
   └─────────┘    └─────────┘    └─────────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
                        ▼
                 ┌─────────────┐
                 │   OUTPUT    │
                 │ PDF/Email/  │
                 │ API/DB      │
                 └─────────────┘
```

### Current LeverEdge vs This Pattern
| Current | Supervisor Pattern |
|---------|-------------------|
| Peer agents via Event Bus | ATLAS as true supervisor |
| ARIA talks to all | ATLAS orchestrates, ARIA presents |
| Distributed coordination | Centralized orchestration |

### Recommendation
Keep Event Bus for notifications, but add supervisor layer for complex multi-agent tasks:
```
User Request → ATLAS (supervisor) → [CHIRON, SCHOLAR, etc.] → ATLAS (synthesize) → ARIA (present)
```

---

## 6. CONCRETE DELIVERABLES

### Their Outputs
| Product | Deliverable |
|---------|-------------|
| BizBot | PDF licensing guide |
| CommentBot | Structured analysis + recommendations |
| WiseBot | Knowledge API responses |

### LeverEdge Should Produce
| Tier | Deliverable |
|------|-------------|
| Lead Magnet | Compliance checklist PDF |
| Tier 1 | Compliance assessment report |
| Tier 2 | Workflow automation + documentation |
| Tier 3 | Full system + dashboards |

**Key insight:** Don't sell hours, sell artifacts.

---

## 7. MCP ARCHITECTURE PATTERNS

### SSE vs Stdio
| Transport | Use Case |
|-----------|----------|
| **Stdio** | Machine-specific, ephemeral, dev/test |
| **SSE** | Shared services, persistent, production |

### LeverEdge Application
| Service | Transport | Why |
|---------|-----------|-----|
| HEPHAESTUS MCP | SSE | Shared across Claude Web + Code |
| Filesystem MCP | Stdio | Local to Claude Code |
| Memory MCP | SSE | Must persist across sessions |

---

## 8. MEMORY AS KNOWLEDGE GRAPH

### Their Pattern
```
Entities: Projects, people, technologies, decisions
Relations: "Project X uses Technology Y"
Observations: Facts attached to entities
```

### Current aria_knowledge vs Knowledge Graph
| aria_knowledge | Knowledge Graph |
|----------------|-----------------|
| Flat records | Entity-relationship model |
| Category tags | Typed relations |
| Text search | Graph traversal |

### Upgrade Path
```sql
-- Entities table
CREATE TABLE entities (
  id UUID PRIMARY KEY,
  type TEXT, -- project, technology, decision, person
  name TEXT,
  metadata JSONB
);

-- Relations table
CREATE TABLE relations (
  id UUID PRIMARY KEY,
  from_entity UUID REFERENCES entities,
  relation_type TEXT, -- uses, decided, owns, created
  to_entity UUID REFERENCES entities,
  metadata JSONB
);

-- Observations (current aria_knowledge becomes this)
CREATE TABLE observations (
  id UUID PRIMARY KEY,
  entity_id UUID REFERENCES entities,
  content TEXT,
  source TEXT,
  created_at TIMESTAMPTZ
);
```

---

## 9. HEALTH CHECK PATTERN

### Their Script Structure
```bash
#!/bin/bash
echo "=== System Health Check ==="

# 1. Network/Mount Status
for host in "${MACHINES[@]}"; do
  check_connectivity "$host"
done

# 2. Service Status
check_scheduler
check_workers

# 3. Environment Status
check_python_venvs
check_dependencies

echo "Health check complete!"
```

### LeverEdge Health Check Script
```bash
#!/bin/bash
# /opt/leveredge/shared/scripts/check-leveredge.sh

echo "╔══════════════════════════════════════╗"
echo "║     LEVEREDGE HEALTH CHECK           ║"
echo "╚══════════════════════════════════════╝"

# 1. Docker containers
echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(gaia|atlas|hades|chronos|hephaestus|aegis|hermes|argus|aloy|athena|aria|chiron|scholar|event-bus)"

# 2. Agent endpoints
echo "=== Agent Endpoints ==="
for port in 8000 8008 8010 8011 8012 8013 8014 8015 8016 8017 8018 8099; do
  curl -s --max-time 2 "http://localhost:$port/health" > /dev/null && echo "✓ Port $port" || echo "✗ Port $port"
done

# 3. Database
echo "=== Supabase ==="
curl -s --max-time 5 "http://localhost:8000/rest/v1/" > /dev/null && echo "✓ Supabase API" || echo "✗ Supabase API"

# 4. n8n instances
echo "=== n8n Instances ==="
curl -s --max-time 5 "http://localhost:5678/healthz" > /dev/null && echo "✓ n8n PROD" || echo "✗ n8n PROD"
curl -s --max-time 5 "http://localhost:5680/healthz" > /dev/null && echo "✓ n8n DEV" || echo "✗ n8n DEV"

echo "═══════════════════════════════════════"
```

---

## 10. COST TRACKING PATTERN

### Their Metrics
- Cost per request tracked
- Daily capacity known
- Per-agent cost attribution

### LeverEdge Implementation Priority
1. Wire `log_llm_usage()` into ARIA workflow (HIGH)
2. Add cost tracking to CHIRON and SCHOLAR
3. Build cost dashboard in Grafana
4. Set budget alerts

---

## 11. DISTRIBUTED ARCHITECTURE (Future Scale)

### Their Pattern
```
DEV MACHINE ──┐
              │
HOME SERVER ──┼── Tailscale Mesh ── VPS (public)
              │
INFRA (Pi) ───┘
```

### LeverEdge Scale Path (when revenue supports)
```
Current: Single VPS ($15/mo)
     ↓
Phase 2: VPS + Home server for heavy processing
     ↓
Phase 3: Multi-region for client proximity
```

---

## IMPLEMENTATION PRIORITY

### Steal Immediately (This Week)
1. ✅ Health check script pattern
2. ✅ BizBot product model (compliance PDF guide)
3. ✅ Cost tracking wiring

### Steal for Planning Mission
4. LIBRARIAN spec based on WiseBot
5. Supervisor-subordinate pattern formalization
6. Multi-LLM routing evaluation

### Steal for Scale Phase
7. Memory knowledge graph upgrade
8. Distributed architecture
9. Processing SLAs

---

## KEY INSIGHT

> "Don't sell hours, sell artifacts."

BizBot delivers a PDF in 5 minutes for $0.36.
That scales infinitely.

Consulting hours don't scale.

**LeverEdge Tier 0:** Automated compliance assessment → PDF
**LeverEdge Tier 1-3:** Implementation of what the assessment recommends

The assessment is the lead magnet AND the roadmap for the paid work.
