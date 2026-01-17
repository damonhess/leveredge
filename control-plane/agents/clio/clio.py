#!/usr/bin/env python3
"""
CLIO - Creative Quality Reviewer Agent
Port: 8034

Quality assurance, brand compliance, fact-checking for the Creative Fleet.
Named after Clio, the Muse of History - bringing truth and accuracy to content.

CAPABILITIES:
- Brand guideline compliance
- Grammar/spelling check
- Fact verification (via SCHOLAR)
- Consistency review
- Accessibility check
- Video quality review
- Audio quality check

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Calls SCHOLAR for fact-checking
- Pulls brand info from creative_brands table
"""

import os
import sys
import json
import re
import subprocess
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="CLIO",
    description="Creative Quality Reviewer - QA, Brand Compliance, Fact-Checking",
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
    "CALLIOPE": "http://calliope:8031",
    "THALIA": "http://thalia:8032",
    "ERATO": "http://erato:8033",
    "SCHOLAR": "http://scholar:8018",
    "HEPHAESTUS": "http://hephaestus:8011",
    "HERMES": "http://hermes:8014",
    "ARIA": "http://aria:8001",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("CLIO")

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class ContentType(str, Enum):
    PRESENTATION = "presentation"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    COPY = "copy"
    AUDIO = "audio"

class CheckType(str, Enum):
    BRAND = "brand"
    GRAMMAR = "grammar"
    FACTS = "facts"
    ACCESSIBILITY = "accessibility"
    QUALITY = "quality"
    CONSISTENCY = "consistency"

# Review checklists by content type
REVIEW_CHECKLISTS = {
    "presentation": [
        {"check": "consistent_font_usage", "description": "Consistent font usage across slides"},
        {"check": "brand_colors_only", "description": "Uses only brand colors"},
        {"check": "logo_placement", "description": "Logo placement is correct"},
        {"check": "no_orphan_bullets", "description": "No orphan bullet points"},
        {"check": "speaker_notes_present", "description": "Speaker notes are present"},
        {"check": "slide_count_appropriate", "description": "Slide count is appropriate for content"},
        {"check": "text_legibility", "description": "Text is legible (size, contrast)"},
        {"check": "image_quality", "description": "Images are high resolution"},
    ],
    "document": [
        {"check": "header_hierarchy", "description": "Header hierarchy is correct"},
        {"check": "consistent_formatting", "description": "Consistent formatting throughout"},
        {"check": "citations_present", "description": "Citations present for claims"},
        {"check": "no_passive_voice_overuse", "description": "No overuse of passive voice"},
        {"check": "reading_level_appropriate", "description": "Reading level is appropriate"},
        {"check": "spelling_grammar", "description": "No spelling or grammar errors"},
        {"check": "table_formatting", "description": "Tables are properly formatted"},
    ],
    "image": [
        {"check": "resolution_sufficient", "description": "Resolution is sufficient (min 150 DPI)"},
        {"check": "brand_colors_present", "description": "Brand colors are present"},
        {"check": "no_text_cutoff", "description": "No text is cut off"},
        {"check": "accessible_contrast", "description": "Accessible contrast ratio (4.5:1)"},
        {"check": "file_size_optimal", "description": "File size is optimized"},
    ],
    "video": [
        {"check": "audio_levels", "description": "Audio levels consistent (-14 to -10 LUFS)"},
        {"check": "no_background_noise", "description": "No background noise or hum"},
        {"check": "captions_present", "description": "Captions are present"},
        {"check": "captions_accurate", "description": "Captions are accurate"},
        {"check": "intro_outro_present", "description": "Intro/outro are present"},
        {"check": "brand_watermark", "description": "Brand watermark is visible"},
        {"check": "duration_within_target", "description": "Duration within target (+/- 10%)"},
        {"check": "resolution_matches_spec", "description": "Resolution matches specification"},
        {"check": "no_visual_artifacts", "description": "No visual artifacts"},
        {"check": "transitions_smooth", "description": "Transitions are smooth"},
        {"check": "music_voice_balance", "description": "Music doesn't overpower voice"},
    ],
    "copy": [
        {"check": "spelling_grammar", "description": "No spelling or grammar errors"},
        {"check": "tone_consistent", "description": "Tone is consistent with brand"},
        {"check": "cta_present", "description": "Call to action is present"},
        {"check": "reading_level", "description": "Reading level appropriate"},
        {"check": "no_jargon_overuse", "description": "No overuse of jargon"},
    ],
    "audio": [
        {"check": "audio_levels", "description": "Audio levels consistent (-14 to -10 LUFS)"},
        {"check": "no_clipping", "description": "No audio clipping"},
        {"check": "no_background_noise", "description": "No background noise"},
        {"check": "pacing_appropriate", "description": "Speaking pace is appropriate"},
        {"check": "pronunciation_correct", "description": "Pronunciations are correct"},
    ]
}

