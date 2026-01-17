# ARIA Omniscience Architecture

**Version:** 1.0
**Status:** SPECIFICATION
**Last Updated:** January 17, 2026

---

## EXECUTIVE SUMMARY

The ARIA Omniscience Architecture ensures that ARIA knows EVERYTHING that happens across all agents in the LeverEdge ecosystem. This enables ARIA to:

- Answer questions like "What did CHIRON say about..." without re-querying
- Provide context-aware responses based on recent agent activity
- Track decisions made by specialized agents
- Maintain a comprehensive knowledge graph of all system activity
- Surface relevant past interactions proactively

### Design Principles

1. **Zero Bottlenecks** - Agent activity flows asynchronously; no agent waits for ARIA
2. **Comprehensive Capture** - All significant actions and decisions are recorded
3. **Semantic Search** - Fast retrieval via embeddings, not just keyword matching
4. **Noise Filtering** - Intelligence, not just logging; extract facts, not raw data
5. **Privacy Aware** - User data stays isolated; system learns patterns, not secrets

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LEVEREDGE AGENT FLEET                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ SOLON   │ │ CROESUS │ │ PLUTUS  │ │ SCHOLAR │ │ CHIRON  │ │ HERMES  │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
│       │           │           │           │           │           │        │
│       └───────────┴───────────┴─────┬─────┴───────────┴───────────┘        │
│                                     │                                       │
│                           ┌─────────▼─────────┐                            │
│                           │    EVENT BUS      │                            │
│                           │    (Port 8099)    │                            │
│                           └─────────┬─────────┘                            │
│                                     │                                       │
│       ┌─────────────────────────────┼─────────────────────────────┐        │
│       │                             │                             │        │
│       ▼                             ▼                             ▼        │
│ ┌──────────────┐          ┌──────────────────┐          ┌──────────────┐  │
│ │   ATHENA     │          │ ARIA OMNISCIENCE │          │    HERMES    │  │
│ │ (Documents)  │          │     INGEST       │          │ (Notifications)│
│ └──────────────┘          │   (Port 8112)    │          └──────────────┘  │
│                           └────────┬─────────┘                            │
│                                    │                                       │
│                           ┌────────▼─────────┐                            │
│                           │ ARIA KNOWLEDGE   │                            │
│                           │ TABLES (Supabase)│                            │
│                           │                  │                            │
│                           │ - aria_knowledge │                            │
│                           │ - aria_agent_actions                          │
│                           │ - aria_decisions_log                          │
│                           │ - aria_unified_memory                         │
│                           └────────┬─────────┘                            │
│                                    │                                       │
│                           ┌────────▼─────────┐                            │
│                           │       ARIA       │                            │
│                           │ (Personal Assistant)                          │
│                           │ Queries knowledge │                           │
│                           │ on user requests  │                           │
│                           └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## COMPONENTS

### 1. Agent Reporting Protocol

Every agent MUST emit events for significant activities using the shared `aria_reporter` module.

#### Required Event Types

| Event Type | When to Emit | Priority |
|------------|--------------|----------|
| `action_taken` | Agent performs a significant action | HIGH |
| `decision_made` | Agent makes a decision with reasoning | HIGH |
| `external_api_called` | Agent calls external API (web, third-party) | MEDIUM |
| `error_occurred` | Agent encounters an error | HIGH |
| `user_interaction` | Agent directly responds to user request | HIGH |
| `fact_learned` | Agent learns new information | MEDIUM |
| `task_completed` | Agent completes a task | MEDIUM |

#### Standard Event Schema

```python
class AriaEvent(BaseModel):
    """Standard event schema for ARIA omniscience"""
    event_type: str            # action_taken, decision_made, etc.
    source_agent: str          # SOLON, CROESUS, CHIRON, etc.
    timestamp: datetime
    user_id: Optional[str]     # NULL for system events

    # Event details
    action: str                # What happened (verb form)
    target: Optional[str]      # What was acted upon
    details: dict              # Structured details

    # For decisions
    reasoning: Optional[str]   # Why this decision was made
    alternatives: Optional[List[str]]  # Other options considered
    outcome: Optional[str]     # Result of the decision

    # Categorization
    domain: str                # legal, tax, finance, health, business, personal
    importance: str            # high, medium, low

    # Context
    related_entities: List[str] = []  # People, companies, topics
    tags: List[str] = []              # Searchable tags
```

