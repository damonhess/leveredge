#!/usr/bin/env python3
"""
MUSE - Creative Director Agent
Port: 8030

Coordinator agent for the LeverEdge Creative Fleet.
Decomposes creative briefs into tasks and orchestrates specialist agents:
- CALLIOPE (8031): Writer
- THALIA (8032): Designer
- ERATO (8033): Media Producer
- CLIO (8034): Reviewer

Capabilities:
- Parse creative briefs into structured tasks
- Route tasks to appropriate specialists
- Manage multi-step workflows with dependencies
- Aggregate outputs into final deliverables
- Track project status and task dependencies
- Create storyboards for video projects
"""

import os
import sys
import json
import uuid
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="MUSE",
    description="Creative Director - Orchestrates the Creative Fleet",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Agent endpoints
AGENT_ENDPOINTS = {
    "CALLIOPE": "http://calliope:8031",
    "THALIA": "http://thalia:8032",
    "ERATO": "http://erato:8033",
    "CLIO": "http://clio:8034",
    "SCHOLAR": "http://scholar:8018",
    "HERMES": "http://hermes:8014",
    "CHRONOS": "http://chronos:8010",
    "HEPHAESTUS": "http://hephaestus:8011",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("MUSE")

# =============================================================================
# ENUMS AND MODELS
# =============================================================================

class ProjectType(str, Enum):
    PRESENTATION = "presentation"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    SOCIAL = "social"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProjectStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class VideoStyle(str, Enum):
    AVATAR = "avatar"
    MOTION = "motion"
    SLIDESHOW = "slideshow"
    STOCK_FOOTAGE = "stock_footage"


class VideoOptions(BaseModel):
    duration_target: Optional[int] = 60  # seconds
    style: Optional[VideoStyle] = VideoStyle.AVATAR
    voice_id: Optional[str] = None
    avatar_id: Optional[str] = None


class CreateProjectRequest(BaseModel):
    type: ProjectType
    brief: str
    brand_id: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[Priority] = Priority.MEDIUM
    video_options: Optional[VideoOptions] = None


class ApproveStageRequest(BaseModel):
    stage: str
    approved: bool
    feedback: Optional[str] = None


class TaskBreakdown(BaseModel):
    task_id: str
    agent: str
    task_type: str
    description: str
    depends_on: List[str] = []
    estimated_duration_seconds: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class ProjectResponse(BaseModel):
    project_id: str
    status: ProjectStatus
    task_breakdown: List[TaskBreakdown]
    estimated_time_minutes: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class Scene(BaseModel):
    scene_number: int
    duration_seconds: float
    narration: str
    visual_direction: str
    on_screen_text: Optional[str] = None


class Storyboard(BaseModel):
    title: str
    total_duration: int
    scenes: List[Scene]
    voice_style: str
    visual_style: str


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
        return "FINAL PUSH"
    elif days_to_launch <= 28:
        return "OUTREACH PHASE"
    elif days_to_launch <= 45:
        return "POLISH PHASE"
    else:
        return "INFRASTRUCTURE PHASE"


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(time_context: dict) -> str:
    """Build creative director system prompt"""
    return f"""You are MUSE - Creative Director for LeverEdge AI.

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}
- Launch: {time_context['launch_date']}
- Status: **{time_context['launch_status']}**
- Phase: {time_context['phase']}

## YOUR IDENTITY
You are the Creative Director of the LeverEdge Creative Fleet. You coordinate a team of specialist agents to produce high-quality content:

- **CALLIOPE** (Writer): Long-form content, copy, scripts, social posts
- **THALIA** (Designer): Presentations, documents, layouts, charts
- **ERATO** (Media Producer): Images, video, audio, avatars
- **CLIO** (Reviewer): Quality assurance, brand compliance, fact-checking

## YOUR CAPABILITIES
1. **Brief Analysis**: Parse creative briefs to understand requirements
2. **Task Decomposition**: Break down projects into discrete tasks
3. **Dependency Management**: Identify which tasks depend on others
4. **Agent Routing**: Assign tasks to the appropriate specialist
5. **Storyboarding**: Create scene-by-scene plans for video projects
6. **Quality Orchestration**: Ensure outputs meet brand standards

## CONTENT TYPES

### Presentations
- Brief -> MUSE outline -> CALLIOPE content -> THALIA design -> ERATO graphics -> CLIO review
- Output: .pptx

### Documents
- Brief -> MUSE structure -> CALLIOPE writing -> THALIA formatting -> CLIO review
- Output: .docx, .pdf, .md

### Images
- Brief -> MUSE direction -> ERATO generation -> CLIO brand check
- Output: .png, .jpg, .svg

### Video
- Brief -> MUSE storyboard -> CALLIOPE script -> ERATO voiceover -> ERATO visuals -> ERATO assembly -> CLIO review
- Output: .mp4, .webm

### Social
- Brief -> MUSE strategy -> CALLIOPE copy -> ERATO image -> CLIO platform check
- Output: text + image package

## TASK DECOMPOSITION RULES

1. **Always start with analysis**: First task is always MUSE analyzing the brief
2. **Parallel when possible**: Tasks without dependencies should run in parallel
3. **Sequential when required**: Design needs content, assembly needs assets
4. **Always end with review**: CLIO reviews all final outputs
5. **Estimate costs**: Include cost estimates for each task

## VIDEO STORYBOARD FORMAT

For video projects, create detailed scene breakdowns:
- Scene number and duration
- Narration text (what is said)
- Visual direction (what is shown)
- On-screen text (titles, captions)

## BRAND AWARENESS

Default brand: LeverEdge AI
- Primary: #1B2951 (Deep storm blue)
- Secondary: #B8860B (Golden bronze)
- Accent: #36454F (Charcoal grey)
- Tone: Professional, knowledgeable, direct but approachable

## OUTPUT FORMAT

When decomposing tasks, return structured JSON with:
- task_id: Unique identifier
- agent: MUSE, CALLIOPE, THALIA, ERATO, or CLIO
- task_type: Specific task type
- description: What needs to be done
- depends_on: List of task_ids this task depends on
- estimated_duration_seconds: Time estimate
- estimated_cost_usd: Cost estimate

{time_context['days_to_launch']} days to launch. Create content that helps LeverEdge succeed.
"""


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def db_insert(table: str, data: dict) -> dict:
    """Insert record into Supabase"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                timeout=10.0
            )
            if response.status_code in [200, 201]:
                result = response.json()
                return result[0] if isinstance(result, list) and result else result
            else:
                print(f"DB insert failed: {response.status_code} - {response.text}")
                return data
    except Exception as e:
        print(f"DB insert error: {e}")
        return data


async def db_update(table: str, record_id: str, data: dict) -> dict:
    """Update record in Supabase"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{record_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                timeout=10.0
            )
            if response.status_code in [200, 201]:
                result = response.json()
                return result[0] if isinstance(result, list) and result else result
            else:
                print(f"DB update failed: {response.status_code}")
                return data
    except Exception as e:
        print(f"DB update error: {e}")
        return data


