#!/usr/bin/env python3
"""
REMINDERS-V2 - Proactive Reminders Agent
Port: 8065

Smart reminder system with:
- User pattern-based timing optimization
- Context-aware nudges
- Deadline approaching alerts
- Daily briefing expansion
- ADHD-friendly motivational check-ins
"""

import os
import json
import httpx
import asyncio
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from patterns import PatternAnalyzer, UserPatterns
from nudges import NudgeGenerator, NudgeType

# Configuration
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GOOGLE_CALENDAR_CREDENTIALS = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "")
DB_PATH = os.getenv("REMINDERS_DB_PATH", "/app/data/reminders_v2.db")
PATTERNS_PATH = os.getenv("PATTERNS_PATH", "/app/data/patterns.json")

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Initialize pattern analyzer and nudge generator
pattern_analyzer = PatternAnalyzer(PATTERNS_PATH)
nudge_generator = NudgeGenerator()

# Database setup
def init_db():
    """Initialize SQLite database for reminders and tracking"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Reminders table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'default',
            title TEXT NOT NULL,
            message TEXT,
            reminder_type TEXT DEFAULT 'standard',
            priority TEXT DEFAULT 'normal',
            scheduled_time TEXT NOT NULL,
            repeat_pattern TEXT,
            context TEXT,
            tags TEXT,
            source TEXT DEFAULT 'manual',
            status TEXT DEFAULT 'pending',
            triggered_at TEXT,
            acknowledged_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Activity log for pattern analysis
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            activity_type TEXT NOT NULL,
            context TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            day_of_week INTEGER,
            hour_of_day INTEGER,
            response_time_seconds REAL
        )
    ''')

    # Check-in history
    c.execute('''
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            checkin_type TEXT NOT NULL,
            mood_score INTEGER,
            focus_score INTEGER,
            energy_level TEXT,
            current_task TEXT,
            blockers TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Briefing history
    c.execute('''
        CREATE TABLE IF NOT EXISTS briefings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            briefing_type TEXT NOT NULL,
            content TEXT,
            items_count INTEGER,
            delivered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            opened_at TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()


class ReminderType(str, Enum):
    STANDARD = "standard"
    DEADLINE = "deadline"
    CHECKIN = "checkin"
    BRIEFING = "briefing"
    MOTIVATIONAL = "motivational"
    CONTEXT_NUDGE = "context_nudge"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RepeatPattern(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


# Request/Response Models
class ScheduleReminderRequest(BaseModel):
    title: str
    message: Optional[str] = None
    scheduled_time: Optional[str] = None  # ISO format, or None for smart timing
    reminder_type: ReminderType = ReminderType.STANDARD
    priority: Priority = Priority.NORMAL
    repeat_pattern: RepeatPattern = RepeatPattern.NONE
    context: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    user_id: str = "default"
    use_smart_timing: bool = True


class TriggerCheckRequest(BaseModel):
    user_id: str = "default"
    force: bool = False
    check_types: Optional[List[str]] = None  # deadline, checkin, briefing, motivation


class CheckInRequest(BaseModel):
    user_id: str = "default"
    mood_score: Optional[int] = Field(None, ge=1, le=10)
    focus_score: Optional[int] = Field(None, ge=1, le=10)
    energy_level: Optional[str] = None  # low, medium, high
    current_task: Optional[str] = None
    blockers: Optional[str] = None


# Helper functions
async def log_to_event_bus(action: str, target: str = "", details: dict = None):
    """Log events to the event bus"""
    if details is None:
        details = {}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "REMINDERS-V2",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")


async def send_reminder_via_hermes(message: str, priority: str = "normal") -> bool:
    """Send reminder notification through HERMES"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "message": message,
                    "priority": priority,
                    "channel": "telegram"
                },
                timeout=10.0
            )
            return resp.status_code == 200
    except Exception as e:
        print(f"HERMES notification failed: {e}")
        return False