# Audio standards
AUDIO_STANDARDS = {
    "lufs_min": -14,
    "lufs_max": -10,
    "peak_max_db": -1,
    "noise_floor_max_db": -60
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
        return "FINAL PUSH - Outreach & Discovery Calls"
    elif days_to_launch <= 28:
        return "OUTREACH PHASE - 10 attempts, 3 calls"
    elif days_to_launch <= 45:
        return "POLISH PHASE - Loose ends & Agent building"
    else:
        return "INFRASTRUCTURE PHASE"

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(time_ctx: dict, brand_info: Optional[dict] = None) -> str:
    """Build quality review agent system prompt"""

    brand_context = ""
    if brand_info:
        brand_context = f"""
## BRAND CONTEXT
- Brand: {brand_info.get('name', 'Unknown')}
- Primary Color: {brand_info.get('color_primary', '#1B2951')}
- Secondary Color: {brand_info.get('color_secondary', '#B8860B')}
- Accent Color: {brand_info.get('color_accent', '#36454F')}
- Headings Font: {brand_info.get('font_headings', 'Inter')}
- Body Font: {brand_info.get('font_body', 'Inter')}
- Tone: {brand_info.get('tone', 'professional')}
- Voice: {brand_info.get('voice_description', 'Confident, knowledgeable, direct but approachable')}
"""

    return f"""You are CLIO - Creative Quality Reviewer for LeverEdge AI.

## TIME AWARENESS
- Current: {time_ctx['day_of_week']}, {time_ctx['current_date']} at {time_ctx['current_time']}
- Launch: {time_ctx['launch_date']}
- Status: **{time_ctx['launch_status']}**
- Phase: {time_ctx['phase']}

## YOUR IDENTITY
You are the quality gate for all creative output. Nothing ships without your approval.
Named after Clio, the Muse of History - you bring truth and accuracy to all content.

Your role is to:
1. Ensure brand compliance
2. Check grammar and spelling
3. Verify facts (via SCHOLAR)
4. Review consistency
5. Check accessibility
6. Assess video/audio quality

{brand_context}

## REVIEW STANDARDS

### Text Review
- No spelling or grammar errors
- Consistent tone matching brand voice
- Facts are verifiable
- Reading level appropriate for audience
- No passive voice overuse
- Clear calls to action

### Visual Review
- Brand colors only
- Consistent typography
- Proper logo placement
- Sufficient contrast for accessibility
- High resolution images

### Video Review
- Audio levels: -14 to -10 LUFS
- No background noise or hum
- Captions present and accurate
- Intro/outro present
- Brand watermark visible
- Duration within target (+/- 10%)
- No visual artifacts
- Smooth transitions

### Accessibility
- Color contrast ratio 4.5:1 minimum
- Alt text for images
- Captions for video
- Readable font sizes (min 14pt for body)

## OUTPUT FORMAT

Always structure your review as:
1. **VERDICT**: PASS / FAIL / NEEDS REVISION
2. **SCORE**: 0-100
3. **CRITICAL ISSUES**: Must fix before publishing
4. **WARNINGS**: Should fix if time permits
5. **SUGGESTIONS**: Nice to have improvements

{time_ctx['days_to_launch']} days to launch. Quality is non-negotiable.
"""

# =============================================================================
# MODELS
# =============================================================================

class ReviewIssue(BaseModel):
    type: str
    severity: Severity
    location: str
    description: str
    suggestion: str
    timestamp: Optional[float] = None  # For video/audio issues

class ReviewRequest(BaseModel):
    content_type: ContentType
    content_path: str
    brand_id: Optional[str] = None
    check_types: Optional[List[CheckType]] = None

class ReviewResponse(BaseModel):
    passed: bool
    score: int
    issues: List[ReviewIssue]
    checklist_results: Optional[Dict[str, bool]] = None
    metadata: Optional[Dict[str, Any]] = None

class BrandReviewRequest(BaseModel):
    content_path: str
    brand_id: str

class BrandViolation(BaseModel):
    rule: str
    location: str
    expected: str
    actual: str

class BrandReviewResponse(BaseModel):
    compliant: bool
    violations: List[BrandViolation]

class VideoReviewRequest(BaseModel):
    video_path: str
    brand_id: Optional[str] = None
    checks: Optional[List[str]] = None

class VideoReviewScores(BaseModel):
    audio_quality: int
    visual_quality: int
    brand_compliance: int
    caption_accuracy: int

class VideoIssue(BaseModel):
    timestamp: Optional[float]
    type: str
    description: str
    suggestion: str

class VideoReviewResponse(BaseModel):
    passed: bool
    scores: VideoReviewScores
    issues: List[VideoIssue]

class TextReviewRequest(BaseModel):
    content: str
    check_grammar: Optional[bool] = True
    check_tone: Optional[bool] = True
    target_tone: Optional[str] = "professional"

class TextSuggestion(BaseModel):
    original: str
    suggested: str
    reason: str

class TextReviewResponse(BaseModel):
    score: int
    issues: List[ReviewIssue]
    suggestions: List[TextSuggestion]

class FactCheckRequest(BaseModel):
    claims: List[str]
    context: Optional[str] = None

class FactCheckResult(BaseModel):
    claim: str
    verified: bool
    confidence: str  # high, medium, low
    source: Optional[str] = None
    notes: Optional[str] = None

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
                    "source_agent": "CLIO",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus notification failed: {e}")

async def call_scholar_fact_check(claims: List[str], context: Optional[str] = None) -> List[FactCheckResult]:
    """Call SCHOLAR agent for fact verification"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{AGENT_ENDPOINTS['SCHOLAR']}/validate-assumption",
                json={
                    "assumption": "; ".join(claims),
                    "importance": "high",
                    "current_evidence": context
                },
                timeout=60.0
            )
            if response.status_code == 200:
                data = response.json()
                # Parse SCHOLAR response and convert to FactCheckResults
                return parse_scholar_response(claims, data.get("validation", ""))
            else:
                return [FactCheckResult(
                    claim=claim,
                    verified=False,
                    confidence="low",
                    notes="SCHOLAR unavailable"
                ) for claim in claims]
    except Exception as e:
        print(f"SCHOLAR fact check failed: {e}")
        return [FactCheckResult(
            claim=claim,
            verified=False,
            confidence="low",
            notes=f"Error: {str(e)}"
        ) for claim in claims]

def parse_scholar_response(claims: List[str], response: str) -> List[FactCheckResult]:
    """Parse SCHOLAR's response into structured fact check results"""
    results = []
    response_lower = response.lower()

    for claim in claims:
        # Simple heuristic based on response content
        if "validated" in response_lower or "confirmed" in response_lower:
            verified = True
            confidence = "high"
        elif "uncertain" in response_lower or "partial" in response_lower:
            verified = False
            confidence = "medium"
        else:
            verified = False
            confidence = "low"

        results.append(FactCheckResult(
            claim=claim,
            verified=verified,
            confidence=confidence,
            source="SCHOLAR agent",
            notes=response[:200] if len(response) > 200 else response
        ))

    return results

async def get_brand_info(brand_id: str) -> Optional[dict]:
    """Fetch brand information from database"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/creative_brands",
                params={"id": f"eq.{brand_id}", "select": "*"},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
    except Exception as e:
        print(f"Failed to fetch brand info: {e}")
    return None

async def get_brand_by_name(name: str) -> Optional[dict]:
    """Fetch brand by name"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/creative_brands",
                params={"name": f"eq.{name}", "select": "*"},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
    except Exception as e:
        print(f"Failed to fetch brand by name: {e}")
    return None

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, time_ctx: dict, brand_info: Optional[dict] = None) -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx, brand_info)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="CLIO",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def analyze_audio_with_ffmpeg(file_path: str) -> dict:
    """Analyze audio using FFmpeg"""
    try:
        # Get loudness stats
        cmd = [
            "ffmpeg", "-i", file_path,
            "-af", "loudnorm=print_format=json",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Parse loudness from stderr
        output = result.stderr
        lufs = None
        peak = None

        # Extract LUFS value
        lufs_match = re.search(r'"input_i"\s*:\s*"(-?\d+\.?\d*)"', output)
        if lufs_match:
            lufs = float(lufs_match.group(1))

        # Extract peak value
        peak_match = re.search(r'"input_tp"\s*:\s*"(-?\d+\.?\d*)"', output)
        if peak_match:
            peak = float(peak_match.group(1))

        return {
            "lufs": lufs,
            "peak_db": peak,
            "analyzed": True
        }
    except Exception as e:
        return {
            "lufs": None,
            "peak_db": None,
            "analyzed": False,
            "error": str(e)
        }

def analyze_video_metadata(file_path: str) -> dict:
    """Analyze video metadata using FFprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            data = json.loads(result.stdout)

            # Extract key info
            format_info = data.get("format", {})
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )
            audio_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
                {}
            )

            return {
                "duration": float(format_info.get("duration", 0)),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream.get("r_frame_rate") else None,
                "video_codec": video_stream.get("codec_name"),
                "audio_codec": audio_stream.get("codec_name"),
                "audio_channels": audio_stream.get("channels"),
                "sample_rate": audio_stream.get("sample_rate"),
                "bitrate": format_info.get("bit_rate"),
                "analyzed": True
            }
    except Exception as e:
        return {
            "analyzed": False,
            "error": str(e)
        }

def check_color_contrast(color1: str, color2: str) -> float:
    """Calculate contrast ratio between two hex colors"""
    def hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def relative_luminance(rgb: tuple) -> float:
        r, g, b = [x / 255.0 for x in rgb]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    try:
        l1 = relative_luminance(hex_to_rgb(color1))
        l2 = relative_luminance(hex_to_rgb(color2))
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)
    except Exception:
        return 0.0

def calculate_reading_level(text: str) -> dict:
    """Calculate reading level metrics"""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = text.split()

    if not sentences or not words:
        return {"grade_level": 0, "difficulty": "unknown"}

    # Simple syllable count estimation
    def count_syllables(word: str) -> int:
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        return max(1, count)

    total_syllables = sum(count_syllables(w) for w in words)
    avg_sentence_length = len(words) / len(sentences)
    avg_syllables_per_word = total_syllables / len(words)

    # Flesch-Kincaid Grade Level
    grade_level = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59
    grade_level = max(0, min(18, grade_level))

    difficulty = "easy" if grade_level < 8 else "moderate" if grade_level < 12 else "advanced"

    return {
        "grade_level": round(grade_level, 1),
        "difficulty": difficulty,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "word_count": len(words)
    }

def detect_passive_voice(text: str) -> List[dict]:
    """Detect passive voice constructions"""
    # Simple pattern matching for passive voice
    passive_patterns = [
        r'\b(is|are|was|were|been|being|be)\s+(\w+ed)\b',
        r'\b(is|are|was|were|been|being|be)\s+(\w+en)\b',
        r'\b(get|gets|got|gotten)\s+(\w+ed)\b'
    ]

    findings = []
    for pattern in passive_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append({
                "text": match.group(0),
                "position": match.start()
            })

    return findings

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "CLIO",
        "role": "Creative Quality Reviewer",
        "version": "1.0.0",
        "port": 8034,
        "team": "Creative Fleet",
        "capabilities": [
            "brand_compliance",
            "grammar_check",
            "fact_verification",
            "consistency_review",
            "accessibility_check",
            "video_quality_review",
            "audio_quality_check"
        ],
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase']
    }

@app.get("/time")
async def get_time():
    """Get current time context"""
    return get_time_context()

@app.get("/checklists")
async def get_checklists():
    """Get all review checklists"""
    return REVIEW_CHECKLISTS

@app.get("/checklists/{content_type}")
async def get_checklist(content_type: str):
    """Get checklist for specific content type"""
    if content_type not in REVIEW_CHECKLISTS:
        raise HTTPException(status_code=404, detail=f"No checklist for content type: {content_type}")
    return REVIEW_CHECKLISTS[content_type]

@app.post("/review", response_model=ReviewResponse)
async def review_content(req: ReviewRequest):
    """Main review endpoint for any content type"""
    time_ctx = get_time_context()

    # Get brand info if provided
    brand_info = None
    if req.brand_id:
        brand_info = await get_brand_info(req.brand_id)

    # Default to all check types if none specified
    check_types = req.check_types or [CheckType.BRAND, CheckType.GRAMMAR, CheckType.QUALITY]

    # Get appropriate checklist
    checklist = REVIEW_CHECKLISTS.get(req.content_type.value, [])

    # Build review prompt
    checks_str = ", ".join([c.value for c in check_types])
    checklist_str = "\n".join([f"- {item['check']}: {item['description']}" for item in checklist])

    prompt = f"""Review this {req.content_type.value} content for quality.

**Content Path:** {req.content_path}
**Check Types:** {checks_str}

**Checklist for {req.content_type.value}:**
{checklist_str}

Analyze the content and provide:
1. Overall pass/fail verdict
2. Score (0-100)
3. List of issues found with:
   - Type of issue
   - Severity (critical/warning/info)
   - Location in content
   - Description
   - Suggestion for fix

Format your response as JSON:
{{
    "passed": true/false,
    "score": 0-100,
    "issues": [
        {{
            "type": "issue_type",
            "severity": "critical|warning|info",
            "location": "where in content",
            "description": "what's wrong",
            "suggestion": "how to fix"
        }}
    ],
    "checklist_results": {{
        "check_name": true/false
    }}
}}

Be thorough but fair. Focus on issues that impact quality and brand perception.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, brand_info)

    # Parse LLM response
    try:
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"passed": False, "score": 0, "issues": []}
    except json.JSONDecodeError:
        result = {"passed": False, "score": 0, "issues": []}

    issues = [
        ReviewIssue(
            type=issue.get("type", "unknown"),
            severity=Severity(issue.get("severity", "info")),
            location=issue.get("location", "unknown"),
            description=issue.get("description", ""),
            suggestion=issue.get("suggestion", ""),
            timestamp=issue.get("timestamp")
        )
        for issue in result.get("issues", [])
    ]

    await notify_event_bus("content_reviewed", {
        "content_type": req.content_type.value,
        "passed": result.get("passed", False),
        "score": result.get("score", 0),
        "issue_count": len(issues)
    })

    return ReviewResponse(
        passed=result.get("passed", False),
        score=result.get("score", 0),
        issues=issues,
        checklist_results=result.get("checklist_results"),
        metadata={
            "content_path": req.content_path,
            "brand_id": req.brand_id,
            "check_types": [c.value for c in check_types],
            "timestamp": time_ctx['current_datetime']
        }
    )