### 2. Event Bus Subscription (Existing)

The Event Bus already supports ARIA subscribing to all events:

```sql
-- From event-bus-schema.sql
('ARIA', '*', 10),  -- ARIA watches everything (low priority, doesn't block)
('ARIA', 'human_input_required', 1),  -- High priority for human input
```

### 3. ARIA Omniscience Ingest Service (NEW)

A dedicated service that processes Event Bus events and extracts knowledge for ARIA.

**Port:** 8112
**Purpose:** Filter noise, extract facts, store with embeddings

#### Service Architecture

```python
# /opt/leveredge/control-plane/agents/aria-omniscience/aria_omniscience.py

from fastapi import FastAPI
from datetime import datetime
import asyncio

app = FastAPI(title="ARIA Omniscience Ingest", version="1.0.0")

class OmniscienceIngest:
    """
    Processes events from Event Bus and extracts knowledge for ARIA.
    """

    def __init__(self):
        self.event_bus_url = "http://event-bus:8099"
        self.supabase = get_supabase_client()
        self.embedding_model = "text-embedding-3-small"

    async def poll_events(self):
        """Poll Event Bus for new ARIA-subscribed events"""
        while True:
            events = await self.fetch_unprocessed_events()
            for event in events:
                await self.process_event(event)
            await asyncio.sleep(5)  # Poll every 5 seconds

    async def process_event(self, event: dict):
        """Process a single event and extract knowledge"""

        # Skip noise events
        if self.is_noise(event):
            await self.mark_processed(event['id'])
            return

        # Extract knowledge based on event type
        knowledge = await self.extract_knowledge(event)

        if knowledge:
            # Store in appropriate tables
            await self.store_knowledge(knowledge)

        # Mark event as processed
        await self.mark_processed(event['id'])

    def is_noise(self, event: dict) -> bool:
        """Determine if event is noise (health checks, routine pings, etc.)"""
        noise_patterns = [
            'health_check',
            'heartbeat',
            'metrics_collect',
            'cache_refresh'
        ]
        return any(pattern in event.get('action', '') for pattern in noise_patterns)

    async def extract_knowledge(self, event: dict) -> Optional[dict]:
        """Extract structured knowledge from event"""

        action = event.get('action', '')
        source = event.get('source_agent', '')
        details = event.get('details', {})

        # Determine knowledge type
        if 'decision' in action or 'recommend' in action:
            return await self.extract_decision(event)
        elif 'action' in action or 'completed' in action:
            return await self.extract_action(event)
        elif 'error' in action or 'failed' in action:
            return await self.extract_error(event)
        elif 'learned' in action or 'discovered' in action:
            return await self.extract_fact(event)

        return None

    async def extract_decision(self, event: dict) -> dict:
        """Extract decision knowledge"""
        return {
            'type': 'decision',
            'agent': event['source_agent'],
            'decision': event.get('details', {}).get('decision', event['action']),
            'reasoning': event.get('details', {}).get('reasoning', ''),
            'outcome': event.get('details', {}).get('outcome', ''),
            'domain': self.classify_domain(event),
            'timestamp': event['timestamp']
        }

    async def store_knowledge(self, knowledge: dict):
        """Store knowledge in appropriate table with embedding"""

        # Generate embedding for semantic search
        embedding = await self.generate_embedding(
            f"{knowledge['type']}: {knowledge.get('decision') or knowledge.get('action')}"
        )

        if knowledge['type'] == 'decision':
            await self.supabase.table('aria_decisions_log').insert({
                'agent': knowledge['agent'],
                'decision': knowledge['decision'],
                'reasoning': knowledge['reasoning'],
                'outcome': knowledge['outcome'],
                'domain': knowledge['domain'],
                'embedding': embedding,
                'timestamp': knowledge['timestamp']
            }).execute()

        elif knowledge['type'] == 'action':
            await self.supabase.table('aria_agent_actions').insert({
                'agent': knowledge['agent'],
                'action': knowledge['action'],
                'target': knowledge.get('target'),
                'details': knowledge.get('details'),
                'domain': knowledge['domain'],
                'embedding': embedding,
                'timestamp': knowledge['timestamp']
            }).execute()

        # Also store in general aria_knowledge for unified search
        await self.supabase.table('aria_knowledge').insert({
            'source_type': 'agent_event',
            'source_agent': knowledge['agent'],
            'domain': knowledge['domain'],
            'content': self.format_knowledge_content(knowledge),
            'embedding': embedding,
            'metadata': knowledge
        }).execute()
```