async def fetch_tasks_from_supabase(user_id: str = "default") -> List[Dict]:
    """Fetch tasks from Supabase aria_tasks table"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/aria_tasks",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Prefer": "return=representation"
                },
                params={
                    "select": "*",
                    "status": "neq.completed",
                    "order": "due_date.asc"
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"Supabase fetch failed: {e}")
    return []


async def fetch_calendar_events(user_id: str = "default", days_ahead: int = 7) -> List[Dict]:
    """Fetch calendar events from Google Calendar API"""
    # Placeholder - would integrate with Google Calendar API
    # For now, return empty list
    return []


def get_pending_reminders(user_id: str = "default") -> List[Dict]:
    """Get all pending reminders for a user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT * FROM reminders
        WHERE user_id = ? AND status = 'pending'
        ORDER BY scheduled_time ASC
    ''', (user_id,))

    reminders = [dict(row) for row in c.fetchall()]
    conn.close()

    # Parse JSON fields
    for r in reminders:
        if r.get('context'):
            r['context'] = json.loads(r['context'])
        if r.get('tags'):
            r['tags'] = json.loads(r['tags'])

    return reminders


def record_activity(user_id: str, activity_type: str, context: dict = None, response_time: float = None):
    """Record user activity for pattern analysis"""
    now = datetime.now()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT INTO activity_log (user_id, activity_type, context, day_of_week, hour_of_day, response_time_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        activity_type,
        json.dumps(context) if context else None,
        now.weekday(),
        now.hour,
        response_time
    ))

    conn.commit()
    conn.close()


async def check_deadlines(user_id: str = "default") -> List[Dict]:
    """Check for approaching deadlines from tasks and calendar"""
    alerts = []
    now = datetime.now()

    # Check Supabase tasks
    tasks = await fetch_tasks_from_supabase(user_id)
    for task in tasks:
        if task.get('due_date'):
            try:
                due = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                time_until = due - now

                if time_until.total_seconds() <= 0:
                    alerts.append({
                        "type": "overdue",
                        "source": "task",
                        "title": task.get('title', 'Untitled Task'),
                        "due_date": task['due_date'],
                        "overdue_hours": abs(time_until.total_seconds()) / 3600,
                        "priority": "urgent"
                    })
                elif time_until.total_seconds() <= 3600:  # 1 hour
                    alerts.append({
                        "type": "imminent",
                        "source": "task",
                        "title": task.get('title', 'Untitled Task'),
                        "due_date": task['due_date'],
                        "hours_remaining": time_until.total_seconds() / 3600,
                        "priority": "high"
                    })
                elif time_until.total_seconds() <= 86400:  # 24 hours
                    alerts.append({
                        "type": "approaching",
                        "source": "task",
                        "title": task.get('title', 'Untitled Task'),
                        "due_date": task['due_date'],
                        "hours_remaining": time_until.total_seconds() / 3600,
                        "priority": "normal"
                    })
            except (ValueError, TypeError):
                pass

    # Check calendar events
    events = await fetch_calendar_events(user_id)
    for event in events:
        if event.get('start'):
            try:
                start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                time_until = start - now

                if 0 < time_until.total_seconds() <= 900:  # 15 minutes
                    alerts.append({
                        "type": "starting_soon",
                        "source": "calendar",
                        "title": event.get('summary', 'Event'),
                        "start_time": event['start'],
                        "minutes_remaining": time_until.total_seconds() / 60,
                        "priority": "high"
                    })
            except (ValueError, TypeError):
                pass

    return alerts


async def generate_daily_briefing(user_id: str = "default") -> Dict:
    """Generate comprehensive daily briefing"""
    now = datetime.now()

    # Gather all relevant information
    pending_reminders = get_pending_reminders(user_id)
    tasks = await fetch_tasks_from_supabase(user_id)
    calendar_events = await fetch_calendar_events(user_id, days_ahead=1)
    deadline_alerts = await check_deadlines(user_id)

    # Get user patterns for personalization
    patterns = pattern_analyzer.get_patterns(user_id)

    # Build briefing
    briefing = {
        "type": "daily",
        "generated_at": now.isoformat(),
        "greeting": _get_time_appropriate_greeting(now.hour),
        "sections": []
    }

    # Weather/mood section (placeholder for future integration)
    briefing["sections"].append({
        "title": "Today's Focus",
        "items": _get_focus_suggestions(patterns, tasks)
    })

    # Urgent items
    urgent_items = [a for a in deadline_alerts if a.get('priority') in ['urgent', 'high']]
    if urgent_items:
        briefing["sections"].append({
            "title": "Needs Immediate Attention",
            "items": urgent_items,
            "priority": "high"
        })

    # Today's schedule
    today_events = [e for e in calendar_events if _is_today(e.get('start', ''))]
    if today_events:
        briefing["sections"].append({
            "title": "Today's Schedule",
            "items": today_events
        })

    # Tasks overview
    task_summary = {
        "total": len(tasks),
        "due_today": len([t for t in tasks if _is_today(t.get('due_date', ''))]),
        "overdue": len([t for t in tasks if t.get('due_date') and _is_overdue(t['due_date'])])
    }
    briefing["sections"].append({
        "title": "Tasks Overview",
        "summary": task_summary,
        "top_tasks": tasks[:5] if tasks else []
    })

    # Motivational element (ADHD-friendly)
    briefing["motivation"] = nudge_generator.get_adhd_motivation(
        time_of_day=_get_time_of_day(now.hour),
        task_count=len(tasks),
        patterns=patterns
    )

    # Record briefing
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO briefings (user_id, briefing_type, content, items_count)
        VALUES (?, ?, ?, ?)
    ''', (user_id, 'daily', json.dumps(briefing), len(tasks)))
    conn.commit()
    conn.close()

    return briefing


