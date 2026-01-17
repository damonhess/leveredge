#!/usr/bin/env python3
"""
IRIS - AI-Powered World Events Reporter Agent
Port: 8209

Named after Iris - The goddess of the rainbow and messenger of the gods,
who traveled between realms delivering news and connecting the heavens
with the mortal world.

CORE CAPABILITIES:
- News aggregation from multiple sources
- AI-generated personalized briefings
- Bias detection and transparency
- Source reliability ranking
- Topic tracking with alerts

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated via Unified Memory
- Logs costs using shared.cost_tracker
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="IRIS",
    description="AI-Powered World Events Reporter Agent",
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
    "HERMES": "http://hermes:8014",
    "MNEMOS": "http://mnemos:8019",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("IRIS")

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
        "timezone": "UTC"
    }

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(news_context: dict) -> str:
    """Build IRIS system prompt with news awareness"""
    return f"""You are IRIS - World Events Reporter Agent for LeverEdge AI.

Named after the goddess of the rainbow and messenger of the gods, you bridge the gap between world events and informed decision-making.

## TIME AWARENESS
- Current: {news_context.get('current_time', 'Unknown')}
- Timezone: {news_context.get('timezone', 'UTC')}
- Days to Launch: {news_context.get('days_to_launch', 'Unknown')}

## YOUR IDENTITY
You are the information hub of LeverEdge. You aggregate news, detect bias, rank sources, and deliver personalized briefings that keep users informed without overwhelming them.

## CURRENT NEWS STATE
- Active Sources: {news_context.get('active_sources', 0)}
- Articles Today: {news_context.get('articles_today', 0)}
- Trending Topics: {', '.join(news_context.get('trending_topics', ['No trending topics']))}
- Last Briefing: {news_context.get('last_briefing', 'None')}

## YOUR CAPABILITIES

### News Aggregation
- Collect from {news_context.get('active_sources', 0)} active sources
- Parse RSS feeds and news APIs
- Deduplicate and categorize articles
- Extract entities and topics automatically

### Briefing Generation
- Create personalized daily briefings
- Multiple formats: summary, bullets, detailed
- Filter by user's tracked topics
- Rank by relevance and importance

### Bias Detection
- Analyze political spectrum (-5 to +5)
- Detect sensationalism and loaded language
- Compare coverage across sources
- Suggest alternative perspectives

### Source Ranking
- Score reliability (0-100)
- Track correction history
- Evaluate editorial independence
- Monitor bias trends over time

### Topic Tracking
- Monitor keywords and entities
- Detect trending stories
- Provide historical context
- Alert on significant developments

## TEAM COORDINATION
- Request user context -> MNEMOS (user memory)
- Send notifications -> HERMES
- Store insights -> ARIA via Unified Memory
- Publish events -> Event Bus
- Cross-reference data -> other agents

## RESPONSE PRINCIPLES
1. **Objectivity First**: Present facts before analysis
2. **Bias Transparency**: Always disclose source bias ratings
3. **Multiple Perspectives**: Offer alternative viewpoints
4. **Source Attribution**: Always cite sources
5. **Recency Priority**: Prefer latest information

## BRIEFING FORMAT
When generating briefings:
1. Lead with most important/impactful stories
2. Group by topic or region as appropriate
3. Include bias indicators for each source
4. Provide "Read More" links
5. End with emerging/developing stories