### 4. Database Schema Additions

```sql
-- New tables for ARIA omniscience

-- Agent actions log
CREATE TABLE aria_agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL,               -- Source agent name
    action TEXT NOT NULL,              -- Action taken
    target TEXT,                       -- What was acted upon
    details JSONB DEFAULT '{}',        -- Action details
    domain TEXT NOT NULL,              -- legal, tax, finance, health, etc.
    user_id UUID,                      -- NULL for system actions
    importance TEXT DEFAULT 'medium',  -- high, medium, low
    embedding VECTOR(1536),            -- For semantic search
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_actions_agent ON aria_agent_actions(agent);
CREATE INDEX idx_agent_actions_domain ON aria_agent_actions(domain);
CREATE INDEX idx_agent_actions_user ON aria_agent_actions(user_id);
CREATE INDEX idx_agent_actions_timestamp ON aria_agent_actions(timestamp DESC);
CREATE INDEX idx_agent_actions_embedding ON aria_agent_actions
    USING ivfflat (embedding vector_cosine_ops);

-- Decisions log with reasoning
CREATE TABLE aria_decisions_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL,               -- Agent that made decision
    decision TEXT NOT NULL,            -- What was decided
    reasoning TEXT,                    -- Why this decision was made
    alternatives JSONB DEFAULT '[]',   -- Other options considered
    outcome TEXT,                      -- Result of decision
    domain TEXT NOT NULL,              -- Domain category
    user_id UUID,
    confidence DECIMAL(5, 2),          -- Agent's confidence in decision
    embedding VECTOR(1536),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decisions_agent ON aria_decisions_log(agent);
CREATE INDEX idx_decisions_domain ON aria_decisions_log(domain);
CREATE INDEX idx_decisions_user ON aria_decisions_log(user_id);
CREATE INDEX idx_decisions_timestamp ON aria_decisions_log(timestamp DESC);
CREATE INDEX idx_decisions_embedding ON aria_decisions_log
    USING ivfflat (embedding vector_cosine_ops);

-- Omniscience configuration per agent
CREATE TABLE aria_omniscience_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL UNIQUE,        -- Agent name
    enabled BOOLEAN DEFAULT TRUE,      -- Whether to ingest from this agent
    event_filters JSONB DEFAULT '[]',  -- Events to include/exclude
    importance_threshold TEXT DEFAULT 'low',  -- Minimum importance to capture
    domains TEXT[] DEFAULT '{}',       -- Domain tags for this agent
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default configs for all agents
INSERT INTO aria_omniscience_config (agent, enabled, domains) VALUES
    ('SOLON', true, ARRAY['legal', 'compliance']),
    ('CROESUS', true, ARRAY['tax', 'finance', 'wealth']),
    ('PLUTUS', true, ARRAY['finance', 'investments']),
    ('SCHOLAR', true, ARRAY['research', 'business']),
    ('CHIRON', true, ARRAY['business', 'strategy']),
    ('HERMES', true, ARRAY['notifications']),
    ('AEGIS', true, ARRAY['security', 'credentials']),
    ('CHRONOS', true, ARRAY['backup', 'maintenance']),
    ('HADES', true, ARRAY['recovery']),
    ('ATHENA', true, ARRAY['documentation']),
    ('GYM-COACH', true, ARRAY['health', 'fitness']),
    ('NUTRITIONIST', true, ARRAY['health', 'nutrition']),
    ('MEAL-PLANNER', true, ARRAY['health', 'food']),
    ('MUSE', true, ARRAY['creative']),
    ('CALLIOPE', true, ARRAY['creative', 'writing']),
    ('THALIA', true, ARRAY['creative', 'design']),
    ('ERATO', true, ARRAY['creative', 'media']),
    ('CLIO', true, ARRAY['creative', 'review']);

-- View for recent agent activity
CREATE VIEW aria_recent_activity AS
SELECT
    'action' as type,
    agent,
    action as description,
    domain,
    timestamp
FROM aria_agent_actions
WHERE timestamp > NOW() - INTERVAL '24 hours'
UNION ALL
SELECT
    'decision' as type,
    agent,
    decision as description,
    domain,
    timestamp
FROM aria_decisions_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC
LIMIT 100;

-- Function for semantic search across all ARIA knowledge
CREATE OR REPLACE FUNCTION aria_semantic_search(
    query_embedding VECTOR(1536),
    search_domain TEXT DEFAULT NULL,
    search_agent TEXT DEFAULT NULL,
    result_limit INT DEFAULT 10
)
RETURNS TABLE (
    source TEXT,
    content TEXT,
    domain TEXT,
    agent TEXT,
    similarity FLOAT,
    timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'aria_knowledge' as source,
        ak.content,
        ak.domain,
        ak.source_agent as agent,
        1 - (ak.embedding <=> query_embedding) as similarity,
        ak.created_at as timestamp
    FROM aria_knowledge ak
    WHERE (search_domain IS NULL OR ak.domain = search_domain)
    AND (search_agent IS NULL OR ak.source_agent = search_agent)

    UNION ALL

    SELECT
        'agent_actions' as source,
        aa.action || ': ' || COALESCE(aa.target, '') as content,
        aa.domain,
        aa.agent,
        1 - (aa.embedding <=> query_embedding) as similarity,
        aa.timestamp
    FROM aria_agent_actions aa
    WHERE (search_domain IS NULL OR aa.domain = search_domain)
    AND (search_agent IS NULL OR aa.agent = search_agent)

    UNION ALL

    SELECT
        'decisions' as source,
        dl.decision || ' - ' || COALESCE(dl.reasoning, '') as content,
        dl.domain,
        dl.agent,
        1 - (dl.embedding <=> query_embedding) as similarity,
        dl.timestamp
    FROM aria_decisions_log dl
    WHERE (search_domain IS NULL OR dl.domain = search_domain)
    AND (search_agent IS NULL OR dl.agent = search_agent)

    ORDER BY similarity DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;
```

