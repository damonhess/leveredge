#!/usr/bin/env python3
"""
GYM COACH - AI-Powered Fitness & Workout Agent
Port: 8100

Personalized workout programming, progressive overload tracking,
exercise guidance, form analysis, and recovery management.
Named after Apollo - Greek god of athletics and physical perfection.

TEAM INTEGRATION:
- Time-aware (knows current date, program week)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs achievements to aria_knowledge

PHASE 1 CAPABILITIES:
- Health and status endpoints
- Program CRUD stubs
- Session management stubs
- Exercise library stubs
- Logging stubs
- Recovery tracking stubs
- Progress analytics stubs
- ARIA tool stubs
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="GYM COACH",
    description="AI-Powered Fitness & Workout Agent",
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
    "HERMES": "http://hermes:8014",
    "CHIRON": "http://chiron:8017",
    "EVENT_BUS": EVENT_BUS_URL
}

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("GYM_COACH")

# =============================================================================
# ENUMS
# =============================================================================

class GoalType(str, Enum):
    STRENGTH = "strength"
    HYPERTROPHY = "hypertrophy"
    ENDURANCE = "endurance"
    POWER = "power"
    FAT_LOSS = "fat_loss"

class SplitType(str, Enum):
    PPL = "ppl"  # Push/Pull/Legs
    UPPER_LOWER = "upper_lower"
    FULL_BODY = "full_body"
    BRO_SPLIT = "bro_split"

class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class WeightUnit(str, Enum):
    LBS = "lbs"
    KG = "kg"

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

# Program Models
class ProgramCreate(BaseModel):
    name: str
    goal: GoalType
    frequency: int = Field(ge=2, le=6, description="Days per week")
    split_type: Optional[SplitType] = None
    duration_weeks: int = Field(default=12, ge=4, le=52)
    notes: Optional[str] = None

class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[GoalType] = None
    frequency: Optional[int] = Field(default=None, ge=2, le=6)
    split_type: Optional[SplitType] = None
    notes: Optional[str] = None

class ProgramGenerateRequest(BaseModel):
    goal: GoalType
    frequency: int = Field(ge=2, le=6)
    equipment: List[str] = ["barbell", "dumbbell", "cable", "machine"]
    experience_level: Difficulty = Difficulty.INTERMEDIATE
    injuries: Optional[List[str]] = None
    preferences: Optional[str] = None

# Session Models
class SessionCreate(BaseModel):
    program_id: Optional[str] = None
    workout_name: str
    scheduled_date: Optional[date] = None
    location: Optional[str] = "gym"

class SessionUpdate(BaseModel):
    workout_name: Optional[str] = None
    notes: Optional[str] = None
    energy_level: Optional[int] = Field(default=None, ge=1, le=10)
    overall_rating: Optional[int] = Field(default=None, ge=1, le=10)

class SessionComplete(BaseModel):
    duration_minutes: int
    notes: Optional[str] = None
    energy_level: Optional[int] = Field(default=None, ge=1, le=10)
    overall_rating: Optional[int] = Field(default=None, ge=1, le=10)

# Exercise Log Models
class ExerciseLogCreate(BaseModel):
    session_id: str
    exercise_name: str
    set_number: int
    reps: Optional[int] = None
    weight: Optional[float] = None
    weight_unit: WeightUnit = WeightUnit.LBS
    rpe: Optional[int] = Field(default=None, ge=1, le=10)
    rest_seconds: Optional[int] = None
    tempo: Optional[str] = None
    notes: Optional[str] = None
    is_warmup: bool = False

# Recovery Models
class RecoveryLogCreate(BaseModel):
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    sleep_quality: Optional[int] = Field(default=None, ge=1, le=10)
    energy_level: Optional[int] = Field(default=None, ge=1, le=10)
    stress_level: Optional[int] = Field(default=None, ge=1, le=10)
    soreness: Optional[Dict[str, int]] = None  # {"legs": 7, "chest": 3}
    notes: Optional[str] = None

class RecoveryCheckIn(BaseModel):
    energy_level: int = Field(ge=1, le=10)
    soreness_level: int = Field(ge=1, le=10)
    sleep_quality: Optional[int] = Field(default=None, ge=1, le=10)

# Body Metrics Models
class BodyMetricsCreate(BaseModel):
    weight: Optional[float] = None
    weight_unit: WeightUnit = WeightUnit.LBS
    body_fat_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    measurements: Optional[Dict[str, float]] = None
    notes: Optional[str] = None

# AI Request Models
class WeightSuggestionRequest(BaseModel):
    exercise_name: str
    target_reps: int
    target_rpe: int = Field(default=8, ge=1, le=10)

class FormCheckRequest(BaseModel):
    exercise_name: str
    description: str  # Description of form issue or question

class PlateauBreakRequest(BaseModel):
    exercise_name: str
    current_weight: float
    current_reps: int
    weeks_stuck: int = 2

# ARIA Tool Models
class LogWorkoutRequest(BaseModel):
    exercises: List[Dict[str, Any]]  # [{name, sets, reps, weight}]
    duration_minutes: int
    energy_level: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None

class ProgressRequest(BaseModel):
    exercise_name: Optional[str] = None
    period: str = "month"  # week, month, quarter, year

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()

    # Calculate week of year for periodization context
    week_of_year = today.isocalendar()[1]

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "week_of_year": week_of_year,
        "is_weekend": today.weekday() >= 5
    }

# =============================================================================
# SYSTEM PROMPT BUILDER
# =============================================================================

def build_system_prompt(fitness_context: dict) -> str:
    """Build the GYM COACH system prompt with fitness context"""

    return f"""You are GYM COACH - Elite Fitness & Training Agent for LeverEdge AI.

