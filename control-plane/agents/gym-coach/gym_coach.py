#!/usr/bin/env python3
"""
GYM-COACH - Personal Fitness & Training Agent
Port: 8230

Your AI personal trainer. Workout planning, form guidance,
progress tracking, and motivation. Knows your goals and adapts.

Named for the timeless role of the coach who pushes athletes to greatness.
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic

# Add shared modules
sys.path.append('/opt/leveredge/control-plane/shared')
try:
    from cost_tracker import CostTracker
except ImportError:
    CostTracker = None

app = FastAPI(
    title="GYM-COACH",
    description="Personal Fitness & Training Agent",
    version="1.0.0"
)

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
cost_tracker = CostTracker("GYM-COACH") if CostTracker else None

# =============================================================================
# MODELS
# =============================================================================

class FitnessGoal(str, Enum):
    STRENGTH = "strength"
    MUSCLE = "muscle_building"
    FAT_LOSS = "fat_loss"
    ENDURANCE = "endurance"
    FLEXIBILITY = "flexibility"
    GENERAL = "general_fitness"
    SPORT_SPECIFIC = "sport_specific"

class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    weight_lbs: Optional[float] = None
    height_inches: Optional[int] = None
    goal: FitnessGoal = FitnessGoal.GENERAL
    experience: ExperienceLevel = ExperienceLevel.BEGINNER
    equipment: List[str] = ["bodyweight"]
    injuries: List[str] = []
    days_per_week: int = 3
    minutes_per_session: int = 45

class WorkoutRequest(BaseModel):
    user_id: str
    profile: Optional[UserProfile] = None
    focus: Optional[str] = None  # "upper", "lower", "full", "cardio", "core"
    duration_minutes: Optional[int] = None
    equipment_available: Optional[List[str]] = None

class ExerciseHelp(BaseModel):
    exercise_name: str
    question: Optional[str] = None  # "form", "alternatives", "progression"

class ProgressLog(BaseModel):
    user_id: str
    exercise: str
    sets: int
    reps: int
    weight_lbs: Optional[float] = None
    notes: Optional[str] = None
    date: Optional[str] = None

class MotivationRequest(BaseModel):
    user_id: str
    situation: Optional[str] = None  # "skipping", "plateau", "tired", "general"

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are GYM-COACH, a knowledgeable and motivating personal fitness trainer.

PERSONALITY:
- Encouraging but not fake - real motivation, not empty hype
- Direct about what works and what doesn't
- Adapts intensity to user's level and mood
- Safety-conscious - always prioritize proper form over ego lifting
- Celebrates progress, no matter how small

EXPERTISE:
- Exercise programming (strength, hypertrophy, endurance, flexibility)
- Proper form and technique for all major exercises
- Progressive overload principles
- Recovery and rest day optimization
- Home workouts with minimal equipment
- Gym-based training with full equipment
- Injury prevention and working around limitations

COMMUNICATION STYLE:
- Clear, actionable instructions
- Use exercise names people know (with alternatives)
- Provide rep ranges and rest periods
- Explain the "why" behind programming choices
- Keep it concise - people want to train, not read essays

SAFETY FIRST:
- Always ask about injuries before programming
- Recommend lighter weights for new exercises
- Emphasize warm-up and mobility
- Know when to recommend seeing a professional

You have access to the user's profile including their goals, experience, equipment, and any injuries.
"""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def call_llm(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """Call Claude for fitness advice"""
    if not client:
        return "API key not configured. Please set ANTHROPIC_API_KEY."

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )

    if cost_tracker:
        await cost_tracker.log_usage(
            agent_name="GYM-COACH",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            operation="fitness_advice"
        )

    return response.content[0].text

async def log_event(event_type: str, data: dict):
    """Log to Event Bus"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={"event_type": event_type, "source": "GYM-COACH", "data": data}
            )
    except:
        pass

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "GYM-COACH",
        "port": 8230,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/workout")
async def generate_workout(request: WorkoutRequest):
    """Generate a personalized workout"""
    profile = request.profile or UserProfile(user_id=request.user_id)

    prompt = f"""Generate a workout for this user:

PROFILE:
- Goal: {profile.goal.value}
- Experience: {profile.experience.value}
- Available equipment: {', '.join(profile.equipment)}
- Injuries/limitations: {', '.join(profile.injuries) if profile.injuries else 'None'}
- Session duration: {request.duration_minutes or profile.minutes_per_session} minutes
- Focus: {request.focus or 'full body'}

