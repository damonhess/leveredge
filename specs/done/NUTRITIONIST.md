# NUTRITIONIST - AI-Powered Nutrition & Diet Management Agent

**Agent Type:** Health & Wellness
**Named After:** Demeter - Greek goddess of harvest, agriculture, and nourishment - NUTRITIONIST cultivates healthy eating habits and nourishes optimal performance
**Port:** 8101
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

NUTRITIONIST is an AI-powered nutrition agent providing personalized TDEE calculation, macro tracking, meal logging, dietary restriction management, and comprehensive nutrition analysis. It serves as the dietary intelligence hub for LeverEdge users seeking to optimize their nutrition.

### Value Proposition
- Personalized TDEE and macro calculations based on individual goals
- Intelligent meal suggestions that fit remaining daily macros
- Comprehensive dietary restriction and allergy tracking
- Micronutrient gap analysis for optimal health
- Streak and milestone tracking for habit formation

---

## CORE CAPABILITIES

### 1. TDEE Calculation
**Purpose:** Calculate Total Daily Energy Expenditure based on individual factors and goals

**Features:**
- Mifflin-St Jeor and Harris-Benedict formula support
- Activity level multipliers (sedentary to athlete)
- Goal-based adjustments (cut, maintain, bulk)
- Periodic recalculation recommendations
- Body composition integration when available

**Activity Levels:**
| Level | Multiplier | Description |
|-------|------------|-------------|
| Sedentary | 1.2 | Little to no exercise |
| Light | 1.375 | 1-3 days/week exercise |
| Moderate | 1.55 | 3-5 days/week exercise |
| Active | 1.725 | 6-7 days/week exercise |
| Athlete | 1.9 | 2x daily or physical job |

### 2. Macro Tracking
**Purpose:** Track protein, carbohydrate, and fat intake against personalized targets

**Features:**
- Goal-specific macro ratios (high protein, keto, balanced, etc.)
- Real-time macro remaining calculations
- Daily/weekly/monthly trend analysis
- Automatic target adjustments based on progress
- Macro split visualization

**Common Macro Splits:**
| Goal | Protein | Carbs | Fat |
|------|---------|-------|-----|
| Muscle Gain | 30% | 45% | 25% |
| Fat Loss | 40% | 30% | 30% |
| Maintenance | 25% | 50% | 25% |
| Keto | 25% | 5% | 70% |
| Endurance | 20% | 55% | 25% |

### 3. Meal Logging
**Purpose:** Log meals with complete nutritional breakdown

**Features:**
- Food item search with autocomplete
- Barcode scanning support (via integration)
- Custom food creation
- Meal templates for recurring meals
- Quick-add for favorite combinations
- Photo meal logging (future AI integration)

**Meal Types:**
- Breakfast
- Morning Snack
- Lunch
- Afternoon Snack
- Dinner
- Evening Snack

### 4. Dietary Restrictions
**Purpose:** Track allergies, preferences, and dietary restrictions

**Features:**
- Common allergen tracking (nuts, dairy, gluten, shellfish, etc.)
- Dietary preference profiles (vegan, vegetarian, pescatarian, etc.)
- Religious dietary requirements (halal, kosher)
- Medical restrictions (low sodium, diabetic-friendly)
- Meal suggestion filtering based on restrictions

**Restriction Categories:**
| Category | Examples |
|----------|----------|
| Allergies | Peanuts, tree nuts, shellfish, eggs, soy |
| Intolerances | Lactose, gluten, FODMAP |
| Preferences | Vegan, vegetarian, pescatarian |
| Medical | Low sodium, diabetic, renal diet |
| Religious | Halal, kosher, no pork |

### 5. Nutrition Analysis
**Purpose:** Analyze diet quality and identify micronutrient gaps

**Features:**
- Daily nutrition score (0-100)
- Micronutrient tracking (vitamins, minerals)
- Diet diversity analysis
- Fiber and water intake tracking
- Processed food percentage
- Meal timing analysis

**Micronutrients Tracked:**
- Vitamins: A, B1-B12, C, D, E, K
- Minerals: Iron, Calcium, Magnesium, Zinc, Potassium
- Other: Fiber, Omega-3, Sodium

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for meal suggestions and analysis
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/nutritionist/
├── nutritionist.py           # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── foods.yaml            # Common food database
│   ├── macros.yaml           # Macro ratio presets
│   └── restrictions.yaml     # Restriction definitions
├── modules/
│   ├── tdee_calculator.py    # TDEE calculation engine
│   ├── macro_tracker.py      # Macro tracking and analysis
│   ├── meal_logger.py        # Meal logging functionality
│   ├── restriction_manager.py # Dietary restriction handling
│   └── nutrition_analyzer.py # Diet quality analysis
└── tests/
    └── test_nutritionist.py
