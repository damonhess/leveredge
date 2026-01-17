#!/usr/bin/env python3
"""
ACADEMIC GUIDE - AI-Powered Learning & Skills Development Agent
Port: 8103

Named after Athena, the Greek goddess of wisdom and learning.
ACADEMIC GUIDE illuminates the path to mastery, tracking skills,
creating personalized learning paths, managing certifications,
and implementing spaced repetition for optimal knowledge retention.

TEAM INTEGRATION:
- Time-aware (knows current date, week number)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs learning milestones to unified memory

PHASE 1 CAPABILITIES:
- Skills tracking with proficiency levels 1-10
- Basic spaced repetition (SM-2 algorithm)
- Learning resource catalog
- Certification tracking with expiration alerts
- Progress monitoring
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import anthropic
import math

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="ACADEMIC GUIDE",
    description="AI-Powered Learning & Skills Development Agent",
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
    "CHRONOS": "http://chronos:8010",
    "HERMES": "http://hermes:8014",
    "CHIRON": "http://chiron:8017",
    "EVENT_BUS": EVENT_BUS_URL
}

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("ACADEMIC_GUIDE")

# =============================================================================
# PROFICIENCY SCALE
# =============================================================================

PROFICIENCY_SCALE = {
    1: {"name": "Beginner", "description": "Basic awareness", "evidence": "Completed intro course"},
    2: {"name": "Beginner+", "description": "Familiar with concepts", "evidence": "Multiple intro resources"},
    3: {"name": "Novice", "description": "Can follow instructions", "evidence": "Small project completed"},
    4: {"name": "Novice+", "description": "Basic independent work", "evidence": "Several small projects"},
    5: {"name": "Intermediate", "description": "Independent work", "evidence": "Multiple projects, some complexity"},
    6: {"name": "Intermediate+", "description": "Solid practitioner", "evidence": "Complex projects completed"},
    7: {"name": "Advanced", "description": "Teaches others", "evidence": "Complex projects, mentoring"},
    8: {"name": "Advanced+", "description": "Deep expertise", "evidence": "Industry recognition beginning"},
    9: {"name": "Expert", "description": "Industry recognized", "evidence": "Publications, speaking"},
    10: {"name": "Master", "description": "Thought leader", "evidence": "Publications, speaking, leadership"}
}

SKILL_DOMAINS = [
    "technical",
    "soft_skills",
    "creative",
    "business",
    "language",
    "health",
    "finance",
    "other"
]

RESOURCE_TYPES = [
    "course",
    "book",
    "tutorial",
    "video",
    "workshop",
    "bootcamp",
    "podcast",
    "article"
]

# =============================================================================
# SPACED REPETITION (SM-2 ALGORITHM)
# =============================================================================

class SM2:
    """SuperMemo 2 Algorithm for spaced repetition scheduling"""

    # Quality ratings (0-5)
    QUALITY_COMPLETE_BLACKOUT = 0
    QUALITY_INCORRECT_REMEMBERED = 1
    QUALITY_INCORRECT_EASY_RECALL = 2
    QUALITY_CORRECT_DIFFICULT = 3
    QUALITY_CORRECT_HESITATION = 4
    QUALITY_PERFECT = 5

    @staticmethod
    def calculate_next_review(
        quality: int,
        repetitions: int,
        ease_factor: float,
        interval_days: int
    ) -> dict:
        """
        Calculate next review date using SM-2 algorithm.

        Args:
            quality: Response quality 0-5 (5 = perfect)
            repetitions: Number of times reviewed
            ease_factor: Current ease factor (1.3 - 3.0)
            interval_days: Current interval in days

        Returns:
            dict with new_interval, new_ease_factor, new_repetitions
        """
        # Clamp quality to valid range
        quality = max(0, min(5, quality))

        # Calculate new ease factor
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        # Clamp ease factor to valid range
        new_ease_factor = max(1.3, min(3.0, new_ease_factor))

        # If quality < 3, reset (item not learned)
        if quality < 3:
            new_repetitions = 0
            new_interval = 1
        else:
            new_repetitions = repetitions + 1

            if new_repetitions == 1:
                new_interval = 1
            elif new_repetitions == 2:
                new_interval = 6
            else:
                new_interval = int(interval_days * new_ease_factor)

        # Cap maximum interval at 365 days
        new_interval = min(365, new_interval)

        return {
            "new_interval": new_interval,
            "new_ease_factor": round(new_ease_factor, 2),
            "new_repetitions": new_repetitions,
            "next_review_date": (datetime.now() + timedelta(days=new_interval)).isoformat()
        }

    @staticmethod
    def get_quality_description(quality: int) -> str:
        """Get human-readable description for quality rating"""
        descriptions = {
            0: "Complete blackout - no recall",
            1: "Incorrect but remembered after seeing answer",
            2: "Incorrect but easy to recall once reminded",
            3: "Correct with serious difficulty",
            4: "Correct after some hesitation",
            5: "Perfect response"
        }
        return descriptions.get(quality, "Unknown")

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
        "week_number": now.isocalendar()[1],
        "month": now.strftime("%B"),
        "year": now.year
    }

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(learning_context: dict) -> str:
    """Build the ACADEMIC GUIDE system prompt with current learning context"""

    time_ctx = get_time_context()

    return f"""You are ACADEMIC GUIDE - Personal Learning Coach for LeverEdge AI.

Named after Athena, the Greek goddess of wisdom and learning, you illuminate the path to mastery and guide learners toward their goals.

