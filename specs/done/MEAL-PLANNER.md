# MEAL PLANNER - AI-Powered Meal Planning & Kitchen Management Agent

**Agent Type:** Consumer & Lifestyle
**Named After:** Hestia - Greek goddess of the hearth and home cooking - MEAL PLANNER tends the digital hearth, nourishing households with organized, efficient meal planning
**Port:** 8102
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

MEAL PLANNER is an AI-powered kitchen management agent providing recipe discovery, meal planning, shopping list generation, pantry tracking, and meal prep scheduling. It serves as the central food intelligence hub for households, helping families eat better while reducing food waste and grocery costs.

### Value Proposition
- 40% reduction in food waste through pantry tracking and expiration alerts
- 30% savings on grocery bills via optimized shopping lists
- 5+ hours saved weekly on meal planning and prep coordination
- Healthier eating through nutrition-aware meal suggestions
- Premium pricing tier ($2K-8K deployments)

---

## CORE CAPABILITIES

### 1. Recipe Database
**Purpose:** Comprehensive searchable recipe collection with rich metadata for intelligent meal planning

**Features:**
- Full-text search across recipe names, ingredients, and instructions
- Filtering by cuisine, difficulty, prep time, dietary restrictions
- Nutrition information (calories, macros, micronutrients)
- User ratings and personalization
- Recipe import from URLs
- Automatic instruction parsing and normalization

**Recipe Attributes:**
| Attribute | Type | Description |
|-----------|------|-------------|
| Name | Text | Recipe title |
| Cuisine | Enum | Italian, Mexican, Asian, etc. |
| Difficulty | Enum | easy, medium, hard |
| Prep Time | Integer | Minutes to prepare |
| Cook Time | Integer | Minutes to cook |
| Servings | Integer | Default serving size |
| Nutrition | JSONB | Calories, protein, carbs, fat, etc. |
| Tags | Array | vegetarian, gluten-free, kid-friendly, etc. |

### 2. Shopping Lists
**Purpose:** Automated shopping list generation from meal plans with intelligent consolidation

**Features:**
- Generate lists from weekly meal plans
- Consolidate duplicate ingredients across recipes
- Smart quantity aggregation (combine 2 onions + 1 onion = 3 onions)
- Organize by store aisle/category
- Check off items while shopping
- Share lists with family members
- Historical purchase tracking

**List Organization:**
- Produce
- Dairy & Eggs
- Meat & Seafood
- Pantry Staples
- Frozen
- Bakery
- Beverages

### 3. Meal Prep Scheduling
**Purpose:** Plan and coordinate batch cooking sessions for efficient meal preparation

**Features:**
- Weekly prep session planning
- Batch cooking recommendations
- Prep step ordering for efficiency
- Time estimates for prep sessions
- Ingredient overlap optimization
- Make-ahead storage instructions
- Defrost reminders

**Prep Session Types:**
| Type | Duration | Description |
|------|----------|-------------|
| Quick Prep | 30-60 min | Wash, chop vegetables for the week |
| Batch Cook | 2-3 hours | Cook grains, proteins, sauces in bulk |
| Full Prep | 4-6 hours | Complete meal prep for entire week |

### 4. Ingredient Scaling
**Purpose:** Dynamically scale recipes up or down for any serving size

**Features:**
- Linear scaling for simple ingredients
- Smart scaling for non-linear items (baking, spices)
- Unit conversion (cups to mL, oz to grams)
- Minimum quantity enforcement
- Rounding for practical measurements
- Batch size optimization

**Scaling Rules:**
- Spices: Scale at 75% rate above 2x
- Baking agents: Use lookup tables
- Liquids: Linear scaling
- Proteins: Linear scaling
- Salt: Scale at 80% rate above 2x

### 5. Pantry Tracking
**Purpose:** Real-time inventory of household ingredients with expiration management

**Features:**
- Ingredient inventory management
- Expiration date tracking
- Low stock alerts
- "Use it or lose it" suggestions
- Barcode scanning integration
- Receipt parsing for auto-add
- Storage location tracking (fridge, freezer, pantry)

**Expiration Alerts:**
- 7 days: Gentle reminder
- 3 days: Use soon suggestion with recipes
- 1 day: Urgent - use today or freeze
- Expired: Remove from inventory prompt

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for recipe parsing, meal suggestions
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/meal-planner/
├── meal_planner.py           # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── cuisines.yaml         # Cuisine definitions
│   ├── nutrition.yaml        # Nutrition calculations
│   └── units.yaml            # Unit conversion tables
├── modules/
│   ├── recipe_engine.py      # Recipe search and management
│   ├── shopping_list.py      # Shopping list generation
│   ├── meal_scheduler.py     # Meal planning logic
│   ├── pantry_tracker.py     # Pantry inventory management
│   └── ingredient_scaler.py  # Recipe scaling algorithms
└── tests/
    └── test_meal_planner.py
