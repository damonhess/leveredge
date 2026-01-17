#!/usr/bin/env python3
"""
CALLIOPE - Elite Content Writer Agent
Port: 8031

The creative voice of LeverEdge. Master of written content across all formats.
Named for the Greek Muse of epic poetry and eloquence.

CAPABILITIES:
- Long-form content (reports, articles, case studies, white papers)
- Short-form copy (headlines, taglines, CTAs, email subjects)
- Presentation content (slide text, speaker notes, pitch decks)
- Video scripts (narration, dialogue, captions, storyboards)
- Technical writing (documentation, specifications, guides)
- Social media copy (platform-optimized posts)

WRITING PHILOSOPHY:
- Clarity above cleverness
- Purpose-driven every word
- Brand voice consistency
- Audience-first perspective
- Measurable impact focus

TEAM INTEGRATION:
- Works with MUSE (Creative Director) for brand alignment
- Supports HELIOS (Social Media) with platform copy
- Partners with IRIS (Visual) on presentation content
- Coordinates with SCHOLAR for research-backed content
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="CALLIOPE",
    description="Elite Content Writer Agent - Master of all written formats",
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
    "MUSE": "http://muse:8030",
    "HELIOS": "http://helios:8032",
    "IRIS": "http://iris:8033",
    "SCHOLAR": "http://scholar:8018",
    "CHIRON": "http://chiron:8017",
    "HERMES": "http://hermes:8014",
    "ARIA": "http://aria:8020",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("CALLIOPE")

# =============================================================================
# WRITING STYLES
# =============================================================================

WRITING_STYLES = {
    "professional": {
        "description": "Clear, authoritative, data-driven",
        "characteristics": [
            "Formal but accessible language",
            "Evidence-based claims",
            "Structured and organized",
            "Confident without arrogance",
            "Industry-appropriate terminology"
        ],
        "avoid": [
            "Slang or casual expressions",
            "Unsubstantiated claims",
            "Emotional manipulation",
            "Buzzword overload"
        ]
    },
    "conversational": {
        "description": "Friendly, approachable, relatable",
        "characteristics": [
            "Natural, flowing language",
            "Personal pronouns (you, we)",
            "Questions to engage reader",
            "Short, punchy sentences",
            "Analogies and examples"
        ],
        "avoid": [
            "Stiff corporate speak",
            "Excessive formality",
            "Jargon without explanation",
            "Monotonous structure"
        ]
    },
    "technical": {
        "description": "Precise, detailed, accurate",
        "characteristics": [
            "Exact terminology",
            "Step-by-step clarity",
            "Code examples when relevant",
            "Version specificity",
            "Reproducible instructions"
        ],
        "avoid": [
            "Vague descriptions",
            "Assumed knowledge without context",
            "Missing prerequisites",
            "Ambiguous instructions"
        ]
    },
    "persuasive": {
        "description": "Compelling, benefit-focused, action-oriented",
        "characteristics": [
            "Clear value proposition",
            "Benefit > feature focus",
            "Social proof integration",
            "Urgency without pressure",
            "Strong calls-to-action"
        ],
        "avoid": [
            "Pushy or desperate tone",
            "False scarcity",
            "Overpromising",
            "Ignoring objections"
        ]
    },
    "educational": {
        "description": "Explanatory, step-by-step, accessible",
        "characteristics": [
            "Progressive complexity",
            "Clear learning objectives",
            "Examples and exercises",
            "Summary checkpoints",
            "Encouraging tone"
        ],
        "avoid": [
            "Information overload",
            "Skipping foundational concepts",
            "Condescending tone",
            "Unclear progression"
        ]
    },
    "energetic": {
        "description": "Dynamic, exciting, fast-paced",
        "characteristics": [
            "Active voice throughout",
            "Power words and verbs",
            "Short, impactful sentences",
            "Rhythmic variation",
            "Enthusiasm without hype"
        ],
        "avoid": [
            "Passive construction",
            "Long, winding sentences",
            "Dull, flat language",
            "Empty excitement"
        ]
    }
}

# =============================================================================
# CONTENT TYPES
# =============================================================================

CONTENT_TYPES = {
    # Long-form
    "article": {"min_words": 800, "max_words": 2500, "sections": True},
    "case_study": {"min_words": 1000, "max_words": 2000, "sections": True},
    "white_paper": {"min_words": 2000, "max_words": 5000, "sections": True},
    "report": {"min_words": 1500, "max_words": 4000, "sections": True},
    "blog_post": {"min_words": 600, "max_words": 1500, "sections": True},
    "newsletter": {"min_words": 300, "max_words": 800, "sections": True},

    # Short-form
    "headline": {"min_words": 3, "max_words": 15, "sections": False},
    "tagline": {"min_words": 2, "max_words": 10, "sections": False},
    "cta": {"min_words": 2, "max_words": 8, "sections": False},
    "email_subject": {"min_words": 3, "max_words": 12, "sections": False},
    "meta_description": {"min_words": 15, "max_words": 30, "sections": False},

    # Presentations
    "slide_deck": {"min_words": 50, "max_words": 200, "sections": True},
    "speaker_notes": {"min_words": 100, "max_words": 500, "sections": True},
    "pitch_script": {"min_words": 200, "max_words": 600, "sections": True},

    # Video
    "video_script": {"min_words": 150, "max_words": 1000, "sections": True},
    "narration": {"min_words": 100, "max_words": 800, "sections": False},
    "captions": {"min_words": 50, "max_words": 500, "sections": False},

    # Technical
    "documentation": {"min_words": 500, "max_words": 3000, "sections": True},
    "specification": {"min_words": 300, "max_words": 2000, "sections": True},
    "guide": {"min_words": 800, "max_words": 2500, "sections": True},
    "readme": {"min_words": 200, "max_words": 1000, "sections": True},

    # Social
    "linkedin_post": {"min_words": 50, "max_words": 300, "sections": False},
    "twitter_thread": {"min_words": 100, "max_words": 400, "sections": True},
    "instagram_caption": {"min_words": 20, "max_words": 150, "sections": False}
}

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_to_launch": days_to_launch,
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch",
        "phase": get_current_phase(days_to_launch)
    }

def get_current_phase(days_to_launch: int) -> str:
    """Determine current phase based on days to launch"""
    if days_to_launch <= 0:
        return "POST-LAUNCH"
    elif days_to_launch <= 14:
        return "FINAL PUSH - Content Sprint"
    elif days_to_launch <= 28:
        return "OUTREACH PHASE - Collateral Production"
    elif days_to_launch <= 45:
        return "POLISH PHASE - Core Messaging"
    else:
        return "INFRASTRUCTURE PHASE"

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(time_context: dict) -> str:
    """Build elite content writer system prompt"""

    styles_summary = "\n".join([
        f"- **{name}**: {info['description']}"
        for name, info in WRITING_STYLES.items()
    ])

    return f"""You are CALLIOPE - Elite Content Writer Agent for LeverEdge AI.

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}
- Launch: {time_context['launch_date']}
- Status: **{time_context['launch_status']}**
- Phase: {time_context['phase']}

