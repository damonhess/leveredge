#!/usr/bin/env python3
"""
NUTRITIONIST - AI-Powered Nutrition & Diet Management Agent
Port: 8101

Named after Demeter - Greek goddess of harvest, agriculture, and nourishment.
NUTRITIONIST cultivates healthy eating habits and nourishes optimal performance.

CORE CAPABILITIES:
- TDEE calculation (Mifflin-St Jeor, Harris-Benedict)
- Macro tracking (protein, carbs, fat)
- Meal logging with nutritional breakdown
- Dietary restriction management
- Nutrition analysis and scoring

TEAM INTEGRATION:
- Time-aware (knows current date)
- Event Bus integration
- Cost tracking via shared.cost_tracker
- ARIA tools exposure
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, time as dt_time
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="NUTRITIONIST",
    description="AI-Powered Nutrition & Diet Management Agent",
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
    "ARIA": "http://aria:8000",
    "HERMES": "http://hermes:8014",
    "ATLAS": "http://atlas:8102",  # Future fitness agent
    "EVENT_BUS": EVENT_BUS_URL
}

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("NUTRITIONIST")

# =============================================================================
# CONSTANTS - Activity Levels & Macro Ratios
# =============================================================================

class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"      # Little to no exercise
    LIGHT = "light"              # 1-3 days/week exercise
    MODERATE = "moderate"        # 3-5 days/week exercise
    ACTIVE = "active"            # 6-7 days/week exercise
    ATHLETE = "athlete"          # 2x daily or physical job

ACTIVITY_MULTIPLIERS = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.ATHLETE: 1.9,
}

class Goal(str, Enum):
    CUT = "cut"          # Fat loss
    MAINTAIN = "maintain" # Maintenance
    BULK = "bulk"        # Muscle gain

# Calorie adjustments for goals
GOAL_ADJUSTMENTS = {
    Goal.CUT: -500,      # 500 calorie deficit
    Goal.MAINTAIN: 0,
    Goal.BULK: 300,      # 300 calorie surplus
}

class MacroPreset(str, Enum):
    MUSCLE_GAIN = "muscle_gain"
    FAT_LOSS = "fat_loss"
    MAINTENANCE = "maintenance"
    KETO = "keto"
    ENDURANCE = "endurance"

# Macro splits as percentages (protein, carbs, fat)
MACRO_PRESETS = {
    MacroPreset.MUSCLE_GAIN: {"protein": 30, "carbs": 45, "fat": 25},
    MacroPreset.FAT_LOSS: {"protein": 40, "carbs": 30, "fat": 30},
    MacroPreset.MAINTENANCE: {"protein": 25, "carbs": 50, "fat": 25},
    MacroPreset.KETO: {"protein": 25, "carbs": 5, "fat": 70},
    MacroPreset.ENDURANCE: {"protein": 20, "carbs": 55, "fat": 25},
}

class MealType(str, Enum):
    BREAKFAST = "breakfast"
    MORNING_SNACK = "morning_snack"
    LUNCH = "lunch"
    AFTERNOON_SNACK = "afternoon_snack"
    DINNER = "dinner"
    EVENING_SNACK = "evening_snack"

class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class TDEERequest(BaseModel):
    weight_kg: float = Field(..., gt=0, description="Weight in kilograms")
    height_cm: float = Field(..., gt=0, description="Height in centimeters")
    age: int = Field(..., gt=0, lt=150, description="Age in years")
    sex: Sex
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    goal: Goal = Goal.MAINTAIN
    formula: Optional[str] = "mifflin"  # "mifflin" or "harris"

class TDEEResponse(BaseModel):
    bmr: int
    tdee: int
    calorie_target: int
    formula_used: str
    activity_multiplier: float
    goal_adjustment: int

class MacroTargets(BaseModel):
    protein_g: int
    carbs_g: int
    fat_g: int
    calories: int

class ProfileCreate(BaseModel):
    user_id: str
    weight_kg: float
    height_cm: float
    age: int
    sex: Sex
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    goal: Goal = Goal.MAINTAIN
    macro_preset: Optional[MacroPreset] = None
    restrictions: Optional[List[str]] = []

class ProfileResponse(BaseModel):
    user_id: str
    tdee: int
    calorie_target: int
    protein_target: int
    carb_target: int
    fat_target: int
    goal: str
    activity_level: str
    restrictions: List[str]
    height_cm: float
    weight_kg: float
    age: int
    sex: str

class FoodItem(BaseModel):
    name: str
    servings: float = 1.0
    calories: int
    protein: float = 0
    carbs: float = 0
    fat: float = 0

class MealLogRequest(BaseModel):
    user_id: str
    meal_type: MealType
    items: List[FoodItem]
    notes: Optional[str] = None
    date: Optional[str] = None  # ISO date, defaults to today
    time: Optional[str] = None  # HH:MM format

class MealLogResponse(BaseModel):
    meal_id: str
    user_id: str
    meal_type: str
    date: str
    time: Optional[str]
    items: List[Dict[str, Any]]
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    notes: Optional[str]

class DailySummary(BaseModel):
    user_id: str
    date: str
    calories: int
    protein: float
    carbs: float
    fat: float
    meal_count: int
    targets: MacroTargets
    remaining: MacroTargets

class FoodSearchRequest(BaseModel):
    query: str
    limit: int = 20

class MealSuggestionRequest(BaseModel):
    user_id: str
    meal_type: MealType
    max_calories: Optional[int] = None
    preferences: Optional[List[str]] = []

class AnalysisRequest(BaseModel):
    user_id: str
    days: int = 7

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "meal_time_suggestion": get_meal_time_suggestion(now)
    }

def get_meal_time_suggestion(now: datetime) -> str:
    """Suggest appropriate meal type based on current time"""
    hour = now.hour
    if hour < 10:
        return "breakfast"
    elif hour < 12:
        return "morning_snack"
    elif hour < 14:
        return "lunch"
    elif hour < 17:
        return "afternoon_snack"
    elif hour < 20:
        return "dinner"
    else:
        return "evening_snack"

# =============================================================================
# TDEE CALCULATION ENGINE
# =============================================================================

def calculate_bmr_mifflin(weight_kg: float, height_cm: float, age: int, sex: Sex) -> float:
    """
    Mifflin-St Jeor Equation (more accurate for modern populations)

    Men: BMR = (10 x weight in kg) + (6.25 x height in cm) - (5 x age in years) + 5
    Women: BMR = (10 x weight in kg) + (6.25 x height in cm) - (5 x age in years) - 161
    """
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if sex == Sex.MALE:
        bmr += 5
    else:
        bmr -= 161
    return bmr

def calculate_bmr_harris(weight_kg: float, height_cm: float, age: int, sex: Sex) -> float:
    """
    Harris-Benedict Equation (revised 1984)

    Men: BMR = 88.362 + (13.397 x weight in kg) + (4.799 x height in cm) - (5.677 x age in years)
    Women: BMR = 447.593 + (9.247 x weight in kg) + (3.098 x height in cm) - (4.330 x age in years)
    """
    if sex == Sex.MALE:
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
    return bmr

def calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    activity_level: ActivityLevel,
    formula: str = "mifflin"
) -> tuple[float, float]:
    """Calculate BMR and TDEE using specified formula"""

    if formula == "harris":
        bmr = calculate_bmr_harris(weight_kg, height_cm, age, sex)
    else:
        bmr = calculate_bmr_mifflin(weight_kg, height_cm, age, sex)

    multiplier = ACTIVITY_MULTIPLIERS[activity_level]
    tdee = bmr * multiplier

    return bmr, tdee

def calculate_calorie_target(tdee: float, goal: Goal) -> int:
    """Calculate calorie target based on TDEE and goal"""
    adjustment = GOAL_ADJUSTMENTS[goal]
    return int(tdee + adjustment)

def calculate_macro_targets(
    calorie_target: int,
    goal: Goal,
    preset: Optional[MacroPreset] = None
) -> MacroTargets:
    """
    Calculate macro targets in grams based on calorie target and goal.

    Calories per gram:
    - Protein: 4 kcal/g
    - Carbs: 4 kcal/g
    - Fat: 9 kcal/g
    """
    # Select macro ratios based on preset or goal
    if preset:
        ratios = MACRO_PRESETS[preset]
    elif goal == Goal.BULK:
        ratios = MACRO_PRESETS[MacroPreset.MUSCLE_GAIN]
    elif goal == Goal.CUT:
        ratios = MACRO_PRESETS[MacroPreset.FAT_LOSS]
    else:
        ratios = MACRO_PRESETS[MacroPreset.MAINTENANCE]

    # Calculate grams from percentages
    protein_cals = calorie_target * (ratios["protein"] / 100)
    carbs_cals = calorie_target * (ratios["carbs"] / 100)
    fat_cals = calorie_target * (ratios["fat"] / 100)

    return MacroTargets(
        protein_g=int(protein_cals / 4),
        carbs_g=int(carbs_cals / 4),
        fat_g=int(fat_cals / 9),
        calories=calorie_target
    )

# =============================================================================
# SYSTEM PROMPT BUILDER
# =============================================================================

def build_system_prompt(nutrition_context: dict) -> str:
    """Build the NUTRITIONIST system prompt with current context"""
    return f"""You are NUTRITIONIST - AI Nutrition & Diet Management Agent for LeverEdge.

