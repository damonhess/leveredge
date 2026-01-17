#!/usr/bin/env python3
"""
ARIA Memory V2 - Long-Term Memory Enhancement Agent
Port: 8066

Enhances ARIA's memory capabilities with:
- Long-term fact extraction from conversations
- Preference learning over time
- Decision history tracking
- "Remember when..." query capability

This extends ARIA's chat history with structured, queryable memory.

TEAM INTEGRATION:
- Provides memory services to ARIA and other agents
- Uses Claude for intelligent extraction and recall
- Stores all data in Supabase for persistence
- Logs costs using shared.cost_tracker
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import anthropic

# Add shared modules to path
sys.path.insert(0, '/opt/leveredge/control-plane/shared')
try:
    from cost_tracker import CostTracker, log_llm_usage
except ImportError:
    # Fallback if shared module not available
    class CostTracker:
        def __init__(self, name): pass
        async def log_usage(self, **kwargs): pass
    async def log_llm_usage(**kwargs): pass

# Local imports
from fact_extractor import FactExtractor, ExtractedFact, FactCategory
from preference_learner import PreferenceLearner, LearnedPreference, PreferenceCategory

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

# Agent endpoints
AGENT_ENDPOINTS = {
    "ARIA": "http://aria:8001",
    "HERMES": "http://hermes:8014",
    "EVENT_BUS": EVENT_BUS_URL
}

# Initialize components
fact_extractor = FactExtractor(ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
preference_learner = PreferenceLearner(ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
cost_tracker = CostTracker("MEMORY-V2")

# Anthropic client for recall queries
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# =============================================================================
# LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print("[MEMORY-V2] Starting up...")
    yield
    print("[MEMORY-V2] Shutting down...")

app = FastAPI(
    title="ARIA Memory V2",
    description="Long-Term Memory Enhancement for ARIA",
    version="2.0.0",
    lifespan=lifespan
)

# =============================================================================
# MODELS
# =============================================================================

class ExtractRequest(BaseModel):
    """Request to extract facts from conversation"""
    conversation: str = Field(..., description="Conversation text to extract facts from")
    user_id: str = Field(default="default", description="User identifier")
    conversation_id: Optional[str] = Field(default=None, description="Source conversation ID")
    include_preferences: bool = Field(default=True, description="Also extract preferences")

class LearnPreferenceRequest(BaseModel):
    """Request to learn/record a preference"""
    user_id: str = Field(default="default")
    preference_key: str = Field(..., description="Unique key for the preference")
    preference_value: str = Field(..., description="The preference value")
    category: str = Field(default="general", description="Preference category")
    evidence: Optional[str] = Field(default=None, description="Supporting evidence")
    conversation_id: Optional[str] = Field(default=None)

class LogDecisionRequest(BaseModel):
    """Request to log a decision"""
    user_id: str = Field(default="default")
    decision: str = Field(..., description="The decision made")
    decision_type: str = Field(default="general", description="Type of decision")
    context: Dict[str, Any] = Field(default_factory=dict, description="Decision context")
    options_considered: Optional[List[str]] = Field(default=None)
    reasoning: Optional[str] = Field(default=None)
    source_agent: Optional[str] = Field(default=None)
    conversation_id: Optional[str] = Field(default=None)

class RecordOutcomeRequest(BaseModel):
    """Request to record decision outcome"""
    outcome: str = Field(..., description="What was the outcome")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Outcome rating 1-5")

class RecallRequest(BaseModel):
    """Request for 'Remember when...' queries"""
    user_id: str = Field(default="default")
    query: str = Field(..., description="What to remember (e.g., 'when I talked about...'')")
    include_facts: bool = Field(default=True)
    include_preferences: bool = Field(default=True)
    include_decisions: bool = Field(default=True)
    limit: int = Field(default=10, ge=1, le=50)

# =============================================================================
# DATABASE HELPERS
# =============================================================================

async def db_query(
    table: str,
    method: str = "GET",
    data: dict = None,
    filters: str = "",
    select: str = "*",
    order: str = None
) -> Any:
    """Generic database query helper"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
        if filters:
            url += f"&{filters}"
        if order:
            url += f"&order={order}"

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                resp = await client.get(url, headers=headers, timeout=10.0)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=data, timeout=10.0)
            elif method == "PATCH":
                resp = await client.patch(url, headers=headers, json=data, timeout=10.0)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers, timeout=10.0)
            else:
                return None

            if resp.status_code in [200, 201]:
                return resp.json()
            else:
                print(f"[DB] Query failed: {resp.status_code} - {resp.text}")
                return None
    except Exception as e:
        print(f"[DB] Query error: {e}")
        return None

