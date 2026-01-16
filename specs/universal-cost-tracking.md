# UNIVERSAL COST TRACKING - All Agents

## Overview
Add cost tracking to EVERY agent by default. This is critical infrastructure - we cannot optimize what we don't measure.

---

## PART 1: Create Shared Cost Tracking Module

Create `/opt/leveredge/control-plane/shared/cost_tracker.py`:

```python
"""
Universal Cost Tracking Module for LeverEdge Agents
Import this in EVERY agent that makes LLM or API calls.
"""

import os
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Pricing as of Jan 2026 (update as needed)
PRICING = {
    # Anthropic Claude
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},  # per 1M tokens
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
    # Aliases
    "claude-sonnet": {"input": 3.00, "output": 15.00},
    "claude-opus": {"input": 15.00, "output": 75.00},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    # OpenAI (if used)
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Google (if used)
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
}

# Tool/feature costs
FEATURE_COSTS = {
    "web_search": 0.01,  # per search (estimate)
    "pdf_processing": 0.02,  # per page (estimate)
    "image_processing": 0.01,  # per image
}

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")


@dataclass
class UsageRecord:
    """Single usage record for tracking"""
    agent: str
    endpoint: str
    model: str
    input_tokens: int
    output_tokens: int
    web_searches: int = 0
    other_features: Dict[str, int] = None
    
    @property
    def input_cost(self) -> float:
        pricing = PRICING.get(self.model, PRICING["claude-sonnet"])
        return (self.input_tokens / 1_000_000) * pricing["input"]
    
    @property
    def output_cost(self) -> float:
        pricing = PRICING.get(self.model, PRICING["claude-sonnet"])
        return (self.output_tokens / 1_000_000) * pricing["output"]
    
    @property
    def feature_cost(self) -> float:
        cost = self.web_searches * FEATURE_COSTS["web_search"]
        if self.other_features:
            for feature, count in self.other_features.items():
                cost += count * FEATURE_COSTS.get(feature, 0)
        return cost
    
    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost + self.feature_cost


class CostTracker:
    """Universal cost tracker for all LeverEdge agents"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
    
    async def log_usage(
        self,
        endpoint: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        web_searches: int = 0,
        other_features: Dict[str, int] = None,
        metadata: Dict[str, Any] = None
    ) -> dict:
        """Log usage to database and event bus"""
        
        record = UsageRecord(
            agent=self.agent_name,
            endpoint=endpoint,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            web_searches=web_searches,
            other_features=other_features or {}
        )
        
        # Build log entry
        log_entry = {
            "agent": self.agent_name,
            "endpoint": endpoint,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "web_searches": web_searches,
            "other_features": other_features or {},
            "input_cost": round(record.input_cost, 6),
            "output_cost": round(record.output_cost, 6),
            "feature_cost": round(record.feature_cost, 6),
            "total_cost": round(record.total_cost, 6),
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log to database
        await self._log_to_database(log_entry)
        
        # Log to event bus
        await self._log_to_event_bus(log_entry)
        
        return log_entry
    
    async def _log_to_database(self, entry: dict) -> None:
        """Insert usage record into Supabase"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/agent_usage_logs",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json=entry,
                    timeout=5.0
                )
                if response.status_code not in [200, 201]:
                    print(f"[CostTracker] DB log failed: {response.status_code}")
        except Exception as e:
            print(f"[CostTracker] DB log error: {e}")
    
    async def _log_to_event_bus(self, entry: dict) -> None:
        """Publish usage event to event bus"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{EVENT_BUS_URL}/publish",
                    json={
                        "event_type": "agent_usage",
                        "source": self.agent_name,
                        "data": {
                            "endpoint": entry["endpoint"],
                            "total_cost": entry["total_cost"],
                            "model": entry["model"]
                        }
                    },
                    timeout=2.0
                )
        except Exception as e:
            print(f"[CostTracker] Event bus error: {e}")
    
    @staticmethod
    def extract_usage_from_response(response) -> tuple:
        """Extract token counts from Anthropic API response"""
        usage = getattr(response, 'usage', None)
        if usage:
            return (
                getattr(usage, 'input_tokens', 0),
                getattr(usage, 'output_tokens', 0)
            )
        return (0, 0)
    
    @staticmethod
    def count_web_searches(response) -> int:
        """Count web searches in response content blocks"""
        count = 0
        content = getattr(response, 'content', [])
        for block in content:
            if getattr(block, 'type', '') == 'tool_use':
                if getattr(block, 'name', '') == 'web_search':
                    count += 1
        return count


# Convenience function for quick logging
async def log_llm_usage(
    agent: str,
    endpoint: str,
    model: str,
    response,
    web_searches: int = 0,
    metadata: dict = None
) -> dict:
    """Quick helper to log usage from an Anthropic response"""
    tracker = CostTracker(agent)
    input_tokens, output_tokens = tracker.extract_usage_from_response(response)
    
    return await tracker.log_usage(
        endpoint=endpoint,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        web_searches=web_searches,
        metadata=metadata
    )
```

---

## PART 2: Create Database Table

Run in Supabase (PROD):

