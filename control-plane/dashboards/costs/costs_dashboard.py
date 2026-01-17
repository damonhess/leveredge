"""
Cost Tracking Dashboard - API Costs for All Agents
Port: 8061

Dashboard for monitoring and analyzing API costs across all LeverEdge agents.
Queries aria_cost_tracking table from Supabase.
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import httpx

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54323")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU")
TABLE_NAME = "aria_cost_tracking"

# Budget thresholds (configurable)
BUDGET_THRESHOLDS = {
    "daily": float(os.getenv("DAILY_BUDGET_THRESHOLD", "50.0")),
    "weekly": float(os.getenv("WEEKLY_BUDGET_THRESHOLD", "300.0")),
    "monthly": float(os.getenv("MONTHLY_BUDGET_THRESHOLD", "1000.0")),
}

app = FastAPI(
    title="Cost Tracking Dashboard",
    description="API costs monitoring for all LeverEdge agents",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="/opt/leveredge/control-plane/dashboards/costs/static"), name="static")


def get_headers() -> dict:
    """Get Supabase API headers"""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


async def query_supabase(
    start_date: datetime,
    end_date: datetime,
    agent_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Query cost data from Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
        params = {
            "select": "*",
            "created_at": f"gte.{start_date.isoformat()}",
            "order": "created_at.desc"
        }

        # Build query string manually for multiple conditions
        query_parts = [
            f"created_at=gte.{start_date.isoformat()}",
            f"created_at=lte.{end_date.isoformat()}",
            "order=created_at.desc",
            "select=*"
        ]

        if agent_name:
            query_parts.append(f"agent_name=eq.{agent_name}")

        query_string = "&".join(query_parts)
        full_url = f"{url}?{query_string}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                full_url,
                headers=get_headers(),
                timeout=30.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Supabase query error: {response.status_code} - {response.text}")
                return []

    except Exception as e:
        print(f"Query error: {e}")
        return []


def aggregate_costs(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate cost data from records"""
    if not records:
        return {
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "request_count": 0,
            "by_model": {},
            "by_agent": {}
        }

    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    by_model = {}
    by_agent = {}

    for record in records:
        cost = float(record.get("cost_usd", 0) or 0)
        input_tokens = int(record.get("input_tokens", 0) or 0)
        output_tokens = int(record.get("output_tokens", 0) or 0)
        model = record.get("model", "unknown")
        agent = record.get("agent_name", "unknown")

        total_cost += cost
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        # By model
        if model not in by_model:
            by_model[model] = {"cost": 0.0, "count": 0, "input_tokens": 0, "output_tokens": 0}
        by_model[model]["cost"] += cost
        by_model[model]["count"] += 1
        by_model[model]["input_tokens"] += input_tokens
        by_model[model]["output_tokens"] += output_tokens

        # By agent
        if agent not in by_agent:
            by_agent[agent] = {"cost": 0.0, "count": 0, "input_tokens": 0, "output_tokens": 0}
        by_agent[agent]["cost"] += cost
        by_agent[agent]["count"] += 1
        by_agent[agent]["input_tokens"] += input_tokens
        by_agent[agent]["output_tokens"] += output_tokens

    return {
        "total_cost": round(total_cost, 4),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "request_count": len(records),
        "by_model": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_model.items()},
        "by_agent": {k: {**v, "cost": round(v["cost"], 4)} for k, v in sorted(by_agent.items(), key=lambda x: -x[1]["cost"])}
    }


def check_budget_alerts(aggregated: Dict[str, Any], period: str) -> Dict[str, Any]:
    """Check if costs exceed budget thresholds"""
    threshold = BUDGET_THRESHOLDS.get(period, 0)
    total_cost = aggregated.get("total_cost", 0)

    alerts = []
    if total_cost > threshold:
        alerts.append({
            "level": "critical",
            "message": f"{period.capitalize()} budget exceeded: ${total_cost:.2f} > ${threshold:.2f}",
            "excess": round(total_cost - threshold, 2)
        })
    elif total_cost > threshold * 0.8:
        alerts.append({
            "level": "warning",
            "message": f"{period.capitalize()} budget at {(total_cost/threshold)*100:.1f}%: ${total_cost:.2f} / ${threshold:.2f}",
            "remaining": round(threshold - total_cost, 2)
        })

    return {
        "threshold": threshold,
        "current": total_cost,
        "percentage": round((total_cost / threshold) * 100, 1) if threshold > 0 else 0,
        "alerts": alerts
    }


# ========== ENDPOINTS ==========

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Quick Supabase connectivity check
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?select=count&limit=1",
                headers=get_headers(),
                timeout=5.0
            )
            db_status = "connected" if response.status_code == 200 else "error"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "service": "cost-tracking-dashboard",
        "port": 8061,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def serve_dashboard():
    """Serve the dashboard HTML"""
    return FileResponse("/opt/leveredge/control-plane/dashboards/costs/static/index.html")


@app.get("/api/costs/today")
async def get_costs_today():
    """Get today's costs"""
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    records = await query_supabase(start_of_day, now)
    aggregated = aggregate_costs(records)
    budget = check_budget_alerts(aggregated, "daily")

    return {
        "period": "today",
        "start": start_of_day.isoformat(),
        "end": now.isoformat(),
        **aggregated,
        "budget": budget
    }


