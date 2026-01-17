#!/usr/bin/env python3
"""
LeverEdge Usage Tracker

Aggregates usage data from agent_usage_logs into billing_usage_records.
Designed to be run daily or on-demand before invoice generation.

Usage:
    python3 usage-tracker.py                    # Aggregate all clients, last 30 days
    python3 usage-tracker.py --client-id UUID   # Specific client
    python3 usage-tracker.py --start 2026-01-01 --end 2026-01-31  # Date range
    python3 usage-tracker.py --dry-run          # Preview without writing
"""

import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Any

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Pricing (matches cost_tracker.py)
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
    "claude-sonnet": {"input": 3.00, "output": 15.00},
    "claude-opus": {"input": 15.00, "output": 75.00},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

FEATURE_COSTS = {
    "web_search": 0.01,
    "pdf_processing": 0.02,
    "image_processing": 0.01,
}


class UsageTracker:
    """Aggregates agent usage into billing records."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = httpx.Client(timeout=30.0)
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def _supabase_get(self, table: str, params: Dict = None) -> List[Dict]:
        """GET from Supabase REST API."""
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        response = self.client.get(url, headers=self.headers, params=params or {})
        response.raise_for_status()
        return response.json()

    def _supabase_post(self, table: str, data: Dict) -> Dict:
        """POST to Supabase REST API."""
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = {**self.headers, "Prefer": "return=representation"}
        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def _supabase_upsert(self, table: str, data: Dict, on_conflict: str) -> Dict:
        """UPSERT to Supabase REST API."""
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        headers = {
            **self.headers,
            "Prefer": "return=representation,resolution=merge-duplicates",
        }
        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_clients(self, client_id: Optional[str] = None) -> List[Dict]:
        """Get active billing clients."""
        params = {"status": "eq.active", "select": "*"}
        if client_id:
            params["id"] = f"eq.{client_id}"
        return self._supabase_get("billing_clients", params)

    def get_client_mapping(self) -> Dict[str, str]:
        """
        Get mapping of agent/metadata to client_id.

        This is a placeholder - in production, you'd have a way to
        associate agent_usage_logs with specific clients.

        Options:
        1. Add client_id to agent_usage_logs metadata
        2. Map agents to clients (if each client has dedicated agents)
        3. Use API keys to identify clients
        """
        # For now, return empty mapping (single-tenant mode)
        # TODO: Implement multi-tenant client mapping
        return {}

    def get_usage_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        client_id: Optional[str] = None,
    ) -> List[Dict]:
        """Get usage logs for date range."""
        params = {
            "select": "*",
            "timestamp": f"gte.{start_date.isoformat()}",
            "order": "timestamp.asc",
        }

        # Add end date filter
        logs = self._supabase_get("agent_usage_logs", params)

        # Filter by end date (Supabase multiple filters on same column)
        logs = [
            log
            for log in logs
            if datetime.fromisoformat(log["timestamp"].replace("Z", "")) <= end_date
        ]

        # Filter by client if mapping exists
        if client_id:
            client_mapping = self.get_client_mapping()
            # For now, include all logs (single-tenant)
            pass

        return logs

    def calculate_token_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost for token usage."""
        pricing = PRICING.get(model, PRICING["claude-sonnet"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def calculate_feature_cost(self, web_searches: int, other_features: Dict) -> float:
        """Calculate cost for feature usage."""
        cost = web_searches * FEATURE_COSTS["web_search"]
        for feature, count in (other_features or {}).items():
            cost += count * FEATURE_COSTS.get(feature, 0)
        return round(cost, 6)

    def aggregate_usage(
        self,
        logs: List[Dict],
        period_start: datetime,
        period_end: datetime,
    ) -> Dict[str, Dict]:
        """
        Aggregate usage logs by agent.

        Returns: {agent_name: {metrics...}}
        """
        aggregated = {}

        for log in logs:
            agent = log.get("agent", "unknown")

            if agent not in aggregated:
                aggregated[agent] = {
                    "agent_name": agent,
                    "period_start": period_start.date().isoformat(),
                    "period_end": period_end.date().isoformat(),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "web_searches": 0,
                    "api_calls": 0,
                    "request_count": 0,
                    "token_cost_usd": 0.0,
                    "feature_cost_usd": 0.0,
                    "total_cost_usd": 0.0,
                    "models_used": {},
                }

            agg = aggregated[agent]

            # Sum tokens
            agg["input_tokens"] += log.get("input_tokens", 0)
            agg["output_tokens"] += log.get("output_tokens", 0)

            # Sum features
            agg["web_searches"] += log.get("web_searches", 0)
            agg["request_count"] += 1

            # Track models
            model = log.get("model", "unknown")
            if model not in agg["models_used"]:
                agg["models_used"][model] = 0
            agg["models_used"][model] += 1

            # Sum costs
            agg["token_cost_usd"] += float(log.get("input_cost", 0)) + float(
                log.get("output_cost", 0)
            )
            agg["feature_cost_usd"] += float(log.get("feature_cost", 0))
            agg["total_cost_usd"] += float(log.get("total_cost", 0))

        # Round final values
        for agent, agg in aggregated.items():
            agg["token_cost_usd"] = round(agg["token_cost_usd"], 4)
            agg["feature_cost_usd"] = round(agg["feature_cost_usd"], 4)
            agg["total_cost_usd"] = round(agg["total_cost_usd"], 4)

        return aggregated

    def save_usage_records(
        self, client_id: str, aggregated: Dict[str, Dict]
    ) -> List[Dict]:
        """Save aggregated usage to billing_usage_records."""
        saved = []

        for agent_name, metrics in aggregated.items():
            record = {
                "client_id": client_id,
                **metrics,
                "recorded_at": datetime.utcnow().isoformat(),
            }

            if self.dry_run:
                print(f"  [DRY RUN] Would save: {agent_name}")
                print(f"    Tokens: {metrics['input_tokens']:,} in / {metrics['output_tokens']:,} out")
                print(f"    Cost: ${metrics['total_cost_usd']:.4f}")
                saved.append(record)
            else:
                try:
                    result = self._supabase_upsert(
                        "billing_usage_records",
                        record,
                        on_conflict="client_id,agent_name,period_start,period_end",
                    )
                    saved.append(result)
                    print(f"  Saved: {agent_name} - ${metrics['total_cost_usd']:.4f}")
                except Exception as e:
                    print(f"  Error saving {agent_name}: {e}")

        return saved

    def run(
        self,
        client_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Main aggregation run.

        Returns summary of aggregated data.
        """
        # Default to last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        print(f"Usage Tracker - {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print("-" * 50)

        # Get clients
        clients = self.get_clients(client_id)

        if not clients:
            # If no billing clients, operate in single-tenant mode
            print("No billing clients found. Operating in single-tenant mode.")
            clients = [{"id": "default", "name": "Default Client"}]

        results = {"period_start": start_date.isoformat(), "period_end": end_date.isoformat(), "clients": []}

        for client in clients:
            cid = client["id"]
            cname = client.get("name", "Unknown")
            print(f"\nClient: {cname}")

            # Get usage logs
            logs = self.get_usage_logs(start_date, end_date, cid)
            print(f"  Found {len(logs)} usage records")

            if not logs:
                results["clients"].append(
                    {"client_id": cid, "name": cname, "records": 0, "total_cost": 0}
                )
                continue

            # Aggregate by agent
            aggregated = self.aggregate_usage(logs, start_date, end_date)

            # Calculate totals
            total_cost = sum(a["total_cost_usd"] for a in aggregated.values())
            total_tokens = sum(
                a["input_tokens"] + a["output_tokens"] for a in aggregated.values()
            )
            total_requests = sum(a["request_count"] for a in aggregated.values())

            print(f"  Agents: {len(aggregated)}")
            print(f"  Total tokens: {total_tokens:,}")
            print(f"  Total requests: {total_requests:,}")
            print(f"  Total cost: ${total_cost:.4f}")

            # Save records (unless default single-tenant)
            if cid != "default":
                saved = self.save_usage_records(cid, aggregated)
            else:
                print("  [Single-tenant mode - not saving to billing_usage_records]")
                saved = list(aggregated.values())

            results["clients"].append(
                {
                    "client_id": cid,
                    "name": cname,
                    "records": len(saved),
                    "total_cost": total_cost,
                    "total_tokens": total_tokens,
                    "total_requests": total_requests,
                    "by_agent": aggregated,
                }
            )

        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY")
        total_all = sum(c["total_cost"] for c in results["clients"])
        print(f"Total cost across all clients: ${total_all:.4f}")

        return results


def main():
    parser = argparse.ArgumentParser(description="Aggregate usage for billing")
    parser.add_argument("--client-id", help="Specific client UUID")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without saving"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    # Parse dates
    start_date = None
    end_date = None

    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
    if args.end:
        end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )

    # Run tracker
    with UsageTracker(dry_run=args.dry_run) as tracker:
        results = tracker.run(
            client_id=args.client_id, start_date=start_date, end_date=end_date
        )

    if args.json:
        print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
