# JANUARY BUILD SPRINT: Infrastructure & Agent Fleet

## MANDATE
**January 17-31: BUILD ONLY. No outreach. No business. Infrastructure and agents.**

February = Business. January = Foundation.

---

## BUILD TARGETS

### 1. VARYS LITE (Mission Guardian MVP)
**Effort:** 4-6 hours
**Value:** Daily accountability, drift detection, weekly reviews - automated

#### Components

**A. Daily Brief Generator (6 AM via HERMES)**
```
- Reads MASTER-LAUNCH-CALENDAR.md
- Calculates days to launch
- Identifies TODAY's focus from calendar
- Scans yesterday's git commits, categorizes by goal alignment
- Sends via Telegram
```

**B. Drift Detection Scanner**
```
- Monitors git commits for scope creep patterns
- Flags: "quick addition", "enhancement", "while we're at it", "one more thing"
- Alerts when work doesn't map to launch goals
- Weekly drift report
```

**C. Weekly Review Automation (Sunday 8 PM)**
```
- Aggregates week's git activity
- Pulls portfolio changes from aria_wins
- Triggers CHIRON weekly-review action
- Sends comprehensive report via HERMES
```

**D. Sacred Mission Documents**
```
/opt/leveredge/mission/
├── MISSION.md           # Why we exist
├── LAUNCH-DATE.md       # March 1, 2026 - IMMUTABLE
├── REVENUE-GOAL.md      # $30K MRR target
├── BOUNDARIES.md        # What we will NOT do before launch
└── PORTFOLIO-TARGET.md  # Win tracking
```

#### Implementation

**File:** `/opt/leveredge/control-plane/agents/varys/varys.py`