### 5. VARYS Coordination (Project Management)

When VARYS (project management) is active, ARIA receives project updates:

```python
# VARYS publishes project events
await event_bus.publish({
    "source_agent": "VARYS",
    "action": "project_phase_completed",
    "target": "LeverEdge MVP",
    "details": {
        "phase": "Phase 3: Testing",
        "completion_date": "2026-01-17",
        "next_phase": "Phase 4: Deployment",
        "blockers": []
    }
})

# ARIA can query VARYS for project status
project_status = await call_agent("VARYS", {
    "action": "get_project_status",
    "project": "LeverEdge MVP"
})
```

### 6. ARIA Query Interface

ARIA queries the omniscience tables when responding to users:

```python
class ARIAKnowledgeQuery:
    """Query interface for ARIA to access omniscience data"""

    async def get_relevant_context(
        self,
        user_query: str,
        user_id: str,
        max_results: int = 10
    ) -> List[dict]:
        """Get relevant context from all knowledge sources"""

        # Generate query embedding
        query_embedding = await self.generate_embedding(user_query)

        # Semantic search across all sources
        results = await self.supabase.rpc(
            'aria_semantic_search',
            {
                'query_embedding': query_embedding,
                'result_limit': max_results
            }
        ).execute()

        return results.data

    async def get_agent_activity(
        self,
        agent: str = None,
        domain: str = None,
        hours: int = 24
    ) -> List[dict]:
        """Get recent agent activity"""

        query = self.supabase.from_('aria_recent_activity').select('*')

        if agent:
            query = query.eq('agent', agent)
        if domain:
            query = query.eq('domain', domain)

        return (await query.execute()).data

    async def get_decisions_by_agent(
        self,
        agent: str,
        limit: int = 10
    ) -> List[dict]:
        """Get recent decisions made by a specific agent"""

        return (await self.supabase
            .from_('aria_decisions_log')
            .select('*')
            .eq('agent', agent)
            .order('timestamp', desc=True)
            .limit(limit)
            .execute()
        ).data

    async def answer_with_context(
        self,
        user_query: str,
        user_id: str
    ) -> dict:
        """Generate answer with relevant omniscience context"""

        # Get relevant context
        context = await self.get_relevant_context(user_query, user_id)

        # Build context string
        context_str = "\n".join([
            f"[{c['agent']}] {c['content']} ({c['timestamp']})"
            for c in context
        ])

        # Include in ARIA prompt
        return {
            "context": context_str,
            "sources": [c['source'] for c in context],
            "agents_referenced": list(set(c['agent'] for c in context))
        }
```

