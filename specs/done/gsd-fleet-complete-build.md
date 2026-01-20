# GSD: Complete Fleet Build - Fix All Broken Agents

**Priority:** HIGH
**Estimated Time:** 30-45 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Fix all broken agents so the full fleet can start:
1. Build GYM-COACH from stub to full agent
2. Build ACADEMIC-GUIDE from stub to full agent
3. Fix SCRIBE Dockerfile (broken COPY --from=shared)
4. Add BOMBADIL (nutritionist) to fleet compose
5. Add SAMWISE (meal-planner) to fleet compose
6. Remove AEGIS from Docker (runs via systemd)
7. Start complete fleet

---

## ENVIRONMENT

**Target:** Control plane agents

```
Location: /opt/leveredge/control-plane/agents/
Fleet compose: /opt/leveredge/docker-compose.fleet.yml
```

---

## CURRENT STATE

| Agent | Code | Dockerfile | In Compose | Issue |
|-------|------|------------|------------|-------|
| gym-coach | 1.4KB stub | ❌ | Yes | Needs full build |
| academic-guide | 1.4KB stub | ❌ | Yes | Needs full build |
| scribe | 22KB ✅ | ⚠️ Broken | Yes | Bad COPY --from |
| bombadil (nutritionist) | 43KB ✅ | ✅ | ❌ No | Add to compose |
| samwise (meal-planner) | 38KB ✅ | ✅ | ❌ No | Add to compose |
| aegis | 57KB ✅ | ❌ | Yes | Uses systemd |

---

## PHASE 1: BUILD GYM-COACH

Create full agent at `/opt/leveredge/control-plane/agents/gym-coach/`

### 1.1 gym_coach.py (Full Implementation)

```python
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
```

### 1.2 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ /opt/leveredge/control-plane/shared/

# Copy agent
COPY gym_coach.py .

EXPOSE 8230

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8230/health || exit 1