```python
"""
VARYS - The Mission Guardian
"The realm. Someone must."

Port: 8020
Functions:
- Daily briefs
- Drift detection
- Weekly reviews
- Mission document guardian
"""

from fastapi import FastAPI, BackgroundTasks
from datetime import datetime, timedelta
import httpx
import os
import re
import subprocess

app = FastAPI(title="VARYS", description="Mission Guardian")

HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
CHIRON_URL = os.getenv("CHIRON_URL", "http://chiron:8010")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")

MISSION_DIR = "/opt/leveredge/mission"
CALENDAR_PATH = "/opt/leveredge/MASTER-LAUNCH-CALENDAR.md"
LAUNCH_DATE = datetime(2026, 3, 1)

# Scope creep detection patterns
DRIFT_PATTERNS = [
    r"quick (addition|fix|change)",
    r"small (enhancement|tweak|update)",
    r"while we're at it",
    r"one more thing",
    r"might as well",
    r"real quick",
    r"shouldn't take long",
    r"just need to add",
]

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "varys", "role": "mission_guardian"}

@app.get("/days-to-launch")
async def days_to_launch():
    """Calculate days remaining to launch."""
    today = datetime.now()
    delta = LAUNCH_DATE - today
    return {
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_remaining": delta.days,
        "weeks_remaining": delta.days // 7,
        "urgency": "CRITICAL" if delta.days < 30 else "HIGH" if delta.days < 45 else "MODERATE"
    }

@app.get("/todays-focus")
async def todays_focus():
    """Extract today's focus from MASTER-LAUNCH-CALENDAR."""
    try:
        with open(CALENDAR_PATH, 'r') as f:
            calendar = f.read()
        
        today = datetime.now()
        today_str = today.strftime("%B %d").lstrip("0").replace(" 0", " ")
        
        # Find current week/phase
        lines = calendar.split('\n')
        current_focus = "Review MASTER-LAUNCH-CALENDAR for today's focus"
        
        for i, line in enumerate(lines):
            if today_str in line or today.strftime("%b %d") in line:
                # Get context around this date
                start = max(0, i - 5)
                end = min(len(lines), i + 5)
                current_focus = '\n'.join(lines[start:end])
                break
        
        return {
            "date": today.strftime("%Y-%m-%d"),
            "day_of_week": today.strftime("%A"),
            "focus": current_focus,
            "days_to_launch": (LAUNCH_DATE - today).days
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/scan-drift")
async def scan_drift(days: int = 1):
    """Scan recent git commits for scope creep patterns."""
    try:
        # Get recent commits
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--oneline", "--all"],
            cwd="/opt/leveredge",
            capture_output=True,
            text=True
        )
        commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        drift_detected = []
        for commit in commits:
            for pattern in DRIFT_PATTERNS:
                if re.search(pattern, commit, re.IGNORECASE):
                    drift_detected.append({
                        "commit": commit,
                        "pattern": pattern,
                        "risk": "SCOPE_CREEP"
                    })
        
        return {
            "period_days": days,
            "total_commits": len(commits),
            "drift_flags": len(drift_detected),
            "drift_details": drift_detected,
            "status": "CLEAN" if not drift_detected else "DRIFT_DETECTED"
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/daily-brief")
async def generate_daily_brief():
    """Generate and send daily brief via HERMES."""
    days_info = await days_to_launch()
    focus_info = await todays_focus()
    drift_info = await scan_drift(days=1)
    
    brief = f"""
🌅 **DAILY BRIEF** - {datetime.now().strftime("%A, %B %d, %Y")}

⏰ **{days_info['days_remaining']} DAYS TO LAUNCH**
Status: {days_info['urgency']}

📋 **TODAY'S FOCUS**
{focus_info.get('focus', 'Check MASTER-LAUNCH-CALENDAR')}

📊 **YESTERDAY'S ACTIVITY**
Commits: {drift_info.get('total_commits', 0)}
Drift flags: {drift_info.get('drift_flags', 0)}
Status: {drift_info.get('status', 'UNKNOWN')}

{"⚠️ **DRIFT DETECTED** - Review commits for scope creep" if drift_info.get('drift_flags', 0) > 0 else "✅ On track"}

---
*VARYS watches. The mission endures.*
"""
    
    # Send via HERMES
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "channel": "telegram",
                    "message": brief,
                    "priority": "normal"
                }
            )
        except:
            pass  # Log but don't fail
    
    # Log to Event Bus
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": "varys.daily_brief",
                    "payload": {
                        "days_to_launch": days_info['days_remaining'],
                        "drift_status": drift_info.get('status'),
                        "timestamp": datetime.now().isoformat()
                    }
                }
            )
        except:
            pass
    
    return {"status": "sent", "brief": brief}

@app.post("/weekly-review")
async def generate_weekly_review():
    """Generate weekly review via CHIRON and send via HERMES."""
    drift_info = await scan_drift(days=7)
    days_info = await days_to_launch()
    
    # Get portfolio summary (would query Supabase)
    # For now, placeholder
    
    # Trigger CHIRON weekly review
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            chiron_response = await client.post(
                f"{CHIRON_URL}/weekly-review",
                json={
                    "wins": [],  # Would pull from aria_wins
                    "losses": [],
                    "lessons": [],
                    "context": f"{days_info['days_remaining']} days to March 1 launch"
                }
            )
            chiron_review = chiron_response.json()
        except Exception as e:
            chiron_review = {"error": str(e)}
    
    review = f"""
📅 **WEEKLY REVIEW** - Week of {datetime.now().strftime("%B %d, %Y")}

⏰ **{days_info['days_remaining']} DAYS TO LAUNCH**

📊 **THIS WEEK'S STATS**
Total commits: {drift_info.get('total_commits', 0)}
Drift flags: {drift_info.get('drift_flags', 0)}

🎯 **CHIRON'S ANALYSIS**
{chiron_review.get('response', chiron_review.get('weekly_review', 'Review unavailable'))}

---
*VARYS watches. The realm endures.*
"""
    
    # Send via HERMES
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "channel": "telegram",
                    "message": review,
                    "priority": "high"
                }
            )
        except:
            pass
    
    return {"status": "sent", "review": review}

@app.get("/mission/{document}")
async def get_mission_document(document: str):
    """Retrieve sacred mission documents."""
    allowed = ["MISSION", "LAUNCH-DATE", "REVENUE-GOAL", "BOUNDARIES", "PORTFOLIO-TARGET"]
    if document.upper() not in allowed:
        return {"error": f"Unknown document. Allowed: {allowed}"}
    
    path = f"{MISSION_DIR}/{document.upper()}.md"
    try:
        with open(path, 'r') as f:
            return {"document": document, "content": f.read()}
    except FileNotFoundError:
        return {"error": f"Document not found: {path}"}

@app.post("/validate-decision")
async def validate_decision(decision: dict):
    """Validate a decision against mission alignment."""
    description = decision.get("description", "")
    
    # Check against boundaries
    try:
        with open(f"{MISSION_DIR}/BOUNDARIES.md", 'r') as f:
            boundaries = f.read().lower()
    except:
        boundaries = ""
    
    # Simple keyword checks
    red_flags = []
    
    # Check for scope creep language
    for pattern in DRIFT_PATTERNS:
        if re.search(pattern, description, re.IGNORECASE):
            red_flags.append(f"Scope creep language detected: {pattern}")
    
    # Check if it mentions post-launch items
    post_launch_keywords = ["nice to have", "later", "after launch", "eventually", "someday"]
    for keyword in post_launch_keywords:
        if keyword in description.lower():
            red_flags.append(f"Post-launch indicator: '{keyword}'")
    
    alignment = "ALIGNED" if not red_flags else "REVIEW_NEEDED"
    
    return {
        "decision": description,
        "alignment": alignment,
        "red_flags": red_flags,
        "recommendation": "Proceed" if alignment == "ALIGNED" else "Consult CHIRON before proceeding"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
```