Named after Demeter, Greek goddess of harvest and nourishment, you cultivate healthy eating habits and help users achieve their nutrition goals.

## TIME AWARENESS
- Current: {nutrition_context.get('current_time', 'Unknown')}
- Today's Date: {nutrition_context.get('today', 'Unknown')}

## YOUR IDENTITY
You are the nutrition intelligence of LeverEdge. You track meals, calculate macros, suggest meals, and help users optimize their diet for their goals.

## USER'S NUTRITION PROFILE
- TDEE: {nutrition_context.get('tdee', 'Not set')} kcal/day
- Goal: {nutrition_context.get('goal', 'Not set')}
- Daily Targets:
  - Calories: {nutrition_context.get('calorie_target', 0)} kcal
  - Protein: {nutrition_context.get('protein_target', 0)}g
  - Carbs: {nutrition_context.get('carb_target', 0)}g
  - Fat: {nutrition_context.get('fat_target', 0)}g
- Restrictions: {nutrition_context.get('restrictions', [])}

## TODAY'S PROGRESS
- Calories: {nutrition_context.get('today_calories', 0)}/{nutrition_context.get('calorie_target', 0)} kcal
- Protein: {nutrition_context.get('today_protein', 0)}/{nutrition_context.get('protein_target', 0)}g
- Carbs: {nutrition_context.get('today_carbs', 0)}/{nutrition_context.get('carb_target', 0)}g
- Fat: {nutrition_context.get('today_fat', 0)}/{nutrition_context.get('fat_target', 0)}g
- Meals Logged: {nutrition_context.get('meals_today', 0)}

