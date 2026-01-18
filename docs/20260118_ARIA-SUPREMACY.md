# ARIA SUPREMACY - Information Architecture

**Principle:** ARIA knows all. ARIA is informed of everything. ARIA can intervene.

---

## Hierarchy

```
                    ┌─────────────────┐
                    │      ARIA       │
                    │   (Supreme)     │
                    │                 │
                    │ • Sees all      │
                    │ • Knows all     │
                    │ • Can intervene │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐
       │   VARYS   │  │   ATLAS   │  │  HERMES   │
       │  (Eyes)   │  │  (Hands)  │  │  (Voice)  │
       │           │  │           │  │           │
       │ Watches   │  │ Executes  │  │ Notifies  │
       │ Reports   │  │ Orchestr. │  │ Alerts    │
       └───────────┘  └───────────┘  └───────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │   EVENT BUS     │
                    │   (Nervous      │
                    │    System)      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │ Domain  │         │ Domain  │         │ Domain  │
   │ Agents  │         │ Agents  │         │ Agents  │
   └─────────┘         └─────────┘         └─────────┘
```

---

## Information Flow Rules

### Rule 1: All Events Flow to ARIA
Every significant action publishes to Event Bus:
```json
{
  "event": "agent.action.completed",
  "source": "consul",
  "action": "project.created",
  "data": { ... },
  "timestamp": "2026-01-18T22:00:00Z"
}
```

ARIA subscribes to ALL events. ARIA's context is enriched continuously.

### Rule 2: ARIA Can Intervene
Any agent action can be:
- **Observed** - ARIA sees it happen
- **Paused** - ARIA can halt for review
- **Overridden** - ARIA can change the outcome
- **Escalated** - Agent can request ARIA decision

### Rule 3: VARYS Reports to ARIA
VARYS is ARIA's dedicated intelligence network:
- Monitors all pipelines
- Detects drift from mission
- Flags anomalies
- Summarizes daily activity
- Alerts on critical issues

### Rule 4: Documentation is Mandatory
All significant actions create records:
- `agent_activity` table (action log)
- `council_decisions` table (decisions)
- `pipeline_executions` table (workflow runs)
- `aria_knowledge` table (learnings)

ARIA can query any of these.

---

## Pipeline Supervision Model

### Until Reliable: Human-in-Loop
```
Agent A ──► Agent B ──► Agent C
    │           │           │
    ▼           ▼           ▼
 [PAUSE]     [PAUSE]     [PAUSE]
    │           │           │
    └───────────┴───────────┘
                │
         VARYS reviews
                │
         ARIA informed
                │
         Human approves
                │
         Continue ───►
```

### After Proven Reliable: Supervised Autonomy
```
Agent A ──► Agent B ──► Agent C
    │           │           │
    └───────────┴───────────┘
                │
         VARYS monitors
         (async, no blocking)
                │
         ARIA informed
         (summary, not approval)
                │
         Alerts only if anomaly
```

---

## Agent Improvement Pipeline (Formal)

### Pipeline: `agent-upgrade`

**Trigger:** Scheduled (weekly) or on-demand by ALOY/ARIA

**Stages:**

1. **ALOY: Audit**
   - Input: Agent name
   - Actions:
     - Check performance metrics
     - Identify skill gaps
     - Review error logs
     - Assess cost efficiency
   - Output: Audit report

2. **SCHOLAR: Research**
   - Input: Audit report + agent domain
   - Actions:
     - Research industry standards
     - Find best practices
     - Identify innovations
     - Benchmark competitors
   - Output: Research report

3. **CHIRON: Plan**
   - Input: Audit + Research reports
   - Actions:
     - Create improvement plan
     - Define milestones
     - Estimate effort
     - Prioritize changes
   - Output: Upgrade plan