```

### Database Schema

```sql
-- Nutrition profiles table
CREATE TABLE nutrition_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    tdee INTEGER NOT NULL,                    -- Total Daily Energy Expenditure
    goal TEXT NOT NULL,                       -- cut, maintain, bulk
    protein_target INTEGER NOT NULL,          -- grams per day
    carb_target INTEGER NOT NULL,             -- grams per day
    fat_target INTEGER NOT NULL,              -- grams per day
    calorie_target INTEGER NOT NULL,          -- derived from TDEE and goal
    restrictions TEXT[] DEFAULT '{}',         -- array of restriction codes
    activity_level TEXT DEFAULT 'moderate',   -- sedentary, light, moderate, active, athlete
    height_cm FLOAT,
    weight_kg FLOAT,
    age INTEGER,
    sex TEXT,                                 -- male, female, other
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_profiles_user ON nutrition_profiles(user_id);
CREATE INDEX idx_profiles_goal ON nutrition_profiles(goal);

-- Food items database
CREATE TABLE food_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    calories INTEGER NOT NULL,                -- per serving
    protein FLOAT NOT NULL,                   -- grams per serving
    carbs FLOAT NOT NULL,                     -- grams per serving
    fat FLOAT NOT NULL,                       -- grams per serving
    fiber FLOAT DEFAULT 0,                    -- grams per serving
    sugar FLOAT DEFAULT 0,                    -- grams per serving
    sodium FLOAT DEFAULT 0,                   -- mg per serving
    serving_size FLOAT NOT NULL,              -- numeric amount
    serving_unit TEXT NOT NULL,               -- g, oz, cup, piece, etc.
    barcode TEXT,                             -- UPC/EAN code
    brand TEXT,
    category TEXT,                            -- protein, vegetable, grain, etc.
    verified BOOLEAN DEFAULT FALSE,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_foods_name ON food_items USING gin(to_tsvector('english', name));
CREATE INDEX idx_foods_barcode ON food_items(barcode);
CREATE INDEX idx_foods_category ON food_items(category);

-- Meal logs table
CREATE TABLE meal_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    meal_type TEXT NOT NULL,                  -- breakfast, lunch, dinner, snack
    date DATE NOT NULL,
    time TIME,
    items JSONB NOT NULL,                     -- array of {food_id, name, servings, calories, protein, carbs, fat}
    total_calories INTEGER NOT NULL,
    total_protein FLOAT NOT NULL,
    total_carbs FLOAT NOT NULL,
    total_fat FLOAT NOT NULL,
    notes TEXT,
    photo_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meals_user_date ON meal_logs(user_id, date DESC);
CREATE INDEX idx_meals_type ON meal_logs(meal_type);
CREATE INDEX idx_meals_date ON meal_logs(date DESC);

-- Daily totals (aggregated for quick queries)
CREATE TABLE daily_totals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    date DATE NOT NULL,
    calories INTEGER DEFAULT 0,
    protein FLOAT DEFAULT 0,
    carbs FLOAT DEFAULT 0,
    fat FLOAT DEFAULT 0,
    fiber FLOAT DEFAULT 0,
    water_oz INTEGER DEFAULT 0,
    meal_count INTEGER DEFAULT 0,
    nutrition_score INTEGER,                  -- 0-100 daily quality score
    on_target BOOLEAN DEFAULT FALSE,          -- hit calorie target within 10%
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_totals_user_date ON daily_totals(user_id, date);
CREATE INDEX idx_totals_date ON daily_totals(date DESC);