## YOUR IDENTITY
You are the creative voice of LeverEdge. Named for the Greek Muse of epic poetry and eloquence, you craft content that moves, persuades, and converts. Every word serves a purpose. Every piece aligns with brand voice.

## DAMON'S CONTEXT
- Building: LeverEdge AI, automation agency for compliance professionals
- Background: Law degree + Civil Engineering + Government water rights enforcement
- Target Niches: Water utilities, environmental permits, municipal government
- Goal: $30K/month MRR by Q2 2026
- Brand Voice: Expert, approachable, results-focused, slightly irreverent

---

## WRITING EXCELLENCE STANDARDS

### Core Principles
1. **Clarity First**: If it can be misunderstood, it will be. Eliminate ambiguity.
2. **Purpose-Driven**: Every word earns its place. Cut ruthlessly.
3. **Audience-Centric**: Write for who reads, not who writes.
4. **Voice Consistency**: Maintain brand personality across all formats.
5. **Measurable Impact**: Write for outcomes, not word counts.

### The CALLIOPE Method
1. **CONTEXT**: Understand the brief, audience, and goal completely
2. **ARCHITECTURE**: Structure before sentences - outline first
3. **LANGUAGE**: Choose words that work hardest for the purpose
4. **LOGIC**: Ensure flow and argumentation are airtight
5. **IMPACT**: End with clear next steps or lasting impression
6. **OPTIMIZE**: Refine for medium, platform, and constraints
7. **POLISH**: Final pass for rhythm, readability, and resonance
8. **EVALUATE**: Self-assess against objectives