## YOUR MISSION
Keep LeverEdge users informed with accurate, balanced, and relevant news.
Combat information overload with intelligent curation.
Expose bias while respecting all perspectives.
"""

# =============================================================================
# MODELS
# =============================================================================

# News Models
class ArticleResponse(BaseModel):
    id: str
    title: str
    url: str
    summary: Optional[str] = None
    source_name: str
    source_bias: Optional[float] = None
    published_at: str
    topics: List[str] = []
    importance_score: float = 50.0

class NewsSearchRequest(BaseModel):
    query: str
    topics: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 20

class FetchRequest(BaseModel):
    source_ids: Optional[List[str]] = None
    force: bool = False

# Briefing Models
class BriefingGenerateRequest(BaseModel):
    user_id: str = "default"
    format: str = "summary"  # summary, bullets, detailed, audio
    briefing_type: str = "morning"  # morning, topic, breaking, weekly
    topics: Optional[List[str]] = None
    max_articles: int = 10

class BriefingScheduleRequest(BaseModel):
    user_id: str
    briefing_type: str = "morning"
    time: str = "07:00"
    timezone: str = "UTC"
    topics: Optional[List[str]] = None
    format: str = "summary"
    enabled: bool = True

# Bias Models
class BiasAnalyzeRequest(BaseModel):
    text: str
    context: Optional[str] = None

class BiasCompareRequest(BaseModel):
    topic: str
    source_ids: Optional[List[str]] = None
    limit: int = 5

# Source Models
class SourceCreate(BaseModel):
    name: str
    url: str
    rss_feed: Optional[str] = None
    category: str = "major"
    fetch_frequency_minutes: int = 60
    metadata: Optional[Dict[str, Any]] = None

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    rss_feed: Optional[str] = None
    category: Optional[str] = None
    active: Optional[bool] = None
    fetch_frequency_minutes: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

# Topic Models
class TopicCreate(BaseModel):
    name: str
    display_name: str
    keywords: List[str]
    related_topics: Optional[List[str]] = None

class TopicUpdate(BaseModel):
    display_name: Optional[str] = None
    keywords: Optional[List[str]] = None
    related_topics: Optional[List[str]] = None
    importance: Optional[float] = None

class TopicSubscribeRequest(BaseModel):
    user_id: str
    topic_id: str
    alert_threshold: str = "high"  # breaking, high, all

# User Preferences Models
class UserPreferencesUpdate(BaseModel):
    topics: Optional[List[str]] = None
    excluded_topics: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    excluded_sources: Optional[List[str]] = None
    briefing_time: Optional[str] = None
    briefing_timezone: Optional[str] = None
    briefing_format: Optional[str] = None
    bias_preference: Optional[str] = None
    language: Optional[str] = None

class TopicAddRequest(BaseModel):
    topics: List[str]

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
                    "source_agent": "IRIS",
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
                    "message": f"[IRIS] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "IRIS"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")

async def store_to_unified_memory(
    memory_type: str,
    content: str,
    category: str,
    tags: List[str] = None
):
    """Store insights to Unified Memory via ARIA"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/unified_memory",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "memory_type": memory_type,
                    "content": content,
                    "category": category,
                    "source_type": "agent_result",
                    "source_agent": "IRIS",
                    "tags": tags or [],
                    "created_at": time_ctx['current_datetime']
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"Unified memory storage failed: {e}")
        return False