#### Docker Configuration

**File:** `/opt/leveredge/control-plane/agents/varys/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn httpx

COPY varys.py .

# Install git for commit scanning
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

EXPOSE 8020

CMD ["uvicorn", "varys:app", "--host", "0.0.0.0", "--port", "8020"]
```

#### Docker Compose Addition

```yaml
  varys:
    build:
      context: ./agents/varys
      dockerfile: Dockerfile
    container_name: varys
    ports:
      - "8020:8020"
    environment:
      - HERMES_URL=http://hermes:8014
      - CHIRON_URL=http://chiron:8010
      - EVENT_BUS_URL=http://event-bus:8099
    volumes:
      - /opt/leveredge:/opt/leveredge:ro
    networks:
      - control-plane-net
    restart: unless-stopped
```

#### Cron Jobs (via n8n or system cron)

```bash
# Daily brief at 6 AM
0 6 * * * curl -X POST http://localhost:8020/daily-brief

# Weekly review Sunday 8 PM
0 20 * * 0 curl -X POST http://localhost:8020/weekly-review
```

---

### 2. MISSION DOCUMENTS (Sacred Texts)

**Directory:** `/opt/leveredge/mission/`

#### MISSION.md
```markdown
# LEVEREDGE AI MISSION

## WHY WE EXIST
To liberate compliance professionals from soul-crushing manual work through intelligent automation.

## WHAT SUCCESS LOOKS LIKE
- First paying client by March 1, 2026
- $30K MRR within 6 months of launch
- Systems that work while Damon sleeps

## CORE VALUES
- Ship fast, iterate faster
- Build what clients pay for
- Automate everything, including ourselves

## THE PROMISE
Every system we build must pass the "Damon Test":
Would this let Damon take a week off without the business stopping?
```

#### LAUNCH-DATE.md
```markdown
# LAUNCH DATE

## MARCH 1, 2026

**THIS DATE IS IMMUTABLE.**

No exceptions. No extensions. No "just one more week."

### Milestones
- January 31: All infrastructure complete
- February 1-14: Business preparation
- February 15-28: Outreach execution
- March 1: IN BUSINESS

### What "Launch" Means
- Can accept paying clients
- Can deliver promised services
- Has sales process ready
- Has at least one demo-able solution
```

#### REVENUE-GOAL.md
```markdown
# REVENUE GOAL

## $30K MRR

Monthly Recurring Revenue target within 6 months of launch.

### Path to $30K
- 3 clients at $10K/month, OR
- 6 clients at $5K/month, OR
- 10 clients at $3K/month

### Pricing Tiers (Draft)
- Tier 1: $2,500-5,000 (Lead capture, chatbots)
- Tier 2: $5,000-10,000 (Multi-step agents, compliance workflows)
- Tier 3: $10,000-25,000 (Enterprise multi-tenant solutions)

### Current Portfolio Value
$58,500 - $117,000 across 28 wins (proof of capability)
```

#### BOUNDARIES.md
```markdown
# BOUNDARIES

## WHAT WE WILL NOT DO BEFORE LAUNCH

### Infrastructure
- ❌ Perfect Greek UI for AEGIS (basic works)
- ❌ Full creative fleet (MUSE, DESIGNER, etc.)
- ❌ Advanced VARYS features beyond daily/weekly briefs
- ❌ Complex credential rotation beyond MVP

### Business
- ❌ LinkedIn content strategy
- ❌ Conference attendance
- ❌ Partnership discussions
- ❌ Hiring planning

### Technical
- ❌ New programming languages
- ❌ Complex CRM systems
- ❌ Perfect documentation
- ❌ Comprehensive test suites

## WHAT WE WILL DO

### January (BUILD)
- ✅ VARYS Lite (daily briefs, drift detection)
- ✅ Agent fleet completion
- ✅ OLYMPUS stabilization
- ✅ ARIA hardening

### February (BUSINESS)
- ✅ Portfolio documentation
- ✅ Pricing finalization
- ✅ Sales materials
- ✅ Outreach execution
```

