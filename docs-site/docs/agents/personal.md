# Personal Fleet

The Personal Fleet provides AI-powered assistance for health, fitness, nutrition, learning, and personal development.

## Fleet Overview

| Agent | Port | Purpose | Type |
|-------|------|---------|------|
| GYM-COACH | 8110 | Fitness guidance | FastAPI (LLM) |
| NUTRITIONIST | 8101 | Nutrition advice | FastAPI (LLM) |
| MEAL-PLANNER | 8102 | Meal planning | FastAPI (LLM) |
| ACADEMIC-GUIDE | 8103 | Learning paths | FastAPI (LLM) |
| EROS | 8104 | Relationship advice | FastAPI (LLM) |

!!! note "Port Note"
    GYM-COACH runs on port 8110 (not 8100) due to a port conflict with supabase-kong-dev.

---

## GYM-COACH - Fitness Guidance

**Port:** 8110 | **Type:** LLM-Powered

GYM-COACH provides personalized workout planning, exercise guidance, and fitness progress tracking.

### Capabilities

- Workout planning and tracking
- Exercise form guidance
- Fitness goal setting
- Progress monitoring
- Exercise alternatives
- Recovery recommendations
- Training program design

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/workout/plan` | POST | Generate workout plan |
| `/workout/log` | POST | Log completed workout |
| `/exercise/guide` | POST | Get exercise guidance |
| `/exercise/alternatives` | POST | Find exercise alternatives |
| `/progress` | GET | Get fitness progress |
| `/goals` | POST | Set fitness goals |
| `/recovery` | POST | Recovery recommendations |

### Example Usage

```bash
# Generate workout plan
curl -X POST http://localhost:8110/workout/plan \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "muscle building",
    "experience_level": "intermediate",
    "days_per_week": 4,
    "equipment": ["barbell", "dumbbells", "cables"],
    "time_per_session": 60
  }'

# Get exercise guidance
curl -X POST http://localhost:8110/exercise/guide \
  -H "Content-Type: application/json" \
  -d '{
    "exercise": "deadlift",
    "concerns": ["lower back pain history"]
  }'
```

### Training Programs

| Program | Duration | Focus |
|---------|----------|-------|
| Strength | 8-12 weeks | Compound movements, progressive overload |
| Hypertrophy | 6-10 weeks | Volume, time under tension |
| Endurance | 4-8 weeks | Cardio, high rep work |
| Flexibility | Ongoing | Mobility, stretching |

---

## NUTRITIONIST - Nutrition Advice

**Port:** 8101 | **Type:** LLM-Powered

NUTRITIONIST provides personalized nutrition guidance, macro tracking, and dietary recommendations.

### Capabilities

- Nutrition advice and planning
- Macro/micronutrient tracking
- Diet recommendations
- Supplement guidance
- Food analysis
- Calorie calculations
- Dietary restriction support

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/analyze/meal` | POST | Analyze meal nutrition |
| `/calculate/macros` | POST | Calculate daily macros |
| `/recommend/diet` | POST | Diet recommendations |
| `/supplements` | POST | Supplement guidance |
| `/food/lookup` | POST | Food nutrition lookup |
| `/plan/daily` | POST | Daily nutrition plan |

### Example Usage

```bash
# Calculate macros
curl -X POST http://localhost:8101/calculate/macros \
  -H "Content-Type: application/json" \
  -d '{
    "weight_kg": 80,
    "height_cm": 180,
    "age": 35,
    "activity_level": "moderate",
    "goal": "muscle_gain"
  }'

# Analyze meal
curl -X POST http://localhost:8101/analyze/meal \
  -H "Content-Type: application/json" \
  -d '{
    "foods": [
      {"name": "chicken breast", "amount": "200g"},
      {"name": "rice", "amount": "150g"},
      {"name": "broccoli", "amount": "100g"}
    ]
  }'
```

### Dietary Profiles

| Profile | Description |
|---------|-------------|
| Balanced | Standard macros for general health |
| Keto | High fat, low carb |
| High Protein | For muscle building |
| Plant-Based | Vegan/vegetarian options |
| Low Carb | Reduced carbohydrate intake |

---

## MEAL-PLANNER - Meal Planning

**Port:** 8102 | **Type:** LLM-Powered

MEAL-PLANNER creates weekly meal plans, generates recipes, and produces grocery lists.

### Capabilities

