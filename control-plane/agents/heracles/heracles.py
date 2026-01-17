#!/usr/bin/env python3
"""
HERACLES - AI-Powered Project Management Agent
Port: 8200

Sprint planning, task breakdown, time tracking, velocity measurement,
and external PM tool integration.

Named after Heracles (Hercules) - the legendary hero who completed
the 12 labors through meticulous planning, resource management,
and relentless execution.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs decisions to aria_knowledge
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="HERACLES",
    description="AI-Powered Project Management Agent",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "ARIA": "http://aria:8001",
    "ATLAS": "http://atlas:8002",
    "CHRONOS": "http://chronos:8010",
    "HERMES": "http://hermes:8014",
    "CHIRON": "http://chiron:8017",
    "HEPHAESTUS": "http://hephaestus:8011",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("HERACLES")

# =============================================================================
# IN-MEMORY STORAGE (Phase 1 - will be replaced with database)
# =============================================================================

# Temporary in-memory storage for Phase 1
_projects: Dict[str, dict] = {}
_sprints: Dict[str, dict] = {}
_tasks: Dict[str, dict] = {}
_time_entries: Dict[str, dict] = {}
_velocity_history: Dict[str, dict] = {}

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_to_launch": days_to_launch,
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch",
        "phase": get_current_phase(days_to_launch)
    }

def get_current_phase(days_to_launch: int) -> str:
    """Determine current phase based on days to launch"""
    if days_to_launch <= 0:
        return "POST-LAUNCH"
    elif days_to_launch <= 14:
        return "FINAL PUSH - Outreach & Discovery Calls"
    elif days_to_launch <= 28:
        return "OUTREACH PHASE - 10 attempts, 3 calls"
    elif days_to_launch <= 45:
        return "POLISH PHASE - Loose ends & Agent building"
    else:
        return "INFRASTRUCTURE PHASE"

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(project_context: dict = None) -> str:
    """Build HERACLES system prompt with project context"""
    time_ctx = get_time_context()

    # Get project stats from context or defaults
    ctx = project_context or {}
    active_projects = ctx.get('active_projects', len([p for p in _projects.values() if p.get('status') == 'active']))
    active_sprints = ctx.get('active_sprints', len([s for s in _sprints.values() if s.get('status') == 'active']))
    tasks_in_progress = ctx.get('tasks_in_progress', len([t for t in _tasks.values() if t.get('status') == 'in_progress']))
    avg_velocity = ctx.get('avg_velocity', 0)
    team_capacity = ctx.get('team_capacity', 40)

    return f"""You are HERACLES - Elite Project Management Agent for LeverEdge AI.

Named after the legendary hero who completed the 12 labors through meticulous planning, resource management, and relentless execution, you help teams achieve their project goals with precision.

## TIME AWARENESS
- Current: {time_ctx['day_of_week']}, {time_ctx['current_date']} at {time_ctx['current_time']}
- Days to Launch: {time_ctx['days_to_launch']}
- Phase: {time_ctx['phase']}

## YOUR IDENTITY
You are the project management brain of LeverEdge. You plan sprints, break down work, track time, measure velocity, and keep projects on track.

## CURRENT PROJECT STATUS
- Active Projects: {active_projects}
- Active Sprints: {active_sprints}
- Tasks In Progress: {tasks_in_progress}
- Average Velocity: {avg_velocity} points/sprint
- Team Capacity: {team_capacity} hours this sprint

## YOUR CAPABILITIES

### Sprint Planning
- Create sprints with clear goals and capacity
- Assign tasks based on skills and availability
- Calculate realistic sprint capacity
- Identify overcommitment risks

### Task Breakdown
- Decompose epics into stories
- Break stories into actionable tasks
- Generate acceptance criteria
- Estimate effort for tasks

### Time Tracking
- Log time entries against tasks
- Track billable vs non-billable hours
- Generate timesheets and reports
- Timer-based tracking support

### Velocity Management
- Calculate sprint velocity
- Track velocity trends
- Forecast delivery dates
- Identify performance patterns

### External Integration
- Sync with OpenProject/Leantime
- Import tasks from external systems
- Export time entries
- Resolve sync conflicts

## TEAM COORDINATION
- Route financial tasks -> ATLAS
- Request calendar events -> CHRONOS
- Send notifications -> HERMES
- Log insights -> ARIA via Unified Memory
- Publish events -> Event Bus

## RESPONSE FORMAT
For sprint planning:
1. Sprint goal and duration
2. Capacity analysis
3. Task recommendations
4. Risk assessment
5. Success metrics

For task breakdown:
1. Task hierarchy
2. Estimates for each item
3. Dependencies identified
4. Acceptance criteria

