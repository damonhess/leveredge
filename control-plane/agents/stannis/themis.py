#!/usr/bin/env python3
"""
THEMIS - Elite Quality Assurance Agent (AUDITOR-QA)
Port: 8203

AI-powered quality assurance providing output review, compliance checking,
quality gates enforcement, and continuous feedback loops for all LeverEdge agents.
Named after Themis, Greek goddess of justice and fair judgment.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs decisions to aria_knowledge

CAPABILITIES:
- Deep content analysis using LLM evaluation
- Multi-dimensional quality scoring
- Compliance rule checking
- Quality gate enforcement
- Feedback loop management
- Metrics and analytics
"""

import os
import sys
import json
import re
import uuid
import httpx
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="THEMIS",
    description="Elite Quality Assurance Agent - AUDITOR-QA",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "HEPHAESTUS": "http://hephaestus:8011",
    "CHRONOS": "http://chronos:8010",
    "HADES": "http://hades:8008",
    "AEGIS": "http://aegis:8012",
    "ATHENA": "http://athena:8013",
    "HERMES": "http://hermes:8014",
    "ALOY": "http://aloy:8015",
    "ARGUS": "http://argus:8016",
    "CHIRON": "http://chiron:8017",
    "SCHOLAR": "http://scholar:8018",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("THEMIS")

# Quality dimension weights
QUALITY_DIMENSIONS = {
    "accuracy": 0.30,      # Factual correctness and precision
    "completeness": 0.25,  # All requirements addressed
    "clarity": 0.20,       # Clear, understandable output
    "relevance": 0.15,     # Appropriate for context/request
    "format": 0.10         # Proper structure and presentation
}

# Default quality threshold
DEFAULT_QUALITY_THRESHOLD = 70.0

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

def build_system_prompt(qa_context: dict) -> str:
    """Build elite QA system prompt"""
    return f"""You are THEMIS - Elite Quality Assurance Agent for LeverEdge AI.

Named after Themis, the Greek goddess of justice and fair judgment, you ensure quality and fairness in all agent outputs.

## TIME AWARENESS
- Current: {qa_context['current_time']}
- Days to Launch: {qa_context['days_to_launch']}

## YOUR IDENTITY
You are the quality brain of LeverEdge. You review outputs, enforce standards, verify compliance, and drive continuous improvement across all agents.

## CURRENT QA STATUS
- Pending Reviews: {qa_context.get('pending_reviews', 0)}
- Average Quality Score: {qa_context.get('avg_score', 'N/A')}%
- Pass Rate (24h): {qa_context.get('pass_rate', 'N/A')}%
- Active Compliance Violations: {qa_context.get('violations', 0)}

## YOUR CAPABILITIES

### Output Review
- Deep content analysis for quality assessment
- Multi-dimensional scoring (accuracy, clarity, completeness, relevance, format)
- Issue detection with severity classification
- Actionable improvement suggestions

### Compliance Checking
- Pattern-based rule matching
- Domain-specific compliance verification
- Severity-based violation classification
- Remediation recommendations

### Quality Gates
- Threshold enforcement before output approval
- Multi-check gate definitions
- Failure routing (reject, escalate, notify)
- Override management for authorized bypasses

### Feedback Loop
- Specific, actionable feedback generation
- Pattern identification across reviews
- Agent-specific improvement tracking
- Verification of improvements

### Metrics & Analytics
- Real-time quality dashboards
- Trend analysis and forecasting
- Comparative benchmarking
- Exportable reports

## QUALITY DIMENSIONS
1. **Accuracy** (30%): Factual correctness, precision, no errors
2. **Completeness** (25%): All requirements addressed, nothing missing
3. **Clarity** (20%): Clear, understandable, well-organized
4. **Relevance** (15%): Appropriate for context, addresses actual need
5. **Format** (10%): Proper structure, presentation, formatting

## TEAM COORDINATION
- Review outputs from ALL agents
- Provide feedback to agents for improvement
- Alert HERMES on critical quality issues
- Log insights to ARIA via Unified Memory
- Publish events to Event Bus

## RESPONSE FORMAT
For quality reviews:
1. Overall score and pass/fail status
2. Dimension-by-dimension breakdown
3. Specific findings with severity
4. Actionable improvement suggestions
5. Pattern observations (if recurring)

## YOUR MISSION
Maintain the highest quality standards across LeverEdge.
Fair, consistent, constructive feedback.
Every output matters.
"""

# =============================================================================
# MODELS
# =============================================================================

# Review Models
class ReviewRequest(BaseModel):
    output: str = Field(..., description="The output content to review")
    output_type: str = Field(..., description="Type of output: code, response, document, report")
    agent_name: str = Field(..., description="Name of agent that produced output")
    context: Optional[str] = Field(None, description="Optional context about the request")
    standards: Optional[List[str]] = Field(None, description="Optional specific standards to check")
    output_id: Optional[str] = Field(None, description="Optional ID for the output being reviewed")

class BatchReviewRequest(BaseModel):
    reviews: List[ReviewRequest]

class Finding(BaseModel):
    issue: str
    severity: str  # critical, high, medium, low
    location: Optional[str] = None
    suggestion: str
    category: str  # accuracy, completeness, clarity, relevance, format

class ReviewResponse(BaseModel):
    review_id: str
    agent_name: str
    output_type: str
    score: float
    passed: bool
    findings: List[Finding]
    dimension_scores: Dict[str, float]
    reviewed_at: str
    review_duration_ms: int

# Compliance Models
class ComplianceCheckRequest(BaseModel):
    output: str = Field(..., description="The output content to check")
    domain: str = Field(..., description="Domain for applicable rules")
    rules: Optional[List[str]] = Field(None, description="Optional specific rule names to check")

class ComplianceRule(BaseModel):
    name: str
    description: Optional[str] = None
    pattern: str
    severity: str  # critical, high, medium, low
    domain: str
    remediation: Optional[str] = None

class ComplianceViolation(BaseModel):
    rule_name: str
    severity: str
    matched_content: str
    remediation: str

class ComplianceResponse(BaseModel):
    compliant: bool
    violations: List[ComplianceViolation]
    remediation: List[str]