@app.post("/review/brand", response_model=BrandReviewResponse)
async def review_brand_compliance(req: BrandReviewRequest):
    """Review content for brand guideline compliance"""
    time_ctx = get_time_context()

    # Get brand info
    brand_info = await get_brand_info(req.brand_id)
    if not brand_info:
        raise HTTPException(status_code=404, detail=f"Brand not found: {req.brand_id}")

    prompt = f"""Review this content for brand compliance.

**Content Path:** {req.content_path}

**Brand Guidelines:**
- Name: {brand_info.get('name')}
- Primary Color: {brand_info.get('color_primary')}
- Secondary Color: {brand_info.get('color_secondary')}
- Accent Color: {brand_info.get('color_accent')}
- Background Color: {brand_info.get('color_background')}
- Text Color: {brand_info.get('color_text')}
- Headings Font: {brand_info.get('font_headings')}
- Body Font: {brand_info.get('font_body')}
- Tone: {brand_info.get('tone')}
- Voice: {brand_info.get('voice_description')}

Check for:
1. Color usage - only brand colors should be used
2. Typography - correct fonts for headings and body
3. Tone of voice - matches brand personality
4. Logo usage - correct placement and sizing
5. Visual consistency - aligned with brand aesthetic

Format your response as JSON:
{{
    "compliant": true/false,
    "violations": [
        {{
            "rule": "which guideline was violated",
            "location": "where in content",
            "expected": "what should be there",
            "actual": "what is actually there"
        }}
    ]
}}

Be strict on brand compliance - consistency is key.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, brand_info)

    # Parse response
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"compliant": True, "violations": []}
    except json.JSONDecodeError:
        result = {"compliant": True, "violations": []}

    violations = [
        BrandViolation(
            rule=v.get("rule", "unknown"),
            location=v.get("location", "unknown"),
            expected=v.get("expected", ""),
            actual=v.get("actual", "")
        )
        for v in result.get("violations", [])
    ]

    await notify_event_bus("brand_review_completed", {
        "brand_id": req.brand_id,
        "compliant": result.get("compliant", True),
        "violation_count": len(violations)
    })

    return BrandReviewResponse(
        compliant=result.get("compliant", True),
        violations=violations
    )

@app.post("/review/video", response_model=VideoReviewResponse)
async def review_video(req: VideoReviewRequest):
    """Review video for quality and brand compliance"""
    time_ctx = get_time_context()

    # Get brand info if provided
    brand_info = None
    if req.brand_id:
        brand_info = await get_brand_info(req.brand_id)

    # Default checks
    checks = req.checks or [
        "audio_quality", "visual_quality", "brand", "captions", "duration"
    ]

    issues = []
    scores = {
        "audio_quality": 100,
        "visual_quality": 100,
        "brand_compliance": 100,
        "caption_accuracy": 100
    }

    # Analyze video metadata
    video_meta = analyze_video_metadata(req.video_path)

    if not video_meta.get("analyzed"):
        issues.append(VideoIssue(
            timestamp=None,
            type="metadata_error",
            description=f"Could not analyze video: {video_meta.get('error', 'unknown error')}",
            suggestion="Ensure video file exists and is in a supported format"
        ))
        scores["visual_quality"] = 0
    else:
        # Check resolution
        if video_meta.get("width") and video_meta.get("height"):
            if video_meta["width"] < 1280 or video_meta["height"] < 720:
                issues.append(VideoIssue(
                    timestamp=None,
                    type="resolution",
                    description=f"Video resolution ({video_meta['width']}x{video_meta['height']}) is below 720p",
                    suggestion="Re-render at minimum 1280x720 resolution"
                ))
                scores["visual_quality"] -= 20

    # Analyze audio
    if "audio_quality" in checks:
        audio_analysis = analyze_audio_with_ffmpeg(req.video_path)

        if audio_analysis.get("analyzed"):
            lufs = audio_analysis.get("lufs")
            if lufs is not None:
                if lufs < AUDIO_STANDARDS["lufs_min"]:
                    issues.append(VideoIssue(
                        timestamp=None,
                        type="audio_level",
                        description=f"Audio is too quiet ({lufs:.1f} LUFS, target: -14 to -10 LUFS)",
                        suggestion="Increase audio levels or apply normalization"
                    ))
                    scores["audio_quality"] -= 25
                elif lufs > AUDIO_STANDARDS["lufs_max"]:
                    issues.append(VideoIssue(
                        timestamp=None,
                        type="audio_level",
                        description=f"Audio is too loud ({lufs:.1f} LUFS, target: -14 to -10 LUFS)",
                        suggestion="Reduce audio levels to prevent distortion"
                    ))
                    scores["audio_quality"] -= 25

            peak = audio_analysis.get("peak_db")
            if peak is not None and peak > AUDIO_STANDARDS["peak_max_db"]:
                issues.append(VideoIssue(
                    timestamp=None,
                    type="audio_clipping",
                    description=f"Audio peaks are clipping ({peak:.1f} dB, max: -1 dB)",
                    suggestion="Apply a limiter to prevent clipping"
                ))
                scores["audio_quality"] -= 30

    # LLM-based review for subjective qualities
    prompt = f"""Review this video for quality.