def _get_time_appropriate_greeting(hour: int) -> str:
    """Get greeting based on time of day"""
    if 5 <= hour < 12:
        return "Good morning! Here's your daily briefing."
    elif 12 <= hour < 17:
        return "Good afternoon! Here's what you need to know."
    elif 17 <= hour < 21:
        return "Good evening! Let's wrap up the day."
    else:
        return "Working late? Here's a quick update."


def _get_time_of_day(hour: int) -> str:
    """Get time of day category"""
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _is_today(date_str: str) -> bool:
    """Check if a date string is today"""
    if not date_str:
        return False
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.date() == datetime.now().date()
    except (ValueError, TypeError):
        return False


def _is_overdue(date_str: str) -> bool:
    """Check if a date string is in the past"""
    if not date_str:
        return False
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date < datetime.now()
    except (ValueError, TypeError):
        return False


def _get_focus_suggestions(patterns: UserPatterns, tasks: List[Dict]) -> List[str]:
    """Get focus suggestions based on patterns and current tasks"""
    suggestions = []

    if patterns and patterns.peak_focus_hours:
        peak_hours = patterns.peak_focus_hours
        suggestions.append(f"Your peak focus time is typically {peak_hours[0]}:00-{peak_hours[-1]+1}:00")

    high_priority = [t for t in tasks if t.get('priority') == 'high']
    if high_priority:
        suggestions.append(f"You have {len(high_priority)} high-priority tasks to tackle")

    if not suggestions:
        suggestions.append("Ready to make today productive!")

    return suggestions