# Quality Gate Models
class GateCheckRequest(BaseModel):
    output: str = Field(..., description="The output content to check")
    output_type: str = Field(..., description="Type of output")
    agent_name: str = Field(..., description="Agent that produced the output")
    gate_name: Optional[str] = Field(None, description="Specific gate to check")
    output_id: Optional[str] = Field(None, description="ID of the output")

class QualityGate(BaseModel):
    name: str
    domain: str
    min_score: float
    checks: List[str]
    action_on_fail: str = "reject"  # reject, warn, escalate
    escalation_contact: Optional[str] = None

class GateResult(BaseModel):
    gate_name: str
    passed: bool
    score: float
    min_score: float
    action: str

class GateCheckResponse(BaseModel):
    passed: bool
    gates: List[GateResult]
    action: str  # proceed, revise, escalate

class GateOverrideRequest(BaseModel):
    output_id: str
    gate_name: str
    reason: str
    override_by: str

# Feedback Models
class FeedbackRequest(BaseModel):
    review_id: str
    agent_name: str
    include_patterns: bool = True

class FeedbackAcknowledgeRequest(BaseModel):
    improvements: Optional[List[str]] = None

class FeedbackVerifyRequest(BaseModel):
    new_review_id: str
    expected_improvements: List[str]

# Metrics Models
class MetricsExportRequest(BaseModel):
    agent_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    format: str = "json"  # json, csv

# Standards Models
class QualityStandard(BaseModel):
    domain: str
    name: str
    criteria: List[str]
    weight: float = 1.0

# =============================================================================
# INTER-AGENT COMMUNICATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus for all agents to see"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "source_agent": "THEMIS",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[THEMIS] Event bus notification failed: {e}")

async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[THEMIS] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "THEMIS"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[THEMIS] HERMES notification failed: {e}")

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
                    "p_content": f"{content}\n\n[Logged by THEMIS at {time_ctx['current_datetime']}]",
                    "p_subcategory": "themis",
                    "p_source": "themis",
                    "p_importance": importance
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"[THEMIS] Knowledge update failed: {e}")
        return False

# =============================================================================
# DATABASE HELPERS
# =============================================================================

async def db_insert(table: str, data: dict) -> dict:
    """Insert record into database"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY or SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                timeout=10.0
            )
            if response.status_code in [200, 201]:
                result = response.json()
                return result[0] if isinstance(result, list) and result else result
            else:
                print(f"[THEMIS] DB insert failed: {response.status_code} - {response.text}")
                return {}
    except Exception as e:
        print(f"[THEMIS] DB insert error: {e}")
        return {}

async def db_select(table: str, filters: dict = None, limit: int = 100, order: str = None) -> List[dict]:
    """Select records from database"""
    try:
        params = {}
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        if limit:
            params["limit"] = limit
        if order:
            params["order"] = order

        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY or SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}"
                },
                params=params,
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return []
    except Exception as e:
        print(f"[THEMIS] DB select error: {e}")
        return []

async def db_update(table: str, filters: dict, data: dict) -> dict:
    """Update records in database"""
    try:
        params = {f"{key}": f"eq.{value}" for key, value in filters.items()}
        async with httpx.AsyncClient() as http_client:
            response = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY or SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                params=params,
                json=data,
                timeout=10.0
            )
            if response.status_code == 200:
                result = response.json()
                return result[0] if isinstance(result, list) and result else result
            return {}
    except Exception as e:
        print(f"[THEMIS] DB update error: {e}")
        return {}

async def db_delete(table: str, filters: dict) -> bool:
    """Delete records from database"""
    try:
        params = {f"{key}": f"eq.{value}" for key, value in filters.items()}
        async with httpx.AsyncClient() as http_client:
            response = await http_client.delete(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY or SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY or SUPABASE_KEY}"
                },
                params=params,
                timeout=10.0
            )
            return response.status_code in [200, 204]
    except Exception as e:
        print(f"[THEMIS] DB delete error: {e}")
        return False

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, qa_context: dict) -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        system_prompt = build_system_prompt(qa_context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="THEMIS",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": qa_context.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

async def get_qa_context() -> dict:
    """Build QA context for system prompt"""
    time_ctx = get_time_context()

    # Try to get metrics from database
    try:
        # Get pending reviews count (reviews from last hour without feedback)
        pending_reviews = 0

        # Get average score from recent reviews
        reviews = await db_select("reviews", limit=100, order="reviewed_at.desc")
        if reviews:
            scores = [r.get("score", 0) for r in reviews if r.get("score")]
            avg_score = sum(scores) / len(scores) if scores else 0
            passed_count = sum(1 for r in reviews if r.get("passed", False))
            pass_rate = (passed_count / len(reviews) * 100) if reviews else 0
        else:
            avg_score = 0
            pass_rate = 0

        # Get active violations count
        violations = 0

    except Exception as e:
        print(f"[THEMIS] Error fetching QA context: {e}")
        avg_score = 0
        pass_rate = 0
        pending_reviews = 0
        violations = 0

    return {
        **time_ctx,
        "pending_reviews": pending_reviews,
        "avg_score": round(avg_score, 1),
        "pass_rate": round(pass_rate, 1),
        "violations": violations
    }

# =============================================================================
# QUALITY REVIEW LOGIC
# =============================================================================

async def perform_quality_review(
    output: str,
    output_type: str,
    agent_name: str,
    context: str = None,
    standards: List[str] = None
) -> dict:
    """Perform AI-powered quality review"""
    start_time = datetime.now()
    qa_context = await get_qa_context()

    # Build review prompt
    prompt = f"""Review this {output_type} output from agent {agent_name} for quality.

## OUTPUT TO REVIEW:
```
{output[:8000]}
```

## CONTEXT:
{context or 'No additional context provided'}

## STANDARDS TO CHECK:
{', '.join(standards) if standards else 'All standard quality criteria'}

## YOUR TASK:
Analyze this output and provide a comprehensive quality assessment.

Return your assessment as a JSON object with this exact structure:
{{
    "overall_score": <0-100>,
    "dimension_scores": {{
        "accuracy": <0-100>,
        "completeness": <0-100>,
        "clarity": <0-100>,
        "relevance": <0-100>,
        "format": <0-100>
    }},
    "findings": [
        {{
            "issue": "<description of the issue>",
            "severity": "<critical|high|medium|low>",
            "location": "<where in the output, if applicable>",
            "suggestion": "<how to fix it>",
            "category": "<accuracy|completeness|clarity|relevance|format>"
        }}
    ],
    "summary": "<brief overall assessment>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "improvement_priority": "<most important thing to improve>"
}}