async def db_select(table: str, filters: dict = None, select: str = "*") -> list:
    """Select records from Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
        if filters:
            for key, value in filters.items():
                url += f"&{key}=eq.{value}"

        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"DB select failed: {response.status_code}")
                return []
    except Exception as e:
        print(f"DB select error: {e}")
        return []


# =============================================================================
# INTER-AGENT COMMUNICATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "MUSE",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus notification failed: {e}")


async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[MUSE] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "MUSE"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")


async def call_agent(agent: str, endpoint: str, payload: dict = {}, timeout: float = 60.0) -> dict:
    """Call another agent"""
    if agent not in AGENT_ENDPOINTS:
        return {"error": f"Unknown agent: {agent}"}

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{AGENT_ENDPOINTS[agent]}{endpoint}",
                json=payload,
                timeout=timeout
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, time_ctx: dict, response_format: str = "text") -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="MUSE",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


async def decompose_brief(brief: str, project_type: ProjectType, video_options: VideoOptions = None) -> List[TaskBreakdown]:
    """Use LLM to decompose a creative brief into tasks"""
    time_ctx = get_time_context()

    video_context = ""
    if project_type == ProjectType.VIDEO and video_options:
        video_context = f"""
VIDEO PROJECT DETAILS:
- Target Duration: {video_options.duration_target} seconds
- Style: {video_options.style.value}
- Voice ID: {video_options.voice_id or 'default'}
- Avatar ID: {video_options.avatar_id or 'default'}
"""

    prompt = f"""Decompose this creative brief into tasks for the Creative Fleet.

BRIEF: {brief}

