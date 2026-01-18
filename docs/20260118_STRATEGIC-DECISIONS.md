# STRATEGIC DECISIONS & LOOSE ENDS - January 18, 2026

**Context:** 42 days to launch. Infrastructure stable. Feeling overwhelmed by scope.

---

## 🚨 CRITICAL ISSUE: DEV/PROD ISOLATION

### Problem
Claude Code accidentally made production changes last night. Need hard guardrails.

### Proposed Solutions

#### Option A: Workspace Separation (Recommended)
```
/home/damon/.claude/
├── CLAUDE_PROFILE_DEV      # Default profile
├── CLAUDE_PROFILE_PROD     # Requires explicit activation
└── EXECUTION_RULES.md      # Updated with profile awareness
```

**How it works:**
1. Create two VS Code workspaces: `leveredge-dev.code-workspace` and `leveredge-prod.code-workspace`
2. DEV workspace only has access to `/opt/leveredge/data-plane/dev/`
3. PROD workspace requires explicit confirmation + reason
4. Claude Code's EXECUTION_RULES.md updated to CHECK which workspace before any operation

#### Option B: Environment Lock File
```bash
# /opt/leveredge/.environment-lock
CURRENT_ENV=dev
PROD_UNLOCK_UNTIL=2026-01-18T22:00:00Z  # Temporary prod access
PROD_UNLOCK_REASON="Deploying ARIA V3.2"
```

Claude Code MUST check this file before any operation. If CURRENT_ENV=dev, refuse any command targeting prod paths.

#### Option C: Git Branch Enforcement
- DEV work happens on `dev` branch
- PROD deploys only via `promote-to-prod.sh` which merges dev → main
- Claude Code restricted to `dev` branch only

### Recommendation
**Implement all three:**
1. Workspace separation (VS Code level)
2. Environment lock file (script level)
3. Branch enforcement (git level)

Create `/opt/leveredge/shared/scripts/unlock-prod.sh` that:
- Requires reason
- Sets time limit (max 2 hours)
- Logs who unlocked and why
- Auto-relocks after timeout

---

## 📋 PROJECT MANAGEMENT ASSIGNMENT

### VARYS as Project Manager
VARYS (Port 8020) becomes **Mission Guardian + Project Manager**

**Responsibilities:**
- Days-to-launch countdown
- Drift detection (scope creep alerts)
- Sprint planning coordination
- Decision tracking
- Dependency management
- Agent development prioritization

### Agent Development Order (VARYS-Recommended)

| Priority | Agent | Why | ETA |
|----------|-------|-----|-----|
| 1 | DEV/PROD Isolation | Safety first - prevent accidents | Today |
| 2 | VARYS PM Features | Need PM to manage the rest | Jan 19-20 |
| 3 | AEGIS | Credentials are foundation | Jan 21-22 |
| 4 | ARGUS | Cost tracking critical | Jan 23-24 |
| 5 | CHIRON | Daily planning tool | Jan 25-26 |
| 6 | Command Center UI | Agent pages framework | Jan 27-31 |

**Post-Launch:** CHRONOS page, PANOPTES page, SCHOLAR page, Creative agents, Personal agents

---

## 🏛️ COUNCIL DECISION SYSTEM

### Database Tables (Already Created)
```sql
council_meetings       -- Meeting records
council_participants   -- Who attended
council_messages       -- Discussion transcript
```

### Need to Add
```sql
council_decisions (
    id UUID PRIMARY KEY,
    meeting_id UUID REFERENCES council_meetings(id),
    decision_type TEXT,  -- 'architecture', 'priority', 'policy', 'scope'
    title TEXT,
    description TEXT,
    rationale TEXT,
    participants TEXT[],  -- Who voted/agreed
    status TEXT,  -- 'proposed', 'approved', 'rejected', 'superseded'
    superseded_by UUID,  -- If decision was later changed
    created_at TIMESTAMPTZ,
    effective_date DATE
);

council_decision_impacts (
    id UUID PRIMARY KEY,
    decision_id UUID REFERENCES council_decisions(id),
    affected_agent TEXT,
    affected_system TEXT,
    impact_description TEXT
);
```

### Decision Categories
- **Architecture** - System design choices
- **Priority** - What to work on next
- **Policy** - Rules and constraints
- **Scope** - What's in/out of launch
- **Assignment** - Who owns what

---

## 🔍 AGENT REVIEW SYSTEM

### Assign to: ALOY (Auditor)
ALOY (Port 8015) already handles audit + anomaly detection. Expand to include:

**Agent Review Responsibilities:**
- Skill gap identification
- Performance tracking (response time, error rate)
- Cost tracking per agent
- Model version tracking
- Upgrade recommendations
- Health score trends