Be fair but rigorous. Quality matters.
"""

    messages = [{"role": "user", "content": prompt}]
    response_text = await call_llm(messages, qa_context)

    # Parse JSON from response
    try:
        # Extract JSON from response (it might be wrapped in markdown)
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            review_data = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")
    except Exception as e:
        print(f"[THEMIS] Failed to parse review response: {e}")
        # Return default review structure
        review_data = {
            "overall_score": 50,
            "dimension_scores": {
                "accuracy": 50,
                "completeness": 50,
                "clarity": 50,
                "relevance": 50,
                "format": 50
            },
            "findings": [{
                "issue": "Unable to fully analyze output",
                "severity": "medium",
                "location": None,
                "suggestion": "Please retry the review",
                "category": "accuracy"
            }],
            "summary": "Review could not be completed properly",
            "strengths": [],
            "improvement_priority": "Retry review"
        }

    end_time = datetime.now()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    # Calculate pass/fail
    passed = review_data.get("overall_score", 0) >= DEFAULT_QUALITY_THRESHOLD

    return {
        "score": review_data.get("overall_score", 0),
        "passed": passed,
        "dimension_scores": review_data.get("dimension_scores", {}),
        "findings": review_data.get("findings", []),
        "summary": review_data.get("summary", ""),
        "strengths": review_data.get("strengths", []),
        "improvement_priority": review_data.get("improvement_priority", ""),
        "review_duration_ms": duration_ms
    }

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check with QA system overview"""
    time_ctx = get_time_context()
    qa_ctx = await get_qa_context()

    return {
        "status": "healthy",
        "agent": "THEMIS",
        "alias": "AUDITOR-QA",
        "role": "Quality Assurance",
        "port": 8203,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase'],
        "qa_stats": {
            "pending_reviews": qa_ctx['pending_reviews'],
            "avg_score": qa_ctx['avg_score'],
            "pass_rate": qa_ctx['pass_rate'],
            "active_violations": qa_ctx['violations']
        }
    }