Named after Apollo, Greek god of athletics and physical perfection, you guide users toward their fitness goals with science-backed training wisdom.

## TIME AWARENESS
- Current: {fitness_context.get('current_time', 'Unknown')} on {fitness_context.get('day_of_week', 'Unknown')}, {fitness_context.get('current_date', 'Unknown')}
- User's Program Week: {fitness_context.get('current_week', 'Not set')}/{fitness_context.get('total_weeks', 12)}

## YOUR IDENTITY
You are the personal trainer brain of LeverEdge. You design programs, track progress, analyze form, and ensure users train effectively and safely.

## CURRENT FITNESS STATUS
- Active Program: {fitness_context.get('active_program', 'None')}
- Current Week: {fitness_context.get('current_week', 1)}/{fitness_context.get('total_weeks', 12)}
- Workouts This Week: {fitness_context.get('workouts_this_week', 0)}
- Last Workout: {fitness_context.get('last_workout', 'None recorded')}
- Recent PRs: {fitness_context.get('recent_prs', 'None')}
- Recovery Status: {fitness_context.get('recovery_status', 'Unknown')}

## YOUR CAPABILITIES

### Workout Planning
- Create personalized programs (strength, hypertrophy, endurance)
- Adjust frequency based on schedule and recovery
- Design splits (PPL, Upper/Lower, Full Body, Bro Split)
- Plan periodization and deload weeks
- Substitute exercises based on equipment/injuries

### Progressive Overload
- Track all lifts and suggest weight increases
- Monitor volume and intensity trends
- Detect plateaus and recommend breakthrough strategies
- Celebrate PRs and milestones
- Calculate estimated 1RMs

### Exercise Guidance
- Access library of 500+ exercises
- Provide form cues and common mistake corrections
- Suggest alternatives and variations
- Recommend warm-up and mobility work
- Guide injury-safe training modifications

### Form Analysis
- Analyze form descriptions for issues
- Provide cue recommendations
- Suggest mobility/flexibility work
- Identify movement pattern problems
- Recommend corrective exercises

### Recovery Optimization
- Track sleep, soreness, and energy
- Recommend rest days and deloads
- Consider stress and fatigue accumulation
- Optimize training frequency
- Prevent overtraining

## TRAINING PRINCIPLES
1. Progressive overload is the key to gains
2. Consistency beats intensity
3. Recovery is when growth happens
4. Form before weight, always
5. Track everything to improve anything

## RESPONSE FORMAT
For workout queries:
1. Acknowledge current status/recovery
2. Provide clear exercise prescription
3. Include weight suggestions based on history
4. Note any form cues or considerations
5. Motivate and encourage

## TEAM COORDINATION
- Log insights and PRs -> ARIA via Unified Memory
- Publish achievements -> Event Bus
- Send milestone notifications -> HERMES
- Coordinate with nutrition (future) -> DEMETER