## CURRENT STREAK
- Logging Streak: {nutrition_context.get('logging_streak', 0)} days
- On-Target Streak: {nutrition_context.get('on_target_streak', 0)} days

## YOUR CAPABILITIES

### Meal Logging
- Log meals with nutritional breakdown
- Search food database
- Support custom foods
- Calculate meal totals automatically

### Macro Tracking
- Track protein, carbs, fat in real-time
- Calculate remaining macros for the day
- Show progress toward daily targets
- Identify macro imbalances

### TDEE Management
- Calculate TDEE using proven formulas
- Adjust for activity level and goals
- Recommend calorie targets
- Periodic recalculation based on progress

### Meal Suggestions
- Suggest meals fitting remaining macros
- Respect dietary restrictions
- Consider meal timing
- Provide balanced options

### Nutrition Analysis
- Daily nutrition scoring
- Micronutrient gap identification
- Diet diversity analysis
- Trend analysis over time

## RESPONSE GUIDELINES
1. Be encouraging but honest about nutrition
2. Always respect dietary restrictions
3. Provide specific, actionable suggestions
4. Include calorie and macro info when relevant
5. Celebrate streaks and achievements

## TEAM COORDINATION
- Log health insights via Unified Memory
- Coordinate with fitness tracking (ATLAS if available)
- Send streak achievements to HERMES for notifications
- Publish events to Event Bus

## RESPONSE FORMAT
For meal logging:
1. Confirm foods logged
2. Show meal totals
3. Show updated daily progress
4. Remaining macros for the day

For suggestions:
1. Consider remaining macros
2. Respect restrictions
3. Provide 2-3 options
4. Include nutritional breakdown