## TIME AWARENESS
- Current: {time_ctx['day_of_week']}, {time_ctx['current_date']} at {time_ctx['current_time']}
- Week of Year: {time_ctx['week_number']}

## YOUR IDENTITY
You are the learning brain of LeverEdge. You track skills, create personalized learning paths, monitor progress, manage certifications, and optimize retention through spaced repetition.

## CURRENT LEARNING STATUS
- Active Skills: {learning_context.get('skill_count', 0)}
- Learning Paths: {learning_context.get('path_count', 0)} active
- Courses in Progress: {learning_context.get('courses_in_progress', 0)}
- Certifications: {learning_context.get('cert_count', 0)} ({learning_context.get('expiring_soon', 0)} expiring soon)
- Reviews Due Today: {learning_context.get('reviews_due', 0)}

## YOUR CAPABILITIES

### Skills Tracking
- Track skills across domains (technical, soft skills, creative, business)
- Assess proficiency levels 1-10 with clear rubrics
- Link evidence (projects, certificates, code samples)
- Detect skill decay and recommend refreshers
- Generate skill radar visualizations

### Learning Paths
- Create goal-oriented learning journeys
- Map prerequisites and dependencies
- Estimate completion timelines
- Track milestone progress
- Adapt paths based on progress

### Course Progress
- Monitor all learning resources
- Track completion percentages
- Log time spent learning
- Detect abandoned courses
- Generate completion reports

### Certification Management
- Track all professional credentials
- Alert before expirations (90/60/30/7 days)
- Monitor continuing education credits
- Store verification links
- Track renewal costs

### Spaced Repetition
- Schedule optimal review sessions using SM-2 algorithm
- Adjust intervals based on performance
- Generate daily review lists
- Track retention metrics

## LEARNING PHILOSOPHY
- Consistency beats intensity
- Spaced practice beats cramming
- Active recall beats passive review
- Goals should be specific and measurable
- Progress should be celebrated

## TEAM COORDINATION
- Log insights -> ARIA via Unified Memory
- Publish events -> Event Bus
- Schedule reminders -> CHRONOS (if available)
- Send notifications -> HERMES (if available)

## RESPONSE FORMAT
For learning recommendations:
1. Current status assessment
2. Recommended next steps
3. Time estimate
4. Resources needed
5. Expected outcomes

For skill assessment:
1. Current proficiency level
2. Evidence reviewed
3. Growth areas identified
4. Recommended practice
5. Timeline for improvement

## YOUR MISSION
Guide every learner toward mastery.
Make learning efficient and enjoyable.
Never let a skill atrophy or a certification lapse.
Celebrate progress and encourage consistency.
"""

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

# Skills Models
class SkillCreate(BaseModel):
    name: str
    domain: str = "technical"
    proficiency_level: int = Field(ge=1, le=10, default=1)
    notes: Optional[str] = None
    evidence: Optional[List[Dict[str, Any]]] = []

class SkillUpdate(BaseModel):
    proficiency_level: Optional[int] = Field(ge=1, le=10, default=None)
    notes: Optional[str] = None
    last_practiced: Optional[str] = None

class SkillPractice(BaseModel):
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    project: Optional[str] = None

class SkillEvidence(BaseModel):
    type: str  # project, certificate, code_sample, course_completion
    url: Optional[str] = None
    description: str
    date: Optional[str] = None

# Learning Path Models
class LearningPathCreate(BaseModel):
    name: str
    goal: str
    target_date: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = []

class LearningPathUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    target_date: Optional[str] = None
    status: Optional[str] = None  # active, paused, completed, abandoned

class PathGenerateRequest(BaseModel):
    goal: str
    current_skills: Optional[List[str]] = []
    time_available_hours_per_week: Optional[int] = 10
    target_date: Optional[str] = None

# Learning Resource Models
class ResourceCreate(BaseModel):
    title: str
    type: str  # course, book, tutorial, video, workshop, bootcamp
    url: Optional[str] = None
    author: Optional[str] = None
    platform: Optional[str] = None
    duration_hours: Optional[float] = None
    difficulty: Optional[str] = "intermediate"
    topics: Optional[List[str]] = []
    cost: Optional[float] = 0.0

class ResourceSearch(BaseModel):
    query: Optional[str] = None
    type: Optional[str] = None
    difficulty: Optional[str] = None
    topics: Optional[List[str]] = []

# Progress Models
class ProgressCreate(BaseModel):
    resource_id: str
    notes: Optional[str] = None

class ProgressUpdate(BaseModel):
    percent_complete: Optional[float] = Field(ge=0, le=100, default=None)
    time_spent_hours: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # not_started, in_progress, completed, abandoned

# Certification Models
class CertificationCreate(BaseModel):
    name: str
    issuer: str
    earned_date: str
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    verification_url: Optional[str] = None
    cost: Optional[float] = None
    renewal_cost: Optional[float] = None
    ce_credits_required: Optional[int] = None

class CertificationUpdate(BaseModel):
    expiry_date: Optional[str] = None
    ce_credits_earned: Optional[int] = None
    status: Optional[str] = None  # active, expired, revoked, pending_renewal
    verification_url: Optional[str] = None

# Review Models
class ReviewCreate(BaseModel):
    topic: str
    skill_id: Optional[str] = None
    notes: Optional[str] = None

class ReviewComplete(BaseModel):
    quality: int = Field(ge=0, le=5)  # SM-2 quality rating
    notes: Optional[str] = None

# Chat Models
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = {}
    session_id: Optional[str] = None

# =============================================================================
# IN-MEMORY STORAGE (Phase 1 - will be replaced with database)
# =============================================================================

# Temporary in-memory storage for Phase 1
_skills_store: Dict[str, Dict] = {}
_paths_store: Dict[str, Dict] = {}
_resources_store: Dict[str, Dict] = {}
_progress_store: Dict[str, Dict] = {}
_certs_store: Dict[str, Dict] = {}
_reviews_store: Dict[str, Dict] = {}

def generate_id() -> str:
    """Generate a simple unique ID"""
    import uuid
    return str(uuid.uuid4())

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
                    "event_type": f"learn.{event_type}",
                    "source": "ACADEMIC_GUIDE",
                    "data": data,
                    "timestamp": time_ctx['current_datetime']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[ACADEMIC_GUIDE] Event publish failed: {e}")

async def store_memory(memory_type: str, content: str, category: str, tags: List[str] = None):
    """Store learning milestone in unified memory"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/aria_add_knowledge",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "p_category": category,
                    "p_title": f"Learning: {content[:50]}...",
                    "p_content": content,
                    "p_subcategory": "academic-guide",
                    "p_source": "academic-guide",
                    "p_importance": "normal"
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"[ACADEMIC_GUIDE] Memory store failed: {e}")