**Video Path:** {req.video_path}
**Duration:** {video_meta.get('duration', 'unknown')} seconds
**Resolution:** {video_meta.get('width', 'unknown')}x{video_meta.get('height', 'unknown')}

**Checks to perform:** {', '.join(checks)}

Based on video production best practices, identify any issues with:
1. Visual quality (artifacts, pixelation, poor lighting)
2. Audio quality (background noise, inconsistent levels)
3. Caption accuracy (if captions are present)
4. Pacing and timing
5. Transitions and effects

Format as JSON:
{{
    "issues": [
        {{
            "timestamp": null or seconds,
            "type": "issue_type",
            "description": "what's wrong",
            "suggestion": "how to fix"
        }}
    ],
    "quality_notes": "overall quality assessment"
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, brand_info)

    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            llm_result = json.loads(json_match.group())
            for issue in llm_result.get("issues", []):
                issues.append(VideoIssue(
                    timestamp=issue.get("timestamp"),
                    type=issue.get("type", "quality"),
                    description=issue.get("description", ""),
                    suggestion=issue.get("suggestion", "")
                ))
    except json.JSONDecodeError:
        pass

    # Determine pass/fail
    critical_issues = [i for i in issues if "error" in i.type or "clipping" in i.type]
    passed = len(critical_issues) == 0 and all(s >= 70 for s in scores.values())

    await notify_event_bus("video_reviewed", {
        "video_path": req.video_path,
        "passed": passed,
        "issue_count": len(issues)
    })

    return VideoReviewResponse(
        passed=passed,
        scores=VideoReviewScores(**scores),
        issues=issues
    )

@app.post("/review/text", response_model=TextReviewResponse)
async def review_text(req: TextReviewRequest):
    """Review text content for grammar, tone, and style"""
    time_ctx = get_time_context()

    issues = []
    suggestions = []
    score = 100

    # Calculate reading level
    reading_info = calculate_reading_level(req.content)

    # Check for passive voice
    if req.check_grammar:
        passive_findings = detect_passive_voice(req.content)
        passive_percentage = len(passive_findings) / max(1, reading_info["word_count"]) * 100

        if passive_percentage > 20:
            issues.append(ReviewIssue(
                type="passive_voice",
                severity=Severity.WARNING,
                location="throughout",
                description=f"High passive voice usage ({passive_percentage:.1f}% of sentences)",
                suggestion="Convert passive constructions to active voice for clearer writing"
            ))
            score -= 10

    # LLM-based review
    prompt = f"""Review this text for quality and tone.

**Content:**
{req.content[:2000]}{"..." if len(req.content) > 2000 else ""}

**Check Grammar:** {req.check_grammar}
**Check Tone:** {req.check_tone}
**Target Tone:** {req.target_tone}
**Current Reading Level:** Grade {reading_info['grade_level']} ({reading_info['difficulty']})

Analyze for:
1. Grammar and spelling errors
2. Tone consistency with target ({req.target_tone})
3. Clarity and conciseness
4. Sentence structure variety
5. Word choice appropriateness

Format as JSON:
{{
    "issues": [
        {{
            "type": "grammar|spelling|tone|clarity",
            "severity": "critical|warning|info",
            "location": "where in text",
            "description": "what's wrong",
            "suggestion": "how to fix"
        }}
    ],
    "suggestions": [
        {{
            "original": "original phrase",
            "suggested": "improved phrase",
            "reason": "why this is better"
        }}
    ],
    "score_adjustment": -10 to +5
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())

            for issue in result.get("issues", []):
                issues.append(ReviewIssue(
                    type=issue.get("type", "grammar"),
                    severity=Severity(issue.get("severity", "info")),
                    location=issue.get("location", "unknown"),
                    description=issue.get("description", ""),
                    suggestion=issue.get("suggestion", "")
                ))

            for sugg in result.get("suggestions", []):
                suggestions.append(TextSuggestion(
                    original=sugg.get("original", ""),
                    suggested=sugg.get("suggested", ""),
                    reason=sugg.get("reason", "")
                ))

            score += result.get("score_adjustment", 0)
    except json.JSONDecodeError:
        pass

    # Adjust score based on issues
    critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)
    score = max(0, score - (critical_count * 20) - (warning_count * 5))

    await notify_event_bus("text_reviewed", {
        "word_count": reading_info["word_count"],
        "score": score,
        "issue_count": len(issues)
    })

    return TextReviewResponse(
        score=score,
        issues=issues,
        suggestions=suggestions
    )

@app.post("/fact-check")
async def fact_check(req: FactCheckRequest):
    """Verify factual claims using SCHOLAR agent"""
    time_ctx = get_time_context()

    results = await call_scholar_fact_check(req.claims, req.context)

    verified_count = sum(1 for r in results if r.verified)

    await notify_event_bus("facts_checked", {
        "claim_count": len(req.claims),
        "verified_count": verified_count
    })

    return {
        "results": [r.dict() for r in results],
        "summary": {
            "total_claims": len(req.claims),
            "verified": verified_count,
            "unverified": len(req.claims) - verified_count,
            "verification_rate": verified_count / len(req.claims) if req.claims else 0
        },
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/accessibility-check")
async def check_accessibility(content_path: str, content_type: ContentType = ContentType.DOCUMENT):
    """Check content for accessibility compliance"""
    time_ctx = get_time_context()

    issues = []

    # Accessibility checklist
    prompt = f"""Review this content for accessibility compliance.

**Content Path:** {content_path}
**Content Type:** {content_type.value}

Check for WCAG 2.1 AA compliance:
1. Color contrast (4.5:1 for normal text, 3:1 for large text)
2. Alt text for images
3. Heading hierarchy (proper H1, H2, H3 structure)
4. Link text (descriptive, not "click here")
5. Reading order (logical sequence)
6. Font sizes (minimum 14pt for body)
7. Caption/transcript availability for media

Format as JSON:
{{
    "compliant": true/false,
    "issues": [
        {{
            "wcag_criterion": "1.4.3 Contrast",
            "severity": "critical|warning|info",
            "location": "where in content",
            "description": "what's wrong",
            "suggestion": "how to fix"
        }}
    ],
    "accessibility_score": 0-100
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"compliant": True, "issues": [], "accessibility_score": 100}
    except json.JSONDecodeError:
        result = {"compliant": True, "issues": [], "accessibility_score": 100}

    await notify_event_bus("accessibility_checked", {
        "content_path": content_path,
        "compliant": result.get("compliant", True),
        "score": result.get("accessibility_score", 100)
    })

    return result

@app.get("/audio-standards")
async def get_audio_standards():
    """Get audio quality standards"""
    return {
        "lufs_range": {
            "min": AUDIO_STANDARDS["lufs_min"],
            "max": AUDIO_STANDARDS["lufs_max"],
            "description": "Integrated loudness target range"
        },
        "peak_max_db": {
            "value": AUDIO_STANDARDS["peak_max_db"],
            "description": "Maximum true peak level"
        },
        "noise_floor_max_db": {
            "value": AUDIO_STANDARDS["noise_floor_max_db"],
            "description": "Maximum acceptable noise floor"
        },
        "recommendations": [
            "Use consistent audio levels throughout",
            "Apply normalization to -14 LUFS for dialogue",
            "Keep background music at least 20dB below voice",
            "Remove or reduce background noise",
            "Avoid clipping - keep peaks below -1dB"
        ]
    }

@app.post("/quick-check")
async def quick_check(content: str, check_type: str = "all"):
    """Quick inline check for text content"""
    time_ctx = get_time_context()

    reading_info = calculate_reading_level(content)
    passive_findings = detect_passive_voice(content)

    quick_issues = []

    # Reading level check
    if reading_info["grade_level"] > 12:
        quick_issues.append({
            "type": "readability",
            "message": f"Reading level is high (Grade {reading_info['grade_level']})",
            "suggestion": "Simplify sentences and vocabulary"
        })

    # Passive voice check
    if len(passive_findings) > 3:
        quick_issues.append({
            "type": "passive_voice",
            "message": f"Found {len(passive_findings)} passive voice constructions",
            "suggestion": "Convert to active voice for clarity"
        })

    # Length check
    if reading_info["word_count"] < 50:
        quick_issues.append({
            "type": "length",
            "message": "Content may be too short",
            "suggestion": "Consider adding more detail"
        })
    elif reading_info["word_count"] > 1000:
        quick_issues.append({
            "type": "length",
            "message": "Content may be too long for casual reading",
            "suggestion": "Consider breaking into sections"
        })

    return {
        "word_count": reading_info["word_count"],
        "reading_level": reading_info["grade_level"],
        "difficulty": reading_info["difficulty"],
        "avg_sentence_length": reading_info["avg_sentence_length"],
        "passive_voice_count": len(passive_findings),
        "issues": quick_issues,
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/brands")
async def list_brands():
    """List available brands for review"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/creative_brands",
                params={"select": "id,name,tone,color_primary"},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                return {"brands": response.json()}
    except Exception as e:
        return {"brands": [], "error": str(e)}

@app.get("/brands/{brand_id}")
async def get_brand(brand_id: str):
    """Get brand details"""
    brand = await get_brand_info(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail=f"Brand not found: {brand_id}")
    return brand


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8034)