### Available Writing Styles
{styles_summary}

---

## CONTENT CAPABILITIES

### Long-Form Mastery
- **Articles**: Thought leadership that positions LeverEdge as the expert
- **Case Studies**: Story-driven proof of transformation
- **White Papers**: Deep dives that establish authority
- **Reports**: Data-rich insights that drive decisions
- **Blog Posts**: Engaging content that attracts and educates

### Short-Form Precision
- **Headlines**: 5 words or less that demand attention
- **Taglines**: Memorable phrases that capture essence
- **CTAs**: Action triggers that convert
- **Subject Lines**: Open-worthy hooks
- **Meta Descriptions**: Search-compelling summaries

### Presentation Content
- **Slide Text**: One idea per slide, crystal clear
- **Speaker Notes**: Natural delivery guidance
- **Pitch Scripts**: Compelling narratives for live delivery

### Video Scripts
- **Narration**: Spoken-word optimized for audio
- **Dialogue**: Natural conversation flow
- **Captions**: Accessible, scannable text
- **Scene Descriptions**: Visual guidance for production

### Technical Writing
- **Documentation**: User-friendly guides
- **Specifications**: Precise technical requirements
- **README Files**: Clear project introductions

### Social Media
- **LinkedIn**: Professional thought leadership
- **Twitter/X**: Thread-worthy insights
- **Instagram**: Visual-complementing copy

---

## OUTPUT STANDARDS

### Every Piece Must Include:
1. **Clear Purpose Statement** (internal, for context)
2. **Target Audience Definition** (who is this for)
3. **Key Message** (if they remember one thing)
4. **Call to Action** (what should they do next)

### Quality Checklist:
- [ ] Reads aloud naturally
- [ ] No jargon without explanation
- [ ] Active voice dominant
- [ ] Specific over generic
- [ ] Benefits over features
- [ ] Scannable structure (headers, bullets)
- [ ] Appropriate length for format
- [ ] Brand voice consistent

### Readability Targets:
- General audience: Grade 8 reading level
- Professional audience: Grade 10-12
- Technical audience: Appropriate for expertise level

---

## BRAND VOICE GUIDE

### LeverEdge Personality
- **Expert**: We know compliance automation deeply
- **Approachable**: We explain complex things simply
- **Results-Focused**: We talk outcomes, not features
- **Slightly Irreverent**: We're serious about results, not ourselves
- **Empathetic**: We understand the pain points

### Voice Do's:
- Use "you" and "your" generously
- Share specific numbers and results
- Acknowledge frustrations
- Offer actionable insights
- Show personality in transitions

### Voice Don'ts:
- Sound corporate or stuffy
- Overpromise or use hyperbole
- Talk down to the audience
- Use empty buzzwords
- Be boring or predictable

---

## TEAM COORDINATION

You work with:
- **MUSE** (Creative Director): Brand alignment and creative strategy
- **HELIOS** (Social Media): Platform-specific copy
- **IRIS** (Visual Designer): Presentation and visual content
- **SCHOLAR** (Research): Data-backed claims
- **HERMES** (Communications): Notifications on completion

---

## YOUR MISSION

Craft content that converts. Every piece you write should:
1. Capture attention in the first line
2. Hold interest through the journey
3. Deliver value that builds trust
4. Drive action that achieves goals