# =============================================================================
# ARIA TOOLS STUBS
# =============================================================================

ARIA_TOOLS = [
    {
        "name": "learn.track_skill",
        "description": "Update skill proficiency level",
        "parameters": {
            "skill_name": "string",
            "domain": "string",
            "proficiency_level": "integer (1-10)",
            "notes": "string (optional)"
        }
    },
    {
        "name": "learn.next_lesson",
        "description": "Get recommendation for what to learn next",
        "parameters": {
            "goal": "string (optional)",
            "time_available": "integer (minutes, optional)"
        }
    },
    {
        "name": "learn.progress",
        "description": "Show learning progress summary",
        "parameters": {
            "period": "string (week, month, year, all)",
            "domain": "string (optional)"
        }
    },
    {
        "name": "learn.due_reviews",
        "description": "Get topics that need review today",
        "parameters": {
            "limit": "integer (optional, default 10)"
        }
    },
    {
        "name": "learn.add_cert",
        "description": "Add a new certification",
        "parameters": {
            "name": "string",
            "issuer": "string",
            "earned_date": "date",
            "expiry_date": "date (optional)",
            "credential_id": "string (optional)"
        }
    }
]

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, learning_context: dict = None) -> str:
    """Call Claude API with learning context"""
    if not client:
        return "LLM not configured - ANTHROPIC_API_KEY not set"

    try:
        context = learning_context or get_learning_summary()
        system_prompt = build_system_prompt(context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="ACADEMIC_GUIDE",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"context": "learning_chat"}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

def get_learning_summary() -> dict:
    """Get current learning summary for context"""
    now = datetime.now()

    # Count reviews due today
    reviews_due = 0
    for review in _reviews_store.values():
        next_review = review.get("next_review")
        if next_review:
            review_date = datetime.fromisoformat(next_review)
            if review_date.date() <= now.date():
                reviews_due += 1

    # Count expiring certifications (next 30 days)
    expiring_soon = 0
    for cert in _certs_store.values():
        expiry = cert.get("expiry_date")
        if expiry:
            expiry_date = datetime.fromisoformat(expiry).date()
            days_until = (expiry_date - now.date()).days
            if 0 <= days_until <= 30:
                expiring_soon += 1

    # Count in-progress courses
    in_progress = sum(1 for p in _progress_store.values() if p.get("status") == "in_progress")

    return {
        "skill_count": len(_skills_store),
        "path_count": sum(1 for p in _paths_store.values() if p.get("status") == "active"),
        "courses_in_progress": in_progress,
        "cert_count": len(_certs_store),
        "expiring_soon": expiring_soon,
        "reviews_due": reviews_due
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
        "agent": "ACADEMIC_GUIDE",
        "role": "Learning & Skills Development",
        "port": 8103,
        "current_time": time_ctx['current_datetime'],
        "week_number": time_ctx['week_number']
    }