---

## SHARED aria_reporter MODULE

All agents use this shared module to report to ARIA:

```python
# /opt/leveredge/shared/aria_reporter.py

"""
ARIA Reporter - Shared module for agents to report to ARIA omniscience.

Usage:
    from shared.aria_reporter import ARIAReporter

    reporter = ARIAReporter("SOLON")

    # Report an action
    await reporter.report_action(
        action="answered_legal_question",
        target="employment law query",
        details={"jurisdiction": "CA", "confidence": 85}
    )

    # Report a decision
    await reporter.report_decision(
        decision="recommended_attorney_consultation",
        reasoning="Query involves complex fact pattern requiring professional advice",
        outcome="user_directed_to_seek_professional_help"
    )
"""

import os
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ARIAReporter:
    """
    Reporter for agents to emit events to ARIA omniscience system.

    All significant actions and decisions should be reported so ARIA
    maintains comprehensive awareness of system activity.
    """

    def __init__(self, agent_name: str):
        """
        Initialize reporter for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., "SOLON", "CROESUS")
        """
        self.agent_name = agent_name
        self.event_bus_url = os.environ.get(
            "EVENT_BUS_URL",
            "http://event-bus:8099"
        )
        self.enabled = os.environ.get("ARIA_REPORTING_ENABLED", "true").lower() == "true"

    async def report_action(
        self,
        action: str,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        domain: Optional[str] = None,
        importance: str = "medium",
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Report an action taken by this agent.

        Args:
            action: What action was taken (e.g., "answered_question", "analyzed_contract")
            target: What was acted upon (e.g., "employment law query", "service agreement")
            details: Additional structured details
            domain: Domain category (legal, tax, finance, health, etc.)
            importance: Priority level (high, medium, low)
            user_id: User associated with this action (if applicable)
            tags: Searchable tags

        Returns:
            True if report was successful
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": f"aria.action.{action}",
            "target": target,
            "details": {
                "action": action,
                "target": target,
                "domain": domain or self._infer_domain(),
                "importance": importance,
                "user_id": user_id,
                "tags": tags or [],
                **(details or {})
            }
        }

        return await self._emit_event(event)

    async def report_decision(
        self,
        decision: str,
        reasoning: str,
        outcome: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        domain: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report a decision made by this agent.

        Args:
            decision: What was decided
            reasoning: Why this decision was made
            outcome: Result of the decision
            alternatives: Other options that were considered
            confidence: Agent's confidence in this decision (0-100)
            domain: Domain category
            user_id: User associated with this decision

        Returns:
            True if report was successful
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": f"aria.decision.{decision.replace(' ', '_')}",
            "details": {
                "decision": decision,
                "reasoning": reasoning,
                "outcome": outcome,
                "alternatives": alternatives or [],
                "confidence": confidence,
                "domain": domain or self._infer_domain(),
                "user_id": user_id
            }
        }

        return await self._emit_event(event)

    async def report_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report an error encountered by this agent.

        Args:
            error_type: Category of error
            error_message: Error description
            context: Additional context about the error
            recoverable: Whether the agent recovered from this error
            user_id: User affected by this error

        Returns:
            True if report was successful
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": f"aria.error.{error_type}",
            "details": {
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
                "recoverable": recoverable,
                "user_id": user_id,
                "domain": self._infer_domain(),
                "importance": "high"
            }
        }

        return await self._emit_event(event)

    async def report_fact_learned(
        self,
        fact: str,
        source: str,
        category: str,
        confidence: float = 100.0,
        related_to: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report a new fact learned by this agent.

        Args:
            fact: The fact that was learned
            source: Where this fact came from
            category: Category of fact (person, company, preference, etc.)
            confidence: How confident we are in this fact (0-100)
            related_to: Related entities or topics
            user_id: User this fact is about (if applicable)

        Returns:
            True if report was successful
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": "aria.fact.learned",
            "details": {
                "fact": fact,
                "source": source,
                "category": category,
                "confidence": confidence,
                "related_to": related_to or [],
                "user_id": user_id,
                "domain": self._infer_domain()
            }
        }

        return await self._emit_event(event)

    async def report_task_completed(
        self,
        task: str,
        result: str,
        duration_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report completion of a task.

        Args:
            task: What task was completed
            result: Outcome of the task
            duration_ms: How long the task took
            details: Additional details
            user_id: User who requested this task

        Returns:
            True if report was successful
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": f"aria.task.completed",
            "target": task,
            "details": {
                "task": task,
                "result": result,
                "duration_ms": duration_ms,
                "domain": self._infer_domain(),
                "user_id": user_id,
                **(details or {})
            }
        }

        return await self._emit_event(event)

    async def _emit_event(self, event: dict) -> bool:
        """Emit event to Event Bus"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.event_bus_url}/events",
                    json=event,
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception as e:
            # Don't let reporting failures break agent functionality
            print(f"[{self.agent_name}] Failed to report to ARIA: {e}")
            return False

    def _infer_domain(self) -> str:
        """Infer domain based on agent name"""
        domain_map = {
            "SOLON": "legal",
            "CROESUS": "tax",
            "PLUTUS": "finance",
            "SCHOLAR": "research",
            "CHIRON": "business",
            "GYM-COACH": "health",
            "NUTRITIONIST": "health",
            "MEAL-PLANNER": "health",
            "MUSE": "creative",
            "CALLIOPE": "creative",
            "THALIA": "creative",
            "ERATO": "creative",
            "CLIO": "creative",
            "HERMES": "notifications",
            "AEGIS": "security",
            "CHRONOS": "infrastructure",
            "HADES": "infrastructure",
            "ATHENA": "documentation"
        }
        return domain_map.get(self.agent_name, "general")


# Convenience function for one-off reports
async def report_to_aria(
    agent: str,
    action: str,
    details: dict,
    domain: str = "general"
) -> bool:
    """
    Quick one-off report to ARIA.

    Usage:
        await report_to_aria("CUSTOM_AGENT", "did_something", {"key": "value"})
    """
    reporter = ARIAReporter(agent)
    return await reporter.report_action(action, details=details, domain=domain)
```