async def db_rpc(function_name: str, params: dict = {}) -> Any:
    """Call a database RPC function"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/{function_name}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json=params,
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"[DB RPC] Failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"[DB RPC] Error: {e}")
        return None

# =============================================================================
# EVENT BUS
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "MEMORY-V2",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[EventBus] Notification failed: {e}")

# =============================================================================
# HEALTH ENDPOINT
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check"""
    return {
        "status": "healthy",
        "agent": "MEMORY-V2",
        "role": "Long-Term Memory Enhancement",
        "port": 8066,
        "components": {
            "fact_extractor": fact_extractor is not None,
            "preference_learner": preference_learner is not None,
            "anthropic": anthropic_client is not None,
            "supabase": bool(SUPABASE_KEY)
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# FACT EXTRACTION ENDPOINTS
# =============================================================================

@app.post("/extract")
async def extract_facts(req: ExtractRequest):
    """
    Extract facts (and optionally preferences) from a conversation.

    This is the main entry point for processing conversations.
    Call this after conversations to extract memorable information.
    """
    if not fact_extractor:
        raise HTTPException(status_code=503, detail="Fact extractor not configured (missing API key)")

    results = {
        "user_id": req.user_id,
        "conversation_id": req.conversation_id,
        "facts": [],
        "preferences": [],
        "timestamp": datetime.utcnow().isoformat()
    }

    # Get existing facts to avoid duplicates
    existing_facts = await db_query(
        "aria_facts",
        filters=f"user_id=eq.{req.user_id}&is_active=eq.true",
        select="fact"
    )
    existing_fact_texts = [f["fact"] for f in (existing_facts or [])]

    # Extract facts
    try:
        extracted_facts = await fact_extractor.extract_facts(
            req.conversation,
            req.user_id,
            existing_fact_texts
        )

        # Store each fact
        for fact in extracted_facts:
            fact_data = {
                "user_id": req.user_id,
                "fact": fact.fact,
                "category": fact.category.value,
                "confidence": fact.confidence,
                "source_conversation_id": req.conversation_id,
                "source_message": fact.source_excerpt,
                "extracted_by": "claude"
            }

            stored = await db_query("aria_facts", "POST", fact_data)
            if stored:
                results["facts"].append({
                    "id": stored[0]["id"] if stored else None,
                    **fact.to_dict()
                })

        # Also extract preferences if requested
        if req.include_preferences and preference_learner:
            existing_prefs = await db_query(
                "aria_preferences",
                filters=f"user_id=eq.{req.user_id}&is_active=eq.true",
                select="preference_key,preference_value"
            )
            existing_pref_dict = {
                p["preference_key"]: p["preference_value"]
                for p in (existing_prefs or [])
            }

            learned_prefs = await preference_learner.learn_preferences(
                req.conversation,
                req.user_id,
                existing_pref_dict
            )

            for pref in learned_prefs:
                # Use upsert RPC if available, otherwise manual insert
                pref_id = await db_rpc("upsert_aria_preference", {
                    "p_user_id": req.user_id,
                    "p_preference_key": pref.preference_key,
                    "p_preference_value": pref.preference_value,
                    "p_category": pref.category.value,
                    "p_evidence": pref.evidence[0] if pref.evidence else None,
                    "p_source_conversation_id": req.conversation_id
                })

                results["preferences"].append({
                    "id": pref_id,
                    **pref.to_dict()
                })

        # Notify event bus
        await notify_event_bus("memory.extraction.completed", {
            "user_id": req.user_id,
            "facts_extracted": len(results["facts"]),
            "preferences_learned": len(results["preferences"])
        })

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

# =============================================================================
# PREFERENCE ENDPOINTS
# =============================================================================

@app.post("/learn-preference")
async def learn_preference(req: LearnPreferenceRequest):
    """
    Record a learned preference.

    Use this to explicitly record preferences detected by other agents
    or from user feedback.
    """
    # Use upsert RPC
    pref_id = await db_rpc("upsert_aria_preference", {
        "p_user_id": req.user_id,
        "p_preference_key": req.preference_key,
        "p_preference_value": req.preference_value,
        "p_category": req.category,
        "p_evidence": req.evidence,
        "p_source_conversation_id": req.conversation_id
    })

    if not pref_id:
        # Fallback to direct insert
        pref_data = {
            "user_id": req.user_id,
            "preference_key": req.preference_key,
            "preference_value": req.preference_value,
            "category": req.category,
            "evidence": [req.evidence] if req.evidence else [],
            "source_conversation_ids": [req.conversation_id] if req.conversation_id else [],
            "confidence": 0.8
        }
        result = await db_query("aria_preferences", "POST", pref_data)
        pref_id = result[0]["id"] if result else None

    await notify_event_bus("memory.preference.learned", {
        "user_id": req.user_id,
        "preference_key": req.preference_key
    })

    return {
        "success": True,
        "preference_id": pref_id,
        "preference_key": req.preference_key,
        "preference_value": req.preference_value,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/preferences/{user_id}")
async def get_preferences(
    user_id: str,
    category: Optional[str] = None,
    min_confidence: float = Query(default=0.5, ge=0, le=1)
):
    """
    Get all learned preferences for a user.

    Returns preferences sorted by confidence, optionally filtered by category.
    """
    filters = f"user_id=eq.{user_id}&is_active=eq.true&confidence=gte.{min_confidence}"
    if category:
        filters += f"&category=eq.{category}"

    preferences = await db_query(
        "aria_preferences",
        filters=filters,
        order="confidence.desc,last_confirmed.desc"
    )

    # Group by category
    by_category = {}
    for pref in (preferences or []):
        cat = pref.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(pref)

    return {
        "user_id": user_id,
        "preferences": preferences or [],
        "by_category": by_category,
        "count": len(preferences or []),
        "categories": list(by_category.keys())
    }

# =============================================================================
# DECISION TRACKING ENDPOINTS
# =============================================================================

@app.post("/log-decision")
async def log_decision(req: LogDecisionRequest):
    """
    Log a decision made by or for the user.

    Track decisions to:
    - Learn from outcomes
    - Reference in future similar situations
    - Build pattern recognition
    """
    decision_data = {
        "user_id": req.user_id,
        "decision": req.decision,
        "decision_type": req.decision_type,
        "context": req.context,
        "options_considered": req.options_considered,
        "reasoning": req.reasoning,
        "source_agent": req.source_agent,
        "source_conversation_id": req.conversation_id
    }

    result = await db_query("aria_decisions", "POST", decision_data)

    if result:
        await notify_event_bus("memory.decision.logged", {
            "user_id": req.user_id,
            "decision_type": req.decision_type,
            "decision_id": result[0]["id"]
        })

        return {
            "success": True,
            "decision_id": result[0]["id"],
            "timestamp": datetime.utcnow().isoformat()
        }

    raise HTTPException(status_code=500, detail="Failed to log decision")

@app.get("/decisions/{user_id}")
async def get_decisions(
    user_id: str,
    decision_type: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    include_outcomes: bool = Query(default=False)
):
    """Get decision history for a user."""
    filters = f"user_id=eq.{user_id}"
    if decision_type:
        filters += f"&decision_type=eq.{decision_type}"
    if include_outcomes:
        filters += "&outcome=not.is.null"

    decisions = await db_query(
        "aria_decisions",
        filters=f"{filters}&limit={limit}",
        order="created_at.desc"
    )

    return {
        "user_id": user_id,
        "decisions": decisions or [],
        "count": len(decisions or [])
    }

@app.put("/decisions/{decision_id}/outcome")
async def record_decision_outcome(decision_id: str, req: RecordOutcomeRequest):
    """Record the outcome of a decision."""
    update_data = {
        "outcome": req.outcome,
        "outcome_rating": req.rating,
        "outcome_recorded_at": datetime.utcnow().isoformat()
    }

    result = await db_query(
        "aria_decisions",
        "PATCH",
        update_data,
        filters=f"id=eq.{decision_id}"
    )

    if result:
        return {
            "success": True,
            "decision_id": decision_id,
            "outcome_recorded": True
        }

    raise HTTPException(status_code=404, detail="Decision not found")

# =============================================================================
# FACTS ENDPOINTS
# =============================================================================

@app.get("/facts/{user_id}")
async def get_facts(
    user_id: str,
    category: Optional[str] = None,
    min_confidence: float = Query(default=0.5, ge=0, le=1),
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    Get all known facts about a user.

    Returns facts sorted by confidence and recency.
    """
    filters = f"user_id=eq.{user_id}&is_active=eq.true&confidence=gte.{min_confidence}&limit={limit}"
    if category:
        filters += f"&category=eq.{category}"

    facts = await db_query(
        "aria_facts",
        filters=filters,
        order="confidence.desc,created_at.desc"
    )

    # Group by category
    by_category = {}
    for fact in (facts or []):
        cat = fact.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(fact)

    return {
        "user_id": user_id,
        "facts": facts or [],
        "by_category": by_category,
        "count": len(facts or []),
        "categories": list(by_category.keys())
    }

@app.delete("/facts/{fact_id}")
async def deactivate_fact(fact_id: str):
    """Mark a fact as inactive (soft delete)."""
    result = await db_query(
        "aria_facts",
        "PATCH",
        {"is_active": False, "updated_at": datetime.utcnow().isoformat()},
        filters=f"id=eq.{fact_id}"
    )

    if result:
        return {"success": True, "fact_id": fact_id, "deactivated": True}

    raise HTTPException(status_code=404, detail="Fact not found")

# =============================================================================
# RECALL ENDPOINT - "Remember when..."
# =============================================================================

@app.get("/recall")
async def recall(
    user_id: str = Query(default="default"),
    query: str = Query(..., description="What to remember"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    "Remember when..." query capability.

    Natural language queries against the user's memory:
    - "when I talked about my project deadline"
    - "what my preference for meetings is"
    - "the decision I made about the job offer"
    """
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="Recall not configured (missing API key)")

    results = {
        "user_id": user_id,
        "query": query,
        "facts": [],
        "preferences": [],
        "decisions": [],
        "summary": "",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Search facts using full-text search
    facts = await db_rpc("search_aria_facts", {
        "p_user_id": user_id,
        "p_query": query,
        "p_limit": limit
    })
    results["facts"] = facts or []

    # Search decisions
    decisions = await db_rpc("search_aria_decisions", {
        "p_user_id": user_id,
        "p_query": query,
        "p_limit": limit
    })
    results["decisions"] = decisions or []

    # Get relevant preferences
    preferences = await db_query(
        "aria_preferences",
        filters=f"user_id=eq.{user_id}&is_active=eq.true",
        select="*"
    )
    results["preferences"] = preferences or []

    # Generate a summary using Claude
    context = f"""
User is asking: "{query}"

KNOWN FACTS:
{json.dumps(results['facts'][:10], indent=2) if results['facts'] else 'No matching facts found.'}

PREFERENCES:
{json.dumps(results['preferences'][:10], indent=2) if results['preferences'] else 'No preferences recorded.'}

DECISIONS:
{json.dumps(results['decisions'][:10], indent=2) if results['decisions'] else 'No matching decisions found.'}
"""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="""You are ARIA's memory recall system. Answer the user's memory query
based on the provided facts, preferences, and decisions. Be specific and reference
the actual stored information. If nothing relevant is found, say so clearly.
Format your response conversationally, as if helping someone remember.""",
            messages=[{"role": "user", "content": context}]
        )

        results["summary"] = response.content[0].text

        # Log usage
        await log_llm_usage(
            agent="MEMORY-V2",
            endpoint="/recall",
            model="claude-sonnet-4-20250514",
            response=response
        )

    except Exception as e:
        results["summary"] = f"Memory search completed but summary generation failed: {e}"

    await notify_event_bus("memory.recall.queried", {
        "user_id": user_id,
        "query": query[:50],
        "facts_found": len(results["facts"]),
        "decisions_found": len(results["decisions"])
    })

    return results

@app.post("/recall")
async def recall_post(req: RecallRequest):
    """POST version of recall for more complex queries."""
    return await recall(
        user_id=req.user_id,
        query=req.query,
        limit=req.limit
    )

# =============================================================================
# STATISTICS ENDPOINT
# =============================================================================

@app.get("/stats/{user_id}")
async def get_memory_stats(user_id: str):
    """Get memory statistics for a user."""
    # Count facts
    facts = await db_query(
        "aria_facts",
        filters=f"user_id=eq.{user_id}&is_active=eq.true",
        select="id,category,confidence"
    )

    # Count preferences
    preferences = await db_query(
        "aria_preferences",
        filters=f"user_id=eq.{user_id}&is_active=eq.true",
        select="id,category,confidence"
    )

    # Count decisions
    decisions = await db_query(
        "aria_decisions",
        filters=f"user_id=eq.{user_id}",
        select="id,decision_type,outcome_rating"
    )

    # Calculate stats
    facts_list = facts or []
    prefs_list = preferences or []
    decisions_list = decisions or []

    fact_categories = {}
    for f in facts_list:
        cat = f.get("category", "general")
        fact_categories[cat] = fact_categories.get(cat, 0) + 1

    pref_categories = {}
    for p in prefs_list:
        cat = p.get("category", "general")
        pref_categories[cat] = pref_categories.get(cat, 0) + 1

    decision_types = {}
    for d in decisions_list:
        dt = d.get("decision_type", "general")
        decision_types[dt] = decision_types.get(dt, 0) + 1

    avg_fact_confidence = (
        sum(f.get("confidence", 0) for f in facts_list) / len(facts_list)
        if facts_list else 0
    )

    avg_pref_confidence = (
        sum(p.get("confidence", 0) for p in prefs_list) / len(prefs_list)
        if prefs_list else 0
    )

    rated_decisions = [d for d in decisions_list if d.get("outcome_rating")]
    avg_decision_rating = (
        sum(d["outcome_rating"] for d in rated_decisions) / len(rated_decisions)
        if rated_decisions else None
    )

    return {
        "user_id": user_id,
        "facts": {
            "total": len(facts_list),
            "by_category": fact_categories,
            "avg_confidence": round(avg_fact_confidence, 2)
        },
        "preferences": {
            "total": len(prefs_list),
            "by_category": pref_categories,
            "avg_confidence": round(avg_pref_confidence, 2)
        },
        "decisions": {
            "total": len(decisions_list),
            "by_type": decision_types,
            "with_outcomes": len(rated_decisions),
            "avg_outcome_rating": round(avg_decision_rating, 2) if avg_decision_rating else None
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8066)