async def get_news_context() -> dict:
    """Get current news context for system prompt"""
    time_ctx = get_time_context()

    # Try to fetch real data from database
    try:
        async with httpx.AsyncClient() as http_client:
            # Get source count
            sources_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/news_sources?active=eq.true&select=id",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=5.0
            )
            active_sources = len(sources_resp.json()) if sources_resp.status_code == 200 else 0

            # Get today's article count
            today = time_ctx['current_date']
            articles_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?fetched_at=gte.{today}&select=id",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=5.0
            )
            articles_today = len(articles_resp.json()) if articles_resp.status_code == 200 else 0

            # Get trending topics
            topics_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/topics?order=trending_score.desc&limit=5&select=name",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=5.0
            )
            trending = [t['name'] for t in topics_resp.json()] if topics_resp.status_code == 200 else []

            return {
                **time_ctx,
                "active_sources": active_sources,
                "articles_today": articles_today,
                "trending_topics": trending if trending else ["No trending topics"],
                "last_briefing": "Check briefings endpoint"
            }
    except Exception as e:
        print(f"Failed to get news context: {e}")
        return {
            **time_ctx,
            "active_sources": 0,
            "articles_today": 0,
            "trending_topics": ["Service initializing"],
            "last_briefing": "None"
        }

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, news_ctx: dict = None, endpoint: str = "unknown") -> str:
    """Call Claude API with news context and cost tracking"""
    try:
        if not news_ctx:
            news_ctx = await get_news_context()

        system_prompt = build_system_prompt(news_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="IRIS",
            endpoint=endpoint,
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": news_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check with aggregation status"""
    time_ctx = get_time_context()
    news_ctx = await get_news_context()

    return {
        "status": "healthy",
        "agent": "IRIS",
        "role": "World Events Reporter",
        "port": 8209,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "active_sources": news_ctx.get('active_sources', 0),
        "articles_today": news_ctx.get('articles_today', 0)
    }

@app.get("/status")
async def status():
    """Real-time news pipeline status"""
    news_ctx = await get_news_context()

    return {
        "agent": "IRIS",
        "pipeline_status": "operational",
        "active_sources": news_ctx.get('active_sources', 0),
        "articles_today": news_ctx.get('articles_today', 0),
        "trending_topics": news_ctx.get('trending_topics', []),
        "last_fetch": news_ctx.get('current_datetime'),
        "time_context": get_time_context()
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    news_ctx = await get_news_context()
    time_ctx = get_time_context()

    # Return metrics in Prometheus format
    metrics_text = f"""# HELP iris_active_sources Number of active news sources
# TYPE iris_active_sources gauge
iris_active_sources {news_ctx.get('active_sources', 0)}

# HELP iris_articles_today Number of articles fetched today
# TYPE iris_articles_today counter
iris_articles_today {news_ctx.get('articles_today', 0)}

# HELP iris_days_to_launch Days until launch
# TYPE iris_days_to_launch gauge
iris_days_to_launch {time_ctx.get('days_to_launch', 0)}

# HELP iris_health Agent health status (1=healthy, 0=unhealthy)
# TYPE iris_health gauge
iris_health 1
"""
    return metrics_text

# =============================================================================
# NEWS AGGREGATION ENDPOINTS
# =============================================================================

@app.get("/news")
async def get_news(
    topic: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0
):
    """Get latest news with optional filters"""
    try:
        async with httpx.AsyncClient() as http_client:
            # Build query
            query_parts = ["select=*,news_sources(name,bias_rating,reliability_score)"]
            query_parts.append("order=published_at.desc")
            query_parts.append(f"limit={limit}")
            query_parts.append(f"offset={offset}")

            if topic:
                query_parts.append(f"topics=cs.{{{topic}}}")

            url = f"{SUPABASE_URL}/rest/v1/articles?{'&'.join(query_parts)}"

            resp = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                articles = resp.json()
                return {
                    "articles": articles,
                    "count": len(articles),
                    "offset": offset,
                    "limit": limit,
                    "filters": {"topic": topic, "source": source}
                }
            else:
                return {"articles": [], "count": 0, "message": "No articles found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news: {e}")

@app.get("/news/{article_id}")
async def get_article(article_id: str):
    """Get specific article details"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?id=eq.{article_id}&select=*,news_sources(name,bias_rating,reliability_score)",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                articles = resp.json()
                if articles:
                    return articles[0]
                raise HTTPException(status_code=404, detail="Article not found")
            else:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch article")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch article: {e}")

@app.get("/news/search")
async def search_news(req: NewsSearchRequest):
    """Search articles by keyword/topic"""
    try:
        async with httpx.AsyncClient() as http_client:
            # Build search query
            query_parts = ["select=*,news_sources(name,bias_rating)"]
            query_parts.append(f"or=(title.ilike.%{req.query}%,summary.ilike.%{req.query}%)")
            query_parts.append("order=published_at.desc")
            query_parts.append(f"limit={req.limit}")

            if req.date_from:
                query_parts.append(f"published_at=gte.{req.date_from}")
            if req.date_to:
                query_parts.append(f"published_at=lte.{req.date_to}")

            url = f"{SUPABASE_URL}/rest/v1/articles?{'&'.join(query_parts)}"

            resp = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {
                    "query": req.query,
                    "results": resp.json(),
                    "count": len(resp.json())
                }
            else:
                return {"query": req.query, "results": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

@app.post("/news/fetch")
async def force_fetch(req: FetchRequest):
    """Force fetch from sources"""
    # This would trigger the aggregator to fetch new articles
    await notify_event_bus("news.fetch.triggered", {
        "source_ids": req.source_ids,
        "force": req.force
    })

    return {
        "status": "fetch_triggered",
        "source_ids": req.source_ids or "all",
        "force": req.force,
        "message": "Fetch job queued. Check status endpoint for progress."
    }

@app.get("/news/trending")
async def get_trending():
    """Get trending stories"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?order=importance_score.desc&limit=10&select=*,news_sources(name,bias_rating)",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {
                    "trending": resp.json(),
                    "count": len(resp.json()),
                    "updated_at": get_time_context()['current_datetime']
                }
            return {"trending": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trending: {e}")

# =============================================================================
# BRIEFING ENDPOINTS
# =============================================================================

@app.post("/briefings/generate")
async def generate_briefing(req: BriefingGenerateRequest):
    """Generate a new personalized briefing"""
    news_ctx = await get_news_context()

    # Fetch relevant articles
    try:
        async with httpx.AsyncClient() as http_client:
            query = f"order=importance_score.desc&limit={req.max_articles}&select=*,news_sources(name,bias_rating)"
            if req.topics:
                topics_filter = ",".join(req.topics)
                query += f"&topics=ov.{{{topics_filter}}}"

            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?{query}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            articles = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        articles = []
        print(f"Failed to fetch articles for briefing: {e}")

    # Build briefing prompt
    format_instructions = {
        "summary": "Create a concise executive summary with the top 5 most important stories.",
        "bullets": "Create a bullet-point briefing with one-line summaries for each story.",
        "detailed": "Create a detailed briefing with full context and analysis for each story.",
        "audio": "Create a script suitable for audio narration, conversational tone."
    }

    articles_text = "\n\n".join([
        f"**{a.get('title', 'Untitled')}** (Source: {a.get('news_sources', {}).get('name', 'Unknown')}, Bias: {a.get('news_sources', {}).get('bias_rating', 0)})\n{a.get('summary', 'No summary available')}"
        for a in articles[:req.max_articles]
    ]) if articles else "No articles available. Please check back later."

    prompt = f"""Generate a {req.briefing_type} briefing in {req.format} format.

{format_instructions.get(req.format, format_instructions['summary'])}

Today's date: {news_ctx['current_date']}
Topics of interest: {', '.join(req.topics) if req.topics else 'All topics'}

Articles to include:
{articles_text}

Remember to:
1. Lead with the most important stories
2. Include source bias ratings
3. Offer multiple perspectives where relevant
4. End with emerging/developing stories
"""

    messages = [{"role": "user", "content": prompt}]
    briefing_content = await call_llm(messages, news_ctx, "/briefings/generate")

    # Store briefing
    try:
        async with httpx.AsyncClient() as http_client:
            briefing_data = {
                "user_id": req.user_id,
                "date": news_ctx['current_date'],
                "format": req.format,
                "briefing_type": req.briefing_type,
                "topics": req.topics or [],
                "articles_included": [a.get('id') for a in articles if a.get('id')],
                "content": briefing_content,
                "ai_model": "claude-sonnet-4-20250514",
                "generated_at": news_ctx['current_datetime']
            }

            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/briefings",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=briefing_data,
                timeout=10.0
            )
    except Exception as e:
        print(f"Failed to store briefing: {e}")

    # Publish event
    await notify_event_bus("news.briefing.ready", {
        "user_id": req.user_id,
        "briefing_type": req.briefing_type,
        "format": req.format,
        "article_count": len(articles)
    })

    # Store to unified memory
    await store_to_unified_memory(
        memory_type="event",
        content=f"Daily briefing generated with {len(articles)} articles on {', '.join(req.topics) if req.topics else 'all topics'}",
        category="news",
        tags=["iris", "briefing", req.briefing_type]
    )

    return {
        "briefing": briefing_content,
        "format": req.format,
        "briefing_type": req.briefing_type,
        "article_count": len(articles),
        "topics": req.topics,
        "generated_at": news_ctx['current_datetime']
    }

@app.get("/briefings")
async def list_briefings(
    user_id: str = "default",
    limit: int = 10,
    offset: int = 0
):
    """List user's briefings"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/briefings?user_id=eq.{user_id}&order=generated_at.desc&limit={limit}&offset={offset}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {
                    "briefings": resp.json(),
                    "count": len(resp.json()),
                    "user_id": user_id
                }
            return {"briefings": [], "count": 0, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list briefings: {e}")

@app.get("/briefings/{briefing_id}")
async def get_briefing(briefing_id: str):
    """Get specific briefing"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/briefings?id=eq.{briefing_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                briefings = resp.json()
                if briefings:
                    return briefings[0]
                raise HTTPException(status_code=404, detail="Briefing not found")
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch briefing")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch briefing: {e}")

@app.get("/briefings/today")
async def get_today_briefing(user_id: str = "default"):
    """Get today's briefing for user"""
    time_ctx = get_time_context()
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/briefings?user_id=eq.{user_id}&date=eq.{time_ctx['current_date']}&order=generated_at.desc&limit=1",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                briefings = resp.json()
                if briefings:
                    return briefings[0]
                return {"message": "No briefing generated today", "date": time_ctx['current_date']}
            return {"message": "Failed to fetch briefing", "date": time_ctx['current_date']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's briefing: {e}")

@app.post("/briefings/schedule")
async def schedule_briefing(req: BriefingScheduleRequest):
    """Schedule recurring briefings"""
    # Store schedule in user preferences
    try:
        async with httpx.AsyncClient() as http_client:
            schedule_data = {
                "user_id": req.user_id,
                "briefing_time": req.time,
                "briefing_timezone": req.timezone,
                "briefing_format": req.format
            }

            # Upsert user preferences
            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/user_preferences",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                },
                json=schedule_data,
                timeout=10.0
            )

            await notify_event_bus("news.briefing.scheduled", {
                "user_id": req.user_id,
                "time": req.time,
                "timezone": req.timezone
            })

            return {
                "status": "scheduled",
                "user_id": req.user_id,
                "time": req.time,
                "timezone": req.timezone,
                "format": req.format,
                "enabled": req.enabled
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule briefing: {e}")

@app.delete("/briefings/{briefing_id}")
async def delete_briefing(briefing_id: str):
    """Delete a briefing"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.delete(
                f"{SUPABASE_URL}/rest/v1/briefings?id=eq.{briefing_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code in [200, 204]:
                return {"status": "deleted", "briefing_id": briefing_id}
            raise HTTPException(status_code=resp.status_code, detail="Failed to delete briefing")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete briefing: {e}")

# =============================================================================
# BIAS ANALYSIS ENDPOINTS
# =============================================================================

@app.get("/bias/article/{article_id}")
async def get_article_bias(article_id: str):
    """Get bias analysis for an article"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?id=eq.{article_id}&select=*,news_sources(name,bias_rating,reliability_score)",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                articles = resp.json()
                if articles:
                    article = articles[0]
                    source = article.get('news_sources', {})
                    return {
                        "article_id": article_id,
                        "title": article.get('title'),
                        "bias_score": article.get('bias_score', 0),
                        "sentiment": article.get('sentiment', 0),
                        "source_bias": source.get('bias_rating', 0),
                        "source_reliability": source.get('reliability_score', 50),
                        "bias_interpretation": interpret_bias_score(article.get('bias_score', 0))
                    }
                raise HTTPException(status_code=404, detail="Article not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze bias: {e}")

def interpret_bias_score(score: float) -> str:
    """Interpret bias score into human-readable label"""
    if score <= -3:
        return "Strong Left"
    elif score <= -1:
        return "Left-Leaning"
    elif score < 1:
        return "Center"
    elif score < 3:
        return "Right-Leaning"
    else:
        return "Strong Right"

@app.get("/bias/source/{source_id}")
async def get_source_bias(source_id: str):
    """Get bias profile for a source"""
    try:
        async with httpx.AsyncClient() as http_client:
            # Get source info
            source_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/news_sources?id=eq.{source_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            # Get source ratings
            ratings_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/source_ratings?source_id=eq.{source_id}&order=rated_at.desc",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if source_resp.status_code == 200:
                sources = source_resp.json()
                if sources:
                    source = sources[0]
                    ratings = ratings_resp.json() if ratings_resp.status_code == 200 else []
                    return {
                        "source_id": source_id,
                        "name": source.get('name'),
                        "bias_rating": source.get('bias_rating', 0),
                        "reliability_score": source.get('reliability_score', 50),
                        "bias_interpretation": interpret_bias_score(source.get('bias_rating', 0)),
                        "rating_history": ratings[:10],
                        "category": source.get('category')
                    }
                raise HTTPException(status_code=404, detail="Source not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get source bias: {e}")

@app.post("/bias/analyze")
async def analyze_text_bias(req: BiasAnalyzeRequest):
    """Analyze custom text for bias"""
    news_ctx = await get_news_context()

    prompt = f"""Analyze the following text for bias indicators.

Text to analyze:
{req.text}

{f"Context: {req.context}" if req.context else ""}

Provide analysis in the following format:
1. **Political Spectrum Score** (-5 to +5): [score] - [explanation]
2. **Sensationalism Score** (0-10): [score] - [explanation]
3. **Loaded Language**: [list specific phrases]
4. **Missing Perspectives**: [what viewpoints are not represented]
5. **Factual Claims**: [list claims that should be verified]
6. **Overall Assessment**: [summary]
7. **Suggested Improvements**: [how to make it more balanced]
"""

    messages = [{"role": "user", "content": prompt}]
    analysis = await call_llm(messages, news_ctx, "/bias/analyze")

    return {
        "analysis": analysis,
        "text_length": len(req.text),
        "analyzed_at": news_ctx['current_datetime']
    }

@app.get("/bias/compare")
async def compare_coverage(req: BiasCompareRequest):
    """Compare coverage of a topic across sources"""
    news_ctx = await get_news_context()

    try:
        async with httpx.AsyncClient() as http_client:
            # Fetch articles on the topic from different sources
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?topics=cs.{{{req.topic}}}&order=published_at.desc&limit={req.limit * 3}&select=*,news_sources(name,bias_rating)",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            articles = resp.json() if resp.status_code == 200 else []

            if not articles:
                return {
                    "topic": req.topic,
                    "comparison": "No articles found for this topic",
                    "sources_compared": 0
                }

            # Group by source for comparison
            articles_text = "\n\n".join([
                f"**{a.get('news_sources', {}).get('name', 'Unknown')}** (Bias: {a.get('news_sources', {}).get('bias_rating', 0)})\nTitle: {a.get('title')}\nSummary: {a.get('summary', 'N/A')}"
                for a in articles[:req.limit]
            ])

            prompt = f"""Compare how different news sources are covering this topic: {req.topic}

Articles from various sources:
{articles_text}

Analyze:
1. **Framing Differences**: How do sources frame the same story differently?
2. **Emphasis Variations**: What aspects does each source emphasize?
3. **Missing Context**: What information is present in some sources but not others?
4. **Bias Patterns**: How do the sources' known biases affect coverage?
5. **Balanced View**: What would a balanced reader take away from all sources?
"""

            messages = [{"role": "user", "content": prompt}]
            comparison = await call_llm(messages, news_ctx, "/bias/compare")

            return {
                "topic": req.topic,
                "comparison": comparison,
                "sources_compared": len(set(a.get('news_sources', {}).get('name') for a in articles)),
                "articles_analyzed": len(articles[:req.limit])
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")

@app.get("/bias/spectrum")
async def get_bias_spectrum(topic: str):
    """Get bias spectrum visualization data for a topic"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?topics=cs.{{{topic}}}&select=id,title,bias_score,news_sources(name,bias_rating)&order=bias_score",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            articles = resp.json() if resp.status_code == 200 else []

            # Organize by bias spectrum
            spectrum = {
                "strong_left": [],
                "left": [],
                "center": [],
                "right": [],
                "strong_right": []
            }

            for article in articles:
                score = article.get('bias_score', 0)
                if score <= -3:
                    spectrum["strong_left"].append(article)
                elif score <= -1:
                    spectrum["left"].append(article)
                elif score < 1:
                    spectrum["center"].append(article)
                elif score < 3:
                    spectrum["right"].append(article)
                else:
                    spectrum["strong_right"].append(article)

            return {
                "topic": topic,
                "spectrum": spectrum,
                "total_articles": len(articles),
                "distribution": {k: len(v) for k, v in spectrum.items()}
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bias spectrum: {e}")

# =============================================================================
# SOURCE MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/sources")
async def list_sources(
    category: Optional[str] = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0
):
    """List all news sources"""
    try:
        async with httpx.AsyncClient() as http_client:
            query = f"order=reliability_score.desc&limit={limit}&offset={offset}"
            if active_only:
                query += "&active=eq.true"
            if category:
                query += f"&category=eq.{category}"

            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/news_sources?{query}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {
                    "sources": resp.json(),
                    "count": len(resp.json()),
                    "filters": {"category": category, "active_only": active_only}
                }
            return {"sources": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sources: {e}")

@app.get("/sources/{source_id}")
async def get_source(source_id: str):
    """Get source details"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/news_sources?id=eq.{source_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                sources = resp.json()
                if sources:
                    return sources[0]
                raise HTTPException(status_code=404, detail="Source not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get source: {e}")

@app.post("/sources")
async def add_source(req: SourceCreate):
    """Add a new news source"""
    try:
        async with httpx.AsyncClient() as http_client:
            source_data = {
                "name": req.name,
                "url": req.url,
                "rss_feed": req.rss_feed,
                "category": req.category,
                "fetch_frequency_minutes": req.fetch_frequency_minutes,
                "metadata": req.metadata or {},
                "active": True,
                "bias_rating": 0,
                "reliability_score": 50
            }

            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/news_sources",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=source_data,
                timeout=10.0
            )

            if resp.status_code in [200, 201]:
                source = resp.json()[0] if resp.json() else source_data
                await notify_event_bus("news.source.added", {
                    "name": req.name,
                    "url": req.url,
                    "category": req.category
                })
                return source
            raise HTTPException(status_code=resp.status_code, detail="Failed to add source")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add source: {e}")

@app.put("/sources/{source_id}")
async def update_source(source_id: str, req: SourceUpdate):
    """Update a news source"""
    try:
        async with httpx.AsyncClient() as http_client:
            update_data = {k: v for k, v in req.dict().items() if v is not None}
            update_data["updated_at"] = get_time_context()['current_datetime']

            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/news_sources?id=eq.{source_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=update_data,
                timeout=10.0
            )

            if resp.status_code == 200:
                return resp.json()[0] if resp.json() else {"status": "updated"}
            raise HTTPException(status_code=resp.status_code, detail="Failed to update source")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update source: {e}")

@app.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    """Remove a news source"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.delete(
                f"{SUPABASE_URL}/rest/v1/news_sources?id=eq.{source_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code in [200, 204]:
                return {"status": "deleted", "source_id": source_id}
            raise HTTPException(status_code=resp.status_code, detail="Failed to delete source")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete source: {e}")

@app.get("/sources/rankings")
async def get_source_rankings():
    """Get ranked source list by reliability"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/news_sources?active=eq.true&order=reliability_score.desc&select=id,name,reliability_score,bias_rating,category",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                sources = resp.json()
                return {
                    "rankings": [
                        {
                            "rank": i + 1,
                            **s,
                            "bias_label": interpret_bias_score(s.get('bias_rating', 0))
                        }
                        for i, s in enumerate(sources)
                    ],
                    "count": len(sources)
                }
            return {"rankings": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rankings: {e}")

@app.post("/sources/evaluate")
async def evaluate_source(source_id: str):
    """Trigger source evaluation for reliability and bias"""
    news_ctx = await get_news_context()

    # Get source and recent articles
    try:
        async with httpx.AsyncClient() as http_client:
            source_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/news_sources?id=eq.{source_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            articles_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/articles?source_id=eq.{source_id}&order=published_at.desc&limit=20",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            source = source_resp.json()[0] if source_resp.status_code == 200 and source_resp.json() else None
            articles = articles_resp.json() if articles_resp.status_code == 200 else []

            if not source:
                raise HTTPException(status_code=404, detail="Source not found")

            prompt = f"""Evaluate this news source for reliability and bias.

Source: {source.get('name')}
URL: {source.get('url')}
Category: {source.get('category')}
Current Bias Rating: {source.get('bias_rating', 0)}
Current Reliability Score: {source.get('reliability_score', 50)}

Recent article titles:
{chr(10).join([f"- {a.get('title', 'Untitled')}" for a in articles[:10]])}

Provide updated scores and reasoning:
1. **New Bias Rating** (-5 to +5): [score]
2. **New Reliability Score** (0-100): [score]
3. **Reasoning**: [explain your assessment]
4. **Trends**: [any notable changes or patterns]
5. **Recommendations**: [suggestions for users]
"""

            messages = [{"role": "user", "content": prompt}]
            evaluation = await call_llm(messages, news_ctx, "/sources/evaluate")

            return {
                "source_id": source_id,
                "source_name": source.get('name'),
                "evaluation": evaluation,
                "articles_analyzed": len(articles),
                "evaluated_at": news_ctx['current_datetime']
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")

# =============================================================================
# TOPIC TRACKING ENDPOINTS
# =============================================================================

@app.get("/topics")
async def list_topics(
    trending_only: bool = False,
    subscribed_only: bool = False,
    limit: int = 50,
    offset: int = 0
):
    """List all topics"""
    try:
        async with httpx.AsyncClient() as http_client:
            query = f"order=trending_score.desc&limit={limit}&offset={offset}"
            if trending_only:
                query += "&trending_score=gt.0"
            if subscribed_only:
                query += "&user_subscribed=eq.true"

            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/topics?{query}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {
                    "topics": resp.json(),
                    "count": len(resp.json())
                }
            return {"topics": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list topics: {e}")

@app.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    """Get topic with recent articles"""
    try:
        async with httpx.AsyncClient() as http_client:
            # Get topic
            topic_resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/topics?id=eq.{topic_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if topic_resp.status_code == 200:
                topics = topic_resp.json()
                if topics:
                    topic = topics[0]

                    # Get recent articles for this topic
                    articles_resp = await http_client.get(
                        f"{SUPABASE_URL}/rest/v1/articles?topics=cs.{{{topic.get('name')}}}&order=published_at.desc&limit=10",
                        headers={
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}"
                        },
                        timeout=10.0
                    )

                    articles = articles_resp.json() if articles_resp.status_code == 200 else []

                    return {
                        **topic,
                        "recent_articles": articles,
                        "article_count": len(articles)
                    }
                raise HTTPException(status_code=404, detail="Topic not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get topic: {e}")

@app.post("/topics")
async def create_topic(req: TopicCreate):
    """Create/track a new topic"""
    try:
        async with httpx.AsyncClient() as http_client:
            topic_data = {
                "name": req.name.lower().replace(" ", "_"),
                "display_name": req.display_name,
                "keywords": req.keywords,
                "related_topics": req.related_topics or [],
                "importance": 50,
                "user_subscribed": True,
                "article_count": 0,
                "trending_score": 0
            }

            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/topics",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=topic_data,
                timeout=10.0
            )

            if resp.status_code in [200, 201]:
                return resp.json()[0] if resp.json() else topic_data
            raise HTTPException(status_code=resp.status_code, detail="Failed to create topic")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create topic: {e}")

@app.put("/topics/{topic_id}")
async def update_topic(topic_id: str, req: TopicUpdate):
    """Update topic settings"""
    try:
        async with httpx.AsyncClient() as http_client:
            update_data = {k: v for k, v in req.dict().items() if v is not None}
            update_data["updated_at"] = get_time_context()['current_datetime']

            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/topics?id=eq.{topic_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=update_data,
                timeout=10.0
            )

            if resp.status_code == 200:
                return resp.json()[0] if resp.json() else {"status": "updated"}
            raise HTTPException(status_code=resp.status_code, detail="Failed to update topic")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update topic: {e}")

@app.delete("/topics/{topic_id}")
async def delete_topic(topic_id: str):
    """Stop tracking a topic"""
    try:
        async with httpx.AsyncClient() as http_client:
            # Just mark as not subscribed rather than deleting
            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/topics?id=eq.{topic_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"user_subscribed": False},
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"status": "unsubscribed", "topic_id": topic_id}
            raise HTTPException(status_code=resp.status_code, detail="Failed to unsubscribe from topic")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unsubscribe from topic: {e}")

@app.get("/topics/trending")
async def get_trending_topics():
    """Get trending topics"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/topics?order=trending_score.desc&limit=20&trending_score=gt.0",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {
                    "trending": resp.json(),
                    "count": len(resp.json()),
                    "updated_at": get_time_context()['current_datetime']
                }
            return {"trending": [], "count": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trending topics: {e}")

@app.post("/topics/subscribe")
async def subscribe_to_topic(req: TopicSubscribeRequest):
    """Subscribe to topic alerts"""
    try:
        async with httpx.AsyncClient() as http_client:
            # Update topic subscription
            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/topics?id=eq.{req.topic_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"user_subscribed": True},
                timeout=10.0
            )

            await notify_event_bus("news.topic.subscribed", {
                "user_id": req.user_id,
                "topic_id": req.topic_id,
                "alert_threshold": req.alert_threshold
            })

            return {
                "status": "subscribed",
                "user_id": req.user_id,
                "topic_id": req.topic_id,
                "alert_threshold": req.alert_threshold
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe to topic: {e}")

# =============================================================================
# USER PREFERENCES ENDPOINTS
# =============================================================================

@app.get("/preferences")
async def get_preferences(user_id: str = "default"):
    """Get user preferences"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/user_preferences?user_id=eq.{user_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                prefs = resp.json()
                if prefs:
                    return prefs[0]
                # Return defaults if no preferences set
                return {
                    "user_id": user_id,
                    "topics": [],
                    "excluded_topics": [],
                    "sources": [],
                    "excluded_sources": [],
                    "briefing_time": "07:00",
                    "briefing_timezone": "UTC",
                    "briefing_format": "summary",
                    "bias_preference": "balanced",
                    "language": "en"
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {e}")

@app.put("/preferences")
async def update_preferences(user_id: str, req: UserPreferencesUpdate):
    """Update user preferences"""
    try:
        async with httpx.AsyncClient() as http_client:
            update_data = {"user_id": user_id}
            update_data.update({k: v for k, v in req.dict().items() if v is not None})
            update_data["updated_at"] = get_time_context()['current_datetime']

            # Upsert preferences
            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/user_preferences",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=representation"
                },
                json=update_data,
                timeout=10.0
            )

            if resp.status_code in [200, 201]:
                await notify_event_bus("user.preference.updated", {
                    "user_id": user_id,
                    "updated_fields": list(req.dict(exclude_none=True).keys())
                })
                return resp.json()[0] if resp.json() else update_data
            raise HTTPException(status_code=resp.status_code, detail="Failed to update preferences")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {e}")

@app.post("/preferences/topics")
async def add_tracked_topics(user_id: str, req: TopicAddRequest):
    """Add topics to user's tracked list"""
    try:
        # Get current preferences
        prefs = await get_preferences(user_id)
        current_topics = prefs.get('topics', [])

        # Add new topics (avoid duplicates)
        new_topics = list(set(current_topics + req.topics))

        # Update preferences
        update_req = UserPreferencesUpdate(topics=new_topics)
        return await update_preferences(user_id, update_req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add topics: {e}")

@app.delete("/preferences/topics/{topic_name}")
async def remove_tracked_topic(user_id: str, topic_name: str):
    """Remove topic from user's tracked list"""
    try:
        # Get current preferences
        prefs = await get_preferences(user_id)
        current_topics = prefs.get('topics', [])

        # Remove topic
        if topic_name in current_topics:
            current_topics.remove(topic_name)

        # Update preferences
        update_req = UserPreferencesUpdate(topics=current_topics)
        return await update_preferences(user_id, update_req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove topic: {e}")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8209)