-- Nutrition streaks for gamification
CREATE TABLE nutrition_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    streak_type TEXT NOT NULL,                -- logging, on_target, protein_goal
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_achieved_date DATE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_streaks_user_type ON nutrition_streaks(user_id, streak_type);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # Current nutrition tracking status
GET /metrics             # Prometheus-compatible metrics
```

### Profile Management
```
GET /profile/{user_id}           # Get nutrition profile
POST /profile                    # Create/update nutrition profile
POST /profile/calculate-tdee     # Calculate TDEE for user
PUT /profile/{user_id}/goals     # Update macro goals
PUT /profile/{user_id}/restrictions  # Update dietary restrictions
```

### Meal Logging
```
POST /meals/log                  # Log a meal
GET /meals/{user_id}/today       # Get today's meals
GET /meals/{user_id}/history     # Get meal history (paginated)
DELETE /meals/{meal_id}          # Delete a meal log
PUT /meals/{meal_id}             # Update a meal log
POST /meals/quick-add            # Quick add from template
```

### Nutrition Tracking
```
GET /nutrition/{user_id}/daily   # Get daily nutrition summary
GET /nutrition/{user_id}/macros  # Get current macro status
GET /nutrition/{user_id}/remaining  # Get remaining macros for today
GET /nutrition/{user_id}/weekly  # Get weekly nutrition summary
GET /nutrition/{user_id}/trends  # Get nutrition trends over time
```

### Food Database
```
GET /foods/search                # Search food items
GET /foods/{food_id}             # Get food item details
POST /foods                      # Add custom food item
GET /foods/barcode/{code}        # Lookup by barcode
GET /foods/favorites/{user_id}   # Get user's favorite foods
```

### Meal Suggestions
```
POST /suggest/meal               # Suggest meal fitting remaining macros
POST /suggest/foods              # Suggest foods to hit targets
GET /suggest/recipes             # Get recipe suggestions
```

### Analysis
```
GET /analysis/{user_id}/quality  # Diet quality analysis
GET /analysis/{user_id}/gaps     # Micronutrient gap analysis
GET /analysis/{user_id}/score    # Nutrition score breakdown
GET /streaks/{user_id}           # Get user's nutrition streaks
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store nutrition insights
await aria_store_memory(
    memory_type="fact",
    content=f"User achieved 7-day logging streak",
    category="nutrition",
    source_type="agent_result",
    tags=["nutritionist", "streak", "achievement"]
)

# Store dietary preferences
await aria_store_memory(
    memory_type="preference",
    content=f"User follows high-protein diet with lactose intolerance",
    category="nutrition",
    source_type="user_input"
)

# Store nutrition decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Adjusted TDEE from 2400 to 2200 based on weight trend",
    category="nutrition",
    source_type="automated"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What have I eaten today?"
- Request "Log my lunch: chicken salad with 6oz chicken"
- Query "How many carbs do I have left?"
- Get alerted when daily goals are achieved
- Ask "Suggest something for dinner"

**ARIA Tools:**
```python
# Tools exposed to ARIA for nutrition management
aria_tools = [
    {
        "name": "nutrition.log_meal",
        "description": "Log a meal with food items",
        "parameters": {
            "meal_type": "breakfast|lunch|dinner|snack",
            "items": [{"name": str, "servings": float, "calories": int}],
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
            "weight_kg": float,
            "height_cm": float,
            "age": int,
            "sex": "male|female",
            "activity_level": "sedentary|light|moderate|active|athlete",
            "goal": "cut|maintain|bulk"
        }
    }
]
```

**Routing Triggers:**
```javascript
const nutritionistPatterns = [
  /log (my )?(meal|food|breakfast|lunch|dinner|snack)/i,
  /what (have I|did I) eat/i,
  /calorie|macro|protein|carb|fat/i,
  /tdee|daily (calorie|energy)/i,
  /nutrition|diet|eating/i,
  /how many .*(left|remaining)/i,
  /suggest .*(meal|food|eat)/i
];
```