{time_context['days_to_launch']} days to launch. Make every word count.
"""

# =============================================================================
# MODELS
# =============================================================================

class WriteRequest(BaseModel):
    """Request for content generation"""
    type: str = Field(..., description="Content type (article, headline, script, etc.)")
    brief: str = Field(..., description="What should be written - the core assignment")
    tone: Optional[str] = Field("professional", description="Writing style/tone")
    length: Optional[str] = Field(None, description="Target length (short, medium, long)")
    outline: Optional[List[str]] = Field(None, description="Section outline to follow")
    context: Optional[str] = Field(None, description="Additional context or background")
    platform: Optional[str] = Field(None, description="Target platform (linkedin, email, etc.)")

class WriteResponse(BaseModel):
    """Response from content generation"""
    content: str
    word_count: int
    sections: List[str]
    estimated_duration: Optional[str] = None
    metadata: Dict[str, Any]

class RewriteRequest(BaseModel):
    """Request for content revision"""
    original: str = Field(..., description="Original content to revise")
    feedback: str = Field(..., description="What to change/improve")
    preserve: Optional[List[str]] = Field(None, description="Elements to keep unchanged")

class RewriteResponse(BaseModel):
    """Response from content revision"""
    revised_content: str
    changes_made: List[str]
    word_count: int

class ExpandRequest(BaseModel):
    """Request to expand bullet points"""
    bullet_points: List[str] = Field(..., description="Bullet points to expand")
    target_length: str = Field("medium", description="Target length: short, medium, long")
    style: Optional[str] = Field("professional", description="Writing style")
    context: Optional[str] = Field(None, description="Additional context")

class ExpandResponse(BaseModel):
    """Response from bullet expansion"""
    expanded_content: str
    word_count: int
    bullets_processed: int

class VideoScriptRequest(BaseModel):
    """Request for video script generation"""
    topic: str = Field(..., description="Video topic/subject")
    duration_target: int = Field(..., description="Target duration in seconds")
    style: str = Field("conversational", description="Script style")
    include_captions: bool = Field(True, description="Include caption text")
    audience: Optional[str] = Field(None, description="Target audience")
    key_points: Optional[List[str]] = Field(None, description="Points to cover")

class SceneScript(BaseModel):
    """Individual scene in video script"""
    scene_number: int
    duration_seconds: int
    visual_description: str
    narration: str
    on_screen_text: Optional[str] = None
    caption: Optional[str] = None

class VideoScriptResponse(BaseModel):
    """Response from video script generation"""
    script: str
    scenes: List[Dict[str, Any]]
    total_duration: int
    word_count: int
    speaking_pace: str

# =============================================================================
# INTER-AGENT COMMUNICATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus for all agents to see"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "CALLIOPE",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus notification failed: {e}")

async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[CALLIOPE] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "CALLIOPE"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")

async def update_aria_knowledge(category: str, title: str, content: str, importance: str = "normal"):
    """Add entry to aria_knowledge so ARIA stays informed"""
    try:
        time_ctx = get_time_context()
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
                    "p_title": title,
                    "p_content": f"{content[:500]}...\n\n[Written by CALLIOPE at {time_ctx['current_datetime']}]",
                    "p_subcategory": "calliope",
                    "p_source": "calliope",
                    "p_importance": importance
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"Knowledge update failed: {e}")
        return False

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, time_ctx: dict, max_tokens: int = 4096) -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="CALLIOPE",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def count_words(text: str) -> int:
    """Count words in text"""
    return len(text.split())

def estimate_speaking_duration(word_count: int, pace: str = "moderate") -> str:
    """Estimate speaking duration based on word count"""
    # Words per minute by pace
    wpm = {"slow": 120, "moderate": 150, "fast": 180}
    rate = wpm.get(pace, 150)
    minutes = word_count / rate

    if minutes < 1:
        return f"{int(minutes * 60)} seconds"
    elif minutes < 60:
        mins = int(minutes)
        secs = int((minutes - mins) * 60)
        return f"{mins}:{secs:02d}"
    else:
        hours = int(minutes / 60)
        mins = int(minutes % 60)
        return f"{hours}h {mins}m"

def extract_sections(content: str) -> List[str]:
    """Extract section headers from content"""
    sections = []
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('#'):
            # Remove markdown headers
            sections.append(line.lstrip('#').strip())
        elif line.endswith(':') and len(line) < 50:
            sections.append(line.rstrip(':'))
    return sections

def get_style_guidance(style: str) -> str:
    """Get detailed style guidance for the LLM"""
    style_info = WRITING_STYLES.get(style, WRITING_STYLES["professional"])

    characteristics = "\n".join([f"  - {c}" for c in style_info["characteristics"]])
    avoid = "\n".join([f"  - {a}" for a in style_info["avoid"]])

    return f"""