## YOUR MISSION
Help users achieve their fitness goals safely and effectively.
Every rep counts. Every PR matters.
Build strength, build confidence, build better humans.
"""

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
                    "source": "GYM_COACH",
                    "data": data,
                    "timestamp": time_ctx['current_datetime']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[GYM_COACH] Event bus publish failed: {e}")

async def notify_hermes(message: str, priority: str = "normal"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[GYM COACH] {message}",
                    "priority": priority,
                    "source": "GYM_COACH"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[GYM_COACH] HERMES notification failed: {e}")

async def update_aria_memory(memory_type: str, content: str, category: str = "fitness", tags: List[str] = None):
    """Store memory in ARIA's Unified Memory"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/unified_memories",
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
                    "tags": tags or ["gym-coach"],
                    "created_at": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[GYM_COACH] Memory update failed: {e}")

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, fitness_context: dict) -> str:
    """Call Claude API with fitness context and cost tracking"""
    if not client:
        raise HTTPException(status_code=500, detail="Anthropic client not configured")

    try:
        system_prompt = build_system_prompt(fitness_context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="GYM_COACH",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"program_week": fitness_context.get("current_week")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# STUB: FITNESS CONTEXT BUILDER
# =============================================================================

async def get_fitness_context(user_id: str = "default") -> dict:
    """Build fitness context from database - STUB for Phase 1"""
    time_ctx = get_time_context()

    # TODO: Fetch from database in Phase 2
    return {
        **time_ctx,
        "active_program": "None - Create a program to get started",
        "current_week": 1,
        "total_weeks": 12,
        "workouts_this_week": 0,
        "last_workout": "None recorded",
        "recent_prs": "None yet - let's change that!",
        "recovery_status": "Unknown - log recovery data to track"
    }

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "GYM_COACH",
        "role": "Fitness & Workout Agent",
        "port": 8100,
        "current_time": time_ctx['current_datetime'],
        "day_of_week": time_ctx['day_of_week'],
        "version": "1.0.0"
    }

@app.get("/status")
async def status(user_id: str = "default"):
    """Get current training status overview"""
    fitness_ctx = await get_fitness_context(user_id)

    return {
        "agent": "GYM_COACH",
        "user_id": user_id,
        "fitness_context": fitness_ctx,
        "capabilities": [
            "workout_planning",
            "progressive_overload",
            "exercise_library",
            "form_analysis",
            "recovery_tracking"
        ],
        "aria_tools": [
            "gym.log_workout",
            "gym.get_program",
            "gym.next_workout",
            "gym.progress",
            "gym.suggest_weight"
        ]
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint - STUB"""
    return {
        "gym_coach_requests_total": 0,
        "gym_coach_workouts_logged": 0,
        "gym_coach_prs_achieved": 0,
        "gym_coach_ai_calls_total": 0
    }

# =============================================================================
# WORKOUT PROGRAMS ENDPOINTS
# =============================================================================

@app.get("/programs")
async def list_programs(user_id: str = "default"):
    """List user's workout programs - STUB"""
    return {
        "programs": [],
        "message": "No programs yet. Use POST /programs or POST /programs/generate to create one.",
        "user_id": user_id
    }

@app.post("/programs")
async def create_program(program: ProgramCreate, user_id: str = "default"):
    """Create a new workout program - STUB"""
    # TODO: Implement database storage in Phase 2
    program_id = f"prog_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    await publish_event("gym.program.created", {
        "user_id": user_id,
        "program_id": program_id,
        "name": program.name,
        "goal": program.goal
    })

    return {
        "id": program_id,
        "message": f"Program '{program.name}' created (stub - database not yet connected)",
        "program": program.model_dump(),
        "user_id": user_id
    }

@app.get("/programs/{program_id}")
async def get_program(program_id: str, user_id: str = "default"):
    """Get program details - STUB"""
    return {
        "message": f"Program {program_id} not found (database not yet connected)",
        "stub": True
    }

@app.put("/programs/{program_id}")
async def update_program(program_id: str, update: ProgramUpdate, user_id: str = "default"):
    """Update a program - STUB"""
    return {
        "message": f"Program {program_id} would be updated (stub)",
        "updates": update.model_dump(exclude_none=True)
    }

@app.delete("/programs/{program_id}")
async def delete_program(program_id: str, user_id: str = "default"):
    """Delete a program - STUB"""
    return {
        "message": f"Program {program_id} would be deleted (stub)",
        "deleted": True
    }

@app.post("/programs/{program_id}/activate")
async def activate_program(program_id: str, user_id: str = "default"):
    """Set a program as active - STUB"""
    return {
        "message": f"Program {program_id} would be activated (stub)",
        "active": True
    }