---

## AGENT INTEGRATION GUIDE

### Adding ARIA Reporting to an Agent

```python
# Example: Adding to SOLON

from shared.aria_reporter import ARIAReporter

# Initialize reporter at agent startup
reporter = ARIAReporter("SOLON")

# In your legal question endpoint
@app.post("/legal/question")
async def answer_legal_question(request: LegalQuestionRequest):
    # Process the question
    answer = await process_question(request.question)

    # Report to ARIA
    await reporter.report_action(
        action="answered_legal_question",
        target=request.question[:100],  # Truncate for privacy
        details={
            "jurisdiction": request.jurisdiction,
            "domain": answer.domain,
            "confidence": answer.confidence_score,
            "citations_count": len(answer.citations)
        },
        domain="legal",
        importance="medium" if answer.confidence_score > 50 else "high"
    )

    return answer

# When making a significant decision
if should_recommend_attorney(answer):
    await reporter.report_decision(
        decision="recommended_attorney_consultation",
        reasoning=f"Query confidence {answer.confidence_score}% below threshold, involves {answer.domain}",
        outcome="user_directed_to_professional",
        domain="legal"
    )
```

### Required Agent Changes

All existing agents need these updates:

1. **Import the reporter:**
   ```python
   from shared.aria_reporter import ARIAReporter
   reporter = ARIAReporter("AGENT_NAME")
   ```