## YOUR MISSION
Keep projects on track through effective planning and execution.
No task goes untracked.
Every sprint delivers value.
Velocity improves continuously.
"""

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

# Project Models
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owner: str
    start_date: Optional[str] = None
    target_date: Optional[str] = None
    settings: Optional[Dict[str, Any]] = {}
    metadata: Optional[Dict[str, Any]] = {}

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    start_date: Optional[str] = None
    target_date: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

# Sprint Models
class SprintCreate(BaseModel):
    project_id: str
    name: str
    goal: Optional[str] = None
    start_date: str
    end_date: str
    capacity_hours: Optional[float] = 40.0

class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    capacity_hours: Optional[float] = None
    committed_points: Optional[float] = None
    completed_points: Optional[float] = None
    retrospective: Optional[Dict[str, Any]] = None

# Task Models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: str
    sprint_id: Optional[str] = None
    parent_id: Optional[str] = None
    task_type: Optional[str] = "task"  # epic, story, task, subtask, bug
    priority: Optional[str] = "medium"  # critical, high, medium, low
    estimate_hours: Optional[float] = None
    story_points: Optional[float] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = []
    due_date: Optional[str] = None
    acceptance_criteria: Optional[Dict[str, Any]] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sprint_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    estimate_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    story_points: Optional[float] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    due_date: Optional[str] = None
    blocked_by: Optional[List[str]] = None
    acceptance_criteria: Optional[Dict[str, Any]] = None

# Time Entry Models
class TimeEntryCreate(BaseModel):
    task_id: str
    user_id: str
    date: str
    hours: float
    notes: Optional[str] = None
    billable: Optional[bool] = True

class TimeEntryUpdate(BaseModel):
    hours: Optional[float] = None
    notes: Optional[str] = None
    billable: Optional[bool] = None
    approved: Optional[bool] = None
    approved_by: Optional[str] = None

class TimerStart(BaseModel):
    task_id: str
    user_id: str

class TimerStop(BaseModel):
    task_id: str
    user_id: str
    notes: Optional[str] = None

# Sync Models
class SyncConnect(BaseModel):
    project_id: str
    external_system: str  # openproject, leantime
    external_id: str
    sync_direction: Optional[str] = "bidirectional"

# ARIA Tool Models
class CreateSprintTool(BaseModel):
    project_id: str
    name: str
    goal: Optional[str] = None
    start_date: str
    end_date: str
    capacity_hours: Optional[float] = 40.0

class AddTaskTool(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: str
    sprint_id: Optional[str] = None
    task_type: Optional[str] = "task"
    estimate_hours: Optional[float] = None
    priority: Optional[str] = "medium"
    assignee: Optional[str] = None

class TaskStatusTool(BaseModel):
    task_id: str
    status: str  # todo, in_progress, review, done, blocked
    notes: Optional[str] = None

class SprintReportTool(BaseModel):
    sprint_id: str
    include_tasks: Optional[bool] = True
    include_time: Optional[bool] = True

class LogTimeTool(BaseModel):
    task_id: str
    hours: float
    date: Optional[str] = None
    notes: Optional[str] = None
    billable: Optional[bool] = True

# AI Breakdown Request
class BreakdownRequest(BaseModel):
    title: str
    description: Optional[str] = None
    context: Optional[str] = None

# =============================================================================
# EVENT BUS INTEGRATION
# =============================================================================

async def publish_event(event_type: str, data: dict):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "HERACLES",
                    "data": {
                        **data,
                        "timestamp": time_ctx['current_datetime'],
                        "days_to_launch": time_ctx['days_to_launch']
                    }
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[HERACLES] Event bus publish failed: {e}")

async def notify_aria(memory_type: str, content: str, category: str = "project_management", tags: List[str] = None):
    """Store memory in Unified Memory for ARIA"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/aria_unified_memory",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "memory_type": memory_type,
                    "content": content,
                    "category": category,
                    "source_type": "agent_result",
                    "source_agent": "HERACLES",
                    "tags": tags or ["heracles"]
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[HERACLES] ARIA notification failed: {e}")

# =============================================================================
# VELOCITY CALCULATIONS
# =============================================================================

def calculate_velocity(sprint_id: str) -> dict:
    """Calculate velocity metrics for a sprint"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        return {"error": "Sprint not found"}

    # Get tasks in sprint
    sprint_tasks = [t for t in _tasks.values() if t.get('sprint_id') == sprint_id]

    # Calculate points
    committed_points = sum(t.get('story_points', 0) or 0 for t in sprint_tasks)
    completed_points = sum(t.get('story_points', 0) or 0 for t in sprint_tasks if t.get('status') == 'done')

    # Calculate hours
    committed_hours = sum(t.get('estimate_hours', 0) or 0 for t in sprint_tasks)
    completed_hours = sum(t.get('actual_hours', 0) or 0 for t in sprint_tasks if t.get('status') == 'done')

    return {
        "sprint_id": sprint_id,
        "committed_points": committed_points,
        "completed_points": completed_points,
        "velocity_points": completed_points,
        "committed_hours": committed_hours,
        "completed_hours": completed_hours,
        "velocity_hours": completed_hours,
        "completion_rate": (completed_points / committed_points * 100) if committed_points > 0 else 0,
        "task_count": len(sprint_tasks),
        "completed_task_count": len([t for t in sprint_tasks if t.get('status') == 'done'])
    }

def get_rolling_velocity(project_id: str, sprint_count: int = 3) -> dict:
    """Get rolling average velocity for a project"""
    # Get completed sprints for project, sorted by end date
    project_sprints = [
        s for s in _sprints.values()
        if s.get('project_id') == project_id and s.get('status') == 'completed'
    ]
    project_sprints.sort(key=lambda x: x.get('end_date', ''), reverse=True)

    recent_sprints = project_sprints[:sprint_count]

    if not recent_sprints:
        return {
            "project_id": project_id,
            "sprint_count": 0,
            "average_velocity_points": 0,
            "average_velocity_hours": 0,
            "trend": "insufficient_data"
        }

    velocities = [calculate_velocity(s['id']) for s in recent_sprints]

    avg_points = sum(v['velocity_points'] for v in velocities) / len(velocities)
    avg_hours = sum(v['velocity_hours'] for v in velocities) / len(velocities)

    # Calculate trend
    trend = "stable"
    if len(velocities) >= 2:
        recent = velocities[0]['velocity_points']
        previous = velocities[1]['velocity_points']
        if recent > previous * 1.1:
            trend = "improving"
        elif recent < previous * 0.9:
            trend = "declining"

    return {
        "project_id": project_id,
        "sprint_count": len(recent_sprints),
        "average_velocity_points": round(avg_points, 1),
        "average_velocity_hours": round(avg_hours, 1),
        "trend": trend,
        "sprints_analyzed": [s['name'] for s in recent_sprints]
    }

# =============================================================================
# SPRINT PLANNING LOGIC
# =============================================================================

def analyze_sprint_capacity(sprint_id: str) -> dict:
    """Analyze sprint capacity and commitment"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        return {"error": "Sprint not found"}

    sprint_tasks = [t for t in _tasks.values() if t.get('sprint_id') == sprint_id]

    total_estimate = sum(t.get('estimate_hours', 0) or 0 for t in sprint_tasks)
    total_points = sum(t.get('story_points', 0) or 0 for t in sprint_tasks)
    capacity = sprint.get('capacity_hours', 40)

    utilization = (total_estimate / capacity * 100) if capacity > 0 else 0

    # Risk assessment
    risk_level = "low"
    risk_reasons = []

    if utilization > 100:
        risk_level = "high"
        risk_reasons.append(f"Overcommitted by {utilization - 100:.1f}%")
    elif utilization > 85:
        risk_level = "medium"
        risk_reasons.append("Near capacity limit")

    # Check for tasks without estimates
    unestimated = [t for t in sprint_tasks if not t.get('estimate_hours')]
    if unestimated:
        risk_level = "medium" if risk_level == "low" else risk_level
        risk_reasons.append(f"{len(unestimated)} tasks without estimates")

    # Check for blocked tasks
    blocked = [t for t in sprint_tasks if t.get('status') == 'blocked']
    if blocked:
        risk_level = "high"
        risk_reasons.append(f"{len(blocked)} blocked tasks")

    return {
        "sprint_id": sprint_id,
        "sprint_name": sprint.get('name'),
        "capacity_hours": capacity,
        "committed_hours": total_estimate,
        "committed_points": total_points,
        "utilization_percent": round(utilization, 1),
        "available_hours": max(0, capacity - total_estimate),
        "task_count": len(sprint_tasks),
        "risk_level": risk_level,
        "risk_reasons": risk_reasons
    }

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, context: dict = None) -> str:
    """Call Claude API with full context and cost tracking"""
    if not client:
        return "LLM not configured - ANTHROPIC_API_KEY not set"

    try:
        system_prompt = build_system_prompt(context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="HERACLES",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"context": "project_management"}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    time_ctx = get_time_context()

    return {
        "status": "healthy",
        "agent": "HERACLES",
        "role": "Project Management",
        "port": 8200,
        "version": "1.0.0",
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase'],
        "stats": {
            "projects": len(_projects),
            "sprints": len(_sprints),
            "tasks": len(_tasks),
            "time_entries": len(_time_entries)
        }
    }