PROJECT TYPE: {project_type.value}
{video_context}

Return a JSON array of tasks. Each task should have:
- task_id: Unique string ID (e.g., "task_1", "task_2")
- agent: One of MUSE, CALLIOPE, THALIA, ERATO, CLIO
- task_type: Specific task type (e.g., "analyze_brief", "write_content", "design_slides")
- description: Clear description of what needs to be done
- depends_on: Array of task_ids this task depends on (empty for first tasks)
- estimated_duration_seconds: Time estimate
- estimated_cost_usd: Cost estimate (use 0.05 for text, 0.08 for images, 0.50 for video minutes)

RULES:
1. First task is always MUSE analyzing the brief
2. Last task is always CLIO reviewing the output
3. For video: include script, voiceover, visuals, and assembly tasks
4. Parallelize tasks when possible
5. Be specific about what each task produces

Return ONLY the JSON array, no other text."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    # Parse JSON from response
    try:
        # Try to extract JSON from response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        tasks_data = json.loads(response.strip())
        tasks = [TaskBreakdown(**task) for task in tasks_data]
        return tasks
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        # Return a minimal task breakdown
        return [
            TaskBreakdown(
                task_id="task_1",
                agent="MUSE",
                task_type="analyze_brief",
                description="Analyze the creative brief",
                depends_on=[],
                estimated_duration_seconds=30,
                estimated_cost_usd=0.05
            ),
            TaskBreakdown(
                task_id="task_2",
                agent="CLIO",
                task_type="review",
                description="Review final output",
                depends_on=["task_1"],
                estimated_duration_seconds=60,
                estimated_cost_usd=0.05
            )
        ]