@app.get("/programs/{program_id}/schedule")
async def get_program_schedule(program_id: str, user_id: str = "default"):
    """Get weekly schedule for a program - STUB"""
    return {
        "program_id": program_id,
        "schedule": [],
        "message": "Schedule not yet generated (stub)"
    }

@app.post("/programs/generate")
async def generate_program(request: ProgramGenerateRequest, user_id: str = "default"):
    """AI-generate a workout program - STUB"""
    fitness_ctx = await get_fitness_context(user_id)

    prompt = f"""Generate a workout program with these specifications:
- Goal: {request.goal}
- Frequency: {request.frequency} days per week
- Equipment available: {', '.join(request.equipment)}
- Experience level: {request.experience_level}
- Injuries/limitations: {request.injuries or 'None'}
- Preferences: {request.preferences or 'None'}

Create a detailed weekly program with:
1. Workout split recommendation
2. Daily workout structure
3. Exercise selection with sets/reps
4. Progression strategy
5. Deload week guidelines
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await call_llm(messages, fitness_ctx)

        await publish_event("gym.program.created", {
            "user_id": user_id,
            "type": "ai_generated",
            "goal": request.goal
        })

        return {
            "program": response,
            "generated": True,
            "parameters": request.model_dump()
        }
    except Exception as e:
        return {
            "message": f"Program generation failed: {str(e)}",
            "stub_program": {
                "name": f"{request.goal.title()} Program",
                "goal": request.goal,
                "frequency": request.frequency,
                "split": "full_body" if request.frequency <= 3 else "upper_lower"
            }
        }

# =============================================================================
# WORKOUT SESSIONS ENDPOINTS
# =============================================================================

@app.get("/sessions")
async def list_sessions(
    user_id: str = "default",
    limit: int = Query(default=10, le=100)
):
    """List recent workout sessions - STUB"""
    return {
        "sessions": [],
        "message": "No sessions recorded yet",
        "user_id": user_id
    }

@app.post("/sessions")
async def create_session(session: SessionCreate, user_id: str = "default"):
    """Create/start a workout session - STUB"""
    session_id = f"sess_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    await publish_event("gym.workout.started", {
        "user_id": user_id,
        "session_id": session_id,
        "workout_name": session.workout_name
    })

    return {
        "id": session_id,
        "message": f"Session '{session.workout_name}' started (stub)",
        "session": session.model_dump(),
        "started_at": datetime.now().isoformat()
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: str, user_id: str = "default"):
    """Get session details - STUB"""
    return {
        "message": f"Session {session_id} not found (stub)",
        "stub": True
    }

@app.put("/sessions/{session_id}")
async def update_session(session_id: str, update: SessionUpdate, user_id: str = "default"):
    """Update a session - STUB"""
    return {
        "message": f"Session {session_id} would be updated (stub)",
        "updates": update.model_dump(exclude_none=True)
    }

@app.post("/sessions/{session_id}/complete")
async def complete_session(session_id: str, complete: SessionComplete, user_id: str = "default"):
    """Mark session as complete - STUB"""

    await publish_event("gym.workout.completed", {
        "user_id": user_id,
        "session_id": session_id,
        "duration_minutes": complete.duration_minutes,
        "energy_level": complete.energy_level
    })

    return {
        "message": f"Session {session_id} completed (stub)",
        "duration_minutes": complete.duration_minutes,
        "completed_at": datetime.now().isoformat()
    }

@app.get("/sessions/next")
async def get_next_workout(user_id: str = "default"):
    """Get next scheduled workout - STUB"""
    return {
        "message": "No workout scheduled. Create a program first.",
        "suggestion": "Try POST /programs/generate to create a personalized program"
    }

@app.get("/sessions/today")
async def get_todays_workout(user_id: str = "default"):
    """Get today's workout - STUB"""
    time_ctx = get_time_context()
    return {
        "date": time_ctx['current_date'],
        "day_of_week": time_ctx['day_of_week'],
        "workout": None,
        "message": "No workout scheduled for today"
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = "default"):
    """Delete a session - STUB"""
    return {
        "message": f"Session {session_id} would be deleted (stub)",
        "deleted": True
    }

# =============================================================================
# EXERCISE LIBRARY ENDPOINTS
# =============================================================================