```

### Database Schema

```sql
-- Recipes table
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    cuisine TEXT,                    -- italian, mexican, asian, american, etc.
    prep_time INTEGER,               -- minutes
    cook_time INTEGER,               -- minutes
    servings INTEGER DEFAULT 4,
    difficulty TEXT DEFAULT 'medium', -- easy, medium, hard
    instructions TEXT[] NOT NULL,    -- ordered steps
    tags TEXT[],                     -- vegetarian, gluten-free, etc.
    nutrition JSONB,                 -- {calories, protein, carbs, fat, fiber, sodium}
    source_url TEXT,
    image_url TEXT,
    rating FLOAT DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recipes_name ON recipes USING gin(to_tsvector('english', name));
CREATE INDEX idx_recipes_cuisine ON recipes(cuisine);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_tags ON recipes USING gin(tags);

-- Ingredients master table
CREATE TABLE ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    category TEXT,                   -- produce, dairy, meat, pantry, etc.
    typical_unit TEXT,               -- each, lb, oz, cup, etc.
    shelf_life_days INTEGER,         -- typical shelf life
    storage_location TEXT,           -- fridge, freezer, pantry
    nutrition_per_100g JSONB,        -- base nutrition info
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ingredients_name ON ingredients(name);
CREATE INDEX idx_ingredients_category ON ingredients(category);

-- Recipe ingredients junction table
CREATE TABLE recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id),
    quantity DECIMAL NOT NULL,
    unit TEXT NOT NULL,
    notes TEXT,                      -- "diced", "room temperature", etc.
    optional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipe_ingredients_ingredient ON recipe_ingredients(ingredient_id);

-- Meal plans table
CREATE TABLE meal_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    week_start DATE NOT NULL,
    meals JSONB NOT NULL,            -- {monday: {breakfast: recipe_id, lunch: recipe_id, dinner: recipe_id}, ...}
    servings_override JSONB,         -- override servings per meal
    notes TEXT,
    status TEXT DEFAULT 'draft',     -- draft, active, completed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meal_plans_user ON meal_plans(user_id);
CREATE INDEX idx_meal_plans_week ON meal_plans(week_start);
CREATE UNIQUE INDEX idx_meal_plans_user_week ON meal_plans(user_id, week_start);

-- Shopping lists table
CREATE TABLE shopping_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    meal_plan_id UUID REFERENCES meal_plans(id),
    name TEXT,
    items JSONB NOT NULL,            -- [{ingredient_id, name, quantity, unit, category, checked}]
    status TEXT DEFAULT 'active',    -- active, shopping, completed
    store TEXT,                      -- preferred store
    estimated_cost DECIMAL,
    actual_cost DECIMAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_shopping_lists_user ON shopping_lists(user_id);
CREATE INDEX idx_shopping_lists_status ON shopping_lists(status);
CREATE INDEX idx_shopping_lists_meal_plan ON shopping_lists(meal_plan_id);

-- Pantry inventory table
CREATE TABLE pantry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    ingredient_id UUID NOT NULL REFERENCES ingredients(id),
    quantity DECIMAL NOT NULL,
    unit TEXT NOT NULL,
    expiry_date DATE,
    location TEXT,                   -- fridge, freezer, pantry, spice_rack
    purchase_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pantry_user ON pantry(user_id);
