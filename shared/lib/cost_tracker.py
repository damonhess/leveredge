#!/usr/bin/env python3
"""
LeverEdge Cost Tracker
Tracks LLM API usage and costs across all agents

Usage:
    from shared.lib.cost_tracker import CostTracker

    tracker = CostTracker(supabase_url, supabase_key)
    await tracker.log_usage(
        agent_name="CHIRON",
        model="claude-3-5-sonnet-20241022",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        context="mentor session",
        operation="coaching"
    )
"""

import httpx
from datetime import datetime
from typing import Optional


# Pricing per million tokens (as of Jan 2026)
PRICING = {
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    # OpenAI
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    # Google
    "gemini-pro": {"input": 0.5, "output": 1.5},
    "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
}


class CostTracker:
    """Track LLM usage and costs to Supabase"""

    def __init__(self, supabase_url: str, supabase_key: str, environment: str = "dev"):
        self.supabase_url = supabase_url.rstrip('/')
        self.supabase_key = supabase_key
        self.environment = environment

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD based on model pricing"""
        if model in PRICING:
            p = PRICING[model]
            return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
        # Default fallback pricing
        return (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

    async def log_usage(
        self,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        context: str,
        operation: Optional[str] = None
    ) -> float:
        """Log usage to Supabase llm_usage table"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.supabase_url}/rest/v1/llm_usage",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json={
                        "agent_source": agent_name,
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": cost,
                        "context": f"{context}" + (f" | op:{operation}" if operation else ""),
                        "environment": self.environment,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    timeout=5.0
                )
        except Exception as e:
            # Don't fail operations due to tracking errors
            print(f"[CostTracker] Failed to log usage: {e}")

        return cost

    def log_usage_sync(
        self,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        context: str,
        operation: Optional[str] = None
    ) -> float:
        """Synchronous version for non-async contexts"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        try:
            with httpx.Client() as client:
                client.post(
                    f"{self.supabase_url}/rest/v1/llm_usage",
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json={
                        "agent_source": agent_name,
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": cost,
                        "context": f"{context}" + (f" | op:{operation}" if operation else ""),
                        "environment": self.environment,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    timeout=5.0
                )
        except Exception as e:
            print(f"[CostTracker] Failed to log usage: {e}")

        return cost


# Factory function for common use
def get_tracker(environment: str = "dev") -> CostTracker:
    """Get a configured CostTracker instance"""
    import os

    if environment == "dev":
        url = os.getenv("SUPABASE_DEV_URL", "http://localhost:8100")
        key = os.getenv("SUPABASE_DEV_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UtZGV2IiwiaWF0IjoxNzY4MzQ0MTkwLCJleHAiOjIwODM3MDQxOTB9.mwxbUqKMkk4oluJ_oEPZsVUb46iGmG5Ms2GwUkn0JY4")
    else:
        url = os.getenv("SUPABASE_URL", "http://localhost:8000")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")

    return CostTracker(url, key, environment)