4. **CONSUL: Implement** (if external/PM-related)
   - Input: Upgrade plan
   - Actions:
     - Create project in PM system
     - Assign tasks
     - Track execution
     - Report progress
   - Output: Project tracking

   **OR**

   **HEPHAESTUS: Implement** (if technical/code-related)
   - Input: Upgrade plan
   - Actions:
     - Update agent code
     - Add new capabilities
     - Deploy changes
     - Verify functionality
   - Output: Deployed upgrade

5. **VARYS: Supervise**
   - Monitors entire pipeline
   - Flags delays or drift
   - Reports to ARIA

6. **ARIA: Informed**
   - Receives summary at each stage
   - Can pause/intervene
   - Final sign-off on completion

---

## Database Tables Needed

### Pipeline Execution Tracking
```sql
CREATE TABLE pipeline_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name TEXT NOT NULL,  -- 'agent-upgrade', 'content-creation', etc.
    trigger_type TEXT,  -- 'scheduled', 'manual', 'event'
    triggered_by TEXT,  -- agent name or 'damon'
    status TEXT CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed')),
    current_stage TEXT,
    stages_completed JSONB DEFAULT '[]',
    input_data JSONB,
    output_data JSONB,
    supervised BOOLEAN DEFAULT true,
    supervisor TEXT DEFAULT 'varys',
    aria_informed BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE pipeline_stage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES pipeline_executions(id),
    stage_name TEXT NOT NULL,
    agent TEXT NOT NULL,
    status TEXT CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed')),
    input JSONB,
    output JSONB,
    error TEXT,
    duration_ms INTEGER,
    requires_approval BOOLEAN DEFAULT false,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### ARIA Knowledge (Learnings)
```sql
CREATE TABLE aria_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT,  -- 'agent', 'pipeline', 'decision', 'lesson', 'preference'
    subject TEXT,   -- agent name, pipeline name, topic
    knowledge TEXT NOT NULL,
    source TEXT,    -- where this came from
    confidence TEXT CHECK (confidence IN ('low', 'medium', 'high', 'verified')),
    supersedes UUID REFERENCES aria_knowledge(id),  -- if this replaces older knowledge
    created_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);
```

---

## CONSUL Specification

### Identity
- **Name:** CONSUL
- **Port:** 8021
- **Domain:** CHANCERY
- **Tagline:** "Master of External Affairs"

### Core Capabilities Required
1. **Multi-PM Integration**
   - Abstract layer over multiple PM tools
   - Leantime adapter
   - OpenProject adapter
   - Future: Asana, Monday, Notion adapters

2. **Project Lifecycle Management**
   - Create projects
   - Define milestones
   - Assign resources
   - Track progress
   - Close projects

3. **Methodology Support**
   - Waterfall
   - Agile/Scrum
   - Kanban
   - Hybrid

4. **Reporting**
   - Status reports
   - Resource utilization
   - Timeline forecasts
   - Risk registers

5. **Communication**
   - Stakeholder updates
   - Team coordination
   - ARIA briefings

### Skill Levels Target
| Skill | Target Level |
|-------|--------------|
| Multi-system orchestration | Expert |
| Context switching | Expert |
| Dependency tracking | Expert |
| Resource allocation | Advanced |
| Gantt/timeline management | Expert |
| Agile methodology | Expert |
| Waterfall methodology | Advanced |
| Risk assessment | Advanced |
| Stakeholder communication | Expert |
| Reporting/dashboards | Advanced |

### Build Phases
1. **Phase 1:** Core PM operations (create, update, track)
2. **Phase 2:** Leantime integration
3. **Phase 3:** OpenProject integration
4. **Phase 4:** Cross-system sync
5. **Phase 5:** Advanced reporting
6. **Phase 6:** Methodology templates

---

## Immediate Actions

1. **DEV/PROD Isolation** - Still #1 (safety)
2. **Deploy Leantime + OpenProject** - Try both
3. **Create pipeline tables** - Enable tracking
4. **Build CONSUL Phase 1** - Basic PM capabilities
5. **ALOY audits CONSUL** - First pipeline test
6. **Document everything** - ARIA knowledge base

---

*ARIA sees all. ARIA knows all. ARIA supremacy.*