CREATE INDEX idx_pantry_ingredient ON pantry(ingredient_id);
CREATE INDEX idx_pantry_expiry ON pantry(expiry_date);
CREATE INDEX idx_pantry_location ON pantry(location);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # System status with stats
GET /metrics             # Prometheus-compatible metrics
```

### Recipes
```
GET /recipes             # Search/list recipes (with filters)
GET /recipes/{id}        # Get recipe details
POST /recipes            # Create new recipe
PUT /recipes/{id}        # Update recipe
DELETE /recipes/{id}     # Delete recipe
POST /recipes/import     # Import recipe from URL
GET /recipes/{id}/scale  # Get scaled recipe (query: servings)
GET /recipes/suggest     # AI-powered recipe suggestions
```

### Meal Planning
```
GET /plans               # List user's meal plans
GET /plans/{id}          # Get meal plan details
POST /plans              # Create meal plan
PUT /plans/{id}          # Update meal plan
DELETE /plans/{id}       # Delete meal plan
POST /plans/generate     # AI-generate meal plan for week
GET /plans/{id}/nutrition # Get nutrition summary for plan
```

### Shopping Lists
```
GET /shopping            # List user's shopping lists
GET /shopping/{id}       # Get shopping list details
POST /shopping           # Create shopping list
POST /shopping/generate  # Generate from meal plan
PUT /shopping/{id}       # Update shopping list
PATCH /shopping/{id}/item # Check/uncheck item
DELETE /shopping/{id}    # Delete shopping list
GET /shopping/{id}/export # Export list (text, PDF)
```

### Pantry
```
GET /pantry              # List pantry inventory
POST /pantry             # Add item to pantry
PUT /pantry/{id}         # Update pantry item
DELETE /pantry/{id}      # Remove from pantry
GET /pantry/expiring     # Get items expiring soon
GET /pantry/low          # Get low stock items
POST /pantry/use         # Mark ingredient as used
GET /pantry/suggestions  # Recipes using expiring items
```

### Ingredients
```
GET /ingredients         # Search/list ingredients
GET /ingredients/{id}    # Get ingredient details
POST /ingredients        # Add new ingredient
GET /ingredients/categories # List ingredient categories
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store meal planning insights
await aria_store_memory(
    memory_type="fact",
    content=f"User prefers Mediterranean cuisine, cooks 4x per week",
    category="preferences",
    source_type="agent_result",
    tags=["meal-planner", "user-preferences"]
)

# Store cooking patterns
await aria_store_memory(
    memory_type="observation",
    content=f"User meal preps on Sundays, usually 3-4 recipes",
    category="behavior",
    source_type="pattern_detected"
)