### Database Tables Needed
```sql
agent_skills (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    skill_name TEXT,
    skill_level TEXT,  -- 'basic', 'intermediate', 'advanced', 'expert'
    last_assessed TIMESTAMPTZ,
    notes TEXT
);

agent_skill_gaps (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    required_skill TEXT,
    current_level TEXT,
    target_level TEXT,
    priority TEXT,
    remediation_plan TEXT,
    created_at TIMESTAMPTZ
);

agent_models (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    model_name TEXT,  -- 'claude-3-5-sonnet', 'gpt-4', etc.
    model_version TEXT,
    temperature DECIMAL,
    max_tokens INTEGER,
    cost_per_1k_input DECIMAL,
    cost_per_1k_output DECIMAL,
    effective_date TIMESTAMPTZ
);

agent_performance (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    date DATE,
    total_calls INTEGER,
    successful_calls INTEGER,
    failed_calls INTEGER,
    avg_latency_ms INTEGER,
    total_cost DECIMAL,
    total_tokens INTEGER
);
```

---

## 🎨 CREATIVE TEAM ASSIGNMENTS

| Agent | Role | Owns |
|-------|------|------|
| **MUSE** (8030) | Creative Director | Overall aesthetic vision, project coordination |
| **THALIA** (8032) | Designer | UI/UX, component library, visual consistency |
| **CALLIOPE** (8031) | Writer | Copy, microcopy, documentation voice |
| **CLIO** (8034) | QA Reviewer | Quality checks, consistency audits |

**THALIA is the answer to "Who owns aesthetics?"**

---

## 📦 LOOSE ENDS FROM THIS CHAT

### Captured for Future Action

#### AEGIS Page Requirements (Bolt.new Prompt)
```
Add AEGIS Credentials Management page at route /agents/aegis

Database tables (Supabase):
- aegis_credentials (id, name, display_name, credential_type, provider, project, environment, expires_at, last_tested, test_status, used_by_agents[], is_active)
- aegis_audit_log (credential_id, action, actor, details, created_at)

Sections:
1. Header: 🛡️ AEGIS "Guardian of Secrets" + status
2. Dashboard: Health score gauge, Expiring Soon, Total, Failed Auth cards
3. Credentials list with filters (project, provider, type, status)
4. Actions: [Add Credential] [Bulk Health Check] [Rotate Expiring]
5. Add Credential modal
6. Built-in chat with AEGIS agent

Design: ADHD-friendly, one primary metric prominent, color-coded status
```

#### Frontend Project Separation (Decided)
| Project | Purpose | Isolated |
|---------|---------|----------|
| ARIA | Personal assistant | Yes |
| Command Center | Infrastructure + agent chat | Yes |
| Customer Portal | Client dashboards | Yes (future) |
| Public Website | Marketing | Yes (future) |

#### DNS Pending
- Add `dev.command` A record in Cloudflare

#### Password Reset
```bash
docker exec -it supabase-db psql -U postgres -d postgres -c "
UPDATE auth.users 
SET encrypted_password = crypt('NEW_PASSWORD', gen_salt('bf'))
WHERE email = 'damonhess@hotmail.com';
"
```

#### Git Commit Pending
```bash
cd /opt/leveredge
git add docs/20260118_*.md
git commit -m "Jan 18: Updated guidance documents"
git push origin main
```

---

## 🎯 RECOMMENDED NEXT ACTIONS

### Today (Jan 18)
1. **Implement DEV/PROD isolation** - Workspace + lock file + branch rules
2. **Create this document on server** ✅
3. **Git commit all docs**

### Tomorrow (Jan 19)
1. **VARYS PM features** - Sprint planning, decision tracking
2. **Council decision tables** - Add to database
3. **Start Command Center** - New Bolt.new project

### This Week (Jan 20-25)
1. **AEGIS page** in Command Center
2. **ARGUS page** (cost tracking visible)
3. **Agent review tables** (ALOY expansion)

---

## 📍 DECISIONS MADE TODAY

| Decision | Category | Rationale |
|----------|----------|-----------|
| ARIA and Command Center are separate projects | Architecture | Isolation, redundancy, different failure domains |
| Command Center has built-in agent chat | Architecture | Don't depend on ARIA for agent interaction |
| THALIA owns design/aesthetics | Assignment | Clear ownership |
| MUSE coordinates creative projects | Assignment | Single point of creative direction |
| VARYS becomes PM | Assignment | Need dedicated project management |
| ALOY handles agent review | Assignment | Extends audit role naturally |
| DEV/PROD isolation required | Policy | Safety after accidental prod changes |
| Customer Portal and Public Website will be separate | Architecture | Future isolation |

---

*This document should be reviewed in Council meeting to ratify decisions.*