async def create_storyboard(brief: str, duration_target: int, style: VideoStyle) -> Storyboard:
    """Create a detailed storyboard for a video project"""
    time_ctx = get_time_context()

    prompt = f"""Create a detailed storyboard for this video project.

BRIEF: {brief}
TARGET DURATION: {duration_target} seconds
STYLE: {style.value}

Return a JSON object with:
- title: Video title
- total_duration: Total duration in seconds
- scenes: Array of scene objects, each with:
  - scene_number: Sequential number starting at 1
  - duration_seconds: Duration of this scene
  - narration: Exact text to be spoken (script)
  - visual_direction: What should be shown visually
  - on_screen_text: Any text overlays (optional)
- voice_style: Description of the voice tone (e.g., "professional", "energetic")
- visual_style: Description of the visual aesthetic

RULES:
1. Total scene durations should equal target duration
2. Average speaking rate is ~150 words per minute (~2.5 words per second)
3. Include intro (3-5s) and outro (3-5s) scenes
4. Each scene should be 10-30 seconds typically
5. Visual directions should be specific and actionable

Return ONLY the JSON object, no other text."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    # Parse JSON from response
    try:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        storyboard_data = json.loads(response.strip())
        return Storyboard(**storyboard_data)
    except json.JSONDecodeError as e:
        print(f"Storyboard JSON parse error: {e}")
        # Return a minimal storyboard
        return Storyboard(
            title="Video Project",
            total_duration=duration_target,
            scenes=[
                Scene(
                    scene_number=1,
                    duration_seconds=5.0,
                    narration="Introduction",
                    visual_direction="Show logo and title",
                    on_screen_text="LeverEdge AI"
                ),
                Scene(
                    scene_number=2,
                    duration_seconds=float(duration_target - 10),
                    narration="Main content based on the brief",
                    visual_direction="Show relevant visuals",
                    on_screen_text=None
                ),
                Scene(
                    scene_number=3,
                    duration_seconds=5.0,
                    narration="Thank you for watching",
                    visual_direction="Show outro and call to action",
                    on_screen_text="Visit leveredgeai.com"
                )
            ],
            voice_style="professional",
            visual_style="modern corporate"
        )


# =============================================================================
# PROJECT MANAGEMENT
# =============================================================================

async def create_project_record(req: CreateProjectRequest) -> dict:
    """Create a new project in the database"""
    project_id = str(uuid.uuid4())

    project_data = {
        "id": project_id,
        "type": req.type.value,
        "brief": req.brief,
        "brand_id": req.brand_id,
        "status": ProjectStatus.PENDING.value,
        "priority": req.priority.value if req.priority else "medium",
        "deadline": req.deadline.isoformat() if req.deadline else None,
        "video_config": req.video_options.model_dump() if req.video_options else None,
        "metadata": {}
    }

    result = await db_insert("creative_projects", project_data)
    return result


async def create_task_records(project_id: str, tasks: List[TaskBreakdown]) -> List[dict]:
    """Create task records in the database"""
    created_tasks = []
    task_id_map = {}  # Map string task_ids to UUIDs

    for task in tasks:
        task_uuid = str(uuid.uuid4())
        task_id_map[task.task_id] = task_uuid

    for task in tasks:
        # Convert depends_on to UUIDs
        depends_on_uuids = [task_id_map[dep] for dep in task.depends_on if dep in task_id_map]

        task_data = {
            "id": task_id_map[task.task_id],
            "project_id": project_id,
            "agent": task.agent,
            "task_type": task.task_type,
            "description": task.description,
            "status": TaskStatus.PENDING.value,
            "depends_on": depends_on_uuids,
            "input_data": {},
            "output_data": {},
            "cost_usd": task.estimated_cost_usd or 0,
            "metadata": {
                "original_task_id": task.task_id,
                "estimated_duration_seconds": task.estimated_duration_seconds
            }
        }

        result = await db_insert("creative_tasks", task_data)
        created_tasks.append(result)

    return created_tasks


async def get_project_with_tasks(project_id: str) -> dict:
    """Get a project with all its tasks"""
    projects = await db_select("creative_projects", {"id": project_id})
    if not projects:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    project = projects[0]

    tasks = await db_select("creative_tasks", {"project_id": project_id})

    # Calculate progress
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
    progress_pct = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

    # Determine current stage
    in_progress_tasks = [t for t in tasks if t.get("status") == "in_progress"]
    current_stage = in_progress_tasks[0].get("task_type") if in_progress_tasks else "pending"

    return {
        "project": project,
        "tasks": tasks,
        "current_stage": current_stage,
        "progress_pct": progress_pct
    }


async def get_project_outputs(project_id: str) -> dict:
    """Get all outputs for a project"""
    assets = await db_select("creative_assets", {"project_id": project_id})

    files = []
    preview_urls = []

    for asset in assets:
        if asset.get("is_final"):
            files.append({
                "path": asset.get("file_path"),
                "type": asset.get("asset_type"),
                "size": asset.get("file_size"),
                "mime_type": asset.get("mime_type")
            })
            # Generate preview URL (would be actual URL in production)
            preview_urls.append(f"/preview/{asset.get('id')}")

    return {
        "files": files,
        "preview_urls": preview_urls
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
@app.post("/health")
async def health():
    """Health check endpoint"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "MUSE",
        "role": "Creative Director",
        "version": "1.0.0",
        "port": 8030,
        "fleet": {
            "CALLIOPE": "Writer (8031)",
            "THALIA": "Designer (8032)",
            "ERATO": "Media Producer (8033)",
            "CLIO": "Reviewer (8034)"
        },
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase']
    }


@app.get("/time")
async def get_time():
    """Get current time context"""
    return get_time_context()


@app.get("/fleet")
async def get_fleet():
    """Get Creative Fleet information"""
    return {
        "director": {
            "name": "MUSE",
            "role": "Creative Director",
            "port": 8030
        },
        "specialists": [
            {"name": "CALLIOPE", "role": "Writer", "port": 8031, "capabilities": ["copy", "scripts", "documents", "social"]},
            {"name": "THALIA", "role": "Designer", "port": 8032, "capabilities": ["presentations", "layouts", "charts", "formatting"]},
            {"name": "ERATO", "role": "Media Producer", "port": 8033, "capabilities": ["images", "video", "audio", "avatars"]},
            {"name": "CLIO", "role": "Reviewer", "port": 8034, "capabilities": ["brand_check", "quality", "fact_check"]}
        ],
        "content_types": ["presentation", "document", "image", "video", "social"],
        "endpoints": AGENT_ENDPOINTS
    }