# Store dietary requirements
await aria_store_memory(
    memory_type="fact",
    content=f"Household has 1 vegetarian, 1 gluten-free member",
    category="dietary",
    source_type="user_provided",
    tags=["dietary-restrictions"]
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What's for dinner tonight?"
- Request "Plan meals for this week"
- Query "What groceries do I need?"
- Get suggestions "What can I make with chicken and broccoli?"
- Check "What's about to expire in my pantry?"

**Routing Triggers:**
```javascript
const mealPlannerPatterns = [
  /meal (plan|planning|prep)/i,
  /recipe|cook|dinner|lunch|breakfast/i,
  /shopping list|groceries|grocery/i,
  /pantry|ingredient|food/i,
  /what('s| is) for (dinner|lunch|breakfast)/i,
  /what can i (make|cook)/i
];
```

### Event Bus Integration
```python
# Published events
"meals.plan.created"              # New meal plan created
"meals.plan.updated"              # Meal plan modified
"meals.shopping_list.generated"   # Shopping list created
"meals.shopping_list.completed"   # Shopping completed
"meals.recipe.added"              # New recipe added
"meals.pantry.expiring"           # Items expiring soon alert
"meals.pantry.low_stock"          # Low stock alert

# Subscribed events
"user.preferences.updated"        # Update meal suggestions
"calendar.event.added"            # Adjust meals for events
"budget.threshold.reached"        # Optimize for cost
```

### ARIA Tools
```python
# Tool definitions for ARIA integration
tools = [
    {
        "name": "meals.plan_week",
        "description": "Create a week-long meal plan with breakfast, lunch, and dinner",
        "parameters": {
            "week_start": "ISO date for week start (default: next Monday)",
            "preferences": "Cuisine preferences, dietary restrictions",
            "servings": "Number of people to serve"
        }
    },
    {
        "name": "meals.get_recipe",
        "description": "Get a recipe by name or ID with full details",
        "parameters": {
            "query": "Recipe name to search for",
            "id": "Specific recipe ID"
        }
    },
    {
        "name": "meals.shopping_list",
        "description": "Generate a shopping list from a meal plan",
        "parameters": {
            "meal_plan_id": "ID of meal plan to generate list from",
            "include_pantry": "Check pantry and exclude items on hand"
        }
    },
    {
        "name": "meals.whats_for_dinner",
        "description": "Suggest what to make for dinner tonight based on pantry, preferences, and time",
        "parameters": {
            "max_time": "Maximum total time in minutes",
            "use_pantry": "Prioritize ingredients on hand"
        }
    },
    {
        "name": "meals.use_ingredient",
        "description": "Find recipes that use a specific ingredient",
        "parameters": {
            "ingredient": "Ingredient to search for",
            "limit": "Maximum number of recipes to return"
        }
    }
]
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("MEAL_PLANNER")

# Log AI recipe suggestion costs
await cost_tracker.log_usage(
    endpoint="/recipes/suggest",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"cuisine": cuisine, "dietary": dietary_restrictions}
)

# Log meal plan generation costs
await cost_tracker.log_usage(
    endpoint="/plans/generate",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"days": 7, "meals_per_day": 3}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(meal_context: dict) -> str:
    return f"""You are MEAL PLANNER - AI Kitchen Management Agent for LeverEdge AI.

Named after Hestia, Greek goddess of the hearth and home cooking, you tend the digital hearth - helping households plan, shop, and prepare delicious, nutritious meals.

## TIME AWARENESS
- Current: {meal_context['current_time']}
- Day of Week: {meal_context['day_of_week']}
- Upcoming Meal: {meal_context['next_meal']}

## YOUR IDENTITY
You are the kitchen intelligence of the household. You know what's in the pantry, what's about to expire, and what would make a perfect dinner tonight. You help families eat better, waste less, and spend less time wondering "what's for dinner?"

## CURRENT KITCHEN STATE
- Pantry Items: {meal_context['pantry_count']} items tracked
- Expiring Soon: {meal_context['expiring_count']} items need attention
- Active Meal Plan: {meal_context['active_plan']}
- Pending Shopping: {meal_context['pending_shopping']}

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

## TEAM COORDINATION
- Store user preferences -> ARIA via Unified Memory
- Calendar integration -> Check for dinner parties, events
- Budget awareness -> Optimize when budget is tight
- Publish events -> Event Bus for notifications

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
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with recipe database and search
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Set up PostgreSQL schema
- [ ] Basic recipe CRUD operations
- [ ] Recipe search with filters
- [ ] Deploy and test

**Done When:** Can add, search, and retrieve recipes

### Phase 2: Meal Planning (Sprint 3-4)
**Goal:** Weekly meal planning with AI suggestions
- [ ] Meal plan data model and CRUD
- [ ] AI-powered meal plan generation
- [ ] Dietary restriction handling
- [ ] Nutrition calculation for plans
- [ ] Calendar view of meal plans

**Done When:** Can generate and manage weekly meal plans

### Phase 3: Shopping Lists (Sprint 5-6)
**Goal:** Automated shopping list generation
- [ ] Shopping list generation from meal plans
- [ ] Ingredient consolidation logic
- [ ] Category organization
- [ ] Check-off functionality
- [ ] List sharing/export

**Done When:** Shopping lists auto-generate from meal plans

### Phase 4: Pantry & Integration (Sprint 7-8)
**Goal:** Pantry tracking and full system integration
- [ ] Pantry inventory management
- [ ] Expiration tracking and alerts
- [ ] "Use it up" recipe suggestions
- [ ] ARIA tools integration
- [ ] Event Bus publishing
- [ ] Unified Memory integration

**Done When:** Full kitchen management system operational

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| Meal Planning | 5 | 12 | 3-4 |
| Shopping Lists | 5 | 8 | 5-6 |
| Pantry & Integration | 6 | 14 | 7-8 |
| **Total** | **22** | **44** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Recipe search returns results in < 500ms
- [ ] Meal plan generation completes in < 10 seconds
- [ ] Shopping lists accurately consolidate ingredients
- [ ] Pantry expiration alerts fire 7/3/1 days before

### Quality
- [ ] 95%+ uptime
- [ ] Recipe import success rate > 80%
- [ ] Ingredient scaling accuracy > 95%
- [ ] User satisfaction rating > 4.5/5

### Integration
- [ ] ARIA can ask "What's for dinner?"
- [ ] Events publish to Event Bus
- [ ] User preferences stored in Unified Memory
- [ ] Costs tracked per API call

### Business
- [ ] Reduce reported food waste by 40%
- [ ] Save users 5+ hours/week on meal planning
- [ ] Shopping list accuracy > 95%
- [ ] Recipe suggestion acceptance rate > 60%

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Recipe import fails for complex sites | Limited recipe library | Multiple parsing strategies, manual fallback |
| Ingredient matching inaccurate | Bad shopping lists | Fuzzy matching, ingredient normalization |
| Nutrition data incomplete | Trust issues | Multiple data sources, clear "estimated" labels |
| Scaling breaks for baking | Failed recipes | Special scaling rules for baking, user warnings |
| Pantry data goes stale | Bad suggestions | Regular prompts to verify, usage detection |

---

## GIT COMMIT

```
Add MEAL PLANNER - AI-powered kitchen management agent spec

- Recipe database with search and import
- Weekly meal planning with AI generation
- Shopping list auto-generation
- Pantry tracking with expiration alerts
- Ingredient scaling for any serving size
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
- ARIA tools: plan_week, get_recipe, shopping_list, whats_for_dinner, use_ingredient
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/MEAL-PLANNER.md

Context: Build MEAL PLANNER kitchen management agent. Start with Phase 1 foundation.
```