@app.get("/api/costs/week")
async def get_costs_week():
    """Get this week's costs (last 7 days)"""
    now = datetime.utcnow()
    start = now - timedelta(days=7)

    records = await query_supabase(start, now)
    aggregated = aggregate_costs(records)
    budget = check_budget_alerts(aggregated, "weekly")

    # Group by day for chart
    daily_costs = {}
    for record in records:
        date_str = record.get("created_at", "")[:10]
        cost = float(record.get("cost_usd", 0) or 0)
        if date_str not in daily_costs:
            daily_costs[date_str] = 0.0
        daily_costs[date_str] += cost

    return {
        "period": "week",
        "start": start.isoformat(),
        "end": now.isoformat(),
        **aggregated,
        "budget": budget,
        "daily_breakdown": {k: round(v, 4) for k, v in sorted(daily_costs.items())}
    }


@app.get("/api/costs/month")
async def get_costs_month():
    """Get this month's costs (last 30 days)"""
    now = datetime.utcnow()
    start = now - timedelta(days=30)

    records = await query_supabase(start, now)
    aggregated = aggregate_costs(records)
    budget = check_budget_alerts(aggregated, "monthly")

    # Group by day for chart
    daily_costs = {}
    for record in records:
        date_str = record.get("created_at", "")[:10]
        cost = float(record.get("cost_usd", 0) or 0)
        if date_str not in daily_costs:
            daily_costs[date_str] = 0.0
        daily_costs[date_str] += cost

    return {
        "period": "month",
        "start": start.isoformat(),
        "end": now.isoformat(),
        **aggregated,
        "budget": budget,
        "daily_breakdown": {k: round(v, 4) for k, v in sorted(daily_costs.items())}
    }


@app.get("/api/costs/by-agent")
async def get_costs_by_agent(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze")
):
    """Get cost breakdown by agent"""
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    records = await query_supabase(start, now)
    aggregated = aggregate_costs(records)

    # Sort agents by cost
    agents = []
    for agent, data in aggregated.get("by_agent", {}).items():
        agents.append({
            "agent_name": agent,
            "total_cost": data["cost"],
            "request_count": data["count"],
            "input_tokens": data["input_tokens"],
            "output_tokens": data["output_tokens"],
            "avg_cost_per_request": round(data["cost"] / data["count"], 6) if data["count"] > 0 else 0
        })

    agents.sort(key=lambda x: -x["total_cost"])

    return {
        "period_days": days,
        "start": start.isoformat(),
        "end": now.isoformat(),
        "total_cost": aggregated["total_cost"],
        "agents": agents
    }


@app.get("/api/costs/projection")
async def get_cost_projection():
    """Project monthly cost based on current usage patterns"""
    now = datetime.utcnow()

    # Get last 7 days for projection
    week_start = now - timedelta(days=7)
    records = await query_supabase(week_start, now)

    if not records:
        return {
            "projected_monthly_cost": 0.0,
            "current_month_cost": 0.0,
            "days_elapsed": 0,
            "confidence": "low",
            "message": "No data available for projection"
        }

    week_aggregated = aggregate_costs(records)
    weekly_cost = week_aggregated["total_cost"]
    daily_average = weekly_cost / 7

    # Project to full month (30 days)
    projected_monthly = daily_average * 30

    # Get current month actual
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_records = await query_supabase(month_start, now)
    month_aggregated = aggregate_costs(month_records)
    current_month_cost = month_aggregated["total_cost"]

    # Days elapsed in current month
    days_elapsed = (now - month_start).days + 1
    days_in_month = 30  # Simplified

    # Project remaining
    projected_remaining = daily_average * (days_in_month - days_elapsed)
    total_projected = current_month_cost + projected_remaining

    # Confidence based on data volume
    confidence = "high" if len(records) > 100 else "medium" if len(records) > 20 else "low"

    # Budget comparison
    monthly_budget = BUDGET_THRESHOLDS["monthly"]
    budget_status = "on_track"
    if total_projected > monthly_budget:
        budget_status = "over_budget"
    elif total_projected > monthly_budget * 0.8:
        budget_status = "warning"

    return {
        "projected_monthly_cost": round(total_projected, 2),
        "projected_remaining": round(projected_remaining, 2),
        "current_month_cost": round(current_month_cost, 2),
        "daily_average": round(daily_average, 4),
        "days_elapsed": days_elapsed,
        "days_remaining": days_in_month - days_elapsed,
        "confidence": confidence,
        "sample_size": len(records),
        "monthly_budget": monthly_budget,
        "budget_status": budget_status,
        "budget_percentage": round((total_projected / monthly_budget) * 100, 1) if monthly_budget > 0 else 0,
        "by_agent_projection": {
            agent: {
                "current": data["cost"],
                "projected_monthly": round((data["cost"] / 7) * 30, 2)
            }
            for agent, data in week_aggregated.get("by_agent", {}).items()
        }
    }


@app.get("/api/budgets")
async def get_budgets():
    """Get current budget thresholds"""
    return {
        "thresholds": BUDGET_THRESHOLDS,
        "configurable_via_env": {
            "daily": "DAILY_BUDGET_THRESHOLD",
            "weekly": "WEEKLY_BUDGET_THRESHOLD",
            "monthly": "MONTHLY_BUDGET_THRESHOLD"
        }
    }


@app.get("/api/costs/recent")
async def get_recent_costs(
    limit: int = Query(default=100, ge=1, le=1000, description="Number of records to return")
):
    """Get most recent cost records"""
    now = datetime.utcnow()
    start = now - timedelta(days=30)  # Max 30 days back

    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
        query_string = f"select=*&order=created_at.desc&limit={limit}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{url}?{query_string}",
                headers=get_headers(),
                timeout=30.0
            )

            if response.status_code == 200:
                records = response.json()
                return {
                    "count": len(records),
                    "records": records
                }
            else:
                return {"error": f"Query failed: {response.status_code}"}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8061)