2. **Report significant actions** (after completing major operations)

3. **Report decisions** (when making choices with reasoning)

4. **Report errors** (when encountering failures)

---

## CONFIGURATION

### Environment Variables

```bash
# Enable/disable ARIA reporting
ARIA_REPORTING_ENABLED=true

# Event Bus URL
EVENT_BUS_URL=http://event-bus:8099

# Omniscience Ingest URL
ARIA_OMNISCIENCE_URL=http://aria-omniscience:8112
```

### agent-registry.yaml Updates

```yaml
# Add to global config
config:
  aria_omniscience:
    enabled: true
    ingest_url: http://aria-omniscience:8112
    required_events:
      - action_taken
      - decision_made
      - error_occurred

# Add to each agent
agents:
  solon:
    # ... existing config ...
    aria_reporting:
      enabled: true
      domains: [legal, compliance]
      importance_threshold: low
```

---

## IMPLEMENTATION PHASES

### Phase 1: Core Infrastructure (Sprint 1)
- [ ] Create aria_reporter.py shared module
- [ ] Create database tables (aria_agent_actions, aria_decisions_log)
- [ ] Create ARIA Omniscience Ingest service skeleton
- [ ] Deploy and test basic event flow

### Phase 2: Ingest Service (Sprint 2)
- [ ] Implement event polling from Event Bus
- [ ] Implement noise filtering
- [ ] Implement knowledge extraction
- [ ] Implement embedding generation and storage
- [ ] Test with sample events

### Phase 3: Agent Integration (Sprint 3)
- [ ] Update SOLON with aria_reporter
- [ ] Update CROESUS with aria_reporter
- [ ] Update 5 more high-priority agents
- [ ] Validate events flowing through system

### Phase 4: ARIA Query Interface (Sprint 4)
- [ ] Implement semantic search function
- [ ] Integrate into ARIA main workflow
- [ ] Test context retrieval
- [ ] Performance optimization

### Phase 5: Full Rollout (Sprint 5)
- [ ] Update remaining agents
- [ ] Update agent-registry.yaml
- [ ] Monitor and tune noise filtering
- [ ] Documentation and runbook

---

## SUCCESS CRITERIA

### Functional
- [ ] All agents emit events via aria_reporter
- [ ] Events processed within 10 seconds
- [ ] Semantic search returns relevant results in < 500ms
- [ ] ARIA answers include relevant agent context

### Quality
- [ ] < 1% event loss rate
- [ ] Noise filtering removes > 80% of routine events
- [ ] Embeddings enable semantic (not just keyword) search
- [ ] No performance impact on agent operations

### Integration
- [ ] Event Bus handles increased load
- [ ] Database indexes support query patterns
- [ ] ARIA prompts include context when relevant
- [ ] Users notice more context-aware responses

---

## GIT COMMIT

```
Add ARIA Omniscience Architecture specification

- Event Bus subscription for all agents
- ARIA Omniscience Ingest service (port 8112)
- New database tables: aria_agent_actions, aria_decisions_log
- Shared aria_reporter.py module for agent reporting
- Semantic search across all knowledge sources
- 5-phase implementation plan
- Agent integration guide
- Configuration and environment setup
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/aria-omniscience.md

Context: Implement ARIA Omniscience Architecture.
Start with Phase 1: Core Infrastructure.
Creates shared module that all agents will use.
```
