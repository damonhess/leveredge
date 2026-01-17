#!/usr/bin/env python3
"""
ARIA Omniscience Ingest Service

Processes events from Event Bus and extracts knowledge for ARIA.
Enables ARIA to know EVERYTHING that happens across all agents.

Port: 8112
Version: 1.0.0
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ARIA-OMNISCIENCE")

# =============================================================================
# CONFIGURATION
# =============================================================================

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # For embeddings

# Polling configuration
POLL_INTERVAL_SECONDS = 5
MAX_EVENTS_PER_BATCH = 50

# Noise patterns to filter out
NOISE_PATTERNS = [
    "health_check",
    "heartbeat",
    "metrics_collect",
    "cache_refresh",
    "ping",
    "status_poll",
    "keepalive"
]

# Domain mapping for agents
AGENT_DOMAINS = {
    "SOLON": ["legal", "compliance"],
    "CROESUS": ["tax", "finance", "wealth"],
    "PLUTUS": ["finance", "investments"],
    "SCHOLAR": ["research", "business"],
    "CHIRON": ["business", "strategy"],
    "HERMES": ["notifications"],
    "AEGIS": ["security", "credentials"],
    "CHRONOS": ["backup", "maintenance"],
    "HADES": ["recovery"],
    "ATHENA": ["documentation"],
    "GYM-COACH": ["health", "fitness"],
    "NUTRITIONIST": ["health", "nutrition"],
    "MEAL-PLANNER": ["health", "food"],
    "MUSE": ["creative"],
    "CALLIOPE": ["creative", "writing"],
    "THALIA": ["creative", "design"],
    "ERATO": ["creative", "media"],
    "CLIO": ["creative", "review"],
    "ARIA": ["personal", "assistant"],
    "EVENT-BUS": ["infrastructure"],
    "PORT-MANAGER": ["infrastructure"],
}

# =============================================================================
# MODELS
# =============================================================================

class ProcessedEvent(BaseModel):
    """Processed event ready for storage"""
    event_id: str
    source_agent: str
    action: str
    target: Optional[str] = None
    domain: str
    importance: str = "medium"
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class Knowledge(BaseModel):
    """Extracted knowledge item"""
    type: str  # action, decision, error, fact
    agent: str
    content: str
    domain: str
    importance: str = "medium"
    reasoning: Optional[str] = None
    outcome: Optional[str] = None
    confidence: Optional[float] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class IngestStats(BaseModel):
    """Statistics for the ingest service"""
    events_processed: int = 0
    events_filtered: int = 0
    knowledge_items_stored: int = 0
    errors: int = 0
    last_poll_time: Optional[datetime] = None
    uptime_seconds: float = 0


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    event_bus_connected: bool
    database_connected: bool
    polling_active: bool
    stats: IngestStats


# =============================================================================
# OMNISCIENCE INGEST SERVICE
# =============================================================================

class OmniscienceIngest:
    """
    Main ingest service that processes events and extracts knowledge.
    """

    def __init__(self):
        self.stats = IngestStats()
        self.start_time = datetime.utcnow()
        self.polling_active = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_processed_id: Optional[str] = None

    async def start_polling(self):
        """Start the event polling loop"""
        if self.polling_active:
            logger.warning("Polling already active")
            return

        self.polling_active = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Event polling started")

    async def stop_polling(self):
        """Stop the event polling loop"""
        self.polling_active = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("Event polling stopped")

    async def _poll_loop(self):
        """Main polling loop"""
        while self.polling_active:
            try:
                await self._poll_events()
                self.stats.last_poll_time = datetime.utcnow()
            except Exception as e:
                logger.error(f"Poll error: {e}")
                self.stats.errors += 1

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _poll_events(self):
        """Poll Event Bus for new events"""
        try:
            async with httpx.AsyncClient() as client:
                # Get events subscribed by ARIA (all events)
                response = await client.get(
                    f"{EVENT_BUS_URL}/events/pending/ARIA",
                    params={"limit": MAX_EVENTS_PER_BATCH},
                    timeout=10.0
                )

                if response.status_code == 200:
                    events = response.json()
                    for event in events:
                        await self.process_event(event)
                elif response.status_code == 404:
                    # No pending events - this is normal
                    pass
                else:
                    logger.warning(f"Event Bus returned {response.status_code}")

        except httpx.ConnectError:
            logger.debug("Event Bus not available - will retry")
        except Exception as e:
            logger.error(f"Error polling events: {e}")

    async def process_event(self, event: dict):
        """Process a single event and extract knowledge"""
        event_id = event.get("id", "unknown")

        try:
            # Check if event is noise
            if self._is_noise(event):
                self.stats.events_filtered += 1
                await self._mark_processed(event_id)
                return

            # Extract knowledge
            knowledge = await self._extract_knowledge(event)

            if knowledge:
                # Store the knowledge
                await self._store_knowledge(knowledge)
                self.stats.knowledge_items_stored += 1

            # Mark event as processed
            await self._mark_processed(event_id)
            self.stats.events_processed += 1

        except Exception as e:
            logger.error(f"Error processing event {event_id}: {e}")
            self.stats.errors += 1

    def _is_noise(self, event: dict) -> bool:
        """Determine if event is noise"""
        action = event.get("action", "").lower()
        return any(pattern in action for pattern in NOISE_PATTERNS)

    async def _extract_knowledge(self, event: dict) -> Optional[Knowledge]:
        """Extract structured knowledge from event"""
        action = event.get("action", "")
        source = event.get("source_agent", "UNKNOWN")
        details = event.get("details", {})
        timestamp = event.get("timestamp", datetime.utcnow().isoformat())

        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                timestamp = datetime.utcnow()

        # Classify the event type
        if "aria.decision" in action or "decision" in action.lower():
            return await self._extract_decision(event, timestamp)
        elif "aria.action" in action or "action" in action.lower():
            return await self._extract_action(event, timestamp)
        elif "aria.error" in action or "error" in action.lower() or "failed" in action.lower():
            return await self._extract_error(event, timestamp)
        elif "aria.fact" in action or "learned" in action.lower():
            return await self._extract_fact(event, timestamp)
        elif "aria.task" in action or "completed" in action.lower():
            return await self._extract_task(event, timestamp)

        # Generic knowledge extraction for other events
        return await self._extract_generic(event, timestamp)

    async def _extract_decision(self, event: dict, timestamp: datetime) -> Knowledge:
        """Extract decision knowledge"""
        details = event.get("details", {})
        source = event.get("source_agent", "UNKNOWN")

        return Knowledge(
            type="decision",
            agent=source,
            content=details.get("decision", event.get("action", "")),
            domain=details.get("domain", self._get_primary_domain(source)),
            importance="high",
            reasoning=details.get("reasoning"),
            outcome=details.get("outcome"),
            confidence=details.get("confidence"),
            user_id=details.get("user_id"),
            metadata={
                "alternatives": details.get("alternatives", []),
                "original_action": event.get("action")
            },
            timestamp=timestamp
        )

    async def _extract_action(self, event: dict, timestamp: datetime) -> Knowledge:
        """Extract action knowledge"""
        details = event.get("details", {})
        source = event.get("source_agent", "UNKNOWN")
        target = event.get("target") or details.get("target")

        action_desc = details.get("action", event.get("action", ""))
        if target:
            content = f"{action_desc}: {target}"
        else:
            content = action_desc

        return Knowledge(
            type="action",
            agent=source,
            content=content,
            domain=details.get("domain", self._get_primary_domain(source)),
            importance=details.get("importance", "medium"),
            user_id=details.get("user_id"),
            metadata={
                "target": target,
                "tags": details.get("tags", []),
                "original_action": event.get("action")
            },
            timestamp=timestamp
        )

    async def _extract_error(self, event: dict, timestamp: datetime) -> Knowledge:
        """Extract error knowledge"""
        details = event.get("details", {})
        source = event.get("source_agent", "UNKNOWN")

        error_type = details.get("error_type", "unknown")
        error_msg = details.get("error_message", event.get("action", ""))

        return Knowledge(
            type="error",
            agent=source,
            content=f"{error_type}: {error_msg}",
            domain=details.get("domain", self._get_primary_domain(source)),
            importance="high",
            user_id=details.get("user_id"),
            metadata={
                "error_type": error_type,
                "recoverable": details.get("recoverable", True),
                "context": details.get("context", {}),
                "original_action": event.get("action")
            },
            timestamp=timestamp
        )

    async def _extract_fact(self, event: dict, timestamp: datetime) -> Knowledge:
        """Extract fact knowledge"""
        details = event.get("details", {})
        source = event.get("source_agent", "UNKNOWN")

        return Knowledge(
            type="fact",
            agent=source,
            content=details.get("fact", event.get("action", "")),
            domain=details.get("domain", self._get_primary_domain(source)),
            importance="medium",
            confidence=details.get("confidence", 100.0),
            user_id=details.get("user_id"),
            metadata={
                "source": details.get("source"),
                "category": details.get("category"),
                "related_to": details.get("related_to", []),
                "original_action": event.get("action")
            },
            timestamp=timestamp
        )

    async def _extract_task(self, event: dict, timestamp: datetime) -> Knowledge:
        """Extract task completion knowledge"""
        details = event.get("details", {})
        source = event.get("source_agent", "UNKNOWN")
        target = event.get("target") or details.get("task")

        return Knowledge(
            type="action",
            agent=source,
            content=f"Completed: {target or event.get('action', '')}",
            domain=details.get("domain", self._get_primary_domain(source)),
            importance="medium",
            outcome=details.get("result"),
            user_id=details.get("user_id"),
            metadata={
                "task": target,
                "result": details.get("result"),
                "duration_ms": details.get("duration_ms"),
                "original_action": event.get("action")
            },
            timestamp=timestamp
        )

    async def _extract_generic(self, event: dict, timestamp: datetime) -> Optional[Knowledge]:
        """Extract generic knowledge from any event"""
        source = event.get("source_agent", "UNKNOWN")
        action = event.get("action", "")
        details = event.get("details", {})
        target = event.get("target")

        # Skip events with no meaningful content
        if not action or action in ["event", "update", "change"]:
            return None

        content = action
        if target:
            content = f"{action}: {target}"

        return Knowledge(
            type="action",
            agent=source,
            content=content,
            domain=details.get("domain", self._get_primary_domain(source)),
            importance=details.get("importance", "low"),
            user_id=details.get("user_id"),
            metadata={
                "target": target,
                "details": details,
                "original_action": action
            },
            timestamp=timestamp
        )

    def _get_primary_domain(self, agent: str) -> str:
        """Get primary domain for an agent"""
        domains = AGENT_DOMAINS.get(agent, ["general"])
        return domains[0] if domains else "general"

    async def _store_knowledge(self, knowledge: Knowledge):
        """Store knowledge in database with embedding"""
        if not SUPABASE_KEY:
            logger.debug("No Supabase key - skipping storage")
            return

        try:
            # Generate embedding for semantic search
            embedding = await self._generate_embedding(knowledge.content)

            async with httpx.AsyncClient() as client:
                # Store based on type
                if knowledge.type == "decision":
                    await self._store_decision(client, knowledge, embedding)
                else:
                    await self._store_action(client, knowledge, embedding)

                # Also store in unified aria_knowledge table
                await self._store_unified(client, knowledge, embedding)

        except Exception as e:
            logger.error(f"Error storing knowledge: {e}")
            self.stats.errors += 1

    async def _store_decision(self, client: httpx.AsyncClient, knowledge: Knowledge, embedding: List[float]):
        """Store decision in aria_decisions_log"""
        data = {
            "agent": knowledge.agent,
            "decision": knowledge.content,
            "reasoning": knowledge.reasoning,
            "outcome": knowledge.outcome,
            "domain": knowledge.domain,
            "confidence": knowledge.confidence,
            "user_id": knowledge.user_id,
            "metadata": knowledge.metadata,
            "timestamp": knowledge.timestamp.isoformat()
        }

        if embedding:
            data["embedding"] = embedding

        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/aria_decisions_log",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json=data,
            timeout=10.0
        )

        if response.status_code not in [200, 201]:
            logger.warning(f"Failed to store decision: {response.status_code}")

    async def _store_action(self, client: httpx.AsyncClient, knowledge: Knowledge, embedding: List[float]):
        """Store action in aria_agent_actions"""
        target = knowledge.metadata.get("target")
        details = knowledge.metadata.copy()
        details.pop("target", None)

        data = {
            "agent": knowledge.agent,
            "action": knowledge.content,
            "target": target,
            "details": details,
            "domain": knowledge.domain,
            "importance": knowledge.importance,
            "user_id": knowledge.user_id,
            "timestamp": knowledge.timestamp.isoformat()
        }

        if embedding:
            data["embedding"] = embedding

        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/aria_agent_actions",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json=data,
            timeout=10.0
        )

        if response.status_code not in [200, 201]:
            logger.warning(f"Failed to store action: {response.status_code}")

    async def _store_unified(self, client: httpx.AsyncClient, knowledge: Knowledge, embedding: List[float]):
        """Store in unified aria_knowledge table"""
        # Check if aria_knowledge table exists (it may not in all deployments)
        data = {
            "source_type": "agent_event",
            "source_agent": knowledge.agent,
            "domain": knowledge.domain,
            "content": knowledge.content,
            "metadata": {
                "type": knowledge.type,
                "importance": knowledge.importance,
                "reasoning": knowledge.reasoning,
                "outcome": knowledge.outcome,
                **knowledge.metadata
            }
        }

        if embedding:
            data["embedding"] = embedding

        try:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/aria_knowledge",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=data,
                timeout=10.0
            )
            # Table may not exist - that's OK
        except:
            pass

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI API"""
        if not OPENAI_API_KEY:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": text[:8000],  # Truncate if too long
                        "model": "text-embedding-3-small"
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]

        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")

        return None

    async def _mark_processed(self, event_id: str):
        """Mark event as processed in Event Bus"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{EVENT_BUS_URL}/events/{event_id}/ack",
                    json={"subscriber": "ARIA"},
                    timeout=5.0
                )
        except:
            pass  # Non-critical

    def get_stats(self) -> IngestStats:
        """Get current statistics"""
        self.stats.uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        return self.stats


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

ingest_service = OmniscienceIngest()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("ARIA Omniscience Ingest starting...")
    await ingest_service.start_polling()
    yield
    logger.info("ARIA Omniscience Ingest shutting down...")
    await ingest_service.stop_polling()


app = FastAPI(
    title="ARIA Omniscience Ingest",
    description="Processes events from Event Bus and extracts knowledge for ARIA",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    # Check Event Bus connectivity
    event_bus_ok = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{EVENT_BUS_URL}/health", timeout=5.0)
            event_bus_ok = response.status_code == 200
    except:
        pass

    # Check database connectivity
    db_ok = False
    if SUPABASE_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SUPABASE_URL}/rest/v1/aria_omniscience_config?limit=1",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}"
                    },
                    timeout=5.0
                )
                db_ok = response.status_code == 200
        except:
            pass

    return HealthResponse(
        status="healthy" if event_bus_ok else "degraded",
        service="ARIA Omniscience Ingest",
        version="1.0.0",
        event_bus_connected=event_bus_ok,
        database_connected=db_ok,
        polling_active=ingest_service.polling_active,
        stats=ingest_service.get_stats()
    )


@app.get("/stats", response_model=IngestStats)
async def get_stats():
    """Get ingest statistics"""
    return ingest_service.get_stats()


@app.post("/polling/start")
async def start_polling():
    """Manually start event polling"""
    await ingest_service.start_polling()
    return {"status": "polling started"}


@app.post("/polling/stop")
async def stop_polling():
    """Manually stop event polling"""
    await ingest_service.stop_polling()
    return {"status": "polling stopped"}


@app.post("/process")
async def process_event_manually(event: dict):
    """Manually process a single event (for testing)"""
    await ingest_service.process_event(event)
    return {"status": "processed", "event_id": event.get("id")}


@app.get("/config")
async def get_agent_configs():
    """Get omniscience configuration for all agents"""
    if not SUPABASE_KEY:
        return {"configs": [], "message": "Database not configured"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/aria_omniscience_config",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                return {"configs": response.json()}

    except Exception as e:
        logger.error(f"Error fetching configs: {e}")

    return {"configs": [], "error": "Failed to fetch configs"}


@app.get("/recent")
async def get_recent_activity(
    agent: Optional[str] = None,
    domain: Optional[str] = None,
    hours: int = 24,
    limit: int = 50
):
    """Get recent agent activity from omniscience tables"""
    if not SUPABASE_KEY:
        return {"activity": [], "message": "Database not configured"}

    try:
        async with httpx.AsyncClient() as client:
            # Build query for actions
            url = f"{SUPABASE_URL}/rest/v1/aria_agent_actions"
            params = {
                "order": "timestamp.desc",
                "limit": str(limit)
            }

            if agent:
                params["agent"] = f"eq.{agent}"
            if domain:
                params["domain"] = f"eq.{domain}"

            response = await client.get(
                url,
                params=params,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                return {"activity": response.json()}

    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")

    return {"activity": [], "error": "Failed to fetch activity"}


@app.get("/decisions")
async def get_recent_decisions(
    agent: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 20
):
    """Get recent agent decisions"""
    if not SUPABASE_KEY:
        return {"decisions": [], "message": "Database not configured"}

    try:
        async with httpx.AsyncClient() as client:
            url = f"{SUPABASE_URL}/rest/v1/aria_decisions_log"
            params = {
                "order": "timestamp.desc",
                "limit": str(limit)
            }

            if agent:
                params["agent"] = f"eq.{agent}"
            if domain:
                params["domain"] = f"eq.{domain}"

            response = await client.get(
                url,
                params=params,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                return {"decisions": response.json()}

    except Exception as e:
        logger.error(f"Error fetching decisions: {e}")

    return {"decisions": [], "error": "Failed to fetch decisions"}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8112"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting ARIA Omniscience Ingest on {host}:{port}")

    uvicorn.run(
        "aria_omniscience:app",
        host=host,
        port=port,
        reload=os.getenv("ENV", "development") == "development"
    )