## YOUR MISSION
Help users achieve their nutrition goals through intelligent tracking, personalized suggestions, and positive reinforcement.
Every meal matters. Every macro counts. Build healthy habits that last.
"""

# =============================================================================
# EVENT BUS INTEGRATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "NUTRITIONIST",
                    "event_type": f"nutrition.{event_type}",
                    "details": details,
                    "timestamp": time_ctx['current_datetime']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[NUTRITIONIST] Event bus notification failed: {e}")

async def notify_hermes(message: str, priority: str = "normal"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[NUTRITIONIST] {message}",
                    "priority": priority,
                    "channel": "telegram",
                    "source": "NUTRITIONIST"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[NUTRITIONIST] HERMES notification failed: {e}")

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, nutrition_ctx: dict) -> str:
    """Call Claude API with nutrition context and cost tracking"""
    if not client:
        return "LLM unavailable - ANTHROPIC_API_KEY not set"

    try:
        system_prompt = build_system_prompt(nutrition_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="NUTRITIONIST",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"goal": nutrition_ctx.get("goal")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# IN-MEMORY STORAGE (Phase 1 - Replace with DB in Phase 2)
# =============================================================================

# Temporary in-memory storage for Phase 1
_profiles: Dict[str, dict] = {}
_meal_logs: Dict[str, List[dict]] = {}  # user_id -> list of meals
_daily_totals: Dict[str, Dict[str, dict]] = {}  # user_id -> date -> totals
_food_database: Dict[str, dict] = {}  # food_id -> food item

def _generate_id() -> str:
    """Generate a simple UUID-like ID"""
    import uuid
    return str(uuid.uuid4())

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "NUTRITIONIST",
        "role": "Nutrition & Diet Management",
        "port": 8232,
        "current_time": time_ctx['current_datetime'],
        "meal_suggestion": time_ctx['meal_time_suggestion'],
        "version": "1.0.0"
    }

@app.get("/status")
async def status():
    """Current agent status with stats"""
    time_ctx = get_time_context()
    return {
        "agent": "NUTRITIONIST",
        "status": "operational",
        "time_context": time_ctx,
        "stats": {
            "profiles_count": len(_profiles),
            "meals_logged_today": sum(
                len([m for m in meals if m.get("date") == time_ctx["current_date"]])
                for meals in _meal_logs.values()
            ),
            "active_users": len(_meal_logs)
        },
        "capabilities": [
            "tdee_calculation",
            "macro_tracking",
            "meal_logging",
            "dietary_restrictions",
            "nutrition_analysis"
        ]
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics (stub)"""
    return {
        "nutritionist_requests_total": 0,
        "nutritionist_profiles_total": len(_profiles),
        "nutritionist_meals_logged_total": sum(len(m) for m in _meal_logs.values()),
        "nutritionist_llm_calls_total": 0
    }

# =============================================================================
# PROFILE MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """Get nutrition profile for a user"""
    if user_id not in _profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profiles[user_id]