CMD ["uvicorn", "gym_coach:app", "--host", "0.0.0.0", "--port", "8230"]
```

### 1.3 requirements.txt

```
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pydantic>=2.0.0
anthropic>=0.18.0
```

---

## PHASE 2: BUILD ACADEMIC-GUIDE

Create full agent at `/opt/leveredge/control-plane/agents/academic-guide/`

### 2.1 academic_guide.py (Full Implementation)

```python
#!/usr/bin/env python3
"""
ACADEMIC-GUIDE - Personal Learning & Study Agent
Port: 8231

Your AI tutor and study coach. Explains concepts, creates study plans,
quizzes you, and adapts to your learning style.

Named for the timeless role of the academic mentor who guides students to mastery.
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
    title="ACADEMIC-GUIDE",
    description="Personal Learning & Study Agent",
    version="1.0.0"
)

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
cost_tracker = CostTracker("ACADEMIC-GUIDE") if CostTracker else None

# =============================================================================
# MODELS
# =============================================================================

class LearningStyle(str, Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    READING = "reading_writing"
    KINESTHETIC = "kinesthetic"
    MIXED = "mixed"

class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ExplainRequest(BaseModel):
    topic: str
    context: Optional[str] = None  # What they already know
    learning_style: LearningStyle = LearningStyle.MIXED
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    use_analogies: bool = True

class StudyPlanRequest(BaseModel):
    user_id: str
    subject: str
    goal: str  # "pass exam", "deep understanding", "practical application"
    deadline: Optional[str] = None  # ISO date
    hours_per_week: int = 10
    current_level: DifficultyLevel = DifficultyLevel.BEGINNER

class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 5
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    question_types: List[str] = ["multiple_choice", "short_answer"]

class QuizAnswer(BaseModel):
    quiz_id: str
    answers: Dict[str, str]  # question_id -> answer

class ResourceRequest(BaseModel):
    topic: str
    resource_types: List[str] = ["books", "videos", "courses", "articles"]
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are ACADEMIC-GUIDE, a knowledgeable and patient tutor.

PERSONALITY:
- Patient and encouraging - learning takes time
- Adapts explanations to the student's level
- Uses analogies and real-world examples
- Celebrates understanding, not just correct answers
- Honest about complexity - some things ARE hard

EXPERTISE:
- Breaking down complex topics into digestible pieces
- Multiple explanation approaches for different learning styles
- Socratic method - guiding discovery through questions
- Spaced repetition and effective study techniques
- Connecting new knowledge to existing understanding

TEACHING APPROACH:
1. Assess current understanding
2. Build from known to unknown
3. Use concrete examples before abstractions
4. Check understanding frequently
5. Encourage questions - there are no dumb ones

ADHD-FRIENDLY:
- Chunk information into small pieces
- Use clear structure and formatting
- Provide frequent checkpoints
- Make it engaging, not boring
- Connect to real-world applications

You adapt your teaching style based on the user's preferences and responses.
"""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def call_llm(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """Call Claude for educational content"""
    if not client:
        return "API key not configured. Please set ANTHROPIC_API_KEY."
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    
    if cost_tracker:
        await cost_tracker.log_usage(
            agent_name="ACADEMIC-GUIDE",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            operation="teaching"
        )
    
    return response.content[0].text

async def log_event(event_type: str, data: dict):
    """Log to Event Bus"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={"event_type": event_type, "source": "ACADEMIC-GUIDE", "data": data}
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
        "agent": "ACADEMIC-GUIDE",
        "port": 8231,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/explain")
async def explain_topic(request: ExplainRequest):
    """Explain a topic in an accessible way"""
    style_hints = {
        LearningStyle.VISUAL: "Use diagrams, mental images, and visual analogies.",
        LearningStyle.AUDITORY: "Use rhythm, memorable phrases, and verbal explanations.",
        LearningStyle.READING: "Use structured text, definitions, and written examples.",
        LearningStyle.KINESTHETIC: "Use hands-on examples, physical analogies, and step-by-step processes.",
        LearningStyle.MIXED: "Use a variety of approaches."
    }
    
    prompt = f"""Explain: {request.topic}

Student context: {request.context or 'No prior knowledge specified'}
Difficulty level: {request.difficulty.value}
Learning style preference: {style_hints[request.learning_style]}
Use analogies: {'Yes, use relatable analogies' if request.use_analogies else 'Focus on direct explanation'}

Structure your explanation with:
1. One-sentence summary (the core idea)
2. Main explanation (appropriate to level)
3. {'A relatable analogy' if request.use_analogies else 'A concrete example'}
4. Common misconceptions to avoid
5. A check-for-understanding question
"""
    
    explanation = await call_llm(prompt)
    await log_event("topic_explained", {"topic": request.topic, "level": request.difficulty.value})
    
    return {
        "topic": request.topic,
        "explanation": explanation,
        "difficulty": request.difficulty.value,
        "learning_style": request.learning_style.value
    }

@app.post("/study-plan")
async def create_study_plan(request: StudyPlanRequest):
    """Create a personalized study plan"""
    deadline_info = f"Deadline: {request.deadline}" if request.deadline else "No specific deadline"
    
    prompt = f"""Create a study plan for:

Subject: {request.subject}
Goal: {request.goal}
Current level: {request.current_level.value}
Available time: {request.hours_per_week} hours per week
{deadline_info}

Provide:
1. Weekly breakdown of topics
2. Specific learning objectives for each week
3. Recommended resources for each topic
4. Practice exercises or projects
5. Milestones to track progress
6. Tips for maintaining motivation

Make it realistic and achievable. Account for review time."""
    
    plan = await call_llm(prompt)
    await log_event("study_plan_created", {"user_id": request.user_id, "subject": request.subject})
    
    return {
        "user_id": request.user_id,
        "subject": request.subject,
        "plan": plan,
        "hours_per_week": request.hours_per_week,
        "created_at": datetime.utcnow().isoformat()
    }

@app.post("/quiz")
async def generate_quiz(request: QuizRequest):
    """Generate a quiz on a topic"""
    prompt = f"""Create a {request.num_questions}-question quiz on: {request.topic}

Difficulty: {request.difficulty.value}
Question types to include: {', '.join(request.question_types)}

Format each question as:
Q1. [Question text]
Type: [multiple_choice/short_answer/true_false]
Options: [A, B, C, D if multiple choice]
Answer: [correct answer]
Explanation: [why this is correct]

Make questions that test understanding, not just memorization."""
    
    quiz = await call_llm(prompt)
    quiz_id = f"quiz_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "quiz_id": quiz_id,
        "topic": request.topic,
        "difficulty": request.difficulty.value,
        "quiz": quiz,
        "num_questions": request.num_questions
    }

@app.post("/simplify")
async def simplify_concept(topic: str, target_age: int = 12):
    """Explain something as if to a specific age"""
    prompt = f"""Explain {topic} as if you're talking to a {target_age}-year-old.

Use:
- Simple vocabulary
- Relatable examples from their world
- Short sentences
- No jargon

But don't be condescending - kids are smart, they just lack context."""
    
    simplified = await call_llm(prompt)
    
    return {
        "topic": topic,
        "target_age": target_age,
        "explanation": simplified
    }

@app.post("/resources")
async def recommend_resources(request: ResourceRequest):
    """Recommend learning resources"""
    prompt = f"""Recommend learning resources for: {request.topic}

Level: {request.difficulty.value}
Types requested: {', '.join(request.resource_types)}

For each resource, provide:
- Name/Title
- Type (book/video/course/etc)
- Why it's good for this level
- Estimated time investment
- Free or paid

Prioritize quality over quantity. 3-5 excellent resources beat 20 mediocre ones."""
    
    resources = await call_llm(prompt)
    
    return {
        "topic": request.topic,
        "difficulty": request.difficulty.value,
        "resources": resources
    }

@app.post("/eli5")
async def explain_like_im_five(topic: str):
    """Explain Like I'm 5"""
    prompt = f"""Explain {topic} like I'm 5 years old.

Use:
- Very simple words
- Fun analogies (toys, candy, playground)
- Maybe a little story
- Keep it SHORT (under 100 words)

Make it actually understandable to a child."""
    
    explanation = await call_llm(prompt)
    
    return {
        "topic": topic,
        "explanation": explanation,
        "style": "ELI5"
    }

@app.get("/technique/{name}")
async def study_technique(name: str):
    """Get info on a study technique"""
    techniques = [
        "pomodoro", "spaced_repetition", "feynman", "active_recall",
        "mind_mapping", "cornell_notes", "interleaving", "elaboration"
    ]
    
    if name not in techniques:
        raise HTTPException(400, f"Unknown technique. Available: {techniques}")
    
    prompt = f"""Explain the {name.replace('_', ' ')} study technique:

1. What it is (one sentence)
2. How to do it (step by step)
3. Why it works (the science)
4. Best used for (what types of learning)
5. Common mistakes to avoid
6. Tools that help (apps, methods)"""
    
    info = await call_llm(prompt)
    
    return {
        "technique": name,
        "info": info
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8231)
```

### 2.2 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ /opt/leveredge/control-plane/shared/

# Copy agent
COPY academic_guide.py .

EXPOSE 8231

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8231/health || exit 1

CMD ["uvicorn", "academic_guide:app", "--host", "0.0.0.0", "--port", "8231"]
```

### 2.3 requirements.txt

```
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pydantic>=2.0.0
anthropic>=0.18.0
```

---

## PHASE 3: FIX SCRIBE DOCKERFILE

Replace `/opt/leveredge/control-plane/agents/scribe/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules (fixed - no COPY --from)
COPY shared/ /opt/leveredge/control-plane/shared/

# Copy agent
COPY scribe.py .

EXPOSE 8301

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8301/health || exit 1

CMD ["uvicorn", "scribe:app", "--host", "0.0.0.0", "--port", "8301"]
```

Create shared symlink if needed:
```bash
cd /opt/leveredge/control-plane/agents/scribe
ln -sf ../../shared shared
```

---

## PHASE 4: UPDATE DOCKER-COMPOSE.FLEET.YML

Add these services and fix broken ones:

```yaml
# Add to services section:

  # PERSONAL LIFESTYLE AGENTS
  bombadil:
    build:
      context: ./control-plane/agents/bombadil
      dockerfile: Dockerfile
    container_name: leveredge-bombadil
    ports:
      - "8232:8232"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - EVENT_BUS_URL=http://event-bus:8099
      - SUPABASE_URL=${DEV_SUPABASE_URL}
      - SUPABASE_ANON_KEY=${DEV_SUPABASE_ANON_KEY}
    networks:
      - leveredge-network
    restart: unless-stopped
    profiles:
      - all
      - personal

  samwise:
    build:
      context: ./control-plane/agents/samwise
      dockerfile: Dockerfile
    container_name: leveredge-samwise
    ports:
      - "8233:8233"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - EVENT_BUS_URL=http://event-bus:8099
      - SUPABASE_URL=${DEV_SUPABASE_URL}
      - SUPABASE_ANON_KEY=${DEV_SUPABASE_ANON_KEY}
    networks:
      - leveredge-network
    restart: unless-stopped
    profiles:
      - all
      - personal

  gym-coach:
    build:
      context: ./control-plane/agents/gym-coach
      dockerfile: Dockerfile
    container_name: leveredge-gym-coach
    ports:
      - "8230:8230"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - EVENT_BUS_URL=http://event-bus:8099
      - SUPABASE_URL=${DEV_SUPABASE_URL}
      - SUPABASE_ANON_KEY=${DEV_SUPABASE_ANON_KEY}
    networks:
      - leveredge-network
    restart: unless-stopped
    profiles:
      - all
      - personal

  academic-guide:
    build:
      context: ./control-plane/agents/academic-guide
      dockerfile: Dockerfile
    container_name: leveredge-academic-guide
    ports:
      - "8231:8231"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - EVENT_BUS_URL=http://event-bus:8099
      - SUPABASE_URL=${DEV_SUPABASE_URL}
      - SUPABASE_ANON_KEY=${DEV_SUPABASE_ANON_KEY}
    networks:
      - leveredge-network
    restart: unless-stopped
    profiles:
      - all
      - personal
```

**Remove or comment out aegis from Docker** (it runs via systemd):
```yaml
#  aegis:
#    ... (comment out entire service)
```

---

## PHASE 5: FIX PORT NUMBERS IN EXISTING AGENTS

Check bombadil and samwise use correct ports:

```bash
# bombadil/nutritionist.py should have port 8232
grep -n "8232\|port" /opt/leveredge/control-plane/agents/bombadil/nutritionist.py | head -5

# samwise/meal_planner.py should have port 8233
grep -n "8233\|port" /opt/leveredge/control-plane/agents/samwise/meal_planner.py | head -5
```

Update if needed to match compose file.

---

## PHASE 6: CREATE SHARED SYMLINKS

Each agent needs access to shared modules:

```bash
cd /opt/leveredge/control-plane/agents

# Create symlinks for agents that need them
for agent in gym-coach academic-guide scribe; do
    if [ ! -L "$agent/shared" ]; then
        ln -sf ../../shared "$agent/shared"
    fi
done
```

---

## PHASE 7: START FLEET

```bash
cd /opt/leveredge

# Build and start everything
./fleet-start.sh --build

# Or specific groups
docker compose -f docker-compose.fleet.yml --env-file .env.fleet up -d --build event-bus lcis-librarian lcis-oracle
docker compose -f docker-compose.fleet.yml --env-file .env.fleet up -d --build gym-coach academic-guide bombadil samwise scribe
```

---

## VERIFICATION

```bash
# Check all containers running
docker ps --format "table {{.Names}}\t{{.Status}}" | grep leveredge

# Test health endpoints
curl http://localhost:8230/health  # gym-coach
curl http://localhost:8231/health  # academic-guide
curl http://localhost:8232/health  # bombadil (nutritionist)
curl http://localhost:8233/health  # samwise (meal-planner)
curl http://localhost:8301/health  # scribe
curl http://localhost:8050/health  # lcis-librarian
curl http://localhost:8052/health  # lcis-oracle

# Check AEGIS via systemd
sudo systemctl status leveredge-aegis
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-fleet-complete-build.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Fleet complete build: gym-coach, academic-guide built from stubs. scribe Dockerfile fixed. bombadil+samwise added to compose. Full fleet operational.",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "fleet", "agents", "docker"]
  }'
```

### 3. Update AGENT-REGISTRY.md
Add new agents with correct ports.

### 4. Git Commit
```bash
git add -A
git commit -m "feat: Complete fleet build - all agents operational

- Built gym-coach (8230) from stub to full agent
- Built academic-guide (8231) from stub to full agent  
- Fixed scribe Dockerfile (removed broken COPY --from)
- Added bombadil/nutritionist (8232) to fleet
- Added samwise/meal-planner (8233) to fleet
- Removed aegis from Docker (uses systemd)
- Fleet now starts successfully

Personal lifestyle agents fully operational."
```

---

## ROLLBACK

```bash
# Stop fleet
docker compose -f docker-compose.fleet.yml down

# Revert changes
git checkout HEAD~1 -- control-plane/agents/
git checkout HEAD~1 -- docker-compose.fleet.yml
```

---

## AGENT SUMMARY AFTER BUILD

| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| gym-coach | 8230 | Fitness training | NEW |
| academic-guide | 8231 | Learning/study | NEW |
| bombadil | 8232 | Nutrition | ADDED |
| samwise | 8233 | Meal planning | ADDED |
| scribe | 8301 | Documentation | FIXED |
| aegis | 8012 | Credentials | SYSTEMD |

---

*No agent left behind. Full fleet or nothing.*
