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