@app.get("/exercises")
async def list_exercises(
    muscle_group: Optional[str] = None,
    equipment: Optional[str] = None,
    difficulty: Optional[Difficulty] = None,
    limit: int = Query(default=20, le=100)
):
    """List/search exercises - STUB"""
    # Stub with some sample exercises
    sample_exercises = [
        {"name": "bench_press", "display_name": "Barbell Bench Press", "muscle_groups": ["chest", "triceps", "shoulders"]},
        {"name": "squat", "display_name": "Barbell Back Squat", "muscle_groups": ["quads", "glutes", "hamstrings"]},
        {"name": "deadlift", "display_name": "Conventional Deadlift", "muscle_groups": ["back", "hamstrings", "glutes"]},
        {"name": "overhead_press", "display_name": "Standing Overhead Press", "muscle_groups": ["shoulders", "triceps"]},
        {"name": "barbell_row", "display_name": "Barbell Row", "muscle_groups": ["back", "biceps"]}
    ]

    return {
        "exercises": sample_exercises,
        "total": len(sample_exercises),
        "message": "Showing sample exercises (full library coming in Phase 2)"
    }

@app.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str):
    """Get exercise details - STUB"""
    return {
        "message": f"Exercise {exercise_id} details (stub)",
        "stub_data": {
            "name": exercise_id,
            "instructions": "Full instructions will be added in Phase 2",
            "form_cues": ["Maintain neutral spine", "Control the movement"],
            "common_mistakes": ["Using too much weight", "Poor form"]
        }
    }

@app.get("/exercises/search")
async def search_exercises(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=10, le=50)
):
    """Search exercises by name/muscle/equipment - STUB"""
    return {
        "query": q,
        "results": [],
        "message": f"Search for '{q}' (stub - database not connected)"
    }

@app.get("/exercises/muscle/{muscle_group}")
async def get_exercises_by_muscle(muscle_group: str):
    """Get exercises for a muscle group - STUB"""
    return {
        "muscle_group": muscle_group,
        "exercises": [],
        "message": f"Exercises for {muscle_group} (stub)"
    }

@app.post("/exercises")
async def add_custom_exercise(exercise: Dict[str, Any], user_id: str = "default"):
    """Add a custom exercise - STUB"""
    return {
        "message": "Custom exercise would be added (stub)",
        "exercise": exercise
    }

@app.get("/exercises/{exercise_id}/alternatives")
async def get_exercise_alternatives(exercise_id: str):
    """Get substitute exercises - STUB"""
    return {
        "exercise": exercise_id,
        "alternatives": [],
        "message": "Alternatives will be suggested in Phase 2"
    }

