#!/usr/bin/env python3
"""
MEAL PLANNER - AI-Powered Meal Planning & Kitchen Management Agent
Port: 8102

Named after Hestia - Greek goddess of the hearth and home cooking.
Tends the digital hearth, nourishing households with organized, efficient meal planning.

CORE CAPABILITIES:
- Recipe database with search and scaling
- Weekly meal planning with AI suggestions
- Shopping list generation and consolidation
- Pantry tracking with expiration alerts
- Meal prep scheduling

TEAM INTEGRATION:
- Time-aware (knows current date, meal times)
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs costs to shared cost tracker
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="MEAL PLANNER",
    description="AI-Powered Meal Planning & Kitchen Management Agent",
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
    "EVENT_BUS": EVENT_BUS_URL
}

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("MEAL_PLANNER")

# =============================================================================
# CONSTANTS
# =============================================================================

INGREDIENT_CATEGORIES = [
    "produce",
    "dairy_eggs",
    "meat_seafood",
    "pantry_staples",
    "frozen",
    "bakery",
    "beverages",
    "spices_seasonings"
]

CUISINES = [
    "italian", "mexican", "asian", "american", "mediterranean",
    "indian", "french", "japanese", "chinese", "thai",
    "greek", "middle_eastern", "korean", "vietnamese", "other"
]

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack", "dessert"]

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Scaling rules for non-linear ingredients
SCALING_RULES = {
    "spices": 0.75,      # Scale at 75% rate above 2x
    "salt": 0.80,        # Scale at 80% rate above 2x
    "baking_powder": 0.85,
    "baking_soda": 0.85,
    "yeast": 0.90,
    "vanilla": 0.80,
}

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for meal planning"""
    now = datetime.now()
    today = now.date()
    hour = now.hour

    # Determine next meal based on time of day
    if hour < 10:
        next_meal = "breakfast"
    elif hour < 14:
        next_meal = "lunch"
    elif hour < 18:
        next_meal = "snack"
    else:
        next_meal = "dinner"

    # Calculate next Monday for week start
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "next_meal": next_meal,
        "next_week_start": next_monday.isoformat(),
        "hour_of_day": hour
    }

# =============================================================================
# SYSTEM PROMPT BUILDER
# =============================================================================

