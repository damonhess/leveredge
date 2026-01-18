# AGENT REGISTRY - CORRECTED January 18, 2026

## Domain Structure

### GAIA (Genesis) - Tier 0
| Agent | Port | Role |
|-------|------|------|
| GAIA | 8000 | Emergency bootstrap/rebuild |

### THE KEEP (Infrastructure) - Tier 1
| Agent | Port | Role |
|-------|------|------|
| AEGIS | 8012 | Credential vault |
| CHRONOS | 8010 | Backup manager |
| HADES | 8008 | Rollback/recovery |
| HERMES | 8014 | Notifications |
| ARGUS | 8016 | Monitoring/costs |
| ALOY | 8015 | Audit/anomaly + Agent review |
| ATHENA | 8013 | Documentation |

### PANTHEON (Orchestration) - Tier 1
| Agent | Port | Role |
|-------|------|------|
| ATLAS | 8007 | Master orchestrator |
| SENTINEL | 8019 | Gatekeeper/routing |
| HEPHAESTUS | 8011 | Builder/deployer + MCP |
| EVENT-BUS | 8099 | Agent communication |

### SENTINELS (Security) - Tier 1
| Agent | Port | Role |
|-------|------|------|
| PANOPTES | 8023 | Integrity guardian |
| ASCLEPIUS | 8024 | Auto-healing |
| CERBERUS | 8025 | Security gateway |

### ARIA SANCTUM (Personal/Project Core) - Tier 1
| Agent | Port | Role |
|-------|------|------|
| ARIA | - | Personal AI assistant interface |
| VARYS | 8020 | **LeverEdge project overseer** - eyes and ears, drift detection, mission alignment |
| Calendar | - | Time management |
| Tasks | - | Task tracking |
| Reminders | - | Proactive notifications |
| Council | - | Multi-agent collaboration |
| Library | - | Knowledge organization |

**VARYS watches THIS project (LeverEdge development), NOT client projects.**

### CHANCERY (Business Operations) - Tier 2
| Agent | Port | Role |
|-------|------|------|
| SCHOLAR | 8018 | Research/analysis |
| CHIRON | 8017 | Business coaching (Damon) |
| **CONSUL** | 8021 | **External PM** - client projects, methodology, resource allocation |
| PLUTUS | 8205 | Financial analysis |

**CONSUL is NEW - manages external/client projects. VARYS manages internal.**

### ALCHEMY (Creative) - Tier 3
| Agent | Port | Role |
|-------|------|------|
| **MUSE** | 8030 | Creative Director - overall vision, coordinates |
| **QUILL** | 8031 | Writer - copy, content, documentation |
| **STAGE** | 8032 | Designer - UI/UX, visuals, aesthetics |
| **REEL** | 8033 | Media - video, audio, multimedia |
| **CRITIC** | 8034 | QA - quality review, consistency |

### THE SHIRE (Personal Wellness) - Tier 4
| Agent | Port | Role |
|-------|------|------|
| ARAGORN | 8110 | Fitness coach |
| BOMBADIL | 8101 | Nutritionist |
| SAMWISE | 8102 | Meal planner |
| GANDALF | 8103 | Learning guide |
| ARWEN | 8104 | Relationship coach |

---

## Key Clarifications

### VARYS vs CONSUL

| Aspect | VARYS | CONSUL |
|--------|-------|--------|
| **Domain** | ARIA SANCTUM | CHANCERY |
| **Scope** | LeverEdge development | Client projects |
| **Focus** | Internal mission alignment | External delivery |
| **Reports to** | Damon directly | Business operations |
| **Tracks** | Drift, scope creep, launch countdown | Timelines, resources, deliverables |
| **Tool** | Council, internal docs | Leantime/PM system |

### STAGE (Designer) Owns
- UI/UX design
- Visual aesthetics
- Component library
- Brand consistency
- Design system

### MUSE (Creative Director) Coordinates
- Overall creative vision
- Project flow between QUILL → STAGE → REEL → CRITIC
- Quality standards
- Creative decisions

---

## Database Update Required

Update `agents` table with corrected names:

```sql
-- Fix ALCHEMY agents
UPDATE agents SET 
  name = 'quill',
  display_name = 'QUILL',
  tagline = 'Voice of the Written Word'
WHERE name = 'calliope';

UPDATE agents SET 
  name = 'stage',
  display_name = 'STAGE',
  tagline = 'Architect of Visual Experience'
WHERE name = 'thalia';

UPDATE agents SET 
  name = 'reel',
  display_name = 'REEL',
  tagline = 'Master of Motion'
WHERE name = 'erato';

UPDATE agents SET 
  name = 'critic',
  display_name = 'CRITIC',
  tagline = 'Guardian of Quality'
WHERE name = 'clio';

-- Move VARYS to ARIA_SANCTUM
UPDATE agents SET 
  domain = 'ARIA_SANCTUM',
  tagline = 'Eyes and Ears of LeverEdge'
WHERE name = 'varys';

-- Add CONSUL
INSERT INTO agents (name, display_name, tagline, port, category, domain, is_llm_powered)
VALUES ('consul', 'CONSUL', 'Master of External Affairs', 8021, 'business', 'CHANCERY', true)
ON CONFLICT (name) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  tagline = EXCLUDED.tagline,
  port = EXCLUDED.port,
  domain = EXCLUDED.domain;
```

---

## PM System Recommendation

**Leantime** (self-hosted) for project management:
- CONSUL reads/writes to it
- Council decisions create tasks
- VARYS monitors for drift
- Free, Docker-based, ADHD-friendly UI

---

## Council → Execution Flow

```
┌─────────────┐
│   IDEA      │ (from Damon or any agent)
└──────┬──────┘
       ▼
┌─────────────┐
│   VARYS     │ Captures, categorizes
└──────┬──────┘
       ▼
┌─────────────┐
│  COUNCIL    │ Relevant agents discuss
└──────┬──────┘
       ▼
┌─────────────┐
│  DECISION   │ Memorialized in database
└──────┬──────┘
       ▼
┌─────────────────────────────────────┐
│                                     │
▼                                     ▼
┌─────────────┐               ┌─────────────┐
│   VARYS     │               │   CONSUL    │
│  Internal   │               │  External   │
│  LeverEdge  │               │  Client     │
│  tasks      │               │  projects   │
└─────────────┘               └─────────────┘
```