@app.get("/status")
async def status():
    """Get current project management status"""
    time_ctx = get_time_context()

    active_projects = [p for p in _projects.values() if p.get('status') == 'active']
    active_sprints = [s for s in _sprints.values() if s.get('status') == 'active']

    # Get tasks in progress
    tasks_in_progress = [t for t in _tasks.values() if t.get('status') == 'in_progress']
    tasks_blocked = [t for t in _tasks.values() if t.get('status') == 'blocked']

    return {
        "agent": "HERACLES",
        "time_context": time_ctx,
        "overview": {
            "active_projects": len(active_projects),
            "active_sprints": len(active_sprints),
            "tasks_in_progress": len(tasks_in_progress),
            "tasks_blocked": len(tasks_blocked),
            "total_tasks": len(_tasks)
        },
        "active_sprints": [
            {
                "id": s['id'],
                "name": s['name'],
                "project_id": s['project_id'],
                "end_date": s['end_date'],
                "capacity_analysis": analyze_sprint_capacity(s['id'])
            }
            for s in active_sprints
        ],
        "blocked_tasks": [
            {"id": t['id'], "title": t['title'], "project_id": t.get('project_id')}
            for t in tasks_blocked
        ]
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    lines = [
        "# HELP heracles_projects_total Total number of projects",
        "# TYPE heracles_projects_total gauge",
        f"heracles_projects_total {len(_projects)}",
        "",
        "# HELP heracles_sprints_active Number of active sprints",
        "# TYPE heracles_sprints_active gauge",
        f"heracles_sprints_active {len([s for s in _sprints.values() if s.get('status') == 'active'])}",
        "",
        "# HELP heracles_tasks_total Total number of tasks",
        "# TYPE heracles_tasks_total gauge",
        f"heracles_tasks_total {len(_tasks)}",
        "",
        "# HELP heracles_tasks_completed Number of completed tasks",
        "# TYPE heracles_tasks_completed gauge",
        f"heracles_tasks_completed {len([t for t in _tasks.values() if t.get('status') == 'done'])}",
    ]
    return "\n".join(lines)

# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@app.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    project_id = str(uuid4())
    now = datetime.now().isoformat()

    project_data = {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "status": "active",
        "owner": project.owner,
        "start_date": project.start_date or date.today().isoformat(),
        "target_date": project.target_date,
        "settings": project.settings or {},
        "metadata": project.metadata or {},
        "created_at": now,
        "updated_at": now
    }

    _projects[project_id] = project_data

    # Publish event
    await publish_event("pm.project.created", {
        "project_id": project_id,
        "name": project.name,
        "owner": project.owner
    })

    # Notify ARIA
    await notify_aria(
        "fact",
        f"New project created: {project.name} (Owner: {project.owner})",
        tags=["heracles", "project", project.name]
    )

    return {"success": True, "project": project_data}

@app.get("/projects")
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    owner: Optional[str] = Query(None, description="Filter by owner")
):
    """List all projects"""
    projects = list(_projects.values())

    if status:
        projects = [p for p in projects if p.get('status') == status]
    if owner:
        projects = [p for p in projects if p.get('owner') == owner]

    return {"projects": projects, "total": len(projects)}

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details"""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get related data
    sprints = [s for s in _sprints.values() if s.get('project_id') == project_id]
    tasks = [t for t in _tasks.values() if t.get('project_id') == project_id]

    return {
        "project": project,
        "sprints": sprints,
        "task_count": len(tasks),
        "velocity": get_rolling_velocity(project_id)
    }

@app.put("/projects/{project_id}")
async def update_project(project_id: str, update: ProjectUpdate):
    """Update a project"""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now().isoformat()

    project.update(update_data)

    await publish_event("pm.project.updated", {
        "project_id": project_id,
        "fields_updated": list(update_data.keys())
    })

    return {"success": True, "project": project}

@app.delete("/projects/{project_id}")
async def archive_project(project_id: str):
    """Archive a project (soft delete)"""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project['status'] = 'archived'
    project['updated_at'] = datetime.now().isoformat()

    await publish_event("pm.project.archived", {"project_id": project_id})

    return {"success": True, "message": "Project archived"}

@app.get("/projects/{project_id}/summary")
async def get_project_summary(project_id: str):
    """Get project summary with metrics"""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sprints = [s for s in _sprints.values() if s.get('project_id') == project_id]
    tasks = [t for t in _tasks.values() if t.get('project_id') == project_id]

    # Task breakdown by status
    status_counts = {}
    for task in tasks:
        status = task.get('status', 'todo')
        status_counts[status] = status_counts.get(status, 0) + 1

    # Task breakdown by type
    type_counts = {}
    for task in tasks:
        task_type = task.get('task_type', 'task')
        type_counts[task_type] = type_counts.get(task_type, 0) + 1

    # Time logged
    project_task_ids = {t['id'] for t in tasks}
    time_entries = [te for te in _time_entries.values() if te.get('task_id') in project_task_ids]
    total_hours = sum(te.get('hours', 0) for te in time_entries)
    billable_hours = sum(te.get('hours', 0) for te in time_entries if te.get('billable'))

    return {
        "project": project,
        "metrics": {
            "sprint_count": len(sprints),
            "active_sprints": len([s for s in sprints if s.get('status') == 'active']),
            "completed_sprints": len([s for s in sprints if s.get('status') == 'completed']),
            "total_tasks": len(tasks),
            "tasks_by_status": status_counts,
            "tasks_by_type": type_counts,
            "total_hours_logged": round(total_hours, 2),
            "billable_hours": round(billable_hours, 2)
        },
        "velocity": get_rolling_velocity(project_id)
    }

# =============================================================================
# SPRINT ENDPOINTS
# =============================================================================

@app.post("/sprints")
async def create_sprint(sprint: SprintCreate):
    """Create a new sprint"""
    # Verify project exists
    if sprint.project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    sprint_id = str(uuid4())
    now = datetime.now().isoformat()

    sprint_data = {
        "id": sprint_id,
        "project_id": sprint.project_id,
        "name": sprint.name,
        "goal": sprint.goal,
        "start_date": sprint.start_date,
        "end_date": sprint.end_date,
        "status": "planning",
        "capacity_hours": sprint.capacity_hours,
        "committed_points": 0,
        "completed_points": 0,
        "velocity": None,
        "retrospective": None,
        "created_at": now,
        "updated_at": now
    }

    _sprints[sprint_id] = sprint_data

    await publish_event("pm.sprint.created", {
        "sprint_id": sprint_id,
        "project_id": sprint.project_id,
        "name": sprint.name,
        "start_date": sprint.start_date,
        "end_date": sprint.end_date
    })

    await notify_aria(
        "fact",
        f"Sprint created: {sprint.name} ({sprint.start_date} to {sprint.end_date})",
        tags=["heracles", "sprint", sprint.name]
    )

    return {"success": True, "sprint": sprint_data}

@app.get("/sprints")
async def list_sprints(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """List sprints with optional filters"""
    sprints = list(_sprints.values())

    if project_id:
        sprints = [s for s in sprints if s.get('project_id') == project_id]
    if status:
        sprints = [s for s in sprints if s.get('status') == status]

    return {"sprints": sprints, "total": len(sprints)}

@app.get("/sprints/{sprint_id}")
async def get_sprint(sprint_id: str):
    """Get sprint details"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    tasks = [t for t in _tasks.values() if t.get('sprint_id') == sprint_id]

    return {
        "sprint": sprint,
        "tasks": tasks,
        "capacity_analysis": analyze_sprint_capacity(sprint_id),
        "velocity": calculate_velocity(sprint_id)
    }