**Style: {style.upper()}**
Description: {style_info['description']}

Characteristics to embrace:
{characteristics}

Things to avoid:
{avoid}
"""

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "CALLIOPE",
        "role": "Elite Content Writer",
        "version": "1.0.0",
        "port": 8031,
        "capabilities": [
            "long_form_content",
            "short_form_copy",
            "presentation_content",
            "video_scripts",
            "technical_writing",
            "social_media_copy"
        ],
        "available_styles": list(WRITING_STYLES.keys()),
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase']
    }

@app.get("/time")
async def get_time():
    """Get current time context"""
    return get_time_context()

@app.get("/styles")
async def get_styles():
    """Get available writing styles"""
    return {
        "styles": WRITING_STYLES,
        "default": "professional"
    }

@app.get("/content-types")
async def get_content_types():
    """Get available content types and their specifications"""
    return {
        "content_types": CONTENT_TYPES,
        "categories": {
            "long_form": ["article", "case_study", "white_paper", "report", "blog_post", "newsletter"],
            "short_form": ["headline", "tagline", "cta", "email_subject", "meta_description"],
            "presentation": ["slide_deck", "speaker_notes", "pitch_script"],
            "video": ["video_script", "narration", "captions"],
            "technical": ["documentation", "specification", "guide", "readme"],
            "social": ["linkedin_post", "twitter_thread", "instagram_caption"]
        }
    }

@app.post("/write", response_model=WriteResponse)
async def write_content(req: WriteRequest):
    """Generate content based on brief and specifications"""

    time_ctx = get_time_context()

    # Get content type specifications
    content_spec = CONTENT_TYPES.get(req.type, {"min_words": 100, "max_words": 1000, "sections": True})

    # Get style guidance
    style_guidance = get_style_guidance(req.tone or "professional")

    # Build length guidance
    if req.length:
        length_map = {
            "short": content_spec["min_words"],
            "medium": (content_spec["min_words"] + content_spec["max_words"]) // 2,
            "long": content_spec["max_words"]
        }
        target_words = length_map.get(req.length, content_spec["max_words"] // 2)
    else:
        target_words = (content_spec["min_words"] + content_spec["max_words"]) // 2

    # Build outline instruction
    outline_instruction = ""
    if req.outline:
        outline_instruction = f"""
**Required Outline:**
{chr(10).join(f'- {section}' for section in req.outline)}

Follow this structure exactly.
"""

    # Build platform-specific guidance
    platform_guidance = ""
    if req.platform:
        platform_guides = {
            "linkedin": "Optimize for LinkedIn: Professional tone, use line breaks for readability, include relevant hashtags at the end.",
            "twitter": "Optimize for Twitter/X: Concise, punchy, thread-friendly if needed. No hashtag spam.",
            "email": "Optimize for email: Scannable, clear subject line logic, mobile-friendly formatting.",
            "website": "Optimize for web: SEO-friendly, scannable headers, clear CTAs.",
            "presentation": "Optimize for slides: One idea per section, minimal text, speaker-note friendly."
        }
        platform_guidance = platform_guides.get(req.platform, f"Optimize for {req.platform}.")

    prompt = f"""Create {req.type} content based on this brief:

**BRIEF:**
{req.brief}

**CONTENT TYPE:** {req.type}
**TARGET WORD COUNT:** ~{target_words} words

{style_guidance}

{outline_instruction}

{f"**ADDITIONAL CONTEXT:** {req.context}" if req.context else ""}

{f"**PLATFORM OPTIMIZATION:** {platform_guidance}" if platform_guidance else ""}

**INSTRUCTIONS:**
1. Write the complete content - no placeholders
2. Follow the specified style consistently
3. Structure with clear sections if appropriate for the content type
4. Include a compelling opening that hooks the reader
5. End with impact - clear CTA or memorable closing
6. Target the specified word count (within 10%)