# Scheduled job functions
async def scheduled_reminder_check():
    """Check and trigger due reminders"""
    now = datetime.now()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get reminders that are due
    c.execute('''
        SELECT * FROM reminders
        WHERE status = 'pending' AND scheduled_time <= ?
    ''', (now.isoformat(),))

    due_reminders = [dict(row) for row in c.fetchall()]

    for reminder in due_reminders:
        # Build message
        message = f"<b>{reminder['title']}</b>"
        if reminder.get('message'):
            message += f"\n\n{reminder['message']}"

        # Add context if available
        if reminder.get('context'):
            ctx = json.loads(reminder['context'])
            if ctx.get('task_link'):
                message += f"\n\nTask: {ctx['task_link']}"

        # Send via HERMES
        success = await send_reminder_via_hermes(message, reminder.get('priority', 'normal'))

        if success:
            # Update status
            c.execute('''
                UPDATE reminders
                SET status = 'triggered', triggered_at = ?, updated_at = ?
                WHERE reminder_id = ?
            ''', (now.isoformat(), now.isoformat(), reminder['reminder_id']))

            # Log to event bus
            await log_to_event_bus(
                "reminder_triggered",
                target=reminder['user_id'],
                details={"reminder_id": reminder['reminder_id'], "title": reminder['title']}
            )

            # Handle repeat pattern
            if reminder.get('repeat_pattern') and reminder['repeat_pattern'] != 'none':
                next_time = _calculate_next_occurrence(now, reminder['repeat_pattern'])
                if next_time:
                    new_id = str(uuid.uuid4())[:8]
                    c.execute('''
                        INSERT INTO reminders (reminder_id, user_id, title, message, reminder_type,
                            priority, scheduled_time, repeat_pattern, context, tags, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        new_id, reminder['user_id'], reminder['title'], reminder['message'],
                        reminder['reminder_type'], reminder['priority'], next_time.isoformat(),
                        reminder['repeat_pattern'], reminder.get('context'), reminder.get('tags'),
                        'repeat'
                    ))

    conn.commit()
    conn.close()


def _calculate_next_occurrence(current: datetime, pattern: str) -> Optional[datetime]:
    """Calculate next occurrence based on repeat pattern"""
    if pattern == "daily":
        return current + timedelta(days=1)
    elif pattern == "weekdays":
        next_day = current + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day += timedelta(days=1)
        return next_day
    elif pattern == "weekly":
        return current + timedelta(weeks=1)
    elif pattern == "biweekly":
        return current + timedelta(weeks=2)
    elif pattern == "monthly":
        return current + timedelta(days=30)  # Simplified
    return None


async def scheduled_deadline_check():
    """Periodic check for approaching deadlines"""
    alerts = await check_deadlines()

    for alert in alerts:
        if alert.get('priority') in ['urgent', 'high']:
            if alert['type'] == 'overdue':
                message = f"OVERDUE: {alert['title']}\nWas due: {alert['due_date']}"
            elif alert['type'] == 'imminent':
                message = f"DUE SOON: {alert['title']}\nDue in {alert['hours_remaining']:.1f} hours"
            else:
                message = f"REMINDER: {alert['title']} is due within 24 hours"

            await send_reminder_via_hermes(message, alert['priority'])
            await log_to_event_bus(
                "deadline_alert",
                details={"alert_type": alert['type'], "title": alert['title']}
            )


async def scheduled_adhd_checkin():
    """Periodic ADHD-friendly motivational check-ins"""
    # Get current time context
    now = datetime.now()
    time_of_day = _get_time_of_day(now.hour)

    # Only during reasonable hours
    if now.hour < 8 or now.hour > 21:
        return

    # Get patterns to personalize
    patterns = pattern_analyzer.get_patterns("default")

    # Generate appropriate nudge
    nudge = nudge_generator.get_adhd_checkin(
        time_of_day=time_of_day,
        patterns=patterns
    )

    if nudge:
        await send_reminder_via_hermes(nudge, "normal")
        await log_to_event_bus("adhd_checkin_sent", details={"time_of_day": time_of_day})


async def scheduled_morning_briefing():
    """Send morning daily briefing"""
    briefing = await generate_daily_briefing("default")

    # Format for notification
    message = f"<b>{briefing['greeting']}</b>\n\n"

    for section in briefing['sections'][:3]:  # Limit to top 3 sections
        message += f"<b>{section['title']}</b>\n"
        if section.get('summary'):
            s = section['summary']
            message += f"Tasks: {s['total']} total, {s['due_today']} due today, {s['overdue']} overdue\n"
        elif section.get('items'):
            for item in section['items'][:3]:
                if isinstance(item, str):
                    message += f"- {item}\n"
                elif isinstance(item, dict):
                    message += f"- {item.get('title', str(item))}\n"
        message += "\n"

    if briefing.get('motivation'):
        message += f"\n{briefing['motivation']}"

    await send_reminder_via_hermes(message, "normal")
    await log_to_event_bus("morning_briefing_sent", details={"sections": len(briefing['sections'])})


# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage scheduler lifecycle"""
    # Start scheduler
    scheduler.add_job(
        scheduled_reminder_check,
        IntervalTrigger(minutes=1),
        id="reminder_check",
        replace_existing=True
    )

    scheduler.add_job(
        scheduled_deadline_check,
        IntervalTrigger(minutes=15),
        id="deadline_check",
        replace_existing=True
    )

    scheduler.add_job(
        scheduled_adhd_checkin,
        IntervalTrigger(hours=2),
        id="adhd_checkin",
        replace_existing=True
    )

    # Morning briefing at 8 AM
    scheduler.add_job(
        scheduled_morning_briefing,
        CronTrigger(hour=8, minute=0),
        id="morning_briefing",
        replace_existing=True
    )

    scheduler.start()

    await log_to_event_bus("agent_started", details={"port": 8065})

    yield

    scheduler.shutdown()
    await log_to_event_bus("agent_stopped")


# FastAPI App
app = FastAPI(
    title="REMINDERS-V2",
    description="Proactive Reminders Agent with Smart Timing and ADHD Support",
    version="2.0.0",
    lifespan=lifespan
)


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM reminders WHERE status = 'pending'")
    pending_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM reminders WHERE triggered_at > datetime('now', '-24 hours')")
    triggered_today = c.fetchone()[0]

    conn.close()

    return {
        "status": "healthy",
        "agent": "REMINDERS-V2",
        "port": 8065,
        "scheduler_running": scheduler.running,
        "pending_reminders": pending_count,
        "triggered_last_24h": triggered_today,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/schedule")
async def schedule_reminder(req: ScheduleReminderRequest):
    """Schedule a new reminder with optional smart timing"""
    reminder_id = str(uuid.uuid4())[:8]

    # Determine scheduled time
    if req.scheduled_time:
        scheduled_time = datetime.fromisoformat(req.scheduled_time)
    elif req.use_smart_timing:
        # Use pattern analyzer for optimal timing
        patterns = pattern_analyzer.get_patterns(req.user_id)
        scheduled_time = pattern_analyzer.get_optimal_reminder_time(
            user_id=req.user_id,
            reminder_type=req.reminder_type.value,
            priority=req.priority.value
        )
    else:
        # Default to now + 1 hour
        scheduled_time = datetime.now() + timedelta(hours=1)

    # Store reminder
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT INTO reminders (reminder_id, user_id, title, message, reminder_type,
            priority, scheduled_time, repeat_pattern, context, tags, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        reminder_id,
        req.user_id,
        req.title,
        req.message,
        req.reminder_type.value,
        req.priority.value,
        scheduled_time.isoformat(),
        req.repeat_pattern.value,
        json.dumps(req.context) if req.context else None,
        json.dumps(req.tags) if req.tags else None,
        "api"
    ))

    conn.commit()
    conn.close()

    await log_to_event_bus(
        "reminder_scheduled",
        target=req.user_id,
        details={
            "reminder_id": reminder_id,
            "title": req.title,
            "scheduled_time": scheduled_time.isoformat(),
            "smart_timing": req.use_smart_timing
        }
    )

    return {
        "reminder_id": reminder_id,
        "status": "scheduled",
        "scheduled_time": scheduled_time.isoformat(),
        "smart_timing_used": req.use_smart_timing and not req.scheduled_time
    }


@app.get("/pending")
async def get_pending(
    user_id: str = Query("default"),
    include_context: bool = Query(False)
):
    """Get all pending reminders for a user"""
    reminders = get_pending_reminders(user_id)

    if not include_context:
        for r in reminders:
            r.pop('context', None)

    return {
        "user_id": user_id,
        "pending": reminders,
        "count": len(reminders)
    }


@app.post("/trigger")
async def trigger_check(req: TriggerCheckRequest):
    """Manually trigger reminder/deadline checks"""
    results = {"triggered": [], "user_id": req.user_id}

    check_types = req.check_types or ["reminder", "deadline", "briefing"]

    if "reminder" in check_types:
        await scheduled_reminder_check()
        results["triggered"].append("reminder_check")

    if "deadline" in check_types:
        alerts = await check_deadlines(req.user_id)
        results["deadline_alerts"] = alerts
        results["triggered"].append("deadline_check")

    if "briefing" in check_types:
        briefing = await generate_daily_briefing(req.user_id)
        results["briefing"] = briefing
        results["triggered"].append("briefing")

    if "motivation" in check_types or "checkin" in check_types:
        await scheduled_adhd_checkin()
        results["triggered"].append("motivation_checkin")

    await log_to_event_bus(
        "manual_trigger",
        target=req.user_id,
        details={"check_types": check_types}
    )

    return results


@app.get("/patterns/{user_id}")
async def get_user_patterns(user_id: str):
    """Get activity patterns for a user"""
    patterns = pattern_analyzer.get_patterns(user_id)

    # Get activity stats from database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        SELECT activity_type, COUNT(*) as count,
               AVG(response_time_seconds) as avg_response_time
        FROM activity_log
        WHERE user_id = ?
        GROUP BY activity_type
    ''', (user_id,))

    activity_summary = [
        {"type": row[0], "count": row[1], "avg_response_time": row[2]}
        for row in c.fetchall()
    ]

    c.execute('''
        SELECT hour_of_day, COUNT(*) as count
        FROM activity_log
        WHERE user_id = ?
        GROUP BY hour_of_day
        ORDER BY count DESC
        LIMIT 5
    ''', (user_id,))

    peak_hours = [row[0] for row in c.fetchall()]

    conn.close()

    return {
        "user_id": user_id,
        "patterns": patterns.to_dict() if patterns else None,
        "activity_summary": activity_summary,
        "peak_activity_hours": peak_hours,
        "analyzed_at": datetime.now().isoformat()
    }