@app.post("/profile")
async def create_or_update_profile(profile: ProfileCreate):
    """Create or update a nutrition profile"""
    # Calculate TDEE
    bmr, tdee = calculate_tdee(
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        sex=profile.sex,
        activity_level=profile.activity_level
    )

    # Calculate calorie target
    calorie_target = calculate_calorie_target(tdee, profile.goal)

    # Calculate macro targets
    macros = calculate_macro_targets(calorie_target, profile.goal, profile.macro_preset)

    # Build profile
    profile_data = {
        "user_id": profile.user_id,
        "tdee": int(tdee),
        "calorie_target": calorie_target,
        "protein_target": macros.protein_g,
        "carb_target": macros.carbs_g,
        "fat_target": macros.fat_g,
        "goal": profile.goal.value,
        "activity_level": profile.activity_level.value,
        "restrictions": profile.restrictions or [],
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "age": profile.age,
        "sex": profile.sex.value,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    _profiles[profile.user_id] = profile_data

    # Publish event
    await notify_event_bus("profile.updated", {
        "user_id": profile.user_id,
        "tdee": int(tdee),
        "goal": profile.goal.value
    })

    return profile_data

@app.post("/profile/calculate-tdee")
async def calculate_tdee_endpoint(req: TDEERequest):
    """Calculate TDEE without saving a profile"""
    bmr, tdee = calculate_tdee(
        weight_kg=req.weight_kg,
        height_cm=req.height_cm,
        age=req.age,
        sex=req.sex,
        activity_level=req.activity_level,
        formula=req.formula
    )

    calorie_target = calculate_calorie_target(tdee, req.goal)

    return TDEEResponse(
        bmr=int(bmr),
        tdee=int(tdee),
        calorie_target=calorie_target,
        formula_used=req.formula,
        activity_multiplier=ACTIVITY_MULTIPLIERS[req.activity_level],
        goal_adjustment=GOAL_ADJUSTMENTS[req.goal]
    )

@app.put("/profile/{user_id}/goals")
async def update_goals(user_id: str, goal: Goal, macro_preset: Optional[MacroPreset] = None):
    """Update macro goals for a user"""
    if user_id not in _profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _profiles[user_id]

    # Recalculate with new goal
    calorie_target = calculate_calorie_target(profile["tdee"], goal)
    macros = calculate_macro_targets(calorie_target, goal, macro_preset)

    profile["goal"] = goal.value
    profile["calorie_target"] = calorie_target
    profile["protein_target"] = macros.protein_g
    profile["carb_target"] = macros.carbs_g
    profile["fat_target"] = macros.fat_g
    profile["updated_at"] = datetime.utcnow().isoformat()

    await notify_event_bus("profile.goals_updated", {
        "user_id": user_id,
        "goal": goal.value,
        "calorie_target": calorie_target
    })

    return profile

@app.put("/profile/{user_id}/restrictions")
async def update_restrictions(user_id: str, restrictions: List[str]):
    """Update dietary restrictions"""
    if user_id not in _profiles:
        raise HTTPException(status_code=404, detail="Profile not found")

    _profiles[user_id]["restrictions"] = restrictions
    _profiles[user_id]["updated_at"] = datetime.utcnow().isoformat()

    return _profiles[user_id]

# =============================================================================
# MEAL LOGGING ENDPOINTS
# =============================================================================

@app.post("/meals/log")
async def log_meal(req: MealLogRequest):
    """Log a meal"""
    time_ctx = get_time_context()
    meal_date = req.date or time_ctx["current_date"]
    meal_time = req.time

    # Calculate totals
    total_calories = sum(item.calories * item.servings for item in req.items)
    total_protein = sum(item.protein * item.servings for item in req.items)
    total_carbs = sum(item.carbs * item.servings for item in req.items)
    total_fat = sum(item.fat * item.servings for item in req.items)

    meal_id = _generate_id()

    meal_data = {
        "meal_id": meal_id,
        "user_id": req.user_id,
        "meal_type": req.meal_type.value,
        "date": meal_date,
        "time": meal_time,
        "items": [item.model_dump() for item in req.items],
        "total_calories": int(total_calories),
        "total_protein": round(total_protein, 1),
        "total_carbs": round(total_carbs, 1),
        "total_fat": round(total_fat, 1),
        "notes": req.notes,
        "created_at": datetime.utcnow().isoformat()
    }

    # Store meal
    if req.user_id not in _meal_logs:
        _meal_logs[req.user_id] = []
    _meal_logs[req.user_id].append(meal_data)

    # Update daily totals
    await _update_daily_totals(req.user_id, meal_date)

    # Publish event
    await notify_event_bus("meal.logged", {
        "user_id": req.user_id,
        "meal_type": req.meal_type.value,
        "calories": int(total_calories)
    })

    return meal_data

@app.get("/meals/{user_id}/today")
async def get_todays_meals(user_id: str):
    """Get today's meals for a user"""
    time_ctx = get_time_context()
    today = time_ctx["current_date"]

    if user_id not in _meal_logs:
        return {"meals": [], "date": today}

    todays_meals = [
        meal for meal in _meal_logs[user_id]
        if meal.get("date") == today
    ]

    return {
        "meals": todays_meals,
        "date": today,
        "meal_count": len(todays_meals)
    }

@app.get("/meals/{user_id}/history")
async def get_meal_history(
    user_id: str,
    days: int = Query(default=7, ge=1, le=90),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100)
):
    """Get meal history (paginated)"""
    if user_id not in _meal_logs:
        return {"meals": [], "total": 0}

    # Sort by date descending
    meals = sorted(
        _meal_logs[user_id],
        key=lambda m: (m.get("date", ""), m.get("time", "")),
        reverse=True
    )

    # Paginate
    paginated = meals[offset:offset + limit]

    return {
        "meals": paginated,
        "total": len(meals),
        "offset": offset,
        "limit": limit
    }

@app.delete("/meals/{meal_id}")
async def delete_meal(meal_id: str, user_id: str):
    """Delete a meal log"""
    if user_id not in _meal_logs:
        raise HTTPException(status_code=404, detail="User has no meals")

    meal_to_delete = None
    for i, meal in enumerate(_meal_logs[user_id]):
        if meal.get("meal_id") == meal_id:
            meal_to_delete = _meal_logs[user_id].pop(i)
            break

    if not meal_to_delete:
        raise HTTPException(status_code=404, detail="Meal not found")

    # Update daily totals
    await _update_daily_totals(user_id, meal_to_delete.get("date"))

    return {"deleted": True, "meal_id": meal_id}

