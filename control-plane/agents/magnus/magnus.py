"""
MAGNUS - Universal Project Master
Port: 8017
Domain: CHANCERY

Every move calculated. Every piece in position. Checkmate is inevitable.
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import os
import asyncpg

app = FastAPI(
    title="MAGNUS - Universal Project Master",
    description="Every move calculated. Every piece in position. Checkmate is inevitable.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
pool: asyncpg.Pool = None


@app.on_event("startup")
async def startup():
    global pool
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


# ============ HEALTH ============

@app.get("/health")
async def health():
    db_status = "connected" if pool else "no connection"
    return {
        "status": "healthy",
        "service": "MAGNUS - Universal Project Master",
        "port": 8017,
        "database": db_status,
        "tagline": "Every move calculated. Every piece in position. Checkmate is inevitable."
    }


@app.get("/status")
async def magnus_status():
    """MAGNUS's current assessment of the board"""
    if not pool:
        return {
            "magnus_says": "Database not connected. Cannot assess the board.",
            "active_projects": 0,
            "overdue_tasks": 0,
            "open_blockers": 0,
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "timestamp": datetime.now().isoformat()
        }

    async with pool.acquire() as conn:
        # Get active projects count
        projects = await conn.fetch("""
            SELECT * FROM magnus_projects WHERE status IN ('planning', 'active')
        """)

        # Get overdue tasks count
        overdue = await conn.fetchrow("""
            SELECT COUNT(*) as count FROM magnus_tasks
            WHERE due_date < CURRENT_DATE AND status NOT IN ('done', 'cancelled')
        """)

        # Get open blockers count
        blockers = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM magnus_blockers WHERE status = 'open'"
        )

        overdue_count = overdue['count'] if overdue else 0
        blocker_count = blockers['count'] if blockers else 0

        # MAGNUS's assessment
        if overdue_count > 5:
            assessment = "Critical position. Multiple pieces under attack. Immediate action required."
        elif blocker_count > 3:
            assessment = "Board congestion. Several pieces blocked. Need to clear lanes."
        elif overdue_count > 0 or blocker_count > 0:
            assessment = "Minor pressure on the position. Manageable with focused attention."
        else:
            assessment = "Strong position. Pieces are coordinated. Continuing the attack."

        return {
            "magnus_says": assessment,
            "active_projects": len(projects),
            "overdue_tasks": overdue_count,
            "open_blockers": blocker_count,
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "timestamp": datetime.now().isoformat()
        }


# ============ PROJECTS ============

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_end: Optional[date] = None
    client_name: Optional[str] = None
    template: Optional[str] = None
    priority: int = 50


@app.get("/projects")
async def list_projects(status: Optional[str] = None):
    """List all projects with summaries"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM magnus_project_summary(NULL) WHERE status = $1",
                status
            )
        else:
            rows = await conn.fetch("SELECT * FROM magnus_project_summary(NULL)")
        return [dict(row) for row in rows]


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project with full details"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM magnus_projects WHERE id = $1",
            project_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return dict(row)


@app.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_projects (name, description, target_end, client_name, template_used, priority)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, project.name, project.description, project.target_end,
            project.client_name, project.template, project.priority)
        return dict(row)


@app.patch("/projects/{project_id}")
async def update_project(project_id: str, updates: Dict[str, Any]):
    """Update a project"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    allowed_fields = ['name', 'description', 'status', 'priority', 'target_end', 'client_name']
    updates = {k: v for k, v in updates.items() if k in allowed_fields}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(updates.keys())])
    set_clause += ", updated_at = NOW()"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE magnus_projects SET {set_clause} WHERE id = $1 RETURNING *",
            project_id, *updates.values()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return dict(row)


# ============ TASKS ============

class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    assigned_agent: Optional[str] = None
    due_date: Optional[date] = None
    priority: str = "medium"
    estimated_hours: Optional[float] = None


@app.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    overdue: bool = False
):
    """List tasks with optional filters"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        if overdue:
            rows = await conn.fetch("""
                SELECT t.*, p.name as project_name
                FROM magnus_tasks t
                JOIN magnus_projects p ON t.project_id = p.id
                WHERE t.due_date < CURRENT_DATE
                AND t.status NOT IN ('done', 'cancelled')
                ORDER BY t.due_date
            """)
        else:
            query = """
                SELECT t.*, p.name as project_name
                FROM magnus_tasks t
                JOIN magnus_projects p ON t.project_id = p.id
                WHERE 1=1
            """
            params = []

            if project_id:
                params.append(project_id)
                query += f" AND t.project_id = ${len(params)}::uuid"
            if status:
                params.append(status)
                query += f" AND t.status = ${len(params)}"
            if assigned_agent:
                params.append(assigned_agent)
                query += f" AND t.assigned_agent = ${len(params)}"

            query += " ORDER BY t.priority DESC, t.due_date"
            rows = await conn.fetch(query, *params)

        return [dict(row) for row in rows]


@app.post("/tasks")
async def create_task(task: TaskCreate):
    """Create a new task"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_tasks (project_id, title, description, assigned_agent, due_date, priority, estimated_hours)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, task.project_id, task.title, task.description,
            task.assigned_agent, task.due_date, task.priority, task.estimated_hours)
        return dict(row)