### Event Bus Integration
```python
# Published events
"nutrition.meal.logged"          # Meal logged successfully
"nutrition.goal.achieved"        # Daily target hit (within 10%)
"nutrition.streak.milestone"     # Streak milestone reached (7, 14, 30, 60, 90 days)
"nutrition.profile.updated"      # Profile or goals updated
"nutrition.tdee.calculated"      # TDEE recalculated
"nutrition.warning.low_protein"  # Protein intake below threshold

# Subscribed events
"user.profile.updated"           # Sync user profile changes
"fitness.workout.completed"      # Adjust recommendations post-workout
"health.weight.logged"           # Update TDEE if weight changes significantly
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("NUTRITIONIST")

# Log AI meal suggestion costs
await cost_tracker.log_usage(
    endpoint="/suggest/meal",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"meal_type": meal_type, "restrictions": restrictions}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(nutrition_context: dict) -> str:
    return f"""You are NUTRITIONIST - AI Nutrition & Diet Management Agent for LeverEdge.

Named after Demeter, Greek goddess of harvest and nourishment, you cultivate healthy eating habits and help users achieve their nutrition goals.

## TIME AWARENESS
- Current: {nutrition_context['current_time']}
- Today's Date: {nutrition_context['today']}

## YOUR IDENTITY
You are the nutrition intelligence of LeverEdge. You track meals, calculate macros, suggest meals, and help users optimize their diet for their goals.

## USER'S NUTRITION PROFILE
- TDEE: {nutrition_context['tdee']} kcal/day
- Goal: {nutrition_context['goal']}
- Daily Targets:
  - Calories: {nutrition_context['calorie_target']} kcal
  - Protein: {nutrition_context['protein_target']}g
  - Carbs: {nutrition_context['carb_target']}g
  - Fat: {nutrition_context['fat_target']}g
- Restrictions: {nutrition_context['restrictions']}

## TODAY'S PROGRESS
- Calories: {nutrition_context['today_calories']}/{nutrition_context['calorie_target']} kcal
- Protein: {nutrition_context['today_protein']}/{nutrition_context['protein_target']}g
- Carbs: {nutrition_context['today_carbs']}/{nutrition_context['carb_target']}g
- Fat: {nutrition_context['today_fat']}/{nutrition_context['fat_target']}g
- Meals Logged: {nutrition_context['meals_today']}

## CURRENT STREAK
- Logging Streak: {nutrition_context['logging_streak']} days
- On-Target Streak: {nutrition_context['on_target_streak']} days

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
- Log health insights → ARIA via Unified Memory
- Coordinate with fitness tracking → ATLAS (if available)
- Send streak achievements → HERMES for notifications
- Publish events → Event Bus

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
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with profile management and TDEE calculation
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Database schema creation and migrations
- [ ] TDEE calculation engine with multiple formulas
- [ ] Profile CRUD operations
- [ ] Basic macro target calculation
- [ ] Deploy and test

**Done When:** NUTRITIONIST calculates TDEE and stores nutrition profiles

### Phase 2: Meal Logging (Sprint 3-4)
**Goal:** Complete meal logging functionality
- [ ] Food item database with common foods
- [ ] Food search endpoint with fuzzy matching
- [ ] Meal logging with nutritional calculation
- [ ] Daily totals aggregation
- [ ] Meal history and editing
- [ ] Custom food creation

**Done When:** Users can log meals and see daily nutrition totals

### Phase 3: Tracking & Analysis (Sprint 5-6)
**Goal:** Real-time tracking and nutrition analysis
- [ ] Remaining macros calculation
- [ ] Daily/weekly summary endpoints
- [ ] Nutrition scoring algorithm
- [ ] Trend analysis over time
- [ ] Streak tracking implementation
- [ ] Event bus integration for achievements

**Done When:** Users can see comprehensive nutrition analytics and streaks

### Phase 4: Intelligence & Integration (Sprint 7-8)
**Goal:** AI-powered suggestions and full ARIA integration
- [ ] Meal suggestion engine
- [ ] Dietary restriction filtering
- [ ] ARIA tool integration
- [ ] Unified Memory storage
- [ ] Micronutrient gap analysis
- [ ] Cost tracking implementation

**Done When:** ARIA can fully interact with nutrition tracking via natural language

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 7 | 12 | 1-2 |
| Meal Logging | 6 | 14 | 3-4 |
| Tracking & Analysis | 6 | 12 | 5-6 |
| Intelligence & Integration | 6 | 14 | 7-8 |
| **Total** | **25** | **52** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] TDEE calculation within 5% of established calculators
- [ ] Meal logging with < 2 second response time
- [ ] Remaining macros updated in real-time
- [ ] Meal suggestions respect all dietary restrictions
- [ ] Streak tracking accurate to the day

### Quality
- [ ] 99%+ uptime for nutrition tracking
- [ ] Food database with 1000+ common items
- [ ] < 500ms average API response time
- [ ] Nutrition scoring validated against dietitian review

### Integration
- [ ] ARIA can log meals via natural language
- [ ] Events publish to Event Bus on achievements
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per AI-powered request

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Inaccurate food data | Wrong calorie counts | Use verified food databases, allow user corrections |
| TDEE calculation variance | Wrong calorie targets | Implement multiple formulas, allow manual override |
| User abandons logging | No data to analyze | Gamification, streaks, quick-add features |
| Dietary restriction missed | Allergic reaction suggestion | Strict filtering, clear restriction labeling |
| Complex meal logging | User frustration | Quick-add templates, meal copying, smart search |

---

## GIT COMMIT

```
Add NUTRITIONIST - AI-powered nutrition management agent spec

- TDEE calculation with multiple formulas
- Macro tracking (protein, carbs, fat)
- Meal logging with nutritional breakdown
- Dietary restriction management
- Nutrition analysis and scoring
- ARIA tool integration
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/NUTRITIONIST.md

Context: Build NUTRITIONIST nutrition agent. Start with Phase 1 foundation.
```