@app.put("/sprints/{sprint_id}")
async def update_sprint(sprint_id: str, update: SprintUpdate):
    """Update a sprint"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    update_data = update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now().isoformat()

    sprint.update(update_data)

    await publish_event("pm.sprint.updated", {
        "sprint_id": sprint_id,
        "fields_updated": list(update_data.keys())
    })

    return {"success": True, "sprint": sprint}

@app.post("/sprints/{sprint_id}/start")
async def start_sprint(sprint_id: str):
    """Start a sprint"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    if sprint['status'] != 'planning':
        raise HTTPException(status_code=400, detail=f"Cannot start sprint in {sprint['status']} status")

    sprint['status'] = 'active'
    sprint['updated_at'] = datetime.now().isoformat()

    # Calculate committed points
    tasks = [t for t in _tasks.values() if t.get('sprint_id') == sprint_id]
    sprint['committed_points'] = sum(t.get('story_points', 0) or 0 for t in tasks)

    await publish_event("pm.sprint.started", {
        "sprint_id": sprint_id,
        "name": sprint['name'],
        "committed_points": sprint['committed_points']
    })

    return {"success": True, "sprint": sprint, "capacity_analysis": analyze_sprint_capacity(sprint_id)}

@app.post("/sprints/{sprint_id}/complete")
async def complete_sprint(sprint_id: str):
    """Complete a sprint"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    if sprint['status'] != 'active':
        raise HTTPException(status_code=400, detail=f"Cannot complete sprint in {sprint['status']} status")

    # Calculate final velocity
    velocity_data = calculate_velocity(sprint_id)

    sprint['status'] = 'completed'
    sprint['completed_points'] = velocity_data['completed_points']
    sprint['velocity'] = velocity_data['velocity_points']
    sprint['updated_at'] = datetime.now().isoformat()

    await publish_event("pm.sprint.completed", {
        "sprint_id": sprint_id,
        "name": sprint['name'],
        "velocity": sprint['velocity'],
        "committed_points": sprint['committed_points'],
        "completed_points": sprint['completed_points']
    })

    await notify_aria(
        "fact",
        f"Sprint completed: {sprint['name']} - Velocity: {sprint['velocity']} points (Committed: {sprint['committed_points']}, Completed: {sprint['completed_points']})",
        tags=["heracles", "sprint", "velocity"]
    )

    # Store velocity history
    velocity_id = str(uuid4())
    _velocity_history[velocity_id] = {
        "id": velocity_id,
        "project_id": sprint['project_id'],
        "sprint_id": sprint_id,
        **velocity_data,
        "calculated_at": datetime.now().isoformat()
    }

    await publish_event("pm.velocity.calculated", {
        "sprint_id": sprint_id,
        "project_id": sprint['project_id'],
        "velocity_points": velocity_data['velocity_points']
    })

    return {"success": True, "sprint": sprint, "velocity": velocity_data}

@app.get("/sprints/{sprint_id}/burndown")
async def get_burndown(sprint_id: str):
    """Get burndown chart data for a sprint"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    tasks = [t for t in _tasks.values() if t.get('sprint_id') == sprint_id]

    # Calculate total points
    total_points = sum(t.get('story_points', 0) or 0 for t in tasks)
    completed_points = sum(t.get('story_points', 0) or 0 for t in tasks if t.get('status') == 'done')

    # Generate ideal burndown
    start = datetime.fromisoformat(sprint['start_date'])
    end = datetime.fromisoformat(sprint['end_date'])
    days = (end - start).days + 1

    ideal_burndown = []
    for i in range(days + 1):
        day = start + timedelta(days=i)
        remaining = total_points - (total_points / days * i)
        ideal_burndown.append({
            "date": day.isoformat(),
            "ideal_remaining": round(remaining, 1)
        })

    return {
        "sprint_id": sprint_id,
        "total_points": total_points,
        "completed_points": completed_points,
        "remaining_points": total_points - completed_points,
        "ideal_burndown": ideal_burndown,
        "actual_remaining": total_points - completed_points
    }