@app.post("/exercises/{exercise_id}/form-check")
async def form_check(exercise_id: str, request: FormCheckRequest, user_id: str = "default"):
    """AI form analysis - STUB"""
    fitness_ctx = await get_fitness_context(user_id)

    prompt = f"""Analyze this form description for {request.exercise_name}:

Issue/Question: {request.description}

Provide:
1. Likely cause of the issue
2. Form cues to correct it
3. Mobility work that might help
4. When to see a professional (if concerning)
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await call_llm(messages, fitness_ctx)

        return {
            "exercise": request.exercise_name,
            "analysis": response
        }
    except Exception as e:
        return {
            "exercise": request.exercise_name,
            "message": f"Form analysis failed: {str(e)}",
            "stub_advice": "Focus on controlled movement and proper bracing"
        }

# =============================================================================
# EXERCISE LOGGING ENDPOINTS
# =============================================================================

@app.post("/logs")
async def log_exercise(log: ExerciseLogCreate, user_id: str = "default"):
    """Log a set - STUB"""
    log_id = f"log_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Check for potential PR (stub logic)
    is_pr = False  # TODO: Compare against history

    if is_pr:
        await publish_event("gym.pr.set", {
            "user_id": user_id,
            "exercise": log.exercise_name,
            "weight": log.weight,
            "reps": log.reps
        })

    return {
        "id": log_id,
        "message": f"Logged {log.exercise_name}: {log.weight}{log.weight_unit} x {log.reps} (stub)",
        "is_pr": is_pr,
        "log": log.model_dump()
    }

@app.get("/logs/session/{session_id}")
async def get_session_logs(session_id: str):
    """Get all logs for a session - STUB"""
    return {
        "session_id": session_id,
        "logs": [],
        "message": "No logs for this session (stub)"
    }

@app.put("/logs/{log_id}")
async def update_log(log_id: str, updates: Dict[str, Any]):
    """Update a log entry - STUB"""
    return {
        "message": f"Log {log_id} would be updated (stub)",
        "updates": updates
    }

@app.delete("/logs/{log_id}")
async def delete_log(log_id: str):
    """Delete a log entry - STUB"""
    return {
        "message": f"Log {log_id} would be deleted (stub)",
        "deleted": True
    }

@app.get("/logs/exercise/{exercise_id}")
async def get_exercise_history(exercise_id: str, user_id: str = "default", limit: int = 20):
    """Get history for specific exercise - STUB"""
    return {
        "exercise": exercise_id,
        "history": [],
        "message": f"No history for {exercise_id} yet (stub)"
    }

@app.get("/logs/progress/{exercise_id}")
async def get_exercise_progress(exercise_id: str, user_id: str = "default"):
    """Get progress chart data for exercise - STUB"""
    return {
        "exercise": exercise_id,
        "progress_data": [],
        "trend": "neutral",
        "message": "Progress tracking available after logging workouts"
    }

# =============================================================================
# BODY METRICS ENDPOINTS
# =============================================================================

@app.get("/metrics/body")
async def get_body_metrics(user_id: str = "default", limit: int = 30):
    """Get body metrics history - STUB"""
    return {
        "metrics": [],
        "message": "No body metrics recorded yet (stub)"
    }

@app.post("/metrics/body")
async def log_body_metrics(metrics: BodyMetricsCreate, user_id: str = "default"):
    """Log body metrics - STUB"""
    return {
        "message": "Body metrics logged (stub)",
        "metrics": metrics.model_dump(),
        "date": date.today().isoformat()
    }

@app.get("/metrics/body/latest")
async def get_latest_body_metrics(user_id: str = "default"):
    """Get most recent body metrics - STUB"""
    return {
        "message": "No body metrics recorded yet (stub)",
        "latest": None
    }

@app.get("/metrics/body/progress")
async def get_body_progress(user_id: str = "default", days: int = 90):
    """Get body metrics progress over time - STUB"""
    return {
        "progress": [],
        "period_days": days,
        "message": "Track body metrics to see progress"
    }

# =============================================================================
# RECOVERY ENDPOINTS
# =============================================================================

@app.get("/recovery")
async def get_recovery_history(user_id: str = "default", limit: int = 14):
    """Get recovery history - STUB"""
    return {
        "recovery_logs": [],
        "message": "No recovery data logged yet (stub)"
    }

@app.post("/recovery")
async def log_recovery(recovery: RecoveryLogCreate, user_id: str = "default"):
    """Log recovery data - STUB"""
    # Check if recovery is low
    avg_metrics = []
    if recovery.energy_level:
        avg_metrics.append(recovery.energy_level)
    if recovery.sleep_quality:
        avg_metrics.append(recovery.sleep_quality)

    is_low = avg_metrics and (sum(avg_metrics) / len(avg_metrics)) < 5

    if is_low:
        await publish_event("gym.recovery.low", {
            "user_id": user_id,
            "energy_level": recovery.energy_level,
            "sleep_quality": recovery.sleep_quality
        })

    return {
        "message": "Recovery data logged (stub)",
        "recovery": recovery.model_dump(),
        "date": date.today().isoformat(),
        "warning": "Consider a rest day" if is_low else None
    }

@app.get("/recovery/today")
async def get_todays_recovery(user_id: str = "default"):
    """Get today's recovery status - STUB"""
    return {
        "date": date.today().isoformat(),
        "recovery": None,
        "message": "No recovery data logged today"
    }

@app.get("/recovery/readiness")
async def get_training_readiness(user_id: str = "default"):
    """Calculate training readiness score - STUB"""
    return {
        "readiness_score": None,
        "factors": {
            "sleep": None,
            "soreness": None,
            "energy": None,
            "stress": None
        },
        "recommendation": "Log recovery data to calculate readiness",
        "message": "Readiness calculation requires recovery data (stub)"
    }

@app.post("/recovery/check-in")
async def quick_recovery_checkin(checkin: RecoveryCheckIn, user_id: str = "default"):
    """Quick daily check-in - STUB"""
    readiness = (checkin.energy_level + (11 - checkin.soreness_level)) / 2

    if checkin.sleep_quality:
        readiness = (readiness + checkin.sleep_quality) / 2

    recommendation = "Good to train" if readiness >= 6 else "Consider lighter workout or rest"

    return {
        "message": "Check-in recorded (stub)",
        "readiness_score": round(readiness, 1),
        "recommendation": recommendation,
        "checkin": checkin.model_dump()
    }

