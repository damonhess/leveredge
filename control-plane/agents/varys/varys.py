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