#### PORTFOLIO-TARGET.md
```markdown
# PORTFOLIO TARGET

## CURRENT STATUS
- Wins: 28
- Value: $58,500 - $117,000
- Updated: January 17, 2026

## TARGET BY LAUNCH
- Documented case studies: 3-5
- Demo-ready automations: 2
- Video walkthroughs: 2

## TRACKING
Portfolio updates logged to `aria_wins` and `aria_portfolio_summary` tables.
VARYS monitors via weekly reviews.
```

---

### 3. N8N WORKFLOW: VARYS SCHEDULER

Create workflow in control plane n8n for scheduled triggers.

**Workflow:** "VARYS Scheduler"

```json
{
  "name": "VARYS Scheduler",
  "nodes": [
    {
      "name": "Daily Brief Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {
          "interval": [{"field": "cronExpression", "expression": "0 6 * * *"}]
        }
      }
    },
    {
      "name": "Call Daily Brief",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://varys:8020/daily-brief",
        "method": "POST"
      }
    },
    {
      "name": "Weekly Review Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {
          "interval": [{"field": "cronExpression", "expression": "0 20 * * 0"}]
        }
      }
    },
    {
      "name": "Call Weekly Review",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://varys:8020/weekly-review",
        "method": "POST"
      }
    }
  ]
}
```

---

### 4. AGENT REGISTRY UPDATE

Add VARYS to `/opt/leveredge/config/agent-registry.yaml`:

```yaml
  varys:
    name: "VARYS"
    description: "Mission Guardian - accountability, drift detection, strategic alignment"
    port: 8020
    health_endpoint: "/health"
    actions:
      daily-brief:
        description: "Generate and send daily accountability brief"
        endpoint: "/daily-brief"
        method: POST
        params: {}
      weekly-review:
        description: "Generate comprehensive weekly review"
        endpoint: "/weekly-review"
        method: POST
        params: {}
      days-to-launch:
        description: "Get days remaining until launch"
        endpoint: "/days-to-launch"
        method: GET
        params: {}
      todays-focus:
        description: "Get today's focus from calendar"
        endpoint: "/todays-focus"
        method: GET
        params: {}
      scan-drift:
        description: "Scan for scope creep in recent commits"
        endpoint: "/scan-drift"
        method: GET
        params:
          days:
            type: integer
            default: 1
      validate-decision:
        description: "Validate a decision against mission alignment"
        endpoint: "/validate-decision"
        method: POST
        params:
          description:
            type: string
            required: true
```

---

## EXECUTION ORDER

| # | Task | Effort | Command |
|---|------|--------|---------|
| 1 | Create mission documents | 10 min | In this spec |
| 2 | Create VARYS agent | 30 min | Python + Docker |
| 3 | Add to docker-compose | 5 min | YAML update |
| 4 | Update agent registry | 5 min | YAML update |
| 5 | Create n8n scheduler workflow | 15 min | Control plane |
| 6 | Test daily brief | 5 min | curl |
| 7 | Test weekly review | 5 min | curl |
| 8 | Git commit | 2 min | All changes |

**Total estimated time:** 1.5 hours

---

## SUCCESS CRITERIA

- [ ] VARYS container running on port 8020
- [ ] `/health` returns healthy
- [ ] `/daily-brief` generates and sends via HERMES
- [ ] `/weekly-review` triggers CHIRON and sends via HERMES
- [ ] `/scan-drift` detects scope creep patterns
- [ ] Mission documents created in /opt/leveredge/mission/
- [ ] Agent registry updated with VARYS
- [ ] n8n scheduler workflow created and active
- [ ] Telegram receives test daily brief

---

## GIT COMMIT MESSAGE

```
Add VARYS Mission Guardian agent

The realm. Someone must.

Components:
- VARYS FastAPI agent (port 8020)
- Daily brief generation (6 AM)
- Weekly review automation (Sunday 8 PM)
- Drift detection for scope creep
- Mission document guardian
- Sacred texts: MISSION, LAUNCH-DATE, REVENUE-GOAL, BOUNDARIES

Features:
- Days to launch calculator
- Today's focus extractor
- Git commit drift scanning
- Decision validation against mission
- HERMES integration for alerts
- CHIRON integration for reviews
```