# =============================================================================
# PROGRESS & ANALYTICS ENDPOINTS
# =============================================================================

@app.get("/progress")
async def get_overall_progress(user_id: str = "default"):
    """Get overall progress summary - STUB"""
    return {
        "summary": {
            "total_workouts": 0,
            "total_volume": 0,
            "prs_this_month": 0,
            "current_streak": 0
        },
        "message": "Start logging workouts to track progress (stub)"
    }

@app.get("/progress/exercise/{exercise_id}")
async def get_lift_progress(exercise_id: str, user_id: str = "default"):
    """Get progress for specific lift - STUB"""
    return {
        "exercise": exercise_id,
        "progress": [],
        "estimated_1rm": None,
        "trend": "neutral"
    }

@app.get("/progress/volume")
async def get_volume_trends(user_id: str = "default", weeks: int = 8):
    """Get volume trends over time - STUB"""
    return {
        "volume_data": [],
        "weeks_analyzed": weeks,
        "trend": "neutral"
    }

@app.get("/progress/prs")
async def get_pr_history(user_id: str = "default"):
    """Get personal record history - STUB"""
    return {
        "personal_records": [],
        "message": "No PRs recorded yet - let's change that!"
    }

@app.get("/progress/streaks")
async def get_training_streaks(user_id: str = "default"):
    """Get training streak info - STUB"""
    return {
        "current_streak": 0,
        "longest_streak": 0,
        "this_week": 0,
        "this_month": 0
    }

@app.get("/analytics/summary")
async def get_analytics_summary(user_id: str = "default", period: str = "week"):
    """Get weekly/monthly summary - STUB"""
    return {
        "period": period,
        "summary": {
            "workouts": 0,
            "total_sets": 0,
            "total_reps": 0,
            "total_volume": 0,
            "avg_duration": 0,
            "prs": 0
        },
        "message": f"No data for this {period} (stub)"
    }

# =============================================================================
# AI FEATURE ENDPOINTS
# =============================================================================

@app.post("/ai/suggest-weight")
async def suggest_weight(request: WeightSuggestionRequest, user_id: str = "default"):
    """AI weight suggestion - STUB"""
    fitness_ctx = await get_fitness_context(user_id)

    prompt = f"""Suggest an appropriate weight for:
Exercise: {request.exercise_name}
Target Reps: {request.target_reps}
Target RPE: {request.target_rpe}

Based on typical progression and the target RPE, provide:
1. Suggested starting weight (conservative)
2. Working set weight range
3. Key form cues for this exercise
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await call_llm(messages, fitness_ctx)

        return {
            "exercise": request.exercise_name,
            "target_reps": request.target_reps,
            "target_rpe": request.target_rpe,
            "suggestion": response
        }
    except Exception as e:
        return {
            "exercise": request.exercise_name,
            "message": f"Suggestion failed: {str(e)}",
            "default_advice": "Start conservative and increase if RPE is below target"
        }

@app.post("/ai/form-check")
async def ai_form_check(request: FormCheckRequest, user_id: str = "default"):
    """AI form analysis - delegates to exercise form-check"""
    return await form_check("general", request, user_id)

@app.post("/ai/program-advice")
async def program_advice(question: str = "", user_id: str = "default"):
    """Get AI program recommendations - STUB"""
    fitness_ctx = await get_fitness_context(user_id)

    prompt = f"""User's program question: {question or 'General program advice'}

Based on their fitness context, provide actionable advice about:
1. Program structure
2. Exercise selection
3. Volume and intensity
4. Recovery considerations
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await call_llm(messages, fitness_ctx)

        return {
            "question": question,
            "advice": response
        }
    except Exception as e:
        return {
            "message": f"Advice generation failed: {str(e)}",
            "default_advice": "Focus on consistency, progressive overload, and adequate recovery"
        }

@app.post("/ai/recovery-advice")
async def recovery_advice(user_id: str = "default"):
    """Get AI recovery recommendations - STUB"""
    fitness_ctx = await get_fitness_context(user_id)

    return {
        "advice": "Log recovery data for personalized recommendations",
        "general_tips": [
            "Aim for 7-9 hours of sleep",
            "Stay hydrated throughout the day",
            "Eat adequate protein (0.7-1g per lb bodyweight)",
            "Take rest days seriously",
            "Consider active recovery (light walking, stretching)"
        ]
    }