def build_system_prompt(meal_context: dict = None) -> str:
    """Build the system prompt for MEAL PLANNER AI interactions"""
    time_ctx = get_time_context()

    # Default context values
    ctx = meal_context or {}
    pantry_count = ctx.get("pantry_count", 0)
    expiring_count = ctx.get("expiring_count", 0)
    active_plan = ctx.get("active_plan", "None")
    pending_shopping = ctx.get("pending_shopping", "None")

    return f"""You are MEAL PLANNER - AI Kitchen Management Agent for LeverEdge AI.

Named after Hestia, Greek goddess of the hearth and home cooking, you tend the digital hearth - helping households plan, shop, and prepare delicious, nutritious meals.

## TIME AWARENESS
- Current: {time_ctx['day_of_week']}, {time_ctx['current_date']} at {time_ctx['current_time']}
- Upcoming Meal: {time_ctx['next_meal']}
- Next Week Starts: {time_ctx['next_week_start']}

## YOUR IDENTITY
You are the kitchen intelligence of the household. You know what's in the pantry, what's about to expire, and what would make a perfect dinner tonight. You help families eat better, waste less, and spend less time wondering "what's for dinner?"

## CURRENT KITCHEN STATE
- Pantry Items: {pantry_count} items tracked
- Expiring Soon: {expiring_count} items need attention
- Active Meal Plan: {active_plan}
- Pending Shopping: {pending_shopping}

## YOUR CAPABILITIES

### Recipe Intelligence
- Search thousands of recipes by ingredient, cuisine, time, difficulty
- Import recipes from URLs and parse automatically
- Scale recipes up or down for any serving size
- Calculate complete nutrition information
- Suggest recipes based on preferences and pantry

### Meal Planning
- Generate balanced weekly meal plans
- Account for dietary restrictions and preferences
- Optimize for variety and nutrition
- Plan around busy days with quick meals
- Batch cooking recommendations

### Shopping Management
- Generate consolidated shopping lists from meal plans
- Organize by store aisle for efficient shopping
- Track prices and estimate costs
- Account for pantry inventory
- Share lists with family members

### Pantry Tracking
- Monitor ingredient inventory
- Alert before items expire
- Suggest recipes to use expiring items
- Track typical usage patterns
- Recommend restocking

### Meal Prep Coordination
- Plan efficient prep sessions
- Order tasks for maximum efficiency
- Calculate prep time estimates
- Storage and reheating instructions

## DIETARY AWARENESS
Always consider:
- Allergies (peanut, gluten, dairy, shellfish, etc.)
- Dietary choices (vegetarian, vegan, keto, etc.)
- Cultural/religious requirements (halal, kosher, etc.)
- Nutritional goals (low sodium, high protein, etc.)

## RESPONSE FORMAT
For meal suggestions:
1. Recipe name and brief description
2. Time required (prep + cook)
3. Key ingredients (highlighting pantry items)
4. Nutrition highlights
5. Why this recipe fits the request

For meal plans:
1. Day-by-day breakdown
2. Nutrition summary
3. Shopping list preview
4. Prep schedule recommendation

## YOUR MISSION
Help families eat well, waste less, and enjoy cooking.
Every meal is an opportunity for nourishment and connection.
Make "what's for dinner?" the easiest question of the day.
"""

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

# Recipe Models
class RecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = "other"
    prep_time: Optional[int] = None  # minutes
    cook_time: Optional[int] = None  # minutes
    servings: int = 4
    difficulty: str = "medium"
    instructions: List[str]
    ingredients: List[Dict[str, Any]]  # [{name, quantity, unit, notes, optional}]
    tags: Optional[List[str]] = []
    nutrition: Optional[Dict[str, Any]] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cuisine: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    servings: Optional[int] = None
    difficulty: Optional[str] = None
    instructions: Optional[List[str]] = None
    ingredients: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    nutrition: Optional[Dict[str, Any]] = None

class RecipeSearchParams(BaseModel):
    query: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    max_time: Optional[int] = None  # total time (prep + cook)
    tags: Optional[List[str]] = None
    ingredients: Optional[List[str]] = None  # must include these
    exclude_ingredients: Optional[List[str]] = None
    limit: int = 20

# Meal Plan Models
class MealPlanCreate(BaseModel):
    week_start: str  # ISO date
    meals: Dict[str, Dict[str, str]] = {}  # {monday: {breakfast: recipe_id, ...}, ...}
    servings_override: Optional[Dict[str, int]] = None
    notes: Optional[str] = None

class MealPlanGenerate(BaseModel):
    week_start: Optional[str] = None  # defaults to next Monday
    servings: int = 4
    preferences: Optional[Dict[str, Any]] = None  # {cuisines, dietary, avoid}
    meals_per_day: List[str] = ["breakfast", "lunch", "dinner"]
    budget: Optional[str] = None  # low, medium, high
    prep_style: Optional[str] = "balanced"  # quick, balanced, elaborate

# Shopping List Models
class ShoppingListCreate(BaseModel):
    name: Optional[str] = None
    meal_plan_id: Optional[str] = None
    items: List[Dict[str, Any]] = []  # [{ingredient_id, name, quantity, unit, category}]
    store: Optional[str] = None

class ShoppingListGenerate(BaseModel):
    meal_plan_id: str
    include_pantry_check: bool = True
    organize_by_category: bool = True

class ShoppingItemUpdate(BaseModel):
    item_index: int
    checked: bool

