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