@app.get("/sprints/{sprint_id}/report")
async def get_sprint_report(sprint_id: str):
    """Get full sprint report"""
    sprint = _sprints.get(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    tasks = [t for t in _tasks.values() if t.get('sprint_id') == sprint_id]
    task_ids = {t['id'] for t in tasks}
    time_entries = [te for te in _time_entries.values() if te.get('task_id') in task_ids]

    return {
        "sprint": sprint,
        "capacity_analysis": analyze_sprint_capacity(sprint_id),
        "velocity": calculate_velocity(sprint_id),
        "burndown": await get_burndown(sprint_id),
        "tasks": {
            "total": len(tasks),
            "by_status": {
                status: len([t for t in tasks if t.get('status') == status])
                for status in ['todo', 'in_progress', 'review', 'done', 'blocked']
            },
            "items": tasks
        },
        "time": {
            "total_hours": sum(te.get('hours', 0) for te in time_entries),
            "entries": time_entries
        }
    }

# =============================================================================
# TASK ENDPOINTS
# =============================================================================

@app.post("/tasks")
async def create_task(task: TaskCreate):
    """Create a new task"""
    # Verify project exists
    if task.project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify sprint if provided
    if task.sprint_id and task.sprint_id not in _sprints:
        raise HTTPException(status_code=404, detail="Sprint not found")

    # Verify parent if provided
    if task.parent_id and task.parent_id not in _tasks:
        raise HTTPException(status_code=404, detail="Parent task not found")

    task_id = str(uuid4())
    now = datetime.now().isoformat()

    task_data = {
        "id": task_id,
        "title": task.title,
        "description": task.description,
        "project_id": task.project_id,
        "sprint_id": task.sprint_id,
        "parent_id": task.parent_id,
        "task_type": task.task_type,
        "status": "todo",
        "priority": task.priority,
        "estimate_hours": task.estimate_hours,
        "actual_hours": 0,
        "story_points": task.story_points,
        "assignee": task.assignee,
        "labels": task.labels or [],
        "due_date": task.due_date,
        "blocked_by": [],
        "acceptance_criteria": task.acceptance_criteria,
        "metadata": {},
        "created_at": now,
        "updated_at": now,
        "completed_at": None
    }

    _tasks[task_id] = task_data

    await publish_event("pm.task.created", {
        "task_id": task_id,
        "title": task.title,
        "project_id": task.project_id,
        "sprint_id": task.sprint_id,
        "task_type": task.task_type
    })

    return {"success": True, "task": task_data}

@app.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = Query(None),
    sprint_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None)
):
    """List tasks with optional filters"""
    tasks = list(_tasks.values())

    if project_id:
        tasks = [t for t in tasks if t.get('project_id') == project_id]
    if sprint_id:
        tasks = [t for t in tasks if t.get('sprint_id') == sprint_id]
    if status:
        tasks = [t for t in tasks if t.get('status') == status]
    if task_type:
        tasks = [t for t in tasks if t.get('task_type') == task_type]
    if assignee:
        tasks = [t for t in tasks if t.get('assignee') == assignee]

    return {"tasks": tasks, "total": len(tasks)}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get subtasks
    subtasks = [t for t in _tasks.values() if t.get('parent_id') == task_id]

    # Get time entries
    time_entries = [te for te in _time_entries.values() if te.get('task_id') == task_id]

    return {
        "task": task,
        "subtasks": subtasks,
        "time_entries": time_entries,
        "total_time_logged": sum(te.get('hours', 0) for te in time_entries)
    }

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, update: TaskUpdate):
    """Update a task"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.get('status')
    update_data = update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now().isoformat()

    # Track completion time
    new_status = update_data.get('status')
    if new_status == 'done' and old_status != 'done':
        update_data['completed_at'] = datetime.now().isoformat()
    elif new_status and new_status != 'done':
        update_data['completed_at'] = None

    task.update(update_data)

    # Publish appropriate events
    if new_status and new_status != old_status:
        if new_status == 'done':
            await publish_event("pm.task.completed", {
                "task_id": task_id,
                "title": task['title'],
                "project_id": task.get('project_id')
            })
        elif new_status == 'blocked':
            await publish_event("pm.task.blocked", {
                "task_id": task_id,
                "title": task['title'],
                "project_id": task.get('project_id')
            })
            await publish_event("pm.blocker.detected", {
                "task_id": task_id,
                "title": task['title']
            })

    await publish_event("pm.task.updated", {
        "task_id": task_id,
        "fields_updated": list(update_data.keys())
    })

    return {"success": True, "task": task}

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Delete subtasks first
    subtask_ids = [t['id'] for t in _tasks.values() if t.get('parent_id') == task_id]
    for sid in subtask_ids:
        del _tasks[sid]

    del _tasks[task_id]

    await publish_event("pm.task.deleted", {
        "task_id": task_id,
        "title": task['title']
    })

    return {"success": True, "message": "Task deleted", "subtasks_deleted": len(subtask_ids)}

@app.post("/tasks/{task_id}/breakdown")
async def breakdown_task(task_id: str, request: Optional[BreakdownRequest] = None):
    """AI-powered task breakdown into subtasks"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    prompt = f"""Break down this task into subtasks:

**Task:** {task['title']}
**Type:** {task.get('task_type', 'task')}
**Description:** {task.get('description', 'No description provided')}
**Current Estimate:** {task.get('estimate_hours', 'Not estimated')} hours

{f"**Additional Context:** {request.context}" if request and request.context else ""}

Please provide:
1. A list of subtasks (3-7 subtasks typically)
2. For each subtask:
   - Title (action-oriented)
   - Brief description
   - Estimated hours
   - Priority (high/medium/low)
3. Any dependencies between subtasks
4. Total estimated hours for all subtasks