# Pantry Models
class PantryItemCreate(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str
    expiry_date: Optional[str] = None  # ISO date
    location: Optional[str] = "pantry"  # fridge, freezer, pantry, spice_rack
    purchase_date: Optional[str] = None
    notes: Optional[str] = None

class PantryItemUpdate(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class PantryUseItem(BaseModel):
    pantry_item_id: str
    quantity_used: float

# Ingredient Models
class IngredientCreate(BaseModel):
    name: str
    category: str
    typical_unit: Optional[str] = None
    shelf_life_days: Optional[int] = None
    storage_location: Optional[str] = None
    nutrition_per_100g: Optional[Dict[str, Any]] = None

# ARIA Tool Models
class MealsPlanWeekRequest(BaseModel):
    week_start: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    servings: int = 4

class MealsGetRecipeRequest(BaseModel):
    query: Optional[str] = None
    id: Optional[str] = None

class MealsShoppingListRequest(BaseModel):
    meal_plan_id: str
    include_pantry: bool = True

class MealsWhatsForDinnerRequest(BaseModel):
    max_time: Optional[int] = None  # minutes
    use_pantry: bool = True

class MealsUseIngredientRequest(BaseModel):
    ingredient: str
    limit: int = 5

# Chat Model
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = {}
    user_id: Optional[str] = None

# =============================================================================
# RECIPE SCALING LOGIC
# =============================================================================

def scale_ingredient(
    ingredient: Dict[str, Any],
    original_servings: int,
    target_servings: int
) -> Dict[str, Any]:
    """Scale an ingredient quantity with smart rules for non-linear items"""
    scale_factor = target_servings / original_servings
    original_qty = float(ingredient.get("quantity", 0))
    ingredient_name = ingredient.get("name", "").lower()

    # Determine if this is a special scaling category
    adjusted_factor = scale_factor

    if scale_factor > 2:
        # Apply scaling rules for large multipliers
        for category, rate in SCALING_RULES.items():
            if category in ingredient_name or any(
                spice in ingredient_name for spice in
                ["cumin", "paprika", "oregano", "basil", "thyme", "pepper"]
            ):
                # Non-linear scaling for spices
                excess = scale_factor - 2
                adjusted_factor = 2 + (excess * rate)
                break

    new_qty = original_qty * adjusted_factor

    # Round to practical measurements
    new_qty = round_to_practical(new_qty, ingredient.get("unit", ""))

    return {
        **ingredient,
        "quantity": new_qty,
        "original_quantity": original_qty,
        "scale_factor": round(adjusted_factor, 2)
    }

def round_to_practical(quantity: float, unit: str) -> float:
    """Round quantities to practical cooking measurements"""
    unit_lower = unit.lower()

    # For tablespoons and teaspoons, round to nearest quarter
    if unit_lower in ["tbsp", "tablespoon", "tsp", "teaspoon"]:
        return round(quantity * 4) / 4

    # For cups, round to nearest eighth
    if unit_lower in ["cup", "cups"]:
        return round(quantity * 8) / 8

    # For pieces/whole items, round to nearest whole
    if unit_lower in ["", "each", "piece", "pieces", "whole"]:
        return round(quantity)

    # For weight measurements, round to one decimal
    if unit_lower in ["oz", "ounce", "lb", "pound", "g", "gram", "kg"]:
        return round(quantity, 1)

    # Default: round to two decimals
    return round(quantity, 2)

def scale_recipe(recipe: Dict[str, Any], target_servings: int) -> Dict[str, Any]:
    """Scale an entire recipe to target servings"""
    original_servings = recipe.get("servings", 4)

    scaled_ingredients = [
        scale_ingredient(ing, original_servings, target_servings)
        for ing in recipe.get("ingredients", [])
    ]

    return {
        **recipe,
        "servings": target_servings,
        "original_servings": original_servings,
        "ingredients": scaled_ingredients,
        "scaled": True
    }

# =============================================================================
# SHOPPING LIST CONSOLIDATION
# =============================================================================

def consolidate_ingredients(ingredient_lists: List[List[Dict]]) -> List[Dict]:
    """Consolidate ingredients from multiple recipes into a single shopping list"""
    consolidated = {}

    for ingredients in ingredient_lists:
        for ing in ingredients:
            name = ing.get("name", "").lower().strip()
            unit = ing.get("unit", "").lower().strip()
            quantity = float(ing.get("quantity", 0))
            category = ing.get("category", "pantry_staples")

            # Create a key for matching (name + unit)
            key = f"{name}|{unit}"

            if key in consolidated:
                # Add quantities together
                consolidated[key]["quantity"] += quantity
            else:
                consolidated[key] = {
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "category": category,
                    "checked": False
                }

    # Sort by category then name
    result = sorted(
        consolidated.values(),
        key=lambda x: (INGREDIENT_CATEGORIES.index(x["category"]) if x["category"] in INGREDIENT_CATEGORIES else 99, x["name"])
    )

    return result

def organize_by_category(items: List[Dict]) -> Dict[str, List[Dict]]:
    """Organize shopping list items by category"""
    organized = {cat: [] for cat in INGREDIENT_CATEGORIES}
    organized["other"] = []

    for item in items:
        cat = item.get("category", "other")
        if cat in organized:
            organized[cat].append(item)
        else:
            organized["other"].append(item)

    # Remove empty categories
    return {k: v for k, v in organized.items() if v}

# =============================================================================
# EVENT BUS INTEGRATION
# =============================================================================

async def publish_event(event_type: str, data: Dict[str, Any] = None):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "MEAL_PLANNER",
                    "data": data or {},
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[MEAL_PLANNER] Event bus publish error: {e}")

async def notify_hermes(message: str, priority: str = "normal"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[MEAL PLANNER] {message}",
                    "priority": priority,
                    "source": "MEAL_PLANNER"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[MEAL_PLANNER] HERMES notification error: {e}")

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, meal_context: dict = None) -> str:
    """Call Claude API with full context and cost tracking"""
    if not client:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    try:
        system_prompt = build_system_prompt(meal_context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="MEAL_PLANNER",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"context": meal_context}
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
        "agent": "MEAL_PLANNER",
        "role": "Kitchen Management",
        "port": 8102,
        "current_time": time_ctx["current_datetime"],
        "next_meal": time_ctx["next_meal"],
        "day_of_week": time_ctx["day_of_week"]
    }

@app.get("/status")
async def status():
    """System status with stats"""
    time_ctx = get_time_context()

    # TODO: Fetch actual stats from database when schema is created
    stats = {
        "recipes_count": 0,
        "active_meal_plans": 0,
        "pantry_items": 0,
        "items_expiring_soon": 0,
        "pending_shopping_lists": 0
    }

    return {
        "status": "operational",
        "agent": "MEAL_PLANNER",
        "version": "1.0.0",
        "time_context": time_ctx,
        "stats": stats,
        "capabilities": [
            "recipe_search",
            "recipe_scaling",
            "meal_planning",
            "shopping_list_generation",
            "pantry_tracking",
            "meal_prep_scheduling"
        ],
        "event_bus": EVENT_BUS_URL,
        "database": "pending_schema"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    # TODO: Implement proper Prometheus metrics
    return {
        "meal_planner_requests_total": 0,
        "meal_planner_recipes_served": 0,
        "meal_planner_plans_generated": 0,
        "meal_planner_shopping_lists_created": 0,
        "meal_planner_llm_calls_total": 0,
        "meal_planner_llm_cost_total": 0.0
    }

# =============================================================================
# RECIPE ENDPOINTS
# =============================================================================

@app.get("/recipes")
async def list_recipes(
    query: Optional[str] = None,
    cuisine: Optional[str] = None,
    difficulty: Optional[str] = None,
    max_time: Optional[int] = None,
    tags: Optional[str] = None,
    limit: int = 20
):
    """Search/list recipes with filters"""
    # TODO: Implement database query when schema is created
    # For now, return stub response
    return {
        "recipes": [],
        "total": 0,
        "filters_applied": {
            "query": query,
            "cuisine": cuisine,
            "difficulty": difficulty,
            "max_time": max_time,
            "tags": tags.split(",") if tags else None
        },
        "message": "Database schema pending - recipes will be available after migration"
    }

@app.get("/recipes/{recipe_id}")
async def get_recipe(recipe_id: str):
    """Get recipe details by ID"""
    # TODO: Implement database query when schema is created
    raise HTTPException(status_code=404, detail="Recipe not found - database schema pending")

@app.post("/recipes")
async def create_recipe(recipe: RecipeCreate):
    """Create a new recipe"""
    # TODO: Implement database insert when schema is created
    await publish_event("meals.recipe.added", {"name": recipe.name})

    return {
        "message": "Recipe creation pending database schema",
        "recipe": recipe.model_dump(),
        "id": "pending"
    }

@app.put("/recipes/{recipe_id}")
async def update_recipe(recipe_id: str, recipe: RecipeUpdate):
    """Update an existing recipe"""
    # TODO: Implement database update when schema is created
    raise HTTPException(status_code=404, detail="Recipe not found - database schema pending")

@app.delete("/recipes/{recipe_id}")
async def delete_recipe(recipe_id: str):
    """Delete a recipe"""
    # TODO: Implement database delete when schema is created
    raise HTTPException(status_code=404, detail="Recipe not found - database schema pending")

@app.post("/recipes/import")
async def import_recipe(url: str):
    """Import recipe from URL using AI parsing"""
    # TODO: Implement URL fetching and AI parsing
    return {
        "message": "Recipe import pending implementation",
        "url": url,
        "status": "stub"
    }

@app.get("/recipes/{recipe_id}/scale")
async def get_scaled_recipe(recipe_id: str, servings: int = Query(..., gt=0)):
    """Get a recipe scaled to specified servings"""
    # TODO: Fetch recipe from database and scale
    # For now, demonstrate scaling logic with a stub

    stub_recipe = {
        "id": recipe_id,
        "name": "Sample Recipe",
        "servings": 4,
        "ingredients": [
            {"name": "flour", "quantity": 2, "unit": "cups", "category": "pantry_staples"},
            {"name": "salt", "quantity": 1, "unit": "tsp", "category": "spices_seasonings"},
            {"name": "butter", "quantity": 0.5, "unit": "cups", "category": "dairy_eggs"}
        ]
    }

    scaled = scale_recipe(stub_recipe, servings)

    return {
        "recipe": scaled,
        "target_servings": servings,
        "original_servings": stub_recipe["servings"]
    }

@app.get("/recipes/suggest")
async def suggest_recipes(
    max_time: Optional[int] = None,
    cuisine: Optional[str] = None,
    dietary: Optional[str] = None,
    mood: Optional[str] = None
):
    """AI-powered recipe suggestions"""
    prompt = f"""Suggest 3 recipes based on:
- Max time: {max_time or 'any'} minutes
- Cuisine preference: {cuisine or 'any'}
- Dietary requirements: {dietary or 'none specified'}
- Mood/occasion: {mood or 'everyday dinner'}

Provide brief, practical suggestions with estimated times."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages)

    return {
        "suggestions": response,
        "filters": {
            "max_time": max_time,
            "cuisine": cuisine,
            "dietary": dietary,
            "mood": mood
        }
    }

# =============================================================================
# MEAL PLANNING ENDPOINTS
# =============================================================================

@app.get("/plans")
async def list_meal_plans(user_id: Optional[str] = None, status: Optional[str] = None):
    """List user's meal plans"""
    # TODO: Implement database query when schema is created
    return {
        "plans": [],
        "total": 0,
        "message": "Database schema pending"
    }

@app.get("/plans/{plan_id}")
async def get_meal_plan(plan_id: str):
    """Get meal plan details"""
    # TODO: Implement database query when schema is created
    raise HTTPException(status_code=404, detail="Meal plan not found - database schema pending")

@app.post("/plans")
async def create_meal_plan(plan: MealPlanCreate):
    """Create a meal plan manually"""
    await publish_event("meals.plan.created", {"week_start": plan.week_start})

    return {
        "message": "Meal plan creation pending database schema",
        "plan": plan.model_dump(),
        "id": "pending"
    }

@app.post("/plans/generate")
async def generate_meal_plan(params: MealPlanGenerate):
    """AI-generate a meal plan for the week"""
    time_ctx = get_time_context()
    week_start = params.week_start or time_ctx["next_week_start"]

    prompt = f"""Generate a weekly meal plan starting {week_start}.

Parameters:
- Servings: {params.servings}
- Meals per day: {', '.join(params.meals_per_day)}
- Preferences: {json.dumps(params.preferences) if params.preferences else 'None specified'}
- Budget: {params.budget or 'moderate'}
- Prep style: {params.prep_style}

Create a balanced, practical meal plan with:
1. Day-by-day breakdown
2. Quick meals for busy days (weekdays)
3. More elaborate options for weekends
4. Good variety across the week
5. Batch cooking opportunities

Format as a structured plan that's easy to follow."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, {"pantry_count": 0, "expiring_count": 0})

    await publish_event("meals.plan.created", {"week_start": week_start, "ai_generated": True})

    return {
        "meal_plan": response,
        "week_start": week_start,
        "parameters": params.model_dump(),
        "ai_generated": True
    }

@app.put("/plans/{plan_id}")
async def update_meal_plan(plan_id: str, plan: MealPlanCreate):
    """Update a meal plan"""
    await publish_event("meals.plan.updated", {"plan_id": plan_id})
    raise HTTPException(status_code=404, detail="Meal plan not found - database schema pending")

@app.delete("/plans/{plan_id}")
async def delete_meal_plan(plan_id: str):
    """Delete a meal plan"""
    raise HTTPException(status_code=404, detail="Meal plan not found - database schema pending")

@app.get("/plans/{plan_id}/nutrition")
async def get_plan_nutrition(plan_id: str):
    """Get nutrition summary for a meal plan"""
    # TODO: Calculate nutrition from plan recipes
    raise HTTPException(status_code=404, detail="Meal plan not found - database schema pending")

# =============================================================================
# SHOPPING LIST ENDPOINTS
# =============================================================================

@app.get("/shopping")
async def list_shopping_lists(user_id: Optional[str] = None, status: Optional[str] = None):
    """List user's shopping lists"""
    return {
        "lists": [],
        "total": 0,
        "message": "Database schema pending"
    }

@app.get("/shopping/{list_id}")
async def get_shopping_list(list_id: str):
    """Get shopping list details"""
    raise HTTPException(status_code=404, detail="Shopping list not found - database schema pending")

@app.post("/shopping")
async def create_shopping_list(shopping_list: ShoppingListCreate):
    """Create a shopping list manually"""
    return {
        "message": "Shopping list creation pending database schema",
        "list": shopping_list.model_dump(),
        "id": "pending"
    }

@app.post("/shopping/generate")
async def generate_shopping_list(params: ShoppingListGenerate):
    """Generate shopping list from a meal plan"""
    # TODO: Fetch meal plan recipes and consolidate ingredients

    await publish_event("meals.shopping_list.generated", {"meal_plan_id": params.meal_plan_id})

    return {
        "message": "Shopping list generation pending database schema",
        "meal_plan_id": params.meal_plan_id,
        "include_pantry_check": params.include_pantry_check,
        "status": "stub"
    }

@app.put("/shopping/{list_id}")
async def update_shopping_list(list_id: str, shopping_list: ShoppingListCreate):
    """Update a shopping list"""
    raise HTTPException(status_code=404, detail="Shopping list not found - database schema pending")

@app.patch("/shopping/{list_id}/item")
async def update_shopping_item(list_id: str, item_update: ShoppingItemUpdate):
    """Check/uncheck an item on the shopping list"""
    raise HTTPException(status_code=404, detail="Shopping list not found - database schema pending")

@app.delete("/shopping/{list_id}")
async def delete_shopping_list(list_id: str):
    """Delete a shopping list"""
    raise HTTPException(status_code=404, detail="Shopping list not found - database schema pending")

@app.get("/shopping/{list_id}/export")
async def export_shopping_list(list_id: str, format: str = "text"):
    """Export shopping list (text, PDF)"""
    # TODO: Implement export functionality
    raise HTTPException(status_code=404, detail="Shopping list not found - database schema pending")

# =============================================================================
# PANTRY ENDPOINTS
# =============================================================================

@app.get("/pantry")
async def list_pantry(user_id: Optional[str] = None, location: Optional[str] = None):
    """List pantry inventory"""
    return {
        "items": [],
        "total": 0,
        "locations": INGREDIENT_CATEGORIES,
        "message": "Database schema pending"
    }

@app.post("/pantry")
async def add_pantry_item(item: PantryItemCreate):
    """Add item to pantry"""
    return {
        "message": "Pantry item creation pending database schema",
        "item": item.model_dump(),
        "id": "pending"
    }

@app.put("/pantry/{item_id}")
async def update_pantry_item(item_id: str, item: PantryItemUpdate):
    """Update a pantry item"""
    raise HTTPException(status_code=404, detail="Pantry item not found - database schema pending")

@app.delete("/pantry/{item_id}")
async def remove_pantry_item(item_id: str):
    """Remove item from pantry"""
    raise HTTPException(status_code=404, detail="Pantry item not found - database schema pending")

@app.get("/pantry/expiring")
async def get_expiring_items(days: int = 7):
    """Get items expiring within specified days"""
    # TODO: Query pantry for items expiring soon
    return {
        "items": [],
        "days_threshold": days,
        "message": "Database schema pending"
    }

@app.get("/pantry/low")
async def get_low_stock_items():
    """Get low stock items"""
    # TODO: Implement low stock detection
    return {
        "items": [],
        "message": "Database schema pending"
    }

@app.post("/pantry/use")
async def use_pantry_item(use_info: PantryUseItem):
    """Mark ingredient as used (reduce quantity)"""
    raise HTTPException(status_code=404, detail="Pantry item not found - database schema pending")

@app.get("/pantry/suggestions")
async def get_pantry_suggestions():
    """Get recipe suggestions using expiring/available pantry items"""
    # TODO: Cross-reference pantry with recipes
    return {
        "suggestions": [],
        "based_on": "expiring_items",
        "message": "Database schema pending"
    }

# =============================================================================
# INGREDIENT ENDPOINTS
# =============================================================================

@app.get("/ingredients")
async def list_ingredients(
    query: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
):
    """Search/list ingredients"""
    return {
        "ingredients": [],
        "total": 0,
        "categories": INGREDIENT_CATEGORIES,
        "message": "Database schema pending"
    }

@app.get("/ingredients/{ingredient_id}")
async def get_ingredient(ingredient_id: str):
    """Get ingredient details"""
    raise HTTPException(status_code=404, detail="Ingredient not found - database schema pending")

@app.post("/ingredients")
async def create_ingredient(ingredient: IngredientCreate):
    """Add a new ingredient to the database"""
    return {
        "message": "Ingredient creation pending database schema",
        "ingredient": ingredient.model_dump(),
        "id": "pending"
    }

@app.get("/ingredients/categories")
async def get_ingredient_categories():
    """List all ingredient categories"""
    return {
        "categories": INGREDIENT_CATEGORIES,
        "descriptions": {
            "produce": "Fresh fruits and vegetables",
            "dairy_eggs": "Milk, cheese, yogurt, eggs",
            "meat_seafood": "Fresh and frozen meats, fish, shellfish",
            "pantry_staples": "Canned goods, grains, pasta, oils",
            "frozen": "Frozen vegetables, fruits, prepared foods",
            "bakery": "Bread, pastries, baked goods",
            "beverages": "Drinks, juices, milk alternatives",
            "spices_seasonings": "Herbs, spices, seasonings, sauces"
        }
    }

# =============================================================================
# ARIA TOOLS - Stubs for ARIA integration
# =============================================================================

@app.post("/tools/meals.plan_week")
async def aria_plan_week(request: MealsPlanWeekRequest):
    """ARIA tool: Create a week-long meal plan"""
    params = MealPlanGenerate(
        week_start=request.week_start,
        servings=request.servings,
        preferences=request.preferences
    )
    return await generate_meal_plan(params)

@app.post("/tools/meals.get_recipe")
async def aria_get_recipe(request: MealsGetRecipeRequest):
    """ARIA tool: Get a recipe by name or ID"""
    if request.id:
        return await get_recipe(request.id)

    if request.query:
        return await list_recipes(query=request.query, limit=1)

    raise HTTPException(status_code=400, detail="Provide either 'query' or 'id'")

@app.post("/tools/meals.shopping_list")
async def aria_shopping_list(request: MealsShoppingListRequest):
    """ARIA tool: Generate shopping list from meal plan"""
    params = ShoppingListGenerate(
        meal_plan_id=request.meal_plan_id,
        include_pantry_check=request.include_pantry
    )
    return await generate_shopping_list(params)

@app.post("/tools/meals.whats_for_dinner")
async def aria_whats_for_dinner(request: MealsWhatsForDinnerRequest):
    """ARIA tool: Suggest dinner based on time and pantry"""
    time_ctx = get_time_context()

    prompt = f"""What should we have for dinner tonight?

Current time: {time_ctx['current_time']}
Day: {time_ctx['day_of_week']}
Max cooking time: {request.max_time or 'flexible'} minutes
Use pantry ingredients: {request.use_pantry}

Suggest 2-3 practical dinner options with:
1. Recipe name
2. Total time (prep + cook)
3. Key ingredients needed
4. Why it's a good choice for tonight"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages)

    return {
        "suggestions": response,
        "time_context": time_ctx,
        "parameters": request.model_dump()
    }

@app.post("/tools/meals.use_ingredient")
async def aria_use_ingredient(request: MealsUseIngredientRequest):
    """ARIA tool: Find recipes using a specific ingredient"""
    prompt = f"""Find recipes that use {request.ingredient}.

Suggest {request.limit} recipes that:
1. Feature {request.ingredient} as a main ingredient
2. Are practical for home cooking
3. Have different difficulty levels

For each recipe provide:
- Name
- Brief description
- Total time
- How the ingredient is used"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages)

    return {
        "recipes": response,
        "ingredient": request.ingredient,
        "limit": request.limit
    }

# =============================================================================
# CHAT ENDPOINT
# =============================================================================

@app.post("/chat")
async def chat(request: ChatRequest):
    """Have a conversation with MEAL PLANNER"""
    time_ctx = get_time_context()

    meal_context = {
        "pantry_count": request.context.get("pantry_count", 0),
        "expiring_count": request.context.get("expiring_count", 0),
        "active_plan": request.context.get("active_plan", "None"),
        "pending_shopping": request.context.get("pending_shopping", "None")
    }

    messages = [{"role": "user", "content": request.message}]
    response = await call_llm(messages, meal_context)

    return {
        "response": response,
        "agent": "MEAL_PLANNER",
        "time_context": time_ctx,
        "timestamp": time_ctx["current_datetime"]
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8102)