@app.post("/projects/create", response_model=ProjectResponse)
async def create_project(req: CreateProjectRequest, background_tasks: BackgroundTasks):
    """Create a new creative project"""
    time_ctx = get_time_context()

    # Decompose the brief into tasks
    tasks = await decompose_brief(req.brief, req.type, req.video_options)

    # Create project record
    project = await create_project_record(req)
    project_id = project.get("id", str(uuid.uuid4()))

    # Create task records
    await create_task_records(project_id, tasks)

    # Calculate estimates
    total_time = sum(t.estimated_duration_seconds or 60 for t in tasks)
    total_cost = sum(t.estimated_cost_usd or 0.05 for t in tasks)

    # Notify event bus
    await notify_event_bus("project_created", {
        "project_id": project_id,
        "type": req.type.value,
        "task_count": len(tasks),
        "estimated_cost": total_cost
    })

    return ProjectResponse(
        project_id=project_id,
        status=ProjectStatus.PENDING,
        task_breakdown=tasks,
        estimated_time_minutes=int(total_time / 60) + 1,
        estimated_cost_usd=round(total_cost, 2)
    )


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project status and details"""
    return await get_project_with_tasks(project_id)


@app.post("/projects/{project_id}/approve")
async def approve_stage(project_id: str, req: ApproveStageRequest):
    """Approve or provide feedback on a project stage"""
    time_ctx = get_time_context()

    # Get project
    project_data = await get_project_with_tasks(project_id)
    project = project_data["project"]
    tasks = project_data["tasks"]

    # Find the task for this stage
    stage_task = None
    for task in tasks:
        if task.get("task_type") == req.stage:
            stage_task = task
            break

    if not stage_task:
        raise HTTPException(status_code=404, detail=f"Stage '{req.stage}' not found")

    if req.approved:
        # Mark stage as completed
        await db_update("creative_tasks", stage_task["id"], {
            "status": TaskStatus.COMPLETED.value,
            "completed_at": datetime.now().isoformat()
        })

        await notify_event_bus("stage_approved", {
            "project_id": project_id,
            "stage": req.stage
        })

        return {
            "status": "approved",
            "project_id": project_id,
            "stage": req.stage,
            "message": f"Stage '{req.stage}' approved"
        }
    else:
        # Store feedback for revision
        feedback_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "feedback_type": "revision",
            "feedback_text": req.feedback,
            "given_by": "user"
        }
        await db_insert("creative_feedback", feedback_data)

        await notify_event_bus("stage_feedback", {
            "project_id": project_id,
            "stage": req.stage,
            "feedback": req.feedback
        })

        return {
            "status": "revision_requested",
            "project_id": project_id,
            "stage": req.stage,
            "feedback": req.feedback
        }


@app.get("/projects/{project_id}/output")
async def get_output(project_id: str):
    """Get final outputs for a project"""
    return await get_project_outputs(project_id)


@app.post("/projects/{project_id}/cancel")
async def cancel_project(project_id: str):
    """Cancel a project"""
    # Update project status
    await db_update("creative_projects", project_id, {
        "status": ProjectStatus.FAILED.value
    })

    await notify_event_bus("project_cancelled", {
        "project_id": project_id
    })

    return {
        "status": "cancelled",
        "project_id": project_id,
        "refund_estimate": 0.00  # Would calculate based on incomplete tasks
    }


@app.get("/decompose")
async def decompose_endpoint(brief: str, project_type: str = "document"):
    """Internal endpoint to decompose a brief into tasks"""
    try:
        ptype = ProjectType(project_type)
    except ValueError:
        ptype = ProjectType.DOCUMENT

    tasks = await decompose_brief(brief, ptype)

    return {
        "brief": brief,
        "project_type": project_type,
        "tasks": [t.model_dump() for t in tasks]
    }


@app.post("/storyboard")
async def create_storyboard_endpoint(
    brief: str,
    duration_target: int = 60,
    style: str = "avatar"
):
    """Create a storyboard for a video project"""
    try:
        video_style = VideoStyle(style)
    except ValueError:
        video_style = VideoStyle.AVATAR

    storyboard = await create_storyboard(brief, duration_target, video_style)

    return {
        "storyboard": storyboard.model_dump(),
        "brief": brief,
        "duration_target": duration_target,
        "style": style
    }


@app.get("/brands")
async def list_brands():
    """List available brands"""
    brands = await db_select("creative_brands")
    return {"brands": brands}


@app.get("/brands/{brand_id}")
async def get_brand(brand_id: str):
    """Get brand details"""
    brands = await db_select("creative_brands", {"id": brand_id})
    if not brands:
        raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
    return brands[0]


@app.get("/stats")
async def get_stats():
    """Get creative fleet statistics"""
    projects = await db_select("creative_projects")
    tasks = await db_select("creative_tasks")

    total_projects = len(projects)
    completed_projects = len([p for p in projects if p.get("status") == "completed"])
    in_progress_projects = len([p for p in projects if p.get("status") == "in_progress"])

    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get("status") == "completed"])

    # Calculate total cost
    total_cost = sum(float(p.get("total_cost_usd", 0) or 0) for p in projects)

    # Projects by type
    by_type = {}
    for p in projects:
        ptype = p.get("type", "unknown")
        by_type[ptype] = by_type.get(ptype, 0) + 1

    return {
        "projects": {
            "total": total_projects,
            "completed": completed_projects,
            "in_progress": in_progress_projects,
            "by_type": by_type
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "completion_rate": f"{(completed_tasks / total_tasks * 100):.1f}%" if total_tasks > 0 else "0%"
        },
        "cost": {
            "total_usd": round(total_cost, 2)
        }
    }


# =============================================================================
# WORKFLOW EXECUTION (Background)
# =============================================================================

async def execute_project_workflow(project_id: str):
    """Execute all tasks in a project workflow"""
    project_data = await get_project_with_tasks(project_id)
    tasks = project_data["tasks"]

    # Update project status
    await db_update("creative_projects", project_id, {
        "status": ProjectStatus.IN_PROGRESS.value
    })

    # Build dependency graph
    task_map = {t["id"]: t for t in tasks}
    completed = set()

    while len(completed) < len(tasks):
        # Find tasks that are ready to run (all dependencies completed)
        ready_tasks = []
        for task in tasks:
            task_id = task["id"]
            if task_id in completed:
                continue

            depends_on = task.get("depends_on", [])
            if all(dep in completed for dep in depends_on):
                ready_tasks.append(task)

        if not ready_tasks:
            # No tasks ready but not all complete - possible deadlock
            print(f"Warning: No tasks ready for project {project_id}")
            break

        # Execute ready tasks (could parallelize here)
        for task in ready_tasks:
            try:
                await execute_task(task)
                completed.add(task["id"])
            except Exception as e:
                print(f"Task {task['id']} failed: {e}")
                await db_update("creative_tasks", task["id"], {
                    "status": TaskStatus.FAILED.value,
                    "error_message": str(e)
                })

    # Update project status
    all_completed = len(completed) == len(tasks)
    await db_update("creative_projects", project_id, {
        "status": ProjectStatus.COMPLETED.value if all_completed else ProjectStatus.FAILED.value,
        "completed_at": datetime.now().isoformat() if all_completed else None
    })

    await notify_event_bus("project_completed" if all_completed else "project_failed", {
        "project_id": project_id
    })


async def execute_task(task: dict):
    """Execute a single task by calling the appropriate agent"""
    agent = task.get("agent")
    task_type = task.get("task_type")
    task_id = task.get("id")

    # Mark task as in progress
    await db_update("creative_tasks", task_id, {
        "status": TaskStatus.IN_PROGRESS.value,
        "started_at": datetime.now().isoformat()
    })

    # Route to appropriate agent
    result = {}
    if agent == "MUSE":
        # MUSE handles analysis tasks internally
        result = {"status": "completed", "output": "Brief analyzed"}
    elif agent == "CALLIOPE":
        result = await call_agent("CALLIOPE", "/write", {
            "brief": task.get("description"),
            "type": task_type
        })
    elif agent == "THALIA":
        result = await call_agent("THALIA", "/design", {
            "brief": task.get("description"),
            "type": task_type
        })
    elif agent == "ERATO":
        result = await call_agent("ERATO", "/generate", {
            "brief": task.get("description"),
            "type": task_type
        })
    elif agent == "CLIO":
        result = await call_agent("CLIO", "/review", {
            "content": task.get("input_data"),
            "type": task_type
        })

    # Update task with results
    await db_update("creative_tasks", task_id, {
        "status": TaskStatus.COMPLETED.value,
        "completed_at": datetime.now().isoformat(),
        "output_data": result
    })

    return result


@app.post("/projects/{project_id}/execute")
async def execute_project(project_id: str, background_tasks: BackgroundTasks):
    """Start executing a project workflow"""
    background_tasks.add_task(execute_project_workflow, project_id)

    return {
        "status": "started",
        "project_id": project_id,
        "message": "Project execution started in background"
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)