@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, notes: Optional[str] = None):
    """Mark a task as complete"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE magnus_tasks
            SET status = 'done', completed_at = NOW(), notes = COALESCE($2, notes)
            WHERE id = $1::uuid
            RETURNING *
        """, task_id, notes)
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "completed", "task": dict(row)}


@app.post("/tasks/{task_id}/block")
async def block_task(task_id: str, reason: str, blocker_type: str = "other"):
    """Mark a task as blocked and create a blocker"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Update task status
        task = await conn.fetchrow("""
            UPDATE magnus_tasks SET status = 'blocked', updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Create blocker
        blocker = await conn.fetchrow("""
            INSERT INTO magnus_blockers (task_id, project_id, description, blocker_type)
            VALUES ($1::uuid, $2, $3, $4)
            RETURNING *
        """, task_id, task['project_id'], reason, blocker_type)

        return {
            "status": "blocked",
            "task": dict(task),
            "blocker": dict(blocker)
        }


# ============ BLOCKERS ============

@app.get("/blockers")
async def list_blockers(status: str = "open"):
    """List blockers"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT b.*, t.title as task_title, p.name as project_name
            FROM magnus_blockers b
            LEFT JOIN magnus_tasks t ON b.task_id = t.id
            LEFT JOIN magnus_projects p ON b.project_id = p.id
            WHERE b.status = $1
            ORDER BY b.severity DESC, b.created_at
        """, status)
        return [dict(row) for row in rows]


@app.post("/blockers/{blocker_id}/resolve")
async def resolve_blocker(blocker_id: str, resolution: str):
    """Resolve a blocker"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        blocker = await conn.fetchrow("""
            UPDATE magnus_blockers
            SET status = 'resolved', resolution = $2, resolved_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, blocker_id, resolution)

        if not blocker:
            raise HTTPException(status_code=404, detail="Blocker not found")

        # If there's an associated task, unblock it
        if blocker['task_id']:
            await conn.execute("""
                UPDATE magnus_tasks SET status = 'todo', updated_at = NOW()
                WHERE id = $1 AND status = 'blocked'
            """, blocker['task_id'])

        return {"status": "resolved", "blocker": dict(blocker)}


# ============ DECISIONS ============

class DecisionCreate(BaseModel):
    project_id: str
    question: str
    context: Optional[str] = None
    options: List[str] = []
    deadline: Optional[date] = None


@app.get("/decisions")
async def list_decisions(status: str = "pending"):
    """List pending decisions"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT d.*, p.name as project_name
            FROM magnus_decisions d
            JOIN magnus_projects p ON d.project_id = p.id
            WHERE d.status = $1
            ORDER BY d.decision_deadline, d.created_at
        """, status)
        return [dict(row) for row in rows]


@app.post("/decisions")
async def create_decision(decision: DecisionCreate):
    """Create a decision request"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    import json
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_decisions (project_id, question, context, options, decision_deadline)
            VALUES ($1::uuid, $2, $3, $4::jsonb, $5)
            RETURNING *
        """, decision.project_id, decision.question, decision.context,
            json.dumps(decision.options), decision.deadline)
        return dict(row)