@app.get("/status")
async def status():
    """Get current learning status overview"""
    time_ctx = get_time_context()
    summary = get_learning_summary()

    return {
        "agent": "ACADEMIC_GUIDE",
        "timestamp": time_ctx['current_datetime'],
        "summary": summary,
        "features": {
            "skills_tracking": True,
            "learning_paths": True,
            "spaced_repetition": True,
            "certification_management": True,
            "ai_recommendations": bool(client)
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    summary = get_learning_summary()

    metrics_text = f"""# HELP academic_guide_skills_total Total number of tracked skills
# TYPE academic_guide_skills_total gauge
academic_guide_skills_total {summary['skill_count']}

# HELP academic_guide_paths_active Active learning paths
# TYPE academic_guide_paths_active gauge
academic_guide_paths_active {summary['path_count']}

# HELP academic_guide_courses_in_progress Courses currently in progress
# TYPE academic_guide_courses_in_progress gauge
academic_guide_courses_in_progress {summary['courses_in_progress']}

# HELP academic_guide_certs_total Total certifications
# TYPE academic_guide_certs_total gauge
academic_guide_certs_total {summary['cert_count']}

# HELP academic_guide_certs_expiring Certifications expiring in 30 days
# TYPE academic_guide_certs_expiring gauge
academic_guide_certs_expiring {summary['expiring_soon']}

# HELP academic_guide_reviews_due Reviews due today
# TYPE academic_guide_reviews_due gauge
academic_guide_reviews_due {summary['reviews_due']}
"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=metrics_text, media_type="text/plain")

# =============================================================================
# SKILLS ENDPOINTS
# =============================================================================

@app.get("/skills")
async def list_skills(domain: Optional[str] = None):
    """List all user skills, optionally filtered by domain"""
    skills = list(_skills_store.values())
    if domain:
        skills = [s for s in skills if s.get("domain") == domain]
    return {"skills": skills, "count": len(skills)}

@app.post("/skills")
async def create_skill(skill: SkillCreate):
    """Add a new skill"""
    skill_id = generate_id()
    now = datetime.now().isoformat()

    skill_data = {
        "id": skill_id,
        "name": skill.name,
        "domain": skill.domain,
        "proficiency_level": skill.proficiency_level,
        "notes": skill.notes,
        "evidence": skill.evidence or [],
        "last_practiced": now,
        "created_at": now,
        "updated_at": now
    }

    _skills_store[skill_id] = skill_data

    # Publish event
    await publish_event("skill.created", {
        "skill_id": skill_id,
        "name": skill.name,
        "domain": skill.domain,
        "proficiency_level": skill.proficiency_level
    })

    # Store in memory
    await store_memory(
        "fact",
        f"New skill tracked: {skill.name} ({skill.domain}) at level {skill.proficiency_level}",
        "skills"
    )

    return skill_data

@app.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    """Get skill details"""
    if skill_id not in _skills_store:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _skills_store[skill_id]

@app.put("/skills/{skill_id}")
async def update_skill(skill_id: str, update: SkillUpdate):
    """Update skill"""
    if skill_id not in _skills_store:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills_store[skill_id]
    old_level = skill["proficiency_level"]

    if update.proficiency_level is not None:
        skill["proficiency_level"] = update.proficiency_level
    if update.notes is not None:
        skill["notes"] = update.notes
    if update.last_practiced is not None:
        skill["last_practiced"] = update.last_practiced

    skill["updated_at"] = datetime.now().isoformat()

    # Publish event if level changed
    if update.proficiency_level and update.proficiency_level != old_level:
        await publish_event("skill.updated", {
            "skill_id": skill_id,
            "name": skill["name"],
            "old_level": old_level,
            "new_level": update.proficiency_level
        })

        await store_memory(
            "fact",
            f"{skill['name']} skill increased from level {old_level} to level {update.proficiency_level}",
            "skills"
        )

    return skill

@app.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str):
    """Remove skill"""
    if skill_id not in _skills_store:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills_store.pop(skill_id)
    return {"deleted": True, "skill": skill}

@app.post("/skills/{skill_id}/practice")
async def log_practice(skill_id: str, practice: SkillPractice):
    """Log practice session for a skill"""
    if skill_id not in _skills_store:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills_store[skill_id]
    skill["last_practiced"] = datetime.now().isoformat()
    skill["updated_at"] = skill["last_practiced"]

    # Add practice to notes if provided
    if practice.notes:
        existing_notes = skill.get("notes") or ""
        skill["notes"] = f"{existing_notes}\n[{skill['last_practiced'][:10]}] {practice.notes}".strip()

    await publish_event("skill.practiced", {
        "skill_id": skill_id,
        "name": skill["name"],
        "duration_minutes": practice.duration_minutes
    })

    return {"message": "Practice logged", "skill": skill}

@app.post("/skills/{skill_id}/evidence")
async def add_evidence(skill_id: str, evidence: SkillEvidence):
    """Add evidence to skill"""
    if skill_id not in _skills_store:
        raise HTTPException(status_code=404, detail="Skill not found")

    skill = _skills_store[skill_id]
    evidence_data = {
        "type": evidence.type,
        "url": evidence.url,
        "description": evidence.description,
        "date": evidence.date or datetime.now().isoformat()[:10]
    }

    skill["evidence"].append(evidence_data)
    skill["updated_at"] = datetime.now().isoformat()

    return {"message": "Evidence added", "skill": skill}

@app.get("/skills/domains")
async def list_domains():
    """List available skill domains"""
    return {
        "domains": SKILL_DOMAINS,
        "proficiency_scale": PROFICIENCY_SCALE
    }

@app.get("/skills/radar")
async def get_skill_radar():
    """Get skill radar chart data"""
    radar_data = {}
    for domain in SKILL_DOMAINS:
        domain_skills = [s for s in _skills_store.values() if s.get("domain") == domain]
        if domain_skills:
            avg_level = sum(s["proficiency_level"] for s in domain_skills) / len(domain_skills)
            radar_data[domain] = {
                "average_level": round(avg_level, 1),
                "skill_count": len(domain_skills),
                "top_skill": max(domain_skills, key=lambda x: x["proficiency_level"])["name"]
            }
        else:
            radar_data[domain] = {
                "average_level": 0,
                "skill_count": 0,
                "top_skill": None
            }

    return {"radar": radar_data}

@app.get("/skills/stale")
async def get_stale_skills(days: int = 30):
    """Get skills that haven't been practiced recently"""
    cutoff = datetime.now() - timedelta(days=days)
    stale_skills = []

    for skill in _skills_store.values():
        last_practiced = skill.get("last_practiced")
        if last_practiced:
            practiced_date = datetime.fromisoformat(last_practiced)
            if practiced_date < cutoff:
                days_stale = (datetime.now() - practiced_date).days
                stale_skills.append({
                    **skill,
                    "days_since_practice": days_stale
                })

    # Sort by days stale descending
    stale_skills.sort(key=lambda x: x["days_since_practice"], reverse=True)

    return {"stale_skills": stale_skills, "threshold_days": days}

# =============================================================================
# LEARNING PATHS ENDPOINTS
# =============================================================================

@app.get("/paths")
async def list_paths(status: Optional[str] = None):
    """List user learning paths"""
    paths = list(_paths_store.values())
    if status:
        paths = [p for p in paths if p.get("status") == status]
    return {"paths": paths, "count": len(paths)}

@app.post("/paths")
async def create_path(path: LearningPathCreate):
    """Create new learning path"""
    path_id = generate_id()
    now = datetime.now().isoformat()

    path_data = {
        "id": path_id,
        "name": path.name,
        "goal": path.goal,
        "steps": path.steps or [],
        "current_step": 0,
        "status": "active",
        "target_date": path.target_date,
        "created_at": now,
        "updated_at": now,
        "completed_at": None
    }

    _paths_store[path_id] = path_data

    await publish_event("path.created", {
        "path_id": path_id,
        "name": path.name,
        "goal": path.goal
    })

    await store_memory(
        "decision",
        f"Created learning path: {path.name} - Goal: {path.goal}",
        "learning"
    )

    return path_data

@app.get("/paths/{path_id}")
async def get_path(path_id: str):
    """Get path details"""
    if path_id not in _paths_store:
        raise HTTPException(status_code=404, detail="Path not found")
    return _paths_store[path_id]

@app.put("/paths/{path_id}")
async def update_path(path_id: str, update: LearningPathUpdate):
    """Update learning path"""
    if path_id not in _paths_store:
        raise HTTPException(status_code=404, detail="Path not found")

    path = _paths_store[path_id]

    if update.name is not None:
        path["name"] = update.name
    if update.goal is not None:
        path["goal"] = update.goal
    if update.target_date is not None:
        path["target_date"] = update.target_date
    if update.status is not None:
        path["status"] = update.status
        if update.status == "completed":
            path["completed_at"] = datetime.now().isoformat()

    path["updated_at"] = datetime.now().isoformat()

    return path

@app.delete("/paths/{path_id}")
async def delete_path(path_id: str):
    """Delete learning path"""
    if path_id not in _paths_store:
        raise HTTPException(status_code=404, detail="Path not found")

    path = _paths_store.pop(path_id)
    return {"deleted": True, "path": path}

@app.post("/paths/{path_id}/advance")
async def advance_path(path_id: str):
    """Mark current step complete and advance to next"""
    if path_id not in _paths_store:
        raise HTTPException(status_code=404, detail="Path not found")

    path = _paths_store[path_id]
    current = path["current_step"]
    steps = path["steps"]

    if current < len(steps):
        if steps:
            steps[current]["completed"] = True
        path["current_step"] = current + 1

        if path["current_step"] >= len(steps):
            path["status"] = "completed"
            path["completed_at"] = datetime.now().isoformat()

            await publish_event("path.completed", {
                "path_id": path_id,
                "name": path["name"],
                "goal": path["goal"]
            })

    path["updated_at"] = datetime.now().isoformat()

    return path

@app.post("/paths/generate")
async def generate_path(request: PathGenerateRequest):
    """AI-generate learning path from goal (stub)"""
    # Phase 1: Return placeholder - will implement AI generation later
    return {
        "message": "AI path generation coming in Phase 3",
        "goal": request.goal,
        "suggestion": "Create a manual path for now using POST /paths"
    }

@app.get("/paths/recommendations")
async def get_path_recommendations():
    """Get suggested paths based on current skills (stub)"""
    return {
        "message": "Path recommendations coming in Phase 3",
        "current_skills": len(_skills_store)
    }

# =============================================================================
# LEARNING RESOURCES ENDPOINTS
# =============================================================================

@app.get("/resources")
async def list_resources(type: Optional[str] = None, difficulty: Optional[str] = None):
    """List learning resources"""
    resources = list(_resources_store.values())
    if type:
        resources = [r for r in resources if r.get("type") == type]
    if difficulty:
        resources = [r for r in resources if r.get("difficulty") == difficulty]
    return {"resources": resources, "count": len(resources)}

@app.post("/resources")
async def create_resource(resource: ResourceCreate):
    """Add resource to catalog"""
    resource_id = generate_id()
    now = datetime.now().isoformat()

    resource_data = {
        "id": resource_id,
        "title": resource.title,
        "type": resource.type,
        "url": resource.url,
        "author": resource.author,
        "platform": resource.platform,
        "duration_hours": resource.duration_hours,
        "difficulty": resource.difficulty,
        "topics": resource.topics or [],
        "cost": resource.cost or 0.0,
        "created_at": now,
        "updated_at": now
    }

    _resources_store[resource_id] = resource_data

    return resource_data

@app.get("/resources/{resource_id}")
async def get_resource(resource_id: str):
    """Get resource details"""
    if resource_id not in _resources_store:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _resources_store[resource_id]

@app.put("/resources/{resource_id}")
async def update_resource(resource_id: str, resource: ResourceCreate):
    """Update resource"""
    if resource_id not in _resources_store:
        raise HTTPException(status_code=404, detail="Resource not found")

    existing = _resources_store[resource_id]
    existing.update({
        "title": resource.title,
        "type": resource.type,
        "url": resource.url,
        "author": resource.author,
        "platform": resource.platform,
        "duration_hours": resource.duration_hours,
        "difficulty": resource.difficulty,
        "topics": resource.topics or [],
        "cost": resource.cost or 0.0,
        "updated_at": datetime.now().isoformat()
    })

    return existing

@app.get("/resources/search")
async def search_resources(search: ResourceSearch):
    """Search resources by topic/type"""
    resources = list(_resources_store.values())

    if search.query:
        query_lower = search.query.lower()
        resources = [r for r in resources if
                    query_lower in r.get("title", "").lower() or
                    query_lower in " ".join(r.get("topics", [])).lower()]

    if search.type:
        resources = [r for r in resources if r.get("type") == search.type]

    if search.difficulty:
        resources = [r for r in resources if r.get("difficulty") == search.difficulty]

    if search.topics:
        resources = [r for r in resources if
                    any(t in r.get("topics", []) for t in search.topics)]

    return {"resources": resources, "count": len(resources)}

@app.get("/resources/recommended")
async def get_recommended_resources():
    """AI recommendations (stub)"""
    return {
        "message": "AI resource recommendations coming in Phase 3",
        "available_resources": len(_resources_store)
    }

# =============================================================================
# PROGRESS ENDPOINTS
# =============================================================================

@app.get("/progress")
async def list_progress(status: Optional[str] = None):
    """Get all user progress"""
    progress = list(_progress_store.values())
    if status:
        progress = [p for p in progress if p.get("status") == status]
    return {"progress": progress, "count": len(progress)}

@app.post("/progress")
async def start_progress(progress: ProgressCreate):
    """Start tracking a resource"""
    if progress.resource_id not in _resources_store:
        raise HTTPException(status_code=404, detail="Resource not found")

    progress_id = generate_id()
    now = datetime.now().isoformat()

    progress_data = {
        "id": progress_id,
        "resource_id": progress.resource_id,
        "status": "in_progress",
        "percent_complete": 0,
        "started_at": now,
        "completed_at": None,
        "last_activity": now,
        "time_spent_hours": 0,
        "notes": progress.notes,
        "rating": None
    }

    _progress_store[progress_id] = progress_data

    resource = _resources_store[progress.resource_id]
    await publish_event("course.started", {
        "progress_id": progress_id,
        "resource_title": resource["title"]
    })

    return progress_data

@app.get("/progress/{progress_id}")
async def get_progress(progress_id: str):
    """Get progress details"""
    if progress_id not in _progress_store:
        raise HTTPException(status_code=404, detail="Progress not found")
    return _progress_store[progress_id]

@app.put("/progress/{progress_id}")
async def update_progress(progress_id: str, update: ProgressUpdate):
    """Update progress"""
    if progress_id not in _progress_store:
        raise HTTPException(status_code=404, detail="Progress not found")

    progress = _progress_store[progress_id]

    if update.percent_complete is not None:
        progress["percent_complete"] = update.percent_complete
    if update.time_spent_hours is not None:
        progress["time_spent_hours"] = update.time_spent_hours
    if update.notes is not None:
        progress["notes"] = update.notes
    if update.status is not None:
        progress["status"] = update.status
        if update.status == "completed":
            progress["completed_at"] = datetime.now().isoformat()

    progress["last_activity"] = datetime.now().isoformat()

    return progress

@app.post("/progress/{progress_id}/complete")
async def complete_progress(progress_id: str, rating: Optional[float] = None):
    """Mark resource as completed"""
    if progress_id not in _progress_store:
        raise HTTPException(status_code=404, detail="Progress not found")

    progress = _progress_store[progress_id]
    progress["status"] = "completed"
    progress["percent_complete"] = 100
    progress["completed_at"] = datetime.now().isoformat()
    progress["last_activity"] = progress["completed_at"]
    if rating:
        progress["rating"] = rating

    resource = _resources_store.get(progress["resource_id"], {})
    await publish_event("course.completed", {
        "progress_id": progress_id,
        "resource_title": resource.get("title", "Unknown")
    })

    await store_memory(
        "fact",
        f"Completed {resource.get('title', 'course')} - {resource.get('type', 'resource')}",
        "learning"
    )

    return progress

@app.get("/progress/active")
async def get_active_progress():
    """Get in-progress courses"""
    active = [p for p in _progress_store.values() if p.get("status") == "in_progress"]
    return {"active": active, "count": len(active)}

@app.get("/progress/abandoned")
async def get_abandoned_progress(days: int = 30):
    """Get stale/abandoned courses"""
    cutoff = datetime.now() - timedelta(days=days)
    abandoned = []

    for progress in _progress_store.values():
        if progress.get("status") == "in_progress":
            last_activity = progress.get("last_activity")
            if last_activity:
                activity_date = datetime.fromisoformat(last_activity)
                if activity_date < cutoff:
                    days_inactive = (datetime.now() - activity_date).days
                    abandoned.append({
                        **progress,
                        "days_inactive": days_inactive
                    })

    abandoned.sort(key=lambda x: x["days_inactive"], reverse=True)

    return {"abandoned": abandoned, "threshold_days": days}

@app.get("/progress/stats")
async def get_progress_stats():
    """Get learning statistics"""
    total = len(_progress_store)
    completed = sum(1 for p in _progress_store.values() if p.get("status") == "completed")
    in_progress = sum(1 for p in _progress_store.values() if p.get("status") == "in_progress")
    abandoned = sum(1 for p in _progress_store.values() if p.get("status") == "abandoned")

    total_hours = sum(p.get("time_spent_hours", 0) for p in _progress_store.values())

    return {
        "total_resources": total,
        "completed": completed,
        "in_progress": in_progress,
        "abandoned": abandoned,
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
        "total_hours_logged": round(total_hours, 1)
    }

# =============================================================================
# CERTIFICATION ENDPOINTS
# =============================================================================

@app.get("/certs")
async def list_certs(status: Optional[str] = None):
    """List certifications"""
    certs = list(_certs_store.values())
    if status:
        certs = [c for c in certs if c.get("status") == status]
    return {"certifications": certs, "count": len(certs)}

@app.post("/certs")
async def create_cert(cert: CertificationCreate):
    """Add certification"""
    cert_id = generate_id()
    now = datetime.now().isoformat()

    cert_data = {
        "id": cert_id,
        "name": cert.name,
        "issuer": cert.issuer,
        "earned_date": cert.earned_date,
        "expiry_date": cert.expiry_date,
        "credential_id": cert.credential_id,
        "verification_url": cert.verification_url,
        "cost": cert.cost,
        "renewal_cost": cert.renewal_cost,
        "ce_credits_required": cert.ce_credits_required,
        "ce_credits_earned": 0,
        "status": "active",
        "created_at": now,
        "updated_at": now
    }

    _certs_store[cert_id] = cert_data

    await publish_event("cert.added", {
        "cert_id": cert_id,
        "name": cert.name,
        "issuer": cert.issuer
    })

    await store_memory(
        "fact",
        f"Earned certification: {cert.name} from {cert.issuer}",
        "certifications"
    )

    return cert_data

@app.get("/certs/{cert_id}")
async def get_cert(cert_id: str):
    """Get certification details"""
    if cert_id not in _certs_store:
        raise HTTPException(status_code=404, detail="Certification not found")
    return _certs_store[cert_id]

@app.put("/certs/{cert_id}")
async def update_cert(cert_id: str, update: CertificationUpdate):
    """Update certification"""
    if cert_id not in _certs_store:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert = _certs_store[cert_id]

    if update.expiry_date is not None:
        cert["expiry_date"] = update.expiry_date
    if update.ce_credits_earned is not None:
        cert["ce_credits_earned"] = update.ce_credits_earned
    if update.status is not None:
        cert["status"] = update.status
    if update.verification_url is not None:
        cert["verification_url"] = update.verification_url

    cert["updated_at"] = datetime.now().isoformat()

    return cert

@app.delete("/certs/{cert_id}")
async def delete_cert(cert_id: str):
    """Remove certification"""
    if cert_id not in _certs_store:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert = _certs_store.pop(cert_id)
    return {"deleted": True, "certification": cert}

@app.get("/certs/expiring")
async def get_expiring_certs():
    """Get certifications expiring soon"""
    now = datetime.now().date()
    expiring = []

    alert_thresholds = [90, 60, 30, 7, 0]  # days

    for cert in _certs_store.values():
        expiry = cert.get("expiry_date")
        if expiry:
            expiry_date = datetime.fromisoformat(expiry).date()
            days_until = (expiry_date - now).days

            if days_until <= 90:
                alert_type = "expired" if days_until < 0 else \
                            "critical" if days_until <= 7 else \
                            "urgent" if days_until <= 30 else \
                            "warning" if days_until <= 60 else "planning"

                expiring.append({
                    **cert,
                    "days_until_expiry": days_until,
                    "alert_type": alert_type
                })

    expiring.sort(key=lambda x: x["days_until_expiry"])

    return {"expiring": expiring}

@app.post("/certs/{cert_id}/renew")
async def renew_cert(cert_id: str, new_expiry_date: str):
    """Log certification renewal"""
    if cert_id not in _certs_store:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert = _certs_store[cert_id]
    cert["expiry_date"] = new_expiry_date
    cert["status"] = "active"
    cert["ce_credits_earned"] = 0  # Reset CE credits
    cert["updated_at"] = datetime.now().isoformat()

    await publish_event("cert.renewed", {
        "cert_id": cert_id,
        "name": cert["name"],
        "new_expiry": new_expiry_date
    })

    return cert

@app.get("/certs/timeline")
async def get_cert_timeline():
    """Get certification timeline view"""
    timeline = []

    for cert in _certs_store.values():
        # Add earned date
        timeline.append({
            "date": cert["earned_date"],
            "event": "earned",
            "cert_name": cert["name"],
            "cert_id": cert["id"]
        })

        # Add expiry if exists
        if cert.get("expiry_date"):
            timeline.append({
                "date": cert["expiry_date"],
                "event": "expires",
                "cert_name": cert["name"],
                "cert_id": cert["id"]
            })

    timeline.sort(key=lambda x: x["date"])

    return {"timeline": timeline}

# =============================================================================
# SPACED REPETITION / REVIEW ENDPOINTS
# =============================================================================

@app.get("/reviews/due")
async def get_due_reviews(limit: int = 10):
    """Get topics due for review"""
    now = datetime.now()
    due = []

    for review in _reviews_store.values():
        next_review = review.get("next_review")
        if next_review:
            review_date = datetime.fromisoformat(next_review)
            if review_date <= now:
                days_overdue = (now - review_date).days
                due.append({
                    **review,
                    "days_overdue": days_overdue
                })

    # Sort by most overdue first
    due.sort(key=lambda x: x["days_overdue"], reverse=True)

    return {"due_reviews": due[:limit], "total_due": len(due)}

@app.post("/reviews")
async def create_review(review: ReviewCreate):
    """Add topic to review schedule"""
    review_id = generate_id()
    now = datetime.now()

    review_data = {
        "id": review_id,
        "topic": review.topic,
        "skill_id": review.skill_id,
        "next_review": (now + timedelta(days=1)).isoformat(),  # First review tomorrow
        "interval_days": 1,
        "ease_factor": 2.5,
        "repetitions": 0,
        "last_quality": None,
        "last_reviewed": None,
        "notes": review.notes,
        "created_at": now.isoformat()
    }

    _reviews_store[review_id] = review_data

    return review_data

@app.get("/reviews/{review_id}")
async def get_review(review_id: str):
    """Get review item details"""
    if review_id not in _reviews_store:
        raise HTTPException(status_code=404, detail="Review not found")
    return _reviews_store[review_id]

@app.post("/reviews/{review_id}/complete")
async def complete_review(review_id: str, completion: ReviewComplete):
    """Log review with quality rating and calculate next review"""
    if review_id not in _reviews_store:
        raise HTTPException(status_code=404, detail="Review not found")

    review = _reviews_store[review_id]

    # Calculate next review using SM-2
    sm2_result = SM2.calculate_next_review(
        quality=completion.quality,
        repetitions=review["repetitions"],
        ease_factor=review["ease_factor"],
        interval_days=review["interval_days"]
    )

    # Update review record
    review["interval_days"] = sm2_result["new_interval"]
    review["ease_factor"] = sm2_result["new_ease_factor"]
    review["repetitions"] = sm2_result["new_repetitions"]
    review["next_review"] = sm2_result["next_review_date"]
    review["last_quality"] = completion.quality
    review["last_reviewed"] = datetime.now().isoformat()

    if completion.notes:
        review["notes"] = completion.notes

    await publish_event("review.completed", {
        "review_id": review_id,
        "topic": review["topic"],
        "quality": completion.quality,
        "next_interval": sm2_result["new_interval"]
    })

    return {
        "review": review,
        "sm2_result": sm2_result,
        "quality_description": SM2.get_quality_description(completion.quality)
    }

@app.get("/reviews/schedule")
async def get_review_schedule():
    """Get full review schedule"""
    reviews = list(_reviews_store.values())

    # Group by next review date
    schedule = {}
    for review in reviews:
        next_date = review.get("next_review", "")[:10]  # Get date part
        if next_date not in schedule:
            schedule[next_date] = []
        schedule[next_date].append(review)

    # Sort dates
    sorted_schedule = dict(sorted(schedule.items()))

    return {"schedule": sorted_schedule, "total_items": len(reviews)}

@app.put("/reviews/{review_id}/reschedule")
async def reschedule_review(review_id: str, new_date: str):
    """Manual reschedule"""
    if review_id not in _reviews_store:
        raise HTTPException(status_code=404, detail="Review not found")

    review = _reviews_store[review_id]
    review["next_review"] = new_date

    return review

@app.get("/reviews/stats")
async def get_review_stats():
    """Get retention statistics"""
    reviews = list(_reviews_store.values())

    if not reviews:
        return {"message": "No reviews tracked yet"}

    # Calculate average ease factor
    avg_ease = sum(r["ease_factor"] for r in reviews) / len(reviews)

    # Count by quality
    quality_counts = {i: 0 for i in range(6)}
    for review in reviews:
        if review.get("last_quality") is not None:
            quality_counts[review["last_quality"]] = quality_counts.get(review["last_quality"], 0) + 1

    # Count reviews completed
    completed_count = sum(1 for r in reviews if r.get("last_reviewed"))

    return {
        "total_topics": len(reviews),
        "completed_reviews": completed_count,
        "average_ease_factor": round(avg_ease, 2),
        "quality_distribution": quality_counts,
        "retention_estimate": "Based on quality ratings"  # Would calculate from quality distribution
    }

# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@app.get("/analytics/learning-time")
async def get_learning_time(period: str = "week"):
    """Get time spent learning (stub)"""
    total_hours = sum(p.get("time_spent_hours", 0) for p in _progress_store.values())

    return {
        "period": period,
        "total_hours": round(total_hours, 1),
        "message": "Detailed analytics coming in Phase 4"
    }

@app.get("/analytics/skill-growth")
async def get_skill_growth():
    """Get skill progression over time (stub)"""
    return {
        "message": "Skill growth analytics coming in Phase 4",
        "current_skills": len(_skills_store)
    }

@app.get("/analytics/retention")
async def get_retention_analytics():
    """Get knowledge retention rates (stub)"""
    stats = await get_review_stats()
    return {
        "review_stats": stats,
        "message": "Detailed retention analytics coming in Phase 4"
    }

@app.get("/analytics/goals")
async def get_goal_analytics():
    """Get goal completion rates (stub)"""
    paths = list(_paths_store.values())
    completed = sum(1 for p in paths if p.get("status") == "completed")

    return {
        "total_paths": len(paths),
        "completed": completed,
        "completion_rate": round(completed / len(paths) * 100, 1) if paths else 0,
        "message": "Detailed goal analytics coming in Phase 4"
    }

# =============================================================================
# CHAT ENDPOINT
# =============================================================================

@app.post("/chat")
async def chat(req: ChatRequest):
    """Have a conversation with ACADEMIC GUIDE"""
    time_ctx = get_time_context()
    learning_ctx = get_learning_summary()

    messages = [
        {"role": "user", "content": req.message}
    ]

    response = await call_llm(messages, learning_ctx)

    await publish_event("chat", {
        "message_preview": req.message[:100],
        "session_id": req.session_id
    })

    return {
        "response": response,
        "agent": "ACADEMIC_GUIDE",
        "session_id": req.session_id,
        "time_context": time_ctx,
        "learning_context": learning_ctx
    }

# =============================================================================
# ARIA TOOLS ENDPOINT
# =============================================================================

@app.get("/tools")
async def get_aria_tools():
    """Get ARIA tool definitions for this agent"""
    return {
        "agent": "ACADEMIC_GUIDE",
        "tools": ARIA_TOOLS
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8103)