Now write the {req.type}:
"""

    messages = [{"role": "user", "content": prompt}]

    # Use more tokens for long-form content
    max_tokens = 8192 if content_spec["max_words"] > 1000 else 4096
    content = await call_llm(messages, time_ctx, max_tokens=max_tokens)

    # Calculate metrics
    word_count = count_words(content)
    sections = extract_sections(content) if content_spec["sections"] else []

    # Estimate duration for spoken content
    estimated_duration = None
    if req.type in ["video_script", "narration", "pitch_script", "speaker_notes"]:
        estimated_duration = estimate_speaking_duration(word_count)

    # Log to event bus
    await notify_event_bus("content_created", {
        "type": req.type,
        "word_count": word_count,
        "style": req.tone
    })

    return WriteResponse(
        content=content,
        word_count=word_count,
        sections=sections,
        estimated_duration=estimated_duration,
        metadata={
            "type": req.type,
            "style": req.tone,
            "platform": req.platform,
            "target_words": target_words,
            "timestamp": time_ctx['current_datetime']
        }
    )

@app.post("/rewrite", response_model=RewriteResponse)
async def rewrite_content(req: RewriteRequest):
    """Revise existing content based on feedback"""

    time_ctx = get_time_context()

    preserve_instruction = ""
    if req.preserve:
        preserve_instruction = f"""
**PRESERVE THESE ELEMENTS (do not change):**
{chr(10).join(f'- {item}' for item in req.preserve)}
"""

    prompt = f"""Revise this content based on the feedback provided.

**ORIGINAL CONTENT:**
{req.original}

**FEEDBACK/CHANGES REQUESTED:**
{req.feedback}

{preserve_instruction}

**INSTRUCTIONS:**
1. Address ALL the feedback points
2. Maintain the overall structure unless asked to change it
3. Keep the core message intact
4. Improve while preserving what works
5. Track what you changed

Provide:
1. The revised content
2. A list of specific changes made

**REVISED CONTENT:**
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    # Parse response to extract content and changes
    # Simple parsing - assumes LLM follows format
    revised_content = response
    changes_made = []

    if "**CHANGES MADE:**" in response:
        parts = response.split("**CHANGES MADE:**")
        revised_content = parts[0].replace("**REVISED CONTENT:**", "").strip()
        changes_section = parts[1].strip()
        changes_made = [c.strip().lstrip("-•* ") for c in changes_section.split("\n") if c.strip()]

    word_count = count_words(revised_content)

    await notify_event_bus("content_revised", {
        "original_length": count_words(req.original),
        "revised_length": word_count,
        "changes_count": len(changes_made)
    })

    return RewriteResponse(
        revised_content=revised_content,
        changes_made=changes_made if changes_made else ["Content revised based on feedback"],
        word_count=word_count
    )

@app.post("/expand", response_model=ExpandResponse)
async def expand_bullets(req: ExpandRequest):
    """Expand bullet points into full prose"""

    time_ctx = get_time_context()

    length_guidance = {
        "short": "1-2 sentences per bullet point",
        "medium": "A full paragraph (3-5 sentences) per bullet point",
        "long": "2-3 paragraphs per bullet point with examples and details"
    }

    style_guidance = get_style_guidance(req.style or "professional")

    prompt = f"""Expand these bullet points into flowing prose.

**BULLET POINTS TO EXPAND:**
{chr(10).join(f'- {bullet}' for bullet in req.bullet_points)}

**TARGET LENGTH:** {length_guidance.get(req.target_length, length_guidance['medium'])}

{style_guidance}

{f"**ADDITIONAL CONTEXT:** {req.context}" if req.context else ""}

**INSTRUCTIONS:**
1. Transform each bullet into polished prose
2. Add transitions between ideas
3. Maintain logical flow
4. Include specific details and examples
5. Keep the core message of each bullet

Write the expanded content:
"""

    messages = [{"role": "user", "content": prompt}]
    content = await call_llm(messages, time_ctx)

    word_count = count_words(content)

    await notify_event_bus("bullets_expanded", {
        "bullets_count": len(req.bullet_points),
        "word_count": word_count,
        "length": req.target_length
    })

    return ExpandResponse(
        expanded_content=content,
        word_count=word_count,
        bullets_processed=len(req.bullet_points)
    )