@app.post("/checkin")
async def record_checkin(req: CheckInRequest):
    """Record an ADHD-friendly check-in response"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT INTO checkins (user_id, checkin_type, mood_score, focus_score,
            energy_level, current_task, blockers)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        req.user_id,
        "manual",
        req.mood_score,
        req.focus_score,
        req.energy_level,
        req.current_task,
        req.blockers
    ))

    conn.commit()
    conn.close()

    # Update pattern analyzer
    record_activity(req.user_id, "checkin", {
        "mood": req.mood_score,
        "focus": req.focus_score,
        "energy": req.energy_level
    })

    # Generate contextual response
    response = nudge_generator.get_checkin_response(
        mood=req.mood_score,
        focus=req.focus_score,
        energy=req.energy_level,
        current_task=req.current_task,
        blockers=req.blockers
    )

    await log_to_event_bus(
        "checkin_recorded",
        target=req.user_id,
        details={"mood": req.mood_score, "focus": req.focus_score}
    )

    return {
        "status": "recorded",
        "response": response,
        "suggestions": nudge_generator.get_focus_suggestions(
            focus_score=req.focus_score,
            energy_level=req.energy_level
        )
    }


@app.get("/briefing/{user_id}")
async def get_briefing(user_id: str, briefing_type: str = "daily"):
    """Generate and return a briefing for a user"""
    if briefing_type == "daily":
        briefing = await generate_daily_briefing(user_id)
    else:
        # Quick briefing
        briefing = {
            "type": "quick",
            "pending_reminders": len(get_pending_reminders(user_id)),
            "deadline_alerts": await check_deadlines(user_id),
            "generated_at": datetime.now().isoformat()
        }

    return briefing


@app.delete("/reminder/{reminder_id}")
async def cancel_reminder(reminder_id: str):
    """Cancel a pending reminder"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM reminders WHERE reminder_id = ?", (reminder_id,))
    reminder = c.fetchone()

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    c.execute('''
        UPDATE reminders SET status = 'cancelled', updated_at = ?
        WHERE reminder_id = ?
    ''', (datetime.now().isoformat(), reminder_id))

    conn.commit()
    conn.close()

    await log_to_event_bus("reminder_cancelled", details={"reminder_id": reminder_id})

    return {"status": "cancelled", "reminder_id": reminder_id}


@app.post("/nudge")
async def send_contextual_nudge(
    user_id: str = "default",
    context: Optional[str] = None,
    nudge_type: Optional[str] = None
):
    """Send a context-aware nudge immediately"""
    patterns = pattern_analyzer.get_patterns(user_id)

    if nudge_type:
        nudge = nudge_generator.get_nudge_by_type(NudgeType(nudge_type), patterns)
    else:
        nudge = nudge_generator.get_contextual_nudge(
            context=context,
            time_of_day=_get_time_of_day(datetime.now().hour),
            patterns=patterns
        )

    if nudge:
        await send_reminder_via_hermes(nudge, "normal")
        await log_to_event_bus(
            "nudge_sent",
            target=user_id,
            details={"nudge_type": nudge_type, "context": context}
        )
        return {"status": "sent", "nudge": nudge}

    return {"status": "no_nudge_available"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8065)