```sql
-- Agent usage logs table
CREATE TABLE IF NOT EXISTS agent_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    web_searches INTEGER NOT NULL DEFAULT 0,
    other_features JSONB DEFAULT '{}',
    input_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    output_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    feature_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    total_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_usage_agent ON agent_usage_logs(agent);
CREATE INDEX idx_usage_timestamp ON agent_usage_logs(timestamp);
CREATE INDEX idx_usage_agent_timestamp ON agent_usage_logs(agent, timestamp);

-- Summary view for quick cost overview
CREATE OR REPLACE VIEW agent_cost_summary AS
SELECT 
    agent,
    DATE(timestamp) as date,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(web_searches) as total_web_searches,
    ROUND(SUM(total_cost)::numeric, 4) as total_cost
FROM agent_usage_logs
GROUP BY agent, DATE(timestamp)
ORDER BY date DESC, agent;

-- Function to get cost for date range
CREATE OR REPLACE FUNCTION get_agent_costs(
    start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    agent TEXT,
    request_count BIGINT,
    total_input_tokens BIGINT,
    total_output_tokens BIGINT,
    total_web_searches BIGINT,
    total_cost DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.agent,
        COUNT(*)::BIGINT,
        SUM(l.input_tokens)::BIGINT,
        SUM(l.output_tokens)::BIGINT,
        SUM(l.web_searches)::BIGINT,
        ROUND(SUM(l.total_cost)::numeric, 4)::DECIMAL
    FROM agent_usage_logs l
    WHERE l.timestamp BETWEEN start_date AND end_date
    GROUP BY l.agent
    ORDER BY SUM(l.total_cost) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get daily cost trend
CREATE OR REPLACE FUNCTION get_daily_costs(days INTEGER DEFAULT 30)
RETURNS TABLE (
    date DATE,
    total_cost DECIMAL,
    request_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(timestamp),
        ROUND(SUM(total_cost)::numeric, 4)::DECIMAL,
        COUNT(*)::BIGINT
    FROM agent_usage_logs
    WHERE timestamp > NOW() - (days || ' days')::INTERVAL
    GROUP BY DATE(timestamp)
    ORDER BY DATE(timestamp) DESC;
END;
$$ LANGUAGE plpgsql;
```

---

## PART 3: Update CHIRON to Use Cost Tracking

Add to `/opt/leveredge/control-plane/agents/chiron/chiron.py`:

```python
# At top of file, add import
import sys
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

# Initialize tracker
cost_tracker = CostTracker("CHIRON")

# In call_llm function, after getting response:
async def call_llm(messages: list, time_ctx: dict, portfolio_ctx: dict = None) -> str:
    """Call Claude API with cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx, portfolio_ctx)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )
        
        # LOG COST
        await log_llm_usage(
            agent="CHIRON",
            endpoint=messages[0].get("content", "")[:50],  # First 50 chars of request
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )
        
        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")
```

---

## PART 4: Update SCHOLAR to Use Cost Tracking

Add to `/opt/leveredge/control-plane/agents/scholar/scholar.py`:

```python
# At top of file, add import
import sys
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

# Initialize tracker
cost_tracker = CostTracker("SCHOLAR")

# In call_llm_with_search function:
async def call_llm_with_search(messages: list, time_ctx: dict, enable_search: bool = True) -> str:
    """Call Claude API with web search and cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx)
        
        tools = []
        if enable_search:
            tools = [{"type": "web_search_20250305", "name": "web_search"}]
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
            tools=tools if tools else None
        )
        
        # Count web searches in response
        web_search_count = cost_tracker.count_web_searches(response)
        
        # LOG COST
        await log_llm_usage(
            agent="SCHOLAR",
            endpoint=messages[0].get("content", "")[:50],
            model="claude-sonnet-4-20250514",
            response=response,
            web_searches=web_search_count,
            metadata={"search_enabled": enable_search}
        )
        
        # Extract text from response
        full_response = ""
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                full_response += block.text
        
        return full_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")
```

---

## PART 5: Update ALL Other Agents

Apply same pattern to:
- ARIA (data-plane) - Most important, highest usage
- CHIRON ✓
- SCHOLAR ✓
- ATHENA (if LLM calls)
- Any future agent with LLM calls

---

## PART 6: Add Cost Dashboard Endpoint to ARGUS

Add to ARGUS (monitoring agent):

```python
@app.get("/costs")
async def get_costs(days: int = 30):
    """Get cost summary for monitoring"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_agent_costs",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
                    "end_date": datetime.now().isoformat()
                }
            )
            return {
                "period_days": days,
                "costs_by_agent": response.json(),
                "generated_at": datetime.now().isoformat()
            }
    except Exception as e:
        return {"error": str(e)}

@app.get("/costs/daily")
async def get_daily_costs(days: int = 30):
    """Get daily cost trend"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_daily_costs",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"days": days}
            )
            return {
                "daily_costs": response.json(),
                "generated_at": datetime.now().isoformat()
            }
    except Exception as e:
        return {"error": str(e)}
```

---

## PART 7: Create Shared Directory Structure

```bash
mkdir -p /opt/leveredge/control-plane/shared
touch /opt/leveredge/control-plane/shared/__init__.py
```

---

## IMPLEMENTATION ORDER

1. Create shared directory
2. Create cost_tracker.py module
3. Create database table and functions (PROD Supabase)
4. Update SCHOLAR with cost tracking
5. Update CHIRON with cost tracking
6. Update ARIA with cost tracking
7. Add ARGUS cost endpoints
8. Rebuild containers
9. Test with sample calls
10. Verify logs appear in database

---

## VERIFICATION

After implementation:

```bash
# Make a SCHOLAR call
curl -X POST http://localhost:8018/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "test cost tracking", "depth": "quick"}'

# Check the logs
curl "http://localhost:8000/rest/v1/agent_usage_logs?order=created_at.desc&limit=5" \
  -H "apikey: YOUR_KEY"

# Check cost summary
curl http://localhost:8009/costs
```

---

## GIT COMMIT MESSAGE

```
Add universal cost tracking infrastructure

- Created shared cost_tracker.py module
- Added agent_usage_logs table with indexes
- Added cost summary view and functions
- Integrated into CHIRON, SCHOLAR
- Added ARGUS /costs endpoints

All agents now track:
- Input/output tokens
- Web searches
- Feature usage
- Total cost per request
```