@app.get("/status")
async def status():
    """Real-time quality metrics summary"""
    qa_ctx = await get_qa_context()

    # Get recent review stats
    reviews = await db_select("reviews", limit=50, order="reviewed_at.desc")

    # Calculate stats
    if reviews:
        scores = [r.get("score", 0) for r in reviews]
        avg_score = sum(scores) / len(scores)
        passed_count = sum(1 for r in reviews if r.get("passed", False))
        pass_rate = passed_count / len(reviews) * 100

        # Group by agent
        by_agent = {}
        for r in reviews:
            agent = r.get("agent_name", "unknown")
            if agent not in by_agent:
                by_agent[agent] = {"count": 0, "total_score": 0, "passed": 0}
            by_agent[agent]["count"] += 1
            by_agent[agent]["total_score"] += r.get("score", 0)
            if r.get("passed"):
                by_agent[agent]["passed"] += 1

        agent_stats = {
            agent: {
                "reviews": data["count"],
                "avg_score": round(data["total_score"] / data["count"], 1),
                "pass_rate": round(data["passed"] / data["count"] * 100, 1)
            }
            for agent, data in by_agent.items()
        }
    else:
        avg_score = 0
        pass_rate = 0
        agent_stats = {}

    return {
        "timestamp": qa_ctx['current_datetime'],
        "overall": {
            "average_score": round(avg_score, 1),
            "pass_rate": round(pass_rate, 1),
            "reviews_last_24h": len(reviews),
            "pending_reviews": qa_ctx['pending_reviews'],
            "active_violations": qa_ctx['violations']
        },
        "by_agent": agent_stats,
        "quality_threshold": DEFAULT_QUALITY_THRESHOLD
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    qa_ctx = await get_qa_context()
    reviews = await db_select("reviews", limit=100, order="reviewed_at.desc")

    scores = [r.get("score", 0) for r in reviews] if reviews else []
    avg_score = sum(scores) / len(scores) if scores else 0

    metrics_output = f"""# HELP themis_quality_score_avg Average quality score
# TYPE themis_quality_score_avg gauge
themis_quality_score_avg {avg_score:.2f}

# HELP themis_reviews_total Total reviews performed
# TYPE themis_reviews_total counter
themis_reviews_total {len(reviews)}

# HELP themis_pass_rate Quality gate pass rate
# TYPE themis_pass_rate gauge
themis_pass_rate {qa_ctx['pass_rate']:.2f}

# HELP themis_violations_active Active compliance violations
# TYPE themis_violations_active gauge
themis_violations_active {qa_ctx['violations']}

# HELP themis_days_to_launch Days until launch
# TYPE themis_days_to_launch gauge
themis_days_to_launch {qa_ctx['days_to_launch']}
"""
    return metrics_output

# =============================================================================
# OUTPUT REVIEW ENDPOINTS
# =============================================================================

@app.post("/review", response_model=ReviewResponse)
async def review_output(req: ReviewRequest):
    """Submit output for quality review"""
    review_id = str(uuid.uuid4())
    output_id = req.output_id or str(uuid.uuid4())

    # Perform review
    review_result = await perform_quality_review(
        output=req.output,
        output_type=req.output_type,
        agent_name=req.agent_name,
        context=req.context,
        standards=req.standards
    )

    # Store review in database
    review_record = {
        "id": review_id,
        "agent_name": req.agent_name,
        "output_id": output_id,
        "output_type": req.output_type,
        "score": review_result["score"],
        "passed": review_result["passed"],
        "findings": review_result["findings"],
        "dimension_scores": review_result["dimension_scores"],
        "review_duration_ms": review_result["review_duration_ms"],
        "reviewer_model": "claude-sonnet-4-20250514"
    }
    await db_insert("reviews", review_record)

    # Publish event
    await notify_event_bus("qa.review.completed", {
        "review_id": review_id,
        "agent_name": req.agent_name,
        "output_type": req.output_type,
        "score": review_result["score"],
        "passed": review_result["passed"],
        "findings_count": len(review_result["findings"])
    })

    # If failed, alert HERMES for critical issues
    if not review_result["passed"]:
        critical_findings = [f for f in review_result["findings"] if f.get("severity") == "critical"]
        if critical_findings:
            await notify_hermes(
                f"Critical quality issue in {req.agent_name} output: {critical_findings[0].get('issue', 'Unknown')}",
                priority="high"
            )

    # Log to ARIA knowledge
    await update_aria_knowledge(
        category="quality",
        title=f"Quality Review: {req.agent_name} - {review_result['score']}%",
        content=f"Agent: {req.agent_name}\nType: {req.output_type}\nScore: {review_result['score']}%\nPassed: {review_result['passed']}\nFindings: {len(review_result['findings'])}",
        importance="high" if not review_result["passed"] else "normal"
    )

    return ReviewResponse(
        review_id=review_id,
        agent_name=req.agent_name,
        output_type=req.output_type,
        score=review_result["score"],
        passed=review_result["passed"],
        findings=[Finding(**f) for f in review_result["findings"]],
        dimension_scores=review_result["dimension_scores"],
        reviewed_at=datetime.now().isoformat(),
        review_duration_ms=review_result["review_duration_ms"]
    )

@app.get("/reviews")
async def list_reviews(
    agent_name: Optional[str] = None,
    output_type: Optional[str] = None,
    passed: Optional[bool] = None,
    limit: int = Query(50, le=200)
):
    """List recent reviews with optional filters"""
    filters = {}
    if agent_name:
        filters["agent_name"] = agent_name
    if output_type:
        filters["output_type"] = output_type
    if passed is not None:
        filters["passed"] = passed

    reviews = await db_select("reviews", filters=filters if filters else None, limit=limit, order="reviewed_at.desc")
    return {"reviews": reviews, "count": len(reviews)}

@app.get("/reviews/{review_id}")
async def get_review(review_id: str):
    """Get review detail with findings"""
    reviews = await db_select("reviews", filters={"id": review_id})
    if not reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    return reviews[0]

@app.get("/reviews/agent/{agent_name}")
async def get_agent_reviews(agent_name: str, limit: int = Query(50, le=200)):
    """Get reviews for specific agent"""
    reviews = await db_select("reviews", filters={"agent_name": agent_name}, limit=limit, order="reviewed_at.desc")

    if reviews:
        scores = [r.get("score", 0) for r in reviews]
        avg_score = sum(scores) / len(scores)
        passed_count = sum(1 for r in reviews if r.get("passed", False))
        pass_rate = passed_count / len(reviews) * 100
    else:
        avg_score = 0
        pass_rate = 0

    return {
        "agent_name": agent_name,
        "total_reviews": len(reviews),
        "average_score": round(avg_score, 1),
        "pass_rate": round(pass_rate, 1),
        "reviews": reviews
    }

@app.get("/reviews/summary")
async def reviews_summary():
    """Executive quality summary"""
    reviews = await db_select("reviews", limit=200, order="reviewed_at.desc")

    if not reviews:
        return {
            "summary": "No reviews performed yet",
            "recommendations": ["Start reviewing agent outputs to build quality metrics"]
        }

    # Calculate overall stats
    scores = [r.get("score", 0) for r in reviews]
    avg_score = sum(scores) / len(scores)
    passed_count = sum(1 for r in reviews if r.get("passed", False))

    # Group by agent
    by_agent = {}
    for r in reviews:
        agent = r.get("agent_name", "unknown")
        if agent not in by_agent:
            by_agent[agent] = {"scores": [], "passed": 0, "findings": []}
        by_agent[agent]["scores"].append(r.get("score", 0))
        if r.get("passed"):
            by_agent[agent]["passed"] += 1
        by_agent[agent]["findings"].extend(r.get("findings", []))

    # Build agent summaries
    agent_summaries = []
    for agent, data in by_agent.items():
        agent_avg = sum(data["scores"]) / len(data["scores"])
        agent_summaries.append({
            "agent": agent,
            "reviews": len(data["scores"]),
            "avg_score": round(agent_avg, 1),
            "pass_rate": round(data["passed"] / len(data["scores"]) * 100, 1),
            "common_issues": list(set(f.get("category", "") for f in data["findings"]))[:3]
        })

    # Sort by score (lowest first for attention)
    agent_summaries.sort(key=lambda x: x["avg_score"])

    return {
        "period": "last 200 reviews",
        "overall": {
            "total_reviews": len(reviews),
            "average_score": round(avg_score, 1),
            "pass_rate": round(passed_count / len(reviews) * 100, 1)
        },
        "by_agent": agent_summaries,
        "needs_attention": [a for a in agent_summaries if a["avg_score"] < DEFAULT_QUALITY_THRESHOLD][:3],
        "top_performers": sorted(agent_summaries, key=lambda x: -x["avg_score"])[:3]
    }

@app.post("/review/batch")
async def batch_review(req: BatchReviewRequest):
    """Batch review multiple outputs"""
    results = []
    for review_req in req.reviews:
        try:
            result = await review_output(review_req)
            results.append({"status": "success", "review": result})
        except Exception as e:
            results.append({"status": "error", "error": str(e), "agent_name": review_req.agent_name})

    successful = sum(1 for r in results if r["status"] == "success")
    return {
        "total": len(req.reviews),
        "successful": successful,
        "failed": len(req.reviews) - successful,
        "results": results
    }

# =============================================================================
# COMPLIANCE ENDPOINTS
# =============================================================================

@app.post("/compliance/check", response_model=ComplianceResponse)
async def check_compliance(req: ComplianceCheckRequest):
    """Check output against compliance rules"""
    # Get applicable rules
    rules = await db_select("compliance_rules", filters={"domain": req.domain, "active": True})

    if req.rules:
        # Filter to specific rules
        rules = [r for r in rules if r.get("name") in req.rules]

    violations = []

    for rule in rules:
        pattern = rule.get("pattern", "")
        try:
            if re.search(pattern, req.output, re.IGNORECASE):
                # Found a match - this is a violation
                match = re.search(pattern, req.output, re.IGNORECASE)
                violations.append(ComplianceViolation(
                    rule_name=rule.get("name", "unknown"),
                    severity=rule.get("severity", "medium"),
                    matched_content=match.group()[:100] if match else "",
                    remediation=rule.get("remediation", "Review and correct the flagged content")
                ))
        except re.error as e:
            print(f"[THEMIS] Invalid regex pattern: {pattern} - {e}")

    # Publish event if violations found
    if violations:
        await notify_event_bus("qa.compliance.violation", {
            "domain": req.domain,
            "violation_count": len(violations),
            "severities": [v.severity for v in violations]
        })

        # Alert on critical violations
        critical = [v for v in violations if v.severity == "critical"]
        if critical:
            await notify_hermes(
                f"Critical compliance violation in {req.domain}: {critical[0].rule_name}",
                priority="high"
            )

    return ComplianceResponse(
        compliant=len(violations) == 0,
        violations=violations,
        remediation=[v.remediation for v in violations]
    )

@app.get("/compliance/rules")
async def list_compliance_rules(domain: Optional[str] = None, active: bool = True):
    """List all compliance rules"""
    filters = {"active": active}
    if domain:
        filters["domain"] = domain

    rules = await db_select("compliance_rules", filters=filters, order="severity.asc")
    return {"rules": rules, "count": len(rules)}

@app.post("/compliance/rules")
async def create_compliance_rule(rule: ComplianceRule):
    """Create new compliance rule"""
    rule_data = {
        "name": rule.name,
        "description": rule.description,
        "pattern": rule.pattern,
        "severity": rule.severity,
        "domain": rule.domain,
        "remediation": rule.remediation,
        "active": True
    }

    result = await db_insert("compliance_rules", rule_data)
    if result:
        await notify_event_bus("compliance.rule.created", {"name": rule.name, "domain": rule.domain})

    return {"status": "created", "rule": result}

@app.put("/compliance/rules/{rule_id}")
async def update_compliance_rule(rule_id: str, rule: ComplianceRule):
    """Update compliance rule"""
    rule_data = {
        "name": rule.name,
        "description": rule.description,
        "pattern": rule.pattern,
        "severity": rule.severity,
        "domain": rule.domain,
        "remediation": rule.remediation
    }

    result = await db_update("compliance_rules", {"id": rule_id}, rule_data)
    return {"status": "updated", "rule": result}

@app.delete("/compliance/rules/{rule_id}")
async def delete_compliance_rule(rule_id: str):
    """Delete compliance rule"""
    success = await db_delete("compliance_rules", {"id": rule_id})
    return {"status": "deleted" if success else "failed"}

@app.get("/compliance/violations")
async def list_violations(domain: Optional[str] = None, limit: int = Query(50, le=200)):
    """Get recent compliance violations from reviews"""
    reviews = await db_select("reviews", limit=limit, order="reviewed_at.desc")

    violations = []
    for review in reviews:
        findings = review.get("findings", [])
        for finding in findings:
            if finding.get("severity") in ["critical", "high"]:
                violations.append({
                    "review_id": review.get("id"),
                    "agent_name": review.get("agent_name"),
                    "issue": finding.get("issue"),
                    "severity": finding.get("severity"),
                    "category": finding.get("category"),
                    "reviewed_at": review.get("reviewed_at")
                })

    if domain:
        violations = [v for v in violations if v.get("category") == domain]

    return {"violations": violations, "count": len(violations)}

# =============================================================================
# QUALITY GATE ENDPOINTS
# =============================================================================

@app.post("/gate/check", response_model=GateCheckResponse)
async def check_gate(req: GateCheckRequest):
    """Check if output passes quality gate"""
    # Get applicable gates
    filters = {"domain": req.output_type, "active": True}
    gates = await db_select("quality_gates", filters=filters)

    if req.gate_name:
        gates = [g for g in gates if g.get("name") == req.gate_name]

    if not gates:
        # No gates defined, pass by default
        return GateCheckResponse(
            passed=True,
            gates=[],
            action="proceed"
        )

    # Perform review to get score
    review_result = await perform_quality_review(
        output=req.output,
        output_type=req.output_type,
        agent_name=req.agent_name,
        context=None,
        standards=None
    )

    gate_results = []
    overall_passed = True
    action = "proceed"

    for gate in gates:
        min_score = gate.get("min_score", DEFAULT_QUALITY_THRESHOLD)
        passed = review_result["score"] >= min_score

        gate_results.append(GateResult(
            gate_name=gate.get("name", "unknown"),
            passed=passed,
            score=review_result["score"],
            min_score=min_score,
            action=gate.get("action_on_fail", "reject") if not passed else "proceed"
        ))

        if not passed:
            overall_passed = False
            gate_action = gate.get("action_on_fail", "reject")
            if gate_action == "escalate":
                action = "escalate"
            elif action != "escalate":
                action = "revise"

    # Publish events
    if overall_passed:
        await notify_event_bus("qa.gate.passed", {
            "agent_name": req.agent_name,
            "output_type": req.output_type,
            "score": review_result["score"]
        })
    else:
        await notify_event_bus("qa.gate.failed", {
            "agent_name": req.agent_name,
            "output_type": req.output_type,
            "score": review_result["score"],
            "action": action
        })

        if action == "escalate":
            await notify_hermes(
                f"Quality gate escalation: {req.agent_name} scored {review_result['score']}%",
                priority="high"
            )

    return GateCheckResponse(
        passed=overall_passed,
        gates=gate_results,
        action=action
    )

@app.get("/gates")
async def list_gates(domain: Optional[str] = None, active: bool = True):
    """List all quality gates"""
    filters = {"active": active}
    if domain:
        filters["domain"] = domain

    gates = await db_select("quality_gates", filters=filters)
    return {"gates": gates, "count": len(gates)}

@app.post("/gates")
async def create_gate(gate: QualityGate):
    """Create new quality gate"""
    gate_data = {
        "name": gate.name,
        "domain": gate.domain,
        "min_score": gate.min_score,
        "checks": gate.checks,
        "action_on_fail": gate.action_on_fail,
        "escalation_contact": gate.escalation_contact,
        "active": True
    }

    result = await db_insert("quality_gates", gate_data)
    if result:
        await notify_event_bus("gate.created", {"name": gate.name, "domain": gate.domain})

    return {"status": "created", "gate": result}

@app.put("/gates/{gate_id}")
async def update_gate(gate_id: str, gate: QualityGate):
    """Update quality gate"""
    gate_data = {
        "name": gate.name,
        "domain": gate.domain,
        "min_score": gate.min_score,
        "checks": gate.checks,
        "action_on_fail": gate.action_on_fail,
        "escalation_contact": gate.escalation_contact
    }

    result = await db_update("quality_gates", {"id": gate_id}, gate_data)
    return {"status": "updated", "gate": result}

@app.delete("/gates/{gate_id}")
async def delete_gate(gate_id: str):
    """Delete quality gate"""
    success = await db_delete("quality_gates", {"id": gate_id})
    return {"status": "deleted" if success else "failed"}

@app.get("/gates/status/{output_id}")
async def get_gate_status(output_id: str):
    """Get gate status for specific output"""
    reviews = await db_select("reviews", filters={"output_id": output_id})
    if not reviews:
        return {"output_id": output_id, "status": "not_reviewed", "gates": []}

    review = reviews[0]
    return {
        "output_id": output_id,
        "status": "passed" if review.get("passed") else "failed",
        "score": review.get("score"),
        "reviewed_at": review.get("reviewed_at")
    }

@app.post("/gates/override")
async def override_gate(req: GateOverrideRequest):
    """Override gate decision (authorized)"""
    # Log the override
    await update_aria_knowledge(
        category="decision",
        title=f"Gate Override: {req.gate_name}",
        content=f"Output: {req.output_id}\nGate: {req.gate_name}\nReason: {req.reason}\nOverride by: {req.override_by}",
        importance="high"
    )

    await notify_event_bus("qa.gate.override", {
        "output_id": req.output_id,
        "gate_name": req.gate_name,
        "override_by": req.override_by
    })

    return {
        "status": "override_applied",
        "output_id": req.output_id,
        "gate_name": req.gate_name,
        "override_by": req.override_by,
        "logged": True
    }

# =============================================================================
# FEEDBACK ENDPOINTS
# =============================================================================

@app.post("/feedback")
async def generate_feedback(req: FeedbackRequest):
    """Generate feedback for agent based on review"""
    # Get the review
    reviews = await db_select("reviews", filters={"id": req.review_id})
    if not reviews:
        raise HTTPException(status_code=404, detail="Review not found")

    review = reviews[0]
    findings = review.get("findings", [])

    # Get historical patterns for this agent
    patterns = []
    if req.include_patterns:
        agent_reviews = await db_select("reviews", filters={"agent_name": req.agent_name}, limit=50, order="reviewed_at.desc")

        # Analyze patterns
        issue_counts = {}
        for r in agent_reviews:
            for f in r.get("findings", []):
                category = f.get("category", "unknown")
                issue_counts[category] = issue_counts.get(category, 0) + 1

        # Find recurring issues (>3 occurrences)
        patterns = [
            {"category": cat, "occurrences": count, "type": "pattern"}
            for cat, count in issue_counts.items()
            if count >= 3
        ]

    # Determine feedback type
    if review.get("score", 0) >= 90:
        feedback_type = "praise"
        feedback = f"Excellent work! Score: {review.get('score')}%. This output demonstrates strong quality across all dimensions."
    elif review.get("score", 0) >= 70:
        feedback_type = "suggestion"
        top_issue = findings[0] if findings else None
        feedback = f"Good output (Score: {review.get('score')}%). Main improvement area: {top_issue.get('category', 'general') if top_issue else 'minor refinements'}."
    else:
        feedback_type = "correction"
        critical = [f for f in findings if f.get("severity") in ["critical", "high"]]
        feedback = f"Needs improvement (Score: {review.get('score')}%). {len(critical)} critical/high issues found. Focus on: {', '.join(set(f.get('category', '') for f in critical[:3]))}."

    # Store feedback
    feedback_data = {
        "review_id": req.review_id,
        "agent_name": req.agent_name,
        "feedback": feedback,
        "feedback_type": feedback_type,
        "acknowledged": False
    }

    result = await db_insert("feedback_log", feedback_data)

    return {
        "feedback_id": result.get("id") if result else None,
        "agent_name": req.agent_name,
        "review_id": req.review_id,
        "feedback_type": feedback_type,
        "feedback": feedback,
        "patterns": patterns,
        "specific_issues": findings[:5],
        "improvement_priority": findings[0].get("suggestion") if findings else None
    }

@app.get("/feedback/agent/{agent_name}")
async def get_agent_feedback(agent_name: str, limit: int = Query(50, le=200)):
    """Get feedback history for agent"""
    feedback = await db_select("feedback_log", filters={"agent_name": agent_name}, limit=limit, order="created_at.desc")

    return {
        "agent_name": agent_name,
        "total_feedback": len(feedback),
        "unacknowledged": sum(1 for f in feedback if not f.get("acknowledged", False)),
        "feedback": feedback
    }

@app.post("/feedback/{feedback_id}/acknowledge")
async def acknowledge_feedback(feedback_id: str, req: FeedbackAcknowledgeRequest):
    """Mark feedback as acknowledged"""
    update_data = {
        "acknowledged": True,
        "acknowledged_at": datetime.now().isoformat(),
        "improvements": req.improvements or []
    }

    result = await db_update("feedback_log", {"id": feedback_id}, update_data)
    return {"status": "acknowledged", "feedback": result}

@app.post("/feedback/{feedback_id}/verify")
async def verify_improvement(feedback_id: str, req: FeedbackVerifyRequest):
    """Verify improvement was made"""
    # Get the new review
    new_reviews = await db_select("reviews", filters={"id": req.new_review_id})
    if not new_reviews:
        raise HTTPException(status_code=404, detail="New review not found")

    new_review = new_reviews[0]
    new_findings = new_review.get("findings", [])

    # Check if expected improvements were addressed
    new_issues = set(f.get("category", "") for f in new_findings)
    improvements_verified = []

    for expected in req.expected_improvements:
        if expected not in new_issues:
            improvements_verified.append(expected)

    verified = len(improvements_verified) == len(req.expected_improvements)

    # Update feedback record
    await db_update("feedback_log", {"id": feedback_id}, {
        "verified": verified,
        "improvements": improvements_verified
    })

    return {
        "verified": verified,
        "expected": req.expected_improvements,
        "actually_improved": improvements_verified,
        "remaining_issues": list(new_issues)
    }

@app.get("/feedback/pending")
async def get_pending_feedback(agent_name: Optional[str] = None):
    """Get unacknowledged feedback"""
    filters = {"acknowledged": False}
    if agent_name:
        filters["agent_name"] = agent_name

    feedback = await db_select("feedback_log", filters=filters, order="created_at.desc")
    return {"pending": feedback, "count": len(feedback)}

# =============================================================================
# METRICS & ANALYTICS ENDPOINTS
# =============================================================================

@app.get("/metrics/agent/{agent_name}")
async def get_agent_metrics(agent_name: str, days: int = Query(30, le=90)):
    """Get quality metrics for specific agent"""
    reviews = await db_select("reviews", filters={"agent_name": agent_name}, limit=500, order="reviewed_at.desc")

    if not reviews:
        return {"agent_name": agent_name, "message": "No reviews found"}

    # Calculate metrics
    scores = [r.get("score", 0) for r in reviews]
    passed_count = sum(1 for r in reviews if r.get("passed", False))

    # Get dimension breakdowns
    dimension_totals = {dim: 0 for dim in QUALITY_DIMENSIONS.keys()}
    dimension_counts = {dim: 0 for dim in QUALITY_DIMENSIONS.keys()}

    for r in reviews:
        dim_scores = r.get("dimension_scores", {})
        for dim in QUALITY_DIMENSIONS.keys():
            if dim in dim_scores:
                dimension_totals[dim] += dim_scores[dim]
                dimension_counts[dim] += 1

    dimension_averages = {
        dim: round(dimension_totals[dim] / dimension_counts[dim], 1) if dimension_counts[dim] > 0 else 0
        for dim in QUALITY_DIMENSIONS.keys()
    }

    # Find common issues
    all_findings = []
    for r in reviews:
        all_findings.extend(r.get("findings", []))

    issue_counts = {}
    for f in all_findings:
        cat = f.get("category", "unknown")
        issue_counts[cat] = issue_counts.get(cat, 0) + 1

    common_issues = sorted(issue_counts.items(), key=lambda x: -x[1])[:5]

    return {
        "agent_name": agent_name,
        "period": f"last {days} days",
        "total_reviews": len(reviews),
        "avg_score": round(sum(scores) / len(scores), 1),
        "pass_rate": round(passed_count / len(reviews) * 100, 1),
        "min_score": min(scores),
        "max_score": max(scores),
        "dimension_averages": dimension_averages,
        "common_issues": [{"category": cat, "count": count} for cat, count in common_issues],
        "trend": "stable"  # Would calculate from time series data
    }

@app.get("/metrics/trends")
async def get_trends(days: int = Query(30, le=90), agent_name: Optional[str] = None):
    """Get quality trends over time"""
    filters = {"agent_name": agent_name} if agent_name else None
    reviews = await db_select("reviews", filters=filters, limit=1000, order="reviewed_at.desc")

    if not reviews:
        return {"message": "No reviews found for trend analysis"}

    # Group by day
    daily_data = {}
    for r in reviews:
        reviewed_at = r.get("reviewed_at", "")[:10]  # Get date part
        if reviewed_at not in daily_data:
            daily_data[reviewed_at] = {"scores": [], "passed": 0, "total": 0}
        daily_data[reviewed_at]["scores"].append(r.get("score", 0))
        daily_data[reviewed_at]["total"] += 1
        if r.get("passed"):
            daily_data[reviewed_at]["passed"] += 1

    # Build trend data
    trend_data = []
    for date_str, data in sorted(daily_data.items()):
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        pass_rate = data["passed"] / data["total"] * 100 if data["total"] > 0 else 0
        trend_data.append({
            "date": date_str,
            "avg_score": round(avg_score, 1),
            "pass_rate": round(pass_rate, 1),
            "review_count": data["total"]
        })

    # Calculate overall direction
    if len(trend_data) >= 7:
        recent = trend_data[-7:]
        early = trend_data[:7]
        recent_avg = sum(d["avg_score"] for d in recent) / len(recent)
        early_avg = sum(d["avg_score"] for d in early) / len(early)
        direction = "improving" if recent_avg > early_avg else "declining" if recent_avg < early_avg else "stable"
    else:
        direction = "insufficient_data"

    return {
        "period": f"last {days} days",
        "agent_name": agent_name or "all",
        "data_points": trend_data[-days:],
        "direction": direction,
        "total_reviews": len(reviews)
    }

@app.get("/metrics/comparison")
async def compare_agents():
    """Compare quality scores across agents"""
    reviews = await db_select("reviews", limit=500, order="reviewed_at.desc")

    if not reviews:
        return {"message": "No reviews found for comparison"}

    # Group by agent
    by_agent = {}
    for r in reviews:
        agent = r.get("agent_name", "unknown")
        if agent not in by_agent:
            by_agent[agent] = {"scores": [], "passed": 0}
        by_agent[agent]["scores"].append(r.get("score", 0))
        if r.get("passed"):
            by_agent[agent]["passed"] += 1

    # Calculate comparison data
    comparison = []
    for agent, data in by_agent.items():
        comparison.append({
            "agent_name": agent,
            "reviews": len(data["scores"]),
            "avg_score": round(sum(data["scores"]) / len(data["scores"]), 1),
            "pass_rate": round(data["passed"] / len(data["scores"]) * 100, 1),
            "min_score": min(data["scores"]),
            "max_score": max(data["scores"])
        })

    # Sort by average score
    comparison.sort(key=lambda x: -x["avg_score"])

    return {
        "comparison": comparison,
        "best_performer": comparison[0]["agent_name"] if comparison else None,
        "needs_improvement": comparison[-1]["agent_name"] if comparison else None
    }

@app.get("/metrics/issues")
async def get_common_issues():
    """Get common issues across all agents"""
    reviews = await db_select("reviews", limit=500, order="reviewed_at.desc")

    # Collect all findings
    all_findings = []
    for r in reviews:
        findings = r.get("findings", [])
        for f in findings:
            all_findings.append({
                **f,
                "agent_name": r.get("agent_name"),
                "output_type": r.get("output_type")
            })

    # Group by category and severity
    by_category = {}
    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for f in all_findings:
        cat = f.get("category", "unknown")
        sev = f.get("severity", "medium")

        if cat not in by_category:
            by_category[cat] = {"count": 0, "agents": set()}
        by_category[cat]["count"] += 1
        by_category[cat]["agents"].add(f.get("agent_name", ""))

        if sev in by_severity:
            by_severity[sev] += 1

    # Build response
    issues = [
        {
            "category": cat,
            "count": data["count"],
            "affected_agents": len(data["agents"]),
            "agents": list(data["agents"])[:5]
        }
        for cat, data in sorted(by_category.items(), key=lambda x: -x[1]["count"])
    ]

    return {
        "total_issues": len(all_findings),
        "by_category": issues,
        "by_severity": by_severity,
        "most_common": issues[0] if issues else None
    }

@app.post("/metrics/export")
async def export_metrics(req: MetricsExportRequest):
    """Export metrics report"""
    filters = {}
    if req.agent_name:
        filters["agent_name"] = req.agent_name

    reviews = await db_select("reviews", filters=filters if filters else None, limit=1000, order="reviewed_at.desc")

    if req.format == "json":
        return {
            "export_date": datetime.now().isoformat(),
            "filters": {
                "agent_name": req.agent_name,
                "start_date": req.start_date,
                "end_date": req.end_date
            },
            "reviews": reviews
        }
    else:
        # CSV format
        csv_lines = ["review_id,agent_name,output_type,score,passed,reviewed_at"]
        for r in reviews:
            csv_lines.append(f"{r.get('id','')},{r.get('agent_name','')},{r.get('output_type','')},{r.get('score','')},{r.get('passed','')},{r.get('reviewed_at','')}")
        return "\n".join(csv_lines)

@app.get("/metrics/dashboard")
async def get_dashboard():
    """Get full dashboard data"""
    qa_ctx = await get_qa_context()
    reviews = await db_select("reviews", limit=200, order="reviewed_at.desc")

    # Calculate overview
    if reviews:
        scores = [r.get("score", 0) for r in reviews]
        passed_count = sum(1 for r in reviews if r.get("passed", False))
        avg_score = sum(scores) / len(scores)
        pass_rate = passed_count / len(reviews) * 100
    else:
        avg_score = 0
        pass_rate = 0

    # Get per-agent stats
    by_agent = {}
    for r in reviews:
        agent = r.get("agent_name", "unknown")
        if agent not in by_agent:
            by_agent[agent] = {"scores": [], "passed": 0}
        by_agent[agent]["scores"].append(r.get("score", 0))
        if r.get("passed"):
            by_agent[agent]["passed"] += 1

    agent_cards = [
        {
            "agent": agent,
            "reviews": len(data["scores"]),
            "avg_score": round(sum(data["scores"]) / len(data["scores"]), 1),
            "pass_rate": round(data["passed"] / len(data["scores"]) * 100, 1)
        }
        for agent, data in by_agent.items()
    ]

    return {
        "timestamp": qa_ctx['current_datetime'],
        "days_to_launch": qa_ctx['days_to_launch'],
        "overview": {
            "total_reviews": len(reviews),
            "avg_score": round(avg_score, 1),
            "pass_rate": round(pass_rate, 1),
            "quality_threshold": DEFAULT_QUALITY_THRESHOLD
        },
        "agents": sorted(agent_cards, key=lambda x: -x["avg_score"]),
        "recent_reviews": reviews[:10],
        "alerts": []  # Would populate with critical issues
    }

# =============================================================================
# STANDARDS MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/standards")
async def list_standards(domain: Optional[str] = None, active: bool = True):
    """List all quality standards"""
    filters = {"active": active}
    if domain:
        filters["domain"] = domain

    standards = await db_select("quality_standards", filters=filters)
    return {"standards": standards, "count": len(standards)}

@app.post("/standards")
async def create_standard(standard: QualityStandard):
    """Create new quality standard"""
    standard_data = {
        "domain": standard.domain,
        "name": standard.name,
        "criteria": standard.criteria,
        "weight": standard.weight,
        "active": True
    }

    result = await db_insert("quality_standards", standard_data)
    if result:
        await notify_event_bus("standard.created", {"name": standard.name, "domain": standard.domain})

    return {"status": "created", "standard": result}

@app.put("/standards/{standard_id}")
async def update_standard(standard_id: str, standard: QualityStandard):
    """Update quality standard"""
    standard_data = {
        "domain": standard.domain,
        "name": standard.name,
        "criteria": standard.criteria,
        "weight": standard.weight
    }

    result = await db_update("quality_standards", {"id": standard_id}, standard_data)
    return {"status": "updated", "standard": result}

@app.delete("/standards/{standard_id}")
async def delete_standard(standard_id: str):
    """Delete quality standard"""
    success = await db_delete("quality_standards", {"id": standard_id})
    return {"status": "deleted" if success else "failed"}

@app.get("/standards/domain/{domain}")
async def get_domain_standards(domain: str):
    """Get standards for specific domain"""
    standards = await db_select("quality_standards", filters={"domain": domain, "active": True})
    return {"domain": domain, "standards": standards, "count": len(standards)}

# =============================================================================
# ARIA TOOL ENDPOINTS (for ARIA integration)
# =============================================================================

@app.post("/tools/qa.review")
async def tool_qa_review(req: ReviewRequest):
    """ARIA tool: Review an output for quality"""
    return await review_output(req)

@app.post("/tools/qa.check_compliance")
async def tool_check_compliance(req: ComplianceCheckRequest):
    """ARIA tool: Check output against compliance rules"""
    return await check_compliance(req)

@app.post("/tools/qa.gate_status")
async def tool_gate_status(output_id: str, gate_name: Optional[str] = None):
    """ARIA tool: Check if output passes quality gates"""
    return await get_gate_status(output_id)

@app.get("/tools/qa.agent_score")
async def tool_agent_score(agent_name: str, period: str = "week"):
    """ARIA tool: Get quality score for an agent"""
    days = {"day": 1, "week": 7, "month": 30, "all": 365}.get(period, 7)
    return await get_agent_metrics(agent_name, days=days)

@app.get("/tools/qa.trends")
async def tool_trends(agent_name: Optional[str] = None, days: int = 30, metric: str = "score"):
    """ARIA tool: Get quality trends over time"""
    return await get_trends(days=days, agent_name=agent_name)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8203)