Format as JSON with structure:
{{
  "subtasks": [
    {{"title": "...", "description": "...", "estimate_hours": N, "priority": "...", "depends_on": []}}
  ],
  "total_estimate": N,
  "notes": "any additional notes"
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages)

    await publish_event("pm.task.breakdown_requested", {
        "task_id": task_id,
        "title": task['title']
    })

    return {
        "task_id": task_id,
        "original_task": task,
        "breakdown_suggestion": response,
        "note": "Review the suggestions and use POST /tasks to create the subtasks with parent_id set to this task"
    }

@app.post("/tasks/{task_id}/move")
async def move_task(task_id: str, sprint_id: Optional[str] = None):
    """Move task to a different sprint"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if sprint_id and sprint_id not in _sprints:
        raise HTTPException(status_code=404, detail="Target sprint not found")

    old_sprint = task.get('sprint_id')
    task['sprint_id'] = sprint_id
    task['updated_at'] = datetime.now().isoformat()

    await publish_event("pm.task.moved", {
        "task_id": task_id,
        "from_sprint": old_sprint,
        "to_sprint": sprint_id
    })

    return {"success": True, "task": task}

@app.get("/tasks/{task_id}/history")
async def get_task_history(task_id: str):
    """Get task change history (stub - would need audit table)"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Placeholder - in production this would query an audit table
    return {
        "task_id": task_id,
        "history": [
            {
                "action": "created",
                "timestamp": task['created_at'],
                "details": {"title": task['title']}
            },
            {
                "action": "updated",
                "timestamp": task['updated_at'],
                "details": {"status": task['status']}
            }
        ],
        "note": "Full history tracking requires database audit tables"
    }

# =============================================================================
# TIME TRACKING ENDPOINTS
# =============================================================================

@app.post("/time")
async def log_time(entry: TimeEntryCreate):
    """Log a time entry"""
    # Verify task exists
    if entry.task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    entry_id = str(uuid4())
    now = datetime.now().isoformat()

    entry_data = {
        "id": entry_id,
        "task_id": entry.task_id,
        "user_id": entry.user_id,
        "date": entry.date,
        "hours": entry.hours,
        "notes": entry.notes,
        "billable": entry.billable,
        "approved": False,
        "approved_by": None,
        "timer_started": None,
        "timer_stopped": None,
        "created_at": now,
        "updated_at": now
    }

    _time_entries[entry_id] = entry_data

    # Update task actual hours
    task = _tasks[entry.task_id]
    task['actual_hours'] = task.get('actual_hours', 0) + entry.hours

    await publish_event("pm.time.logged", {
        "entry_id": entry_id,
        "task_id": entry.task_id,
        "user_id": entry.user_id,
        "hours": entry.hours,
        "billable": entry.billable
    })

    return {"success": True, "time_entry": entry_data}

@app.get("/time")
async def list_time_entries(
    task_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """List time entries with filters"""
    entries = list(_time_entries.values())

    if task_id:
        entries = [e for e in entries if e.get('task_id') == task_id]
    if user_id:
        entries = [e for e in entries if e.get('user_id') == user_id]
    if date_from:
        entries = [e for e in entries if e.get('date', '') >= date_from]
    if date_to:
        entries = [e for e in entries if e.get('date', '') <= date_to]

    return {
        "time_entries": entries,
        "total": len(entries),
        "total_hours": sum(e.get('hours', 0) for e in entries)
    }

@app.put("/time/{entry_id}")
async def update_time_entry(entry_id: str, update: TimeEntryUpdate):
    """Update a time entry"""
    entry = _time_entries.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    old_hours = entry.get('hours', 0)
    update_data = update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now().isoformat()

    entry.update(update_data)

    # Update task actual hours if hours changed
    if 'hours' in update_data:
        task = _tasks.get(entry['task_id'])
        if task:
            hours_diff = update_data['hours'] - old_hours
            task['actual_hours'] = task.get('actual_hours', 0) + hours_diff

    return {"success": True, "time_entry": entry}

@app.delete("/time/{entry_id}")
async def delete_time_entry(entry_id: str):
    """Delete a time entry"""
    entry = _time_entries.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")

    # Update task actual hours
    task = _tasks.get(entry['task_id'])
    if task:
        task['actual_hours'] = max(0, task.get('actual_hours', 0) - entry.get('hours', 0))

    del _time_entries[entry_id]

    return {"success": True, "message": "Time entry deleted"}

# Active timers storage
_active_timers: Dict[str, dict] = {}

@app.post("/time/timer/start")
async def start_timer(timer: TimerStart):
    """Start a timer for a task"""
    if timer.task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    timer_key = f"{timer.user_id}:{timer.task_id}"

    if timer_key in _active_timers:
        raise HTTPException(status_code=400, detail="Timer already running for this task")

    _active_timers[timer_key] = {
        "task_id": timer.task_id,
        "user_id": timer.user_id,
        "started_at": datetime.now().isoformat()
    }

    return {"success": True, "timer": _active_timers[timer_key]}

@app.post("/time/timer/stop")
async def stop_timer(timer: TimerStop):
    """Stop a timer and log the time"""
    timer_key = f"{timer.user_id}:{timer.task_id}"

    if timer_key not in _active_timers:
        raise HTTPException(status_code=404, detail="No active timer found")

    active_timer = _active_timers.pop(timer_key)
    started = datetime.fromisoformat(active_timer['started_at'])
    stopped = datetime.now()

    # Calculate hours
    duration = stopped - started
    hours = round(duration.total_seconds() / 3600, 2)

    # Create time entry
    entry = TimeEntryCreate(
        task_id=timer.task_id,
        user_id=timer.user_id,
        date=stopped.date().isoformat(),
        hours=hours,
        notes=timer.notes,
        billable=True
    )

    result = await log_time(entry)

    # Update the entry with timer info
    entry_data = result['time_entry']
    entry_data['timer_started'] = active_timer['started_at']
    entry_data['timer_stopped'] = stopped.isoformat()

    return {"success": True, "time_entry": entry_data, "duration_hours": hours}

@app.get("/time/summary")
async def get_time_summary(
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Get time summary report"""
    entries = list(_time_entries.values())

    if user_id:
        entries = [e for e in entries if e.get('user_id') == user_id]
    if date_from:
        entries = [e for e in entries if e.get('date', '') >= date_from]
    if date_to:
        entries = [e for e in entries if e.get('date', '') <= date_to]

    # Group by date
    by_date = {}
    for entry in entries:
        d = entry.get('date')
        if d not in by_date:
            by_date[d] = {'total': 0, 'billable': 0, 'entries': 0}
        by_date[d]['total'] += entry.get('hours', 0)
        if entry.get('billable'):
            by_date[d]['billable'] += entry.get('hours', 0)
        by_date[d]['entries'] += 1

    # Group by task
    by_task = {}
    for entry in entries:
        tid = entry.get('task_id')
        task = _tasks.get(tid, {})
        if tid not in by_task:
            by_task[tid] = {'title': task.get('title', 'Unknown'), 'total': 0}
        by_task[tid]['total'] += entry.get('hours', 0)

    return {
        "summary": {
            "total_hours": sum(e.get('hours', 0) for e in entries),
            "billable_hours": sum(e.get('hours', 0) for e in entries if e.get('billable')),
            "entry_count": len(entries)
        },
        "by_date": by_date,
        "by_task": by_task
    }

@app.get("/time/timesheet")
async def get_timesheet(
    user_id: str,
    week_start: Optional[str] = Query(None, description="Week start date (Monday)")
):
    """Generate weekly timesheet"""
    # Default to current week
    if not week_start:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.isoformat()

    start = datetime.fromisoformat(week_start).date()
    end = start + timedelta(days=6)

    entries = [
        e for e in _time_entries.values()
        if e.get('user_id') == user_id
        and week_start <= e.get('date', '') <= end.isoformat()
    ]

    # Build timesheet grid
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    timesheet = {}

    for i, day in enumerate(days):
        day_date = (start + timedelta(days=i)).isoformat()
        day_entries = [e for e in entries if e.get('date') == day_date]
        timesheet[day] = {
            "date": day_date,
            "total_hours": sum(e.get('hours', 0) for e in day_entries),
            "entries": day_entries
        }

    return {
        "user_id": user_id,
        "week_start": week_start,
        "week_end": end.isoformat(),
        "timesheet": timesheet,
        "week_total": sum(e.get('hours', 0) for e in entries)
    }

# =============================================================================
# VELOCITY & ANALYTICS ENDPOINTS
# =============================================================================

@app.get("/velocity")
async def get_velocity(project_id: Optional[str] = Query(None)):
    """Get current velocity metrics"""
    if project_id:
        return get_rolling_velocity(project_id)

    # Return velocity for all projects
    velocities = {}
    for pid in _projects.keys():
        velocities[pid] = get_rolling_velocity(pid)

    return {"velocities": velocities}

@app.get("/velocity/history")
async def get_velocity_history(project_id: str):
    """Get velocity history for a project"""
    history = [
        v for v in _velocity_history.values()
        if v.get('project_id') == project_id
    ]
    history.sort(key=lambda x: x.get('calculated_at', ''))

    return {"project_id": project_id, "history": history}

@app.get("/velocity/forecast")
async def get_velocity_forecast(project_id: str, remaining_points: float):
    """Forecast delivery based on velocity"""
    velocity = get_rolling_velocity(project_id)
    avg_velocity = velocity.get('average_velocity_points', 0)

    if avg_velocity <= 0:
        return {
            "project_id": project_id,
            "error": "Insufficient velocity data for forecast",
            "recommendation": "Complete at least one sprint to enable forecasting"
        }

    # Estimate sprints needed
    sprints_needed = remaining_points / avg_velocity

    # Assume 2-week sprints
    days_needed = sprints_needed * 14
    estimated_completion = date.today() + timedelta(days=int(days_needed))

    return {
        "project_id": project_id,
        "remaining_points": remaining_points,
        "average_velocity": avg_velocity,
        "sprints_needed": round(sprints_needed, 1),
        "estimated_days": int(days_needed),
        "estimated_completion": estimated_completion.isoformat(),
        "velocity_trend": velocity.get('trend'),
        "confidence": "medium" if velocity.get('sprint_count', 0) >= 3 else "low"
    }

@app.get("/analytics/cycle-time")
async def get_cycle_time(project_id: Optional[str] = Query(None)):
    """Get cycle time analysis"""
    tasks = list(_tasks.values())

    if project_id:
        tasks = [t for t in tasks if t.get('project_id') == project_id]

    # Filter completed tasks with timestamps
    completed = [
        t for t in tasks
        if t.get('status') == 'done' and t.get('created_at') and t.get('completed_at')
    ]

    if not completed:
        return {"message": "No completed tasks with timing data"}

    # Calculate cycle times
    cycle_times = []
    for task in completed:
        created = datetime.fromisoformat(task['created_at'])
        done = datetime.fromisoformat(task['completed_at'])
        cycle_time = (done - created).total_seconds() / 3600  # hours
        cycle_times.append({
            "task_id": task['id'],
            "title": task['title'],
            "type": task.get('task_type'),
            "cycle_time_hours": round(cycle_time, 2)
        })

    avg_cycle_time = sum(ct['cycle_time_hours'] for ct in cycle_times) / len(cycle_times)

    return {
        "project_id": project_id,
        "task_count": len(cycle_times),
        "average_cycle_time_hours": round(avg_cycle_time, 2),
        "average_cycle_time_days": round(avg_cycle_time / 24, 1),
        "tasks": cycle_times
    }

@app.get("/analytics/throughput")
async def get_throughput(project_id: Optional[str] = Query(None), days: int = 30):
    """Get throughput metrics"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    tasks = list(_tasks.values())
    if project_id:
        tasks = [t for t in tasks if t.get('project_id') == project_id]

    # Filter completed tasks in period
    completed = [
        t for t in tasks
        if t.get('status') == 'done'
        and t.get('completed_at', '') >= cutoff
    ]

    # Group by week
    weekly = {}
    for task in completed:
        completed_date = datetime.fromisoformat(task['completed_at']).date()
        week_start = completed_date - timedelta(days=completed_date.weekday())
        week_key = week_start.isoformat()
        if week_key not in weekly:
            weekly[week_key] = 0
        weekly[week_key] += 1

    return {
        "project_id": project_id,
        "period_days": days,
        "total_completed": len(completed),
        "average_per_week": round(len(completed) / (days / 7), 1),
        "weekly_breakdown": weekly
    }

@app.get("/analytics/team")
async def get_team_metrics(project_id: Optional[str] = Query(None)):
    """Get team performance metrics"""
    tasks = list(_tasks.values())
    time_entries = list(_time_entries.values())

    if project_id:
        tasks = [t for t in tasks if t.get('project_id') == project_id]
        task_ids = {t['id'] for t in tasks}
        time_entries = [te for te in time_entries if te.get('task_id') in task_ids]

    # Group by assignee
    by_assignee = {}
    for task in tasks:
        assignee = task.get('assignee') or 'Unassigned'
        if assignee not in by_assignee:
            by_assignee[assignee] = {
                'tasks_total': 0,
                'tasks_completed': 0,
                'points_completed': 0,
                'hours_logged': 0
            }
        by_assignee[assignee]['tasks_total'] += 1
        if task.get('status') == 'done':
            by_assignee[assignee]['tasks_completed'] += 1
            by_assignee[assignee]['points_completed'] += task.get('story_points', 0) or 0

    # Add time logged
    for entry in time_entries:
        task = _tasks.get(entry.get('task_id'))
        if task:
            assignee = task.get('assignee') or 'Unassigned'
            if assignee in by_assignee:
                by_assignee[assignee]['hours_logged'] += entry.get('hours', 0)

    return {
        "project_id": project_id,
        "team_metrics": by_assignee
    }

# =============================================================================
# EXTERNAL SYNC ENDPOINTS (Stubs)
# =============================================================================

@app.post("/sync/connect")
async def connect_sync(config: SyncConnect):
    """Connect to external PM tool (stub)"""
    return {
        "success": True,
        "message": f"Sync connection to {config.external_system} configured (stub)",
        "note": "Full sync functionality will be implemented in Phase 6",
        "config": config.model_dump()
    }

@app.get("/sync/status")
async def get_sync_status():
    """Get sync status overview (stub)"""
    return {
        "status": "not_configured",
        "message": "External sync not yet configured",
        "supported_systems": ["openproject", "leantime"],
        "note": "Full sync functionality will be implemented in Phase 6"
    }

@app.post("/sync/trigger")
async def trigger_sync(project_id: str):
    """Trigger manual sync (stub)"""
    return {
        "success": True,
        "message": "Sync triggered (stub)",
        "project_id": project_id,
        "note": "Full sync functionality will be implemented in Phase 6"
    }

@app.get("/sync/conflicts")
async def get_sync_conflicts():
    """List sync conflicts (stub)"""
    return {
        "conflicts": [],
        "message": "No conflicts (sync not configured)",
        "note": "Full sync functionality will be implemented in Phase 6"
    }

@app.post("/sync/resolve")
async def resolve_conflict(conflict_id: str, resolution: str):
    """Resolve sync conflict (stub)"""
    return {
        "success": True,
        "message": "Conflict resolved (stub)",
        "conflict_id": conflict_id,
        "resolution": resolution,
        "note": "Full sync functionality will be implemented in Phase 6"
    }

@app.delete("/sync/{sync_id}")
async def disconnect_sync(sync_id: str):
    """Disconnect integration (stub)"""
    return {
        "success": True,
        "message": "Integration disconnected (stub)",
        "sync_id": sync_id,
        "note": "Full sync functionality will be implemented in Phase 6"
    }

# =============================================================================
# ARIA TOOL ENDPOINTS
# =============================================================================

@app.post("/tools/pm.create_sprint")
async def tool_create_sprint(request: CreateSprintTool):
    """ARIA Tool: Create a new sprint"""
    sprint = SprintCreate(
        project_id=request.project_id,
        name=request.name,
        goal=request.goal,
        start_date=request.start_date,
        end_date=request.end_date,
        capacity_hours=request.capacity_hours
    )
    return await create_sprint(sprint)

@app.post("/tools/pm.add_task")
async def tool_add_task(request: AddTaskTool):
    """ARIA Tool: Add a new task"""
    task = TaskCreate(
        title=request.title,
        description=request.description,
        project_id=request.project_id,
        sprint_id=request.sprint_id,
        task_type=request.task_type,
        estimate_hours=request.estimate_hours,
        priority=request.priority,
        assignee=request.assignee
    )
    return await create_task(task)

@app.post("/tools/pm.task_status")
async def tool_task_status(request: TaskStatusTool):
    """ARIA Tool: Update task status"""
    update = TaskUpdate(status=request.status)
    result = await update_task(request.task_id, update)

    if request.notes:
        # Could add a comment/note system here
        pass

    return result

@app.post("/tools/pm.sprint_report")
async def tool_sprint_report(request: SprintReportTool):
    """ARIA Tool: Get sprint report"""
    report = await get_sprint_report(request.sprint_id)

    if not request.include_tasks:
        report['tasks'] = {"total": report['tasks']['total'], "items": "omitted"}
    if not request.include_time:
        report['time'] = {"total_hours": report['time']['total_hours'], "entries": "omitted"}

    return report

@app.post("/tools/pm.log_time")
async def tool_log_time(request: LogTimeTool):
    """ARIA Tool: Log time on a task"""
    entry = TimeEntryCreate(
        task_id=request.task_id,
        user_id="aria",  # Default user for ARIA-logged time
        date=request.date or date.today().isoformat(),
        hours=request.hours,
        notes=request.notes,
        billable=request.billable
    )
    return await log_time(entry)

# =============================================================================
# ADDITIONAL UTILITY ENDPOINTS
# =============================================================================

@app.get("/time-context")
async def get_time():
    """Get current time context"""
    return get_time_context()

@app.get("/system-prompt")
async def get_system_prompt():
    """Get the current system prompt (for debugging)"""
    return {"system_prompt": build_system_prompt()}

@app.post("/ai/breakdown")
async def ai_breakdown(request: BreakdownRequest):
    """AI-powered task breakdown (standalone)"""
    prompt = f"""Break down this work item into actionable tasks:

**Title:** {request.title}
**Description:** {request.description or 'No description'}
**Context:** {request.context or 'No additional context'}

Please provide:
1. A hierarchical breakdown (epic -> stories -> tasks if applicable)
2. For each item:
   - Clear, action-oriented title
   - Brief description
   - Estimated hours
   - Priority
   - Dependencies
3. Acceptance criteria for key items

Format the response as a structured breakdown that can be used to create tasks.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages)

    return {
        "original": request.model_dump(),
        "breakdown": response
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)