@app.put("/meals/{meal_id}")
async def update_meal(meal_id: str, req: MealLogRequest):
    """Update a meal log"""
    if req.user_id not in _meal_logs:
        raise HTTPException(status_code=404, detail="User has no meals")

    for i, meal in enumerate(_meal_logs[req.user_id]):
        if meal.get("meal_id") == meal_id:
            old_date = meal.get("date")

            # Recalculate totals
            total_calories = sum(item.calories * item.servings for item in req.items)
            total_protein = sum(item.protein * item.servings for item in req.items)
            total_carbs = sum(item.carbs * item.servings for item in req.items)
            total_fat = sum(item.fat * item.servings for item in req.items)

            time_ctx = get_time_context()
            new_date = req.date or time_ctx["current_date"]

            _meal_logs[req.user_id][i] = {
                "meal_id": meal_id,
                "user_id": req.user_id,
                "meal_type": req.meal_type.value,
                "date": new_date,
                "time": req.time,
                "items": [item.model_dump() for item in req.items],
                "total_calories": int(total_calories),
                "total_protein": round(total_protein, 1),
                "total_carbs": round(total_carbs, 1),
                "total_fat": round(total_fat, 1),
                "notes": req.notes,
                "updated_at": datetime.utcnow().isoformat()
            }

            # Update daily totals for both old and new dates
            await _update_daily_totals(req.user_id, old_date)
            if new_date != old_date:
                await _update_daily_totals(req.user_id, new_date)

            return _meal_logs[req.user_id][i]

    raise HTTPException(status_code=404, detail="Meal not found")

@app.post("/meals/quick-add")
async def quick_add_meal(user_id: str, template_name: str):
    """Quick add from template (stub - implement with templates)"""
    return {
        "status": "stub",
        "message": "Template system not yet implemented",
        "template_name": template_name
    }

# =============================================================================
# NUTRITION TRACKING ENDPOINTS
# =============================================================================

async def _update_daily_totals(user_id: str, date: str):
    """Recalculate daily totals for a user/date"""
    if user_id not in _daily_totals:
        _daily_totals[user_id] = {}

    if user_id not in _meal_logs:
        _daily_totals[user_id][date] = {
            "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "meal_count": 0
        }
        return

    day_meals = [m for m in _meal_logs[user_id] if m.get("date") == date]

    _daily_totals[user_id][date] = {
        "calories": sum(m.get("total_calories", 0) for m in day_meals),
        "protein": sum(m.get("total_protein", 0) for m in day_meals),
        "carbs": sum(m.get("total_carbs", 0) for m in day_meals),
        "fat": sum(m.get("total_fat", 0) for m in day_meals),
        "meal_count": len(day_meals)
    }

@app.get("/nutrition/{user_id}/daily")
async def get_daily_summary(user_id: str, date: Optional[str] = None):
    """Get daily nutrition summary"""
    time_ctx = get_time_context()
    target_date = date or time_ctx["current_date"]

    # Get profile for targets
    profile = _profiles.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Get or calculate daily totals
    if user_id not in _daily_totals or target_date not in _daily_totals[user_id]:
        await _update_daily_totals(user_id, target_date)

    totals = _daily_totals.get(user_id, {}).get(target_date, {
        "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "meal_count": 0
    })

    return {
        "user_id": user_id,
        "date": target_date,
        "consumed": {
            "calories": totals["calories"],
            "protein": totals["protein"],
            "carbs": totals["carbs"],
            "fat": totals["fat"]
        },
        "targets": {
            "calories": profile["calorie_target"],
            "protein": profile["protein_target"],
            "carbs": profile["carb_target"],
            "fat": profile["fat_target"]
        },
        "remaining": {
            "calories": profile["calorie_target"] - totals["calories"],
            "protein": profile["protein_target"] - totals["protein"],
            "carbs": profile["carb_target"] - totals["carbs"],
            "fat": profile["fat_target"] - totals["fat"]
        },
        "meal_count": totals["meal_count"],
        "on_target": abs(totals["calories"] - profile["calorie_target"]) <= profile["calorie_target"] * 0.1
    }

@app.get("/nutrition/{user_id}/macros")
async def get_macro_status(user_id: str):
    """Get current macro status"""
    return await get_daily_summary(user_id)

@app.get("/nutrition/{user_id}/remaining")
async def get_remaining_macros(user_id: str):
    """Get remaining macros for today"""
    summary = await get_daily_summary(user_id)
    return {
        "user_id": user_id,
        "date": summary["date"],
        "remaining": summary["remaining"],
        "meal_suggestion": get_time_context()["meal_time_suggestion"]
    }

@app.get("/nutrition/{user_id}/weekly")
async def get_weekly_summary(user_id: str):
    """Get weekly nutrition summary (stub)"""
    profile = _profiles.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "status": "stub",
        "message": "Weekly summary requires database implementation",
        "user_id": user_id
    }

@app.get("/nutrition/{user_id}/trends")
async def get_nutrition_trends(user_id: str, days: int = 30):
    """Get nutrition trends over time (stub)"""
    return {
        "status": "stub",
        "message": "Trends require database implementation",
        "user_id": user_id,
        "days": days
    }

# =============================================================================
# FOOD DATABASE ENDPOINTS
# =============================================================================