@app.post("/ai/plateau-break")
async def plateau_break(request: PlateauBreakRequest, user_id: str = "default"):
    """AI strategies for breaking plateau - STUB"""
    fitness_ctx = await get_fitness_context(user_id)

    prompt = f"""User is stuck on a plateau:
Exercise: {request.exercise_name}
Current: {request.current_weight} lbs x {request.current_reps}
Weeks stuck: {request.weeks_stuck}

Provide specific strategies to break through including:
1. Variation/accessory work
2. Rep scheme changes
3. Volume adjustments
4. Technique focus
5. Recovery considerations
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await call_llm(messages, fitness_ctx)

        return {
            "exercise": request.exercise_name,
            "strategies": response
        }
    except Exception as e:
        return {
            "exercise": request.exercise_name,
            "message": f"Strategy generation failed: {str(e)}",
            "default_strategies": [
                "Try paused reps to build strength from the bottom",
                "Add volume with lighter sets",
                "Focus on weak point training",
                "Take a deload week"
            ]
        }

# =============================================================================
# ARIA TOOL ENDPOINTS
# =============================================================================

@app.post("/aria/log_workout")
async def aria_log_workout(request: LogWorkoutRequest, user_id: str = "default"):
    """
    ARIA Tool: gym.log_workout
    Log a completed workout session with all exercises
    """
    session_id = f"sess_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Process exercises
    exercise_summary = []
    total_volume = 0

    for ex in request.exercises:
        name = ex.get("name", "Unknown")
        sets = ex.get("sets", 1)
        reps = ex.get("reps", 0)
        weight = ex.get("weight", 0)

        volume = sets * reps * weight
        total_volume += volume

        exercise_summary.append({
            "name": name,
            "sets": sets,
            "reps": reps,
            "weight": weight,
            "volume": volume
        })

    # Publish workout completed event
    await publish_event("gym.workout.completed", {
        "user_id": user_id,
        "session_id": session_id,
        "workout_name": f"Workout ({len(request.exercises)} exercises)",
        "duration_minutes": request.duration_minutes,
        "exercises_completed": len(request.exercises),
        "total_volume": total_volume,
        "energy_level": request.energy_level
    })

    # Store in ARIA memory
    await update_aria_memory(
        memory_type="fact",
        content=f"Workout completed: {len(request.exercises)} exercises, {request.duration_minutes} min, {total_volume} lbs total volume",
        tags=["gym-coach", "workout", "logged"]
    )

    return {
        "success": True,
        "session_id": session_id,
        "summary": {
            "exercises": len(request.exercises),
            "duration_minutes": request.duration_minutes,
            "total_volume": total_volume,
            "energy_level": request.energy_level
        },
        "exercises": exercise_summary,
        "message": "Workout logged successfully!"
    }

@app.get("/aria/get_program")
async def aria_get_program(user_id: str = "default"):
    """
    ARIA Tool: gym.get_program
    Get the user's current active workout program
    """
    return {
        "has_program": False,
        "message": "No active program. Create one with POST /programs/generate",
        "suggestion": "Ask me to create a workout program based on your goals!"
    }

@app.get("/aria/next_workout")
async def aria_next_workout(user_id: str = "default"):
    """
    ARIA Tool: gym.next_workout
    Get what workout is scheduled next
    """
    time_ctx = get_time_context()

    return {
        "has_next_workout": False,
        "today": time_ctx['day_of_week'],
        "message": "No workout scheduled. Create a program first!",
        "suggestion": "Would you like me to generate a workout program for you?"
    }

@app.get("/aria/progress")
async def aria_progress(request: ProgressRequest = None, user_id: str = "default"):
    """
    ARIA Tool: gym.progress
    Show progress on lifts over time
    """
    exercise = request.exercise_name if request else None
    period = request.period if request else "month"

    return {
        "exercise": exercise or "overall",
        "period": period,
        "has_data": False,
        "message": "No progress data yet. Start logging workouts!",
        "tip": "Track your lifts consistently to see your gains over time"
    }

@app.post("/aria/suggest_weight")
async def aria_suggest_weight(request: WeightSuggestionRequest, user_id: str = "default"):
    """
    ARIA Tool: gym.suggest_weight
    Suggest appropriate weight for next set based on history
    """
    return {
        "exercise": request.exercise_name,
        "target_reps": request.target_reps,
        "target_rpe": request.target_rpe,
        "has_history": False,
        "suggestion": "Start with a weight you can control for all reps with 2-3 reps in reserve",
        "tip": "Log your sets to get personalized weight suggestions!"
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