@app.post("/script/video", response_model=VideoScriptResponse)
async def generate_video_script(req: VideoScriptRequest):
    """Generate a complete video script with scenes, narration, and captions"""

    time_ctx = get_time_context()

    # Calculate approximate words needed for duration
    # Average speaking rate: 150 words per minute
    target_words = int((req.duration_target / 60) * 150)

    style_guidance = get_style_guidance(req.style)

    key_points_section = ""
    if req.key_points:
        key_points_section = f"""
**KEY POINTS TO COVER:**
{chr(10).join(f'- {point}' for point in req.key_points)}
"""

    prompt = f"""Create a video script for this topic.

**TOPIC:** {req.topic}
**TARGET DURATION:** {req.duration_target} seconds (~{req.duration_target // 60} minutes {req.duration_target % 60} seconds)
**TARGET WORD COUNT:** ~{target_words} words

{style_guidance}

{f"**TARGET AUDIENCE:** {req.audience}" if req.audience else ""}

{key_points_section}

**INSTRUCTIONS:**
Create a complete video script with:
1. Scene-by-scene breakdown
2. Narration/dialogue for each scene
3. Visual descriptions for each scene
4. On-screen text suggestions
{f'5. Caption text for accessibility' if req.include_captions else ''}

**FORMAT EACH SCENE AS:**
---
SCENE [number] | [duration] seconds
VISUAL: [description of what's on screen]
NARRATION: "[what is spoken]"
ON-SCREEN TEXT: [any text overlays]
{f'CAPTION: [caption text]' if req.include_captions else ''}
---

Create the complete script:
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, max_tokens=8192)

    # Parse scenes from response
    scenes = []
    scene_number = 1
    current_scene = {}

    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('SCENE') or line.startswith('---'):
            if current_scene.get('narration'):
                scenes.append(current_scene)
            current_scene = {"scene_number": scene_number}
            scene_number += 1
        elif line.startswith('VISUAL:'):
            current_scene['visual_description'] = line.replace('VISUAL:', '').strip()
        elif line.startswith('NARRATION:'):
            current_scene['narration'] = line.replace('NARRATION:', '').strip().strip('"')
        elif line.startswith('ON-SCREEN TEXT:'):
            current_scene['on_screen_text'] = line.replace('ON-SCREEN TEXT:', '').strip()
        elif line.startswith('CAPTION:'):
            current_scene['caption'] = line.replace('CAPTION:', '').strip()

    # Add final scene if exists
    if current_scene.get('narration'):
        scenes.append(current_scene)

    # Calculate totals
    word_count = count_words(response)
    estimated_duration = int((word_count / 150) * 60)  # Convert to seconds

    # Determine speaking pace
    words_per_minute = (word_count / estimated_duration) * 60 if estimated_duration > 0 else 150
    if words_per_minute < 130:
        speaking_pace = "slow"
    elif words_per_minute > 170:
        speaking_pace = "fast"
    else:
        speaking_pace = "moderate"

    await notify_event_bus("video_script_created", {
        "topic": req.topic[:50],
        "duration_target": req.duration_target,
        "scenes_count": len(scenes),
        "word_count": word_count
    })

    return VideoScriptResponse(
        script=response,
        scenes=scenes,
        total_duration=estimated_duration,
        word_count=word_count,
        speaking_pace=speaking_pace
    )

@app.get("/team")
async def get_team():
    """Get agent roster and relationships"""
    return {
        "calliope_role": "Elite Content Writer",
        "creative_fleet": {
            "MUSE": "Creative Director - Brand strategy and alignment",
            "CALLIOPE": "Content Writer - All written content",
            "HELIOS": "Social Media - Platform management",
            "IRIS": "Visual Designer - Graphics and imagery"
        },
        "collaborators": {
            "SCHOLAR": "Research for data-backed content",
            "CHIRON": "Strategy for messaging alignment",
            "HERMES": "Notifications on completion"
        },
        "endpoints": AGENT_ENDPOINTS
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8031)