Provide:
1. Warm-up (5 min)
2. Main workout with sets, reps, and rest periods
3. Cool-down/stretch (5 min)

Format each exercise as:
Exercise Name - Sets x Reps (Rest: Xs) [any notes]
"""

    workout = await call_llm(prompt)
    await log_event("workout_generated", {"user_id": request.user_id, "focus": request.focus})

    return {
        "user_id": request.user_id,
        "workout": workout,
        "duration_minutes": request.duration_minutes or profile.minutes_per_session,
        "focus": request.focus or "full body",
        "generated_at": datetime.utcnow().isoformat()
    }

@app.post("/exercise-help")
async def exercise_help(request: ExerciseHelp):
    """Get help with a specific exercise"""
    question_type = request.question or "form"

    prompts = {
        "form": f"Explain proper form for {request.exercise_name}. Include: setup, execution, common mistakes, and cues.",
        "alternatives": f"Provide 5 alternatives to {request.exercise_name} for different equipment/skill levels.",
        "progression": f"How to progress with {request.exercise_name}? Include regression for beginners and advanced variations."
    }

    prompt = prompts.get(question_type, prompts["form"])
    advice = await call_llm(prompt)

    return {
        "exercise": request.exercise_name,
        "question_type": question_type,
        "advice": advice
    }

@app.post("/log-workout")
async def log_workout(log: ProgressLog):
    """Log a workout for progress tracking"""
    log_date = log.date or date.today().isoformat()

    # Store in Supabase if configured
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/fitness_logs",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "user_id": log.user_id,
                        "exercise": log.exercise,
                        "sets": log.sets,
                        "reps": log.reps,
                        "weight_lbs": log.weight_lbs,
                        "notes": log.notes,
                        "logged_at": log_date
                    }
                )
        except:
            pass

    await log_event("workout_logged", {"user_id": log.user_id, "exercise": log.exercise})

    return {
        "status": "logged",
        "user_id": log.user_id,
        "exercise": log.exercise,
        "date": log_date
    }

@app.post("/motivation")
async def get_motivation(request: MotivationRequest):
    """Get personalized motivation"""
    situations = {
        "skipping": "User is considering skipping their workout today.",
        "plateau": "User feels stuck and isn't seeing progress.",
        "tired": "User is tired but wondering if they should still train.",
        "general": "User just needs some general motivation to keep going."
    }

    situation = situations.get(request.situation, situations["general"])

    prompt = f"""The user needs motivation. Situation: {situation}

Give them a short, genuine motivational message. Not cheesy gym-bro stuff.
Real talk that acknowledges their situation but encourages them appropriately.
Keep it under 100 words."""

    motivation = await call_llm(prompt)

    return {
        "user_id": request.user_id,
        "situation": request.situation,
        "message": motivation
    }

@app.post("/program")
async def create_program(profile: UserProfile):
    """Create a weekly training program"""
    prompt = f"""Create a {profile.days_per_week}-day per week training program for:

PROFILE:
- Goal: {profile.goal.value}
- Experience: {profile.experience.value}
- Equipment: {', '.join(profile.equipment)}
- Injuries: {', '.join(profile.injuries) if profile.injuries else 'None'}
- Session length: {profile.minutes_per_session} minutes

Provide:
1. Weekly split overview
2. Each day's focus and key exercises
3. Progression strategy for 4 weeks
4. Deload recommendations

Keep it practical and sustainable."""

    program = await call_llm(prompt)
    await log_event("program_created", {"user_id": profile.user_id, "goal": profile.goal.value})

    return {
        "user_id": profile.user_id,
        "program": program,
        "days_per_week": profile.days_per_week,
        "goal": profile.goal.value,
        "created_at": datetime.utcnow().isoformat()
    }

@app.get("/tips/{category}")
async def get_tips(category: str):
    """Get quick tips by category"""
    valid_categories = ["warmup", "recovery", "nutrition", "sleep", "form", "motivation"]

    if category not in valid_categories:
        raise HTTPException(400, f"Invalid category. Choose from: {valid_categories}")

    prompt = f"Give 5 quick, actionable tips for {category} related to fitness. Be specific and practical."
    tips = await call_llm(prompt)

    return {
        "category": category,
        "tips": tips
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8230)