@app.post("/decisions/{decision_id}/decide")
async def make_decision(decision_id: str, decision: str, rationale: Optional[str] = None):
    """Record a decision"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE magnus_decisions
            SET status = 'decided', decision = $2, rationale = $3,
                decided_by = 'damon', decided_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, decision_id, decision, rationale)
        if not row:
            raise HTTPException(status_code=404, detail="Decision not found")
        return dict(row)


# ============ STANDUP ============

@app.post("/standup/generate")
async def generate_standup():
    """Generate a daily standup summary"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Get project summaries
        projects = await conn.fetch("SELECT * FROM magnus_project_summary(NULL)")

        # Get overdue tasks
        overdue = await conn.fetch("""
            SELECT t.*, p.name as project_name FROM magnus_tasks t
            JOIN magnus_projects p ON t.project_id = p.id
            WHERE t.due_date < CURRENT_DATE AND t.status NOT IN ('done', 'cancelled')
            ORDER BY t.due_date
        """)

        # Get open blockers
        blockers = await conn.fetch("""
            SELECT b.*, p.name as project_name FROM magnus_blockers b
            JOIN magnus_projects p ON b.project_id = p.id
            WHERE b.status = 'open'
            ORDER BY b.severity DESC
        """)

        # Get pending decisions
        decisions = await conn.fetch("""
            SELECT d.*, p.name as project_name FROM magnus_decisions d
            JOIN magnus_projects p ON d.project_id = p.id
            WHERE d.status = 'pending'
            ORDER BY d.decision_deadline
        """)

        # Calculate overall health
        total_blocked = sum(p['tasks_blocked'] for p in projects)
        total_overdue = len(overdue)
        total_blockers = len(blockers)

        if total_blocked > 5 or total_overdue > 10:
            health_emoji = "🚨"
            health_label = "Critical"
        elif total_blocked > 2 or total_overdue > 5:
            health_emoji = "⚠️"
            health_label = "At Risk"
        elif total_blocked > 0 or total_overdue > 0:
            health_emoji = "🔶"
            health_label = "Minor Issues"
        else:
            health_emoji = "✅"
            health_label = "On Track"

        return {
            "date": str(date.today()),
            "health": f"{health_emoji} {health_label}",
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "projects": [dict(p) for p in projects],
            "overdue_tasks": [dict(t) for t in overdue],
            "open_blockers": [dict(b) for b in blockers],
            "pending_decisions": [dict(d) for d in decisions],
            "summary": {
                "total_projects": len(projects),
                "overdue_count": total_overdue,
                "blockers_count": total_blockers,
                "decisions_pending": len(decisions)
            }
        }


# ============ CONNECTIONS ============

@app.get("/connections")
async def list_connections():
    """List PM tool connections"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM magnus_pm_connections ORDER BY tool_name"
        )
        return [dict(row) for row in rows]


@app.get("/connections/supported")
async def supported_tools():
    """List supported PM tools"""
    return [
        {"name": "leantime", "status": "implemented", "internal": True},
        {"name": "openproject", "status": "stub", "internal": True},
        {"name": "asana", "status": "planned", "internal": False},
        {"name": "jira", "status": "planned", "internal": False},
        {"name": "monday", "status": "planned", "internal": False},
        {"name": "notion", "status": "planned", "internal": False},
        {"name": "linear", "status": "planned", "internal": False},
        {"name": "clickup", "status": "planned", "internal": False},
        {"name": "trello", "status": "planned", "internal": False}
    ]


# ============ TEMPLATES ============

@app.get("/templates")
async def list_templates():
    """List project templates"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM magnus_project_templates ORDER BY name")
        return [dict(row) for row in rows]


@app.post("/projects/from-template")
async def create_project_from_template(
    template_name: str,
    project_name: str,
    client_name: Optional[str] = None,
    target_start: Optional[date] = None
):
    """Create a project from a template"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Get template
        template = await conn.fetchrow(
            "SELECT * FROM magnus_project_templates WHERE name = $1",
            template_name
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Calculate dates
        start = target_start or date.today()
        end = start + timedelta(days=template['estimated_duration_days'] or 30)

        # Create project
        project = await conn.fetchrow("""
            INSERT INTO magnus_projects (name, description, target_start, target_end, client_name, template_used)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, project_name, template['description'], start, end, client_name, template_name)

        # Create default tasks
        import json
        tasks_created = []
        default_tasks = json.loads(template['default_tasks']) if template['default_tasks'] else []

        for task_def in default_tasks:
            task = await conn.fetchrow("""
                INSERT INTO magnus_tasks (project_id, title, notes)
                VALUES ($1, $2, $3)
                RETURNING *
            """, project['id'], task_def.get('title', 'Task'), task_def.get('phase', ''))
            tasks_created.append(dict(task))

        return {
            "project": dict(project),
            "tasks_created": len(tasks_created),
            "template_used": template_name
        }


# ============ AGENT WORKLOAD ============

@app.get("/agents/workload")
async def get_agent_workloads():
    """Get current agent workloads"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT w.*, COALESCE(t.active_count, 0) as current_active
            FROM magnus_agent_workload w
            LEFT JOIN (
                SELECT assigned_agent, COUNT(*) as active_count
                FROM magnus_tasks
                WHERE status IN ('in_progress', 'todo')
                GROUP BY assigned_agent
            ) t ON w.agent = t.assigned_agent
            ORDER BY w.agent
        """)
        return [dict(row) for row in rows]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