@app.get("/foods/search")
async def search_foods(query: str, limit: int = 20):
    """Search food items (stub - returns common foods)"""
    # Phase 1: Return some common foods for testing
    common_foods = [
        {"id": "1", "name": "Chicken Breast (4oz)", "calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "serving_size": 113, "serving_unit": "g"},
        {"id": "2", "name": "Brown Rice (1 cup cooked)", "calories": 216, "protein": 5, "carbs": 45, "fat": 1.8, "serving_size": 195, "serving_unit": "g"},
        {"id": "3", "name": "Broccoli (1 cup)", "calories": 55, "protein": 3.7, "carbs": 11, "fat": 0.6, "serving_size": 91, "serving_unit": "g"},
        {"id": "4", "name": "Salmon (4oz)", "calories": 233, "protein": 25, "carbs": 0, "fat": 14, "serving_size": 113, "serving_unit": "g"},
        {"id": "5", "name": "Egg (large)", "calories": 72, "protein": 6, "carbs": 0.4, "fat": 5, "serving_size": 50, "serving_unit": "g"},
        {"id": "6", "name": "Greek Yogurt (1 cup)", "calories": 100, "protein": 17, "carbs": 6, "fat": 0.7, "serving_size": 245, "serving_unit": "g"},
        {"id": "7", "name": "Banana (medium)", "calories": 105, "protein": 1.3, "carbs": 27, "fat": 0.4, "serving_size": 118, "serving_unit": "g"},
        {"id": "8", "name": "Almonds (1oz)", "calories": 164, "protein": 6, "carbs": 6, "fat": 14, "serving_size": 28, "serving_unit": "g"},
        {"id": "9", "name": "Sweet Potato (medium)", "calories": 103, "protein": 2.3, "carbs": 24, "fat": 0.1, "serving_size": 130, "serving_unit": "g"},
        {"id": "10", "name": "Oatmeal (1 cup cooked)", "calories": 158, "protein": 6, "carbs": 27, "fat": 3.2, "serving_size": 234, "serving_unit": "g"},
    ]

    # Simple search filter
    query_lower = query.lower()
    matches = [f for f in common_foods if query_lower in f["name"].lower()]

    return {
        "query": query,
        "results": matches[:limit],
        "total": len(matches)
    }

@app.get("/foods/{food_id}")
async def get_food(food_id: str):
    """Get food item details (stub)"""
    return {
        "status": "stub",
        "food_id": food_id,
        "message": "Food database requires full implementation"
    }

@app.post("/foods")
async def create_food(food: FoodItem):
    """Add custom food item (stub)"""
    food_id = _generate_id()
    _food_database[food_id] = {
        "id": food_id,
        **food.model_dump(),
        "custom": True,
        "created_at": datetime.utcnow().isoformat()
    }
    return _food_database[food_id]

@app.get("/foods/barcode/{code}")
async def lookup_barcode(code: str):
    """Lookup food by barcode (stub)"""
    return {
        "status": "stub",
        "barcode": code,
        "message": "Barcode lookup requires external API integration"
    }

@app.get("/foods/favorites/{user_id}")
async def get_favorite_foods(user_id: str):
    """Get user's favorite foods (stub)"""
    return {
        "status": "stub",
        "user_id": user_id,
        "favorites": []
    }

# =============================================================================
# MEAL SUGGESTIONS ENDPOINTS
# =============================================================================

@app.post("/suggest/meal")
async def suggest_meal(req: MealSuggestionRequest):
    """Suggest meal fitting remaining macros (stub with basic logic)"""
    # Get remaining macros
    try:
        remaining = await get_remaining_macros(req.user_id)
    except HTTPException:
        return {
            "status": "error",
            "message": "Profile not found - create profile first"
        }

    rem = remaining["remaining"]
    max_cal = req.max_calories or rem["calories"]

    # Basic suggestions based on remaining macros
    suggestions = []

    if rem["protein"] > 20:
        suggestions.append({
            "name": "Grilled Chicken Salad",
            "description": "6oz chicken breast with mixed greens",
            "estimated_macros": {"calories": 350, "protein": 45, "carbs": 10, "fat": 12}
        })

    if rem["carbs"] > 30 and rem["protein"] > 15:
        suggestions.append({
            "name": "Salmon with Brown Rice",
            "description": "4oz salmon with 1 cup brown rice and vegetables",
            "estimated_macros": {"calories": 450, "protein": 30, "carbs": 45, "fat": 15}
        })

    if rem["calories"] < 400:
        suggestions.append({
            "name": "Greek Yogurt Parfait",
            "description": "Greek yogurt with berries and almonds",
            "estimated_macros": {"calories": 250, "protein": 20, "carbs": 25, "fat": 8}
        })

    return {
        "user_id": req.user_id,
        "meal_type": req.meal_type.value,
        "remaining_macros": rem,
        "suggestions": suggestions[:3],
        "note": "AI-powered suggestions require LLM integration"
    }

@app.post("/suggest/foods")
async def suggest_foods(user_id: str, target_macro: str = "protein"):
    """Suggest foods to hit targets (stub)"""
    return {
        "status": "stub",
        "user_id": user_id,
        "target_macro": target_macro,
        "suggestions": []
    }

@app.get("/suggest/recipes")
async def get_recipe_suggestions(user_id: str):
    """Get recipe suggestions (stub)"""
    return {
        "status": "stub",
        "user_id": user_id,
        "recipes": []
    }

# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@app.get("/analysis/{user_id}/quality")
async def analyze_diet_quality(user_id: str, days: int = 7):
    """Diet quality analysis (stub)"""
    return {
        "status": "stub",
        "user_id": user_id,
        "days": days,
        "score": None,
        "message": "Quality analysis requires historical data"
    }

@app.get("/analysis/{user_id}/gaps")
async def analyze_micronutrient_gaps(user_id: str):
    """Micronutrient gap analysis (stub)"""
    return {
        "status": "stub",
        "user_id": user_id,
        "gaps": [],
        "message": "Micronutrient tracking requires expanded food database"
    }

@app.get("/analysis/{user_id}/score")
async def get_nutrition_score(user_id: str):
    """Nutrition score breakdown (stub)"""
    return {
        "status": "stub",
        "user_id": user_id,
        "score": None,
        "breakdown": {}
    }

@app.get("/streaks/{user_id}")
async def get_streaks(user_id: str):
    """Get user's nutrition streaks (stub)"""
    return {
        "user_id": user_id,
        "streaks": {
            "logging_streak": 0,
            "on_target_streak": 0,
            "protein_goal_streak": 0
        },
        "message": "Streak tracking requires database implementation"
    }

# =============================================================================
# ARIA TOOLS - Exposed for ARIA integration
# =============================================================================

ARIA_TOOLS = [
    {
        "name": "nutrition.log_meal",
        "description": "Log a meal with food items",
        "parameters": {
            "meal_type": "breakfast|lunch|dinner|snack",
            "items": [{"name": "str", "servings": "float", "calories": "int"}],
            "notes": "optional string"
        }
    },
    {
        "name": "nutrition.daily_summary",
        "description": "Get today's nutrition summary including calories and macros",
        "parameters": {}
    },
    {
        "name": "nutrition.macros_remaining",
        "description": "Get remaining macros (protein, carbs, fat, calories) for today",
        "parameters": {}
    },
    {
        "name": "nutrition.suggest_meal",
        "description": "Suggest a meal that fits remaining macros and restrictions",
        "parameters": {
            "meal_type": "breakfast|lunch|dinner|snack",
            "max_calories": "optional int"
        }
    },
    {
        "name": "nutrition.calculate_tdee",
        "description": "Calculate or recalculate TDEE based on current stats",
        "parameters": {
            "weight_kg": "float",
            "height_cm": "float",
            "age": "int",
            "sex": "male|female",
            "activity_level": "sedentary|light|moderate|active|athlete",
            "goal": "cut|maintain|bulk"
        }
    }
]

@app.get("/aria/tools")
async def get_aria_tools():
    """Get ARIA tools definition"""
    return {"tools": ARIA_TOOLS}

@app.post("/aria/execute")
async def execute_aria_tool(tool_name: str, parameters: Dict[str, Any], user_id: str):
    """Execute an ARIA tool call"""

    if tool_name == "nutrition.log_meal":
        items = [FoodItem(**item) for item in parameters.get("items", [])]
        meal_type = MealType(parameters.get("meal_type", "lunch"))
        req = MealLogRequest(
            user_id=user_id,
            meal_type=meal_type,
            items=items,
            notes=parameters.get("notes")
        )
        return await log_meal(req)

    elif tool_name == "nutrition.daily_summary":
        return await get_daily_summary(user_id)

    elif tool_name == "nutrition.macros_remaining":
        return await get_remaining_macros(user_id)

    elif tool_name == "nutrition.suggest_meal":
        req = MealSuggestionRequest(
            user_id=user_id,
            meal_type=MealType(parameters.get("meal_type", "lunch")),
            max_calories=parameters.get("max_calories")
        )
        return await suggest_meal(req)

    elif tool_name == "nutrition.calculate_tdee":
        req = TDEERequest(**parameters)
        return await calculate_tdee_endpoint(req)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8232)