- Weekly meal planning
- Recipe suggestions
- Grocery list generation
- Calorie/nutrition balancing
- Meal prep scheduling
- Budget considerations
- Dietary restriction support

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/plan/weekly` | POST | Generate weekly meal plan |
| `/recipe/suggest` | POST | Suggest recipes |
| `/recipe/generate` | POST | Generate custom recipe |
| `/grocery/list` | POST | Generate grocery list |
| `/prep/schedule` | POST | Meal prep schedule |

### Example Usage

```bash
# Generate weekly meal plan
curl -X POST http://localhost:8102/plan/weekly \
  -H "Content-Type: application/json" \
  -d '{
    "daily_calories": 2200,
    "meals_per_day": 4,
    "dietary_restrictions": ["gluten-free"],
    "cuisine_preferences": ["mediterranean", "asian"],
    "budget": "moderate",
    "prep_time_max": 30
  }'

# Generate grocery list
curl -X POST http://localhost:8102/grocery/list \
  -H "Content-Type: application/json" \
  -d '{
    "meal_plan_id": "plan_123",
    "optimize_for": "cost"
  }'
```

---

## ACADEMIC-GUIDE - Learning Paths

**Port:** 8103 | **Type:** LLM-Powered

ACADEMIC-GUIDE creates personalized learning paths, study plans, and educational recommendations.

### Capabilities

- Learning path recommendations
- Study planning and optimization
- Skill development guidance
- Course recommendations
- Progress tracking
- Resource curation
- Knowledge gap analysis

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/path/create` | POST | Create learning path |
| `/study/plan` | POST | Generate study plan |
| `/courses/recommend` | POST | Recommend courses |
| `/skills/assess` | POST | Skill assessment |
| `/resources` | POST | Curate resources |
| `/progress` | GET | Track learning progress |

### Example Usage

```bash
# Create learning path
curl -X POST http://localhost:8103/path/create \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "become proficient in Python for data science",
    "current_level": "beginner",
    "time_available": "10 hours per week",
    "timeline": "3 months",
    "learning_style": "hands-on"
  }'

# Generate study plan
curl -X POST http://localhost:8103/study/plan \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "machine learning",
    "exam_date": "2026-03-01",
    "available_hours": 20,
    "focus_areas": ["neural networks", "model evaluation"]
  }'
```

### Learning Frameworks

| Framework | Description |
|-----------|-------------|
| Spaced Repetition | Optimized review intervals |
| Feynman Technique | Teach to learn |
| Pomodoro | Time-boxed focus sessions |
| Active Recall | Question-based learning |

---

## EROS - Relationship Advice

**Port:** 8104 | **Type:** LLM-Powered

EROS provides guidance on relationships, dating, and interpersonal communication.

### Capabilities

- Dating advice and coaching
- Relationship guidance
- Communication strategies
- Social skill development
- Conflict resolution
- Profile optimization (dating apps)
- Conversation coaching

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/advice` | POST | Get relationship advice |
| `/communication` | POST | Communication strategies |
| `/profile/review` | POST | Review dating profile |
| `/conversation/coach` | POST | Conversation coaching |
| `/conflict/resolve` | POST | Conflict resolution |

### Example Usage

```bash
# Get dating advice
curl -X POST http://localhost:8104/advice \
  -H "Content-Type: application/json" \
  -d '{
    "situation": "planning a first date",
    "context": "met through mutual friends",
    "goals": ["make good impression", "get to know them"]
  }'

# Communication coaching
curl -X POST http://localhost:8104/communication \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "expressing needs in relationship",
    "challenge": "avoiding conflict",
    "communication_style": "direct"
  }'
```

---

## Integration with ARIA

All Personal Fleet agents integrate with ARIA (the personal AI assistant) for seamless user experience:

```
User → ARIA → Personal Fleet Agent → Response → ARIA → User
```

### Trigger Phrases

| Agent | Example Triggers |
|-------|------------------|
| GYM-COACH | "plan a workout", "exercise form", "fitness goals" |
| NUTRITIONIST | "nutrition advice", "calculate macros", "diet help" |
| MEAL-PLANNER | "meal plan", "recipe ideas", "grocery list" |
| ACADEMIC-GUIDE | "learn Python", "study plan", "course recommendations" |
| EROS | "dating advice", "relationship help", "communication tips" |

### Knowledge Persistence

Personal Fleet agents log insights to `aria_knowledge` for continuity:

```sql
SELECT aria_add_knowledge(
  'personal',
  'Fitness Goal Set',
  'User set goal to lose 10kg by March 2026',
  'gym_coach',
  '{"goal": "weight_loss", "target": "10kg", "deadline": "2026-03-01"}',
  'GYM-COACH',
  'normal'
);
```
