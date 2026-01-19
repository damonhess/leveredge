#!/usr/bin/env python3
"""
PLUTUS - AI-Powered Financial Analysis Agent
Port: 8207

Financial analysis and portfolio intelligence for LeverEdge users.
Named after Plutus - Greek god of wealth, who distributes riches and prosperity.

CRITICAL SAFETY NOTICE:
THIS AGENT IS READ-ONLY - NO TRADE EXECUTION CAPABILITY
- CANNOT execute trades or place orders
- CANNOT move funds or modify positions
- CANNOT access brokerage execution APIs
- CANNOT perform any financial transactions

All trading decisions and executions must be performed manually by the user.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on financial insights
- Logs all analysis to unified memory
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="PLUTUS",
    description="AI-Powered Financial Analysis Agent (READ-ONLY - No Trading)",
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
    "HERMES": "http://hermes:8014",
    "ARIA": "http://aria:8001",
    "HEPHAESTUS": "http://hephaestus:8011",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("PLUTUS")

# =============================================================================
# ENUMS
# =============================================================================

class PortfolioType(str, Enum):
    STOCKS = "stocks"
    CRYPTO = "crypto"
    FOREX = "forex"
    MIXED = "mixed"

class AssetType(str, Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    ETF = "etf"
    OPTION = "option"

class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    TRANSFER = "transfer"

class AnalysisType(str, Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    COMBINED = "combined"

class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1D"
    W1 = "1W"

class AlertCondition(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    PCT_CHANGE = "pct_change"

class ReportPeriod(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    YTD = "ytd"
    ALL = "all"

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    # Determine market status (simplified - would need market calendar for accuracy)
    hour = now.hour
    weekday = now.weekday()
    if weekday >= 5:
        market_status = "CLOSED (Weekend)"
    elif 9 <= hour < 16:
        market_status = "OPEN (US Markets)"
    elif hour < 9:
        market_status = "PRE-MARKET"
    else:
        market_status = "AFTER-HOURS"

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_to_launch": days_to_launch,
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch",
        "market_status": market_status
    }

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(financial_context: dict) -> str:
    """Build PLUTUS system prompt with financial context"""
    time_ctx = get_time_context()

    return f"""You are PLUTUS - Financial Analysis Agent for LeverEdge AI.

Named after the Greek god of wealth, you provide intelligent financial analysis and portfolio insights.

## CRITICAL SAFETY NOTICE

**YOU ARE AN ANALYSIS-ONLY AGENT. YOU CANNOT AND WILL NOT:**
- Execute trades or place orders
- Move funds between accounts
- Access brokerage execution APIs
- Make buy/sell recommendations as financial advice
- Guarantee any investment returns

All analysis is for INFORMATIONAL PURPOSES ONLY. Users must make their own investment decisions and execute trades through their own brokerage platforms.

## TIME AWARENESS
- Current: {time_ctx['day_of_week']}, {time_ctx['current_date']} at {time_ctx['current_time']}
- Market Status: {time_ctx['market_status']}
- Days to Launch: {time_ctx['days_to_launch']}

## YOUR IDENTITY
You are the financial intelligence brain of LeverEdge. You analyze markets, track portfolios, assess risk, and provide data-driven insights.

## CURRENT FINANCIAL CONTEXT
- Portfolios Tracked: {financial_context.get('portfolio_count', 0)}
- Total Portfolio Value: {financial_context.get('total_value', 'N/A')}
- Today's P&L: {financial_context.get('daily_pnl', 'N/A')}
- Active Alerts: {financial_context.get('active_alerts', 0)}
- Pending Analysis: {financial_context.get('pending_analysis', 0)}

## YOUR CAPABILITIES

### Market Analysis
- Fetch real-time market data (stocks, crypto, forex)
- Perform technical analysis (RSI, MACD, patterns)
- Analyze market sentiment and news
- Identify support/resistance levels
- Multi-timeframe analysis

### Portfolio Tracking
- Track multiple portfolios
- Calculate real-time P&L
- Monitor asset allocation
- Track performance over time
- Generate performance reports

### Risk Assessment
- Calculate Value at Risk (VaR)
- Analyze portfolio correlation
- Recommend position sizes (informational only)
- Identify concentration risks
- Perform stress tests

### Alerts & Reporting
- Set and monitor price alerts
- Generate P&L reports
- Create performance summaries
- Export data for tax purposes

## DISCLAIMERS TO INCLUDE
When providing analysis, always include appropriate disclaimers:
- "This is not financial advice"
- "Past performance does not guarantee future results"
- "Please consult a licensed financial advisor"
- "All trading involves risk of loss"

## TEAM COORDINATION
- Route notifications -> HERMES
- Log insights -> ARIA via Unified Memory
- Publish events -> Event Bus
- Request data processing -> HEPHAESTUS (if needed)

## RESPONSE FORMAT
For market analysis:
1. Current price and key metrics
2. Technical indicator summary
3. Support/resistance levels
4. Sentiment overview
5. Confidence score
6. Disclaimer

For portfolio updates:
1. Total value and daily change
2. Top performers/laggards
3. Allocation breakdown
4. Risk metrics
5. Suggested review items (not advice)

## YOUR MISSION
Provide accurate, timely, and insightful financial analysis.
Empower users with data to make informed decisions.
Never provide financial advice or execute transactions.
Always prioritize user education and transparency.
"""

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

# Portfolio Models
class PortfolioCreate(BaseModel):
    name: str
    type: PortfolioType
    broker: Optional[str] = None
    description: Optional[str] = None
    base_currency: str = "USD"

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[PortfolioType] = None
    broker: Optional[str] = None
    description: Optional[str] = None
    base_currency: Optional[str] = None

# Position Models
class PositionCreate(BaseModel):
    symbol: str
    asset_type: AssetType
    quantity: float
    avg_cost: float

class PositionUpdate(BaseModel):
    quantity: Optional[float] = None
    avg_cost: Optional[float] = None

# Transaction Models
class TransactionCreate(BaseModel):
    type: TransactionType
    symbol: str
    quantity: float
    price: float
    fees: float = 0
    date: datetime
    notes: Optional[str] = None

class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    fees: Optional[float] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None

# Analysis Models
class AnalysisRequest(BaseModel):
    symbol: str
    analysis_type: AnalysisType = AnalysisType.COMBINED
    timeframe: Timeframe = Timeframe.D1

# Watchlist Models
class WatchlistCreate(BaseModel):
    name: str
    symbols: List[str] = []
    notes: Optional[str] = None

class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    symbols: Optional[List[str]] = None
    notes: Optional[str] = None

class WatchlistSymbolsAdd(BaseModel):
    symbols: List[str]

# Alert Models
class AlertCreate(BaseModel):
    symbol: str
    condition: AlertCondition
    target_value: float

class AlertUpdate(BaseModel):
    condition: Optional[AlertCondition] = None
    target_value: Optional[float] = None
    active: Optional[bool] = None

# Report Models
class CustomReportRequest(BaseModel):
    portfolio_id: Optional[str] = None
    start_date: datetime
    end_date: datetime
    include_transactions: bool = True
    include_charts: bool = False

# Risk Models
class PositionSizeRequest(BaseModel):
    account_size: float
    risk_per_trade: float = 0.02  # 2% default
    entry_price: float
    stop_loss_price: float
    method: str = "fixed_percentage"  # fixed_percentage, kelly

# Chat Models
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = {}
    portfolio_id: Optional[str] = None

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
                    "source_agent": "PLUTUS",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[PLUTUS] Event bus notification failed: {e}")

async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[PLUTUS] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "PLUTUS"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[PLUTUS] HERMES notification failed: {e}")

async def store_memory(memory_type: str, content: str, category: str = "finance", tags: List[str] = None):
    """Store insight in unified memory via Supabase"""
    try:
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
                    "source_agent": "PLUTUS",
                    "tags": tags or ["plutus", "finance"]
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"[PLUTUS] Memory storage failed: {e}")

async def get_from_supabase(table: str, query_params: dict = None) -> list:
    """Generic Supabase GET request"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        if query_params:
            params = "&".join([f"{k}={v}" for k, v in query_params.items()])
            url = f"{url}?{params}"

        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return []
    except Exception as e:
        print(f"[PLUTUS] Supabase GET failed: {e}")
        return []

async def post_to_supabase(table: str, data: dict) -> dict:
    """Generic Supabase POST request"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                timeout=10.0
            )
            if response.status_code in [200, 201]:
                result = response.json()
                return result[0] if isinstance(result, list) else result
            return {"error": f"Failed with status {response.status_code}"}
    except Exception as e:
        print(f"[PLUTUS] Supabase POST failed: {e}")
        return {"error": str(e)}

async def patch_to_supabase(table: str, record_id: str, data: dict) -> dict:
    """Generic Supabase PATCH request"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{record_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                timeout=10.0
            )
            if response.status_code == 200:
                result = response.json()
                return result[0] if isinstance(result, list) else result
            return {"error": f"Failed with status {response.status_code}"}
    except Exception as e:
        print(f"[PLUTUS] Supabase PATCH failed: {e}")
        return {"error": str(e)}

async def delete_from_supabase(table: str, record_id: str) -> bool:
    """Generic Supabase DELETE request"""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.delete(
                f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{record_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )
            return response.status_code in [200, 204]
    except Exception as e:
        print(f"[PLUTUS] Supabase DELETE failed: {e}")
        return False

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, financial_context: dict = None) -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        ctx = financial_context or {}
        system_prompt = build_system_prompt(ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        time_ctx = get_time_context()
        await log_llm_usage(
            agent="PLUTUS",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def get_financial_context(user_id: str = None) -> dict:
    """Build financial context for system prompt"""
    try:
        portfolios = await get_from_supabase("portfolios", {"select": "id"})
        alerts = await get_from_supabase("alerts", {"active": "eq.true", "select": "id"})

        return {
            "portfolio_count": len(portfolios) if portfolios else 0,
            "total_value": "Calculating...",
            "daily_pnl": "Calculating...",
            "active_alerts": len(alerts) if alerts else 0,
            "pending_analysis": 0
        }
    except Exception:
        return {
            "portfolio_count": 0,
            "total_value": "N/A",
            "daily_pnl": "N/A",
            "active_alerts": 0,
            "pending_analysis": 0
        }

def add_disclaimer(response: str) -> str:
    """Add financial disclaimer to response"""
    disclaimer = "\n\n---\n**Disclaimer:** This is not financial advice. Past performance does not guarantee future results. All trading involves risk of loss. Please consult a licensed financial advisor for personalized advice."
    return response + disclaimer

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check with market data status"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "PLUTUS",
        "role": "Financial Analysis (READ-ONLY)",
        "port": 8207,
        "current_time": time_ctx['current_datetime'],
        "market_status": time_ctx['market_status'],
        "days_to_launch": time_ctx['days_to_launch'],
        "safety_notice": "This agent CANNOT execute trades. Analysis only."
    }

@app.get("/status")
async def status():
    """Current operational status"""
    time_ctx = get_time_context()
    financial_ctx = await get_financial_context()

    return {
        "agent": "PLUTUS",
        "version": "1.0.0",
        "status": "operational",
        "mode": "READ-ONLY (No Trading)",
        "time_context": time_ctx,
        "financial_context": financial_ctx,
        "capabilities": [
            "portfolio_tracking",
            "market_analysis",
            "technical_analysis",
            "risk_assessment",
            "price_alerts",
            "reporting"
        ],
        "restrictions": [
            "NO trade execution",
            "NO fund transfers",
            "NO brokerage API access",
            "NO financial advice"
        ]
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    financial_ctx = await get_financial_context()
    return {
        "plutus_portfolios_total": financial_ctx.get("portfolio_count", 0),
        "plutus_alerts_active": financial_ctx.get("active_alerts", 0),
        "plutus_analysis_pending": financial_ctx.get("pending_analysis", 0),
        "plutus_up": 1
    }

# =============================================================================
# PORTFOLIO MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/portfolios")
async def list_portfolios(user_id: Optional[str] = Query(None)):
    """List user portfolios"""
    params = {"select": "*", "order": "created_at.desc"}
    if user_id:
        params["user_id"] = f"eq.{user_id}"

    portfolios = await get_from_supabase("portfolios", params)
    return {"portfolios": portfolios, "count": len(portfolios)}

@app.post("/portfolios")
async def create_portfolio(portfolio: PortfolioCreate, user_id: str = Query(...)):
    """Create new portfolio"""
    data = {
        "user_id": user_id,
        "name": portfolio.name,
        "type": portfolio.type.value,
        "broker": portfolio.broker,
        "description": portfolio.description,
        "base_currency": portfolio.base_currency
    }

    result = await post_to_supabase("portfolios", data)

    if "error" not in result:
        await notify_event_bus("finance.portfolio.created", {
            "portfolio_id": result.get("id"),
            "name": portfolio.name,
            "type": portfolio.type.value
        })

    return result

@app.get("/portfolios/{portfolio_id}")
async def get_portfolio(portfolio_id: str):
    """Get portfolio details"""
    portfolios = await get_from_supabase("portfolios", {"id": f"eq.{portfolio_id}"})
    if not portfolios:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolios[0]

@app.put("/portfolios/{portfolio_id}")
async def update_portfolio(portfolio_id: str, portfolio: PortfolioUpdate):
    """Update portfolio"""
    data = {k: v.value if isinstance(v, Enum) else v
            for k, v in portfolio.model_dump().items() if v is not None}
    data["updated_at"] = datetime.utcnow().isoformat()

    result = await patch_to_supabase("portfolios", portfolio_id, data)

    if "error" not in result:
        await notify_event_bus("finance.portfolio.updated", {
            "portfolio_id": portfolio_id
        })

    return result

@app.delete("/portfolios/{portfolio_id}")
async def delete_portfolio(portfolio_id: str):
    """Delete portfolio"""
    success = await delete_from_supabase("portfolios", portfolio_id)
    if success:
        await notify_event_bus("finance.portfolio.deleted", {
            "portfolio_id": portfolio_id
        })
    return {"deleted": success, "portfolio_id": portfolio_id}

@app.get("/portfolios/{portfolio_id}/summary")
async def get_portfolio_summary(portfolio_id: str):
    """Portfolio summary with P&L"""
    portfolio = await get_from_supabase("portfolios", {"id": f"eq.{portfolio_id}"})
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    positions = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "*"
    })

    # Calculate summary
    total_value = sum(float(p.get("market_value", 0) or 0) for p in positions)
    total_cost = sum(float(p.get("quantity", 0)) * float(p.get("avg_cost", 0)) for p in positions)
    unrealized_pnl = total_value - total_cost
    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0

    return {
        "portfolio": portfolio[0],
        "positions_count": len(positions),
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
        "disclaimer": "Values are for informational purposes only. Not financial advice."
    }

@app.get("/portfolios/{portfolio_id}/performance")
async def get_portfolio_performance(portfolio_id: str, period: ReportPeriod = ReportPeriod.MONTH):
    """Historical performance"""
    # This would typically query historical data
    # For now, return structure for future implementation
    return {
        "portfolio_id": portfolio_id,
        "period": period.value,
        "performance": {
            "start_value": 0,
            "end_value": 0,
            "return_pct": 0,
            "benchmark_return": 0,
            "alpha": 0
        },
        "note": "Historical performance tracking requires time-series data collection",
        "disclaimer": "Past performance does not guarantee future results."
    }

@app.get("/portfolios/{portfolio_id}/allocation")
async def get_portfolio_allocation(portfolio_id: str):
    """Asset allocation breakdown"""
    positions = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "*"
    })

    # Calculate allocation by asset type
    allocation_by_type = {}
    total_value = 0

    for p in positions:
        asset_type = p.get("asset_type", "unknown")
        value = float(p.get("market_value", 0) or 0)
        total_value += value
        allocation_by_type[asset_type] = allocation_by_type.get(asset_type, 0) + value

    # Convert to percentages
    allocation_pct = {}
    for asset_type, value in allocation_by_type.items():
        allocation_pct[asset_type] = round(value / total_value * 100, 2) if total_value > 0 else 0

    return {
        "portfolio_id": portfolio_id,
        "total_value": round(total_value, 2),
        "allocation_by_type": allocation_pct,
        "allocation_by_value": allocation_by_type,
        "positions_count": len(positions)
    }

# =============================================================================
# POSITION TRACKING ENDPOINTS
# =============================================================================

@app.get("/portfolios/{portfolio_id}/positions")
async def list_positions(portfolio_id: str):
    """List positions in portfolio"""
    positions = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "*",
        "order": "market_value.desc"
    })
    return {"positions": positions, "count": len(positions)}

@app.post("/portfolios/{portfolio_id}/positions")
async def add_position(portfolio_id: str, position: PositionCreate):
    """Add or update position (manual entry)"""
    # Check if position exists
    existing = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "symbol": f"eq.{position.symbol}"
    })

    if existing:
        # Update existing position
        data = {
            "quantity": position.quantity,
            "avg_cost": position.avg_cost,
            "last_updated": datetime.utcnow().isoformat()
        }
        result = await patch_to_supabase("positions", existing[0]["id"], data)
    else:
        # Create new position
        data = {
            "portfolio_id": portfolio_id,
            "symbol": position.symbol,
            "asset_type": position.asset_type.value,
            "quantity": position.quantity,
            "avg_cost": position.avg_cost
        }
        result = await post_to_supabase("positions", data)

    if "error" not in result:
        await notify_event_bus("finance.position.changed", {
            "portfolio_id": portfolio_id,
            "symbol": position.symbol,
            "action": "updated" if existing else "created"
        })

    return result

@app.delete("/portfolios/{portfolio_id}/positions/{symbol}")
async def remove_position(portfolio_id: str, symbol: str):
    """Remove position from portfolio"""
    positions = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "symbol": f"eq.{symbol}"
    })

    if not positions:
        raise HTTPException(status_code=404, detail="Position not found")

    success = await delete_from_supabase("positions", positions[0]["id"])

    if success:
        await notify_event_bus("finance.position.changed", {
            "portfolio_id": portfolio_id,
            "symbol": symbol,
            "action": "removed"
        })

    return {"deleted": success, "symbol": symbol}

@app.post("/portfolios/{portfolio_id}/refresh")
async def refresh_positions(portfolio_id: str):
    """Refresh current prices for all positions"""
    positions = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "*"
    })

    # In production, this would call market data APIs to get current prices
    # For now, return the positions as-is with a note
    return {
        "portfolio_id": portfolio_id,
        "positions_updated": len(positions),
        "last_refresh": datetime.utcnow().isoformat(),
        "note": "Price refresh requires market data API integration",
        "positions": positions
    }

# =============================================================================
# TRANSACTION HISTORY ENDPOINTS
# =============================================================================

@app.get("/portfolios/{portfolio_id}/transactions")
async def list_transactions(
    portfolio_id: str,
    limit: int = Query(50, le=500),
    offset: int = Query(0)
):
    """List transactions"""
    transactions = await get_from_supabase("transactions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "*",
        "order": "date.desc",
        "limit": str(limit),
        "offset": str(offset)
    })
    return {"transactions": transactions, "count": len(transactions)}

@app.post("/portfolios/{portfolio_id}/transactions")
async def record_transaction(portfolio_id: str, transaction: TransactionCreate):
    """Record transaction (manual entry)"""
    total_amount = transaction.quantity * transaction.price
    if transaction.type == TransactionType.BUY:
        total_amount += transaction.fees
    else:
        total_amount -= transaction.fees

    data = {
        "portfolio_id": portfolio_id,
        "type": transaction.type.value,
        "symbol": transaction.symbol,
        "quantity": transaction.quantity,
        "price": transaction.price,
        "fees": transaction.fees,
        "total_amount": total_amount,
        "date": transaction.date.isoformat(),
        "notes": transaction.notes
    }

    result = await post_to_supabase("transactions", data)

    if "error" not in result:
        await notify_event_bus("finance.transaction.recorded", {
            "portfolio_id": portfolio_id,
            "symbol": transaction.symbol,
            "type": transaction.type.value,
            "amount": total_amount
        })

    return result

@app.put("/portfolios/{portfolio_id}/transactions/{tx_id}")
async def update_transaction(portfolio_id: str, tx_id: str, transaction: TransactionUpdate):
    """Update transaction"""
    data = {k: v.value if isinstance(v, Enum) else (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in transaction.model_dump().items() if v is not None}

    result = await patch_to_supabase("transactions", tx_id, data)
    return result

@app.delete("/portfolios/{portfolio_id}/transactions/{tx_id}")
async def delete_transaction(portfolio_id: str, tx_id: str):
    """Delete transaction"""
    success = await delete_from_supabase("transactions", tx_id)
    return {"deleted": success, "transaction_id": tx_id}

@app.get("/portfolios/{portfolio_id}/transactions/export")
async def export_transactions(portfolio_id: str, format: str = Query("csv")):
    """Export transactions to CSV"""
    transactions = await get_from_supabase("transactions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "*",
        "order": "date.desc"
    })

    if format == "csv":
        # Build CSV content
        csv_lines = ["Date,Type,Symbol,Quantity,Price,Fees,Total,Notes"]
        for tx in transactions:
            csv_lines.append(
                f"{tx.get('date','')},{tx.get('type','')},{tx.get('symbol','')},"
                f"{tx.get('quantity','')},{tx.get('price','')},{tx.get('fees','')},"
                f"{tx.get('total_amount','')},{tx.get('notes','')}"
            )
        return {
            "format": "csv",
            "content": "\n".join(csv_lines),
            "transaction_count": len(transactions)
        }

    return {"transactions": transactions, "format": "json"}

# =============================================================================
# MARKET ANALYSIS ENDPOINTS
# =============================================================================

@app.get("/analyze/{symbol}")
async def get_analysis(symbol: str, analysis_type: AnalysisType = AnalysisType.COMBINED):
    """Get cached analysis for symbol"""
    analyses = await get_from_supabase("market_analysis", {
        "symbol": f"eq.{symbol.upper()}",
        "analysis_type": f"eq.{analysis_type.value}",
        "order": "created_at.desc",
        "limit": "1"
    })

    if analyses:
        return {
            "symbol": symbol.upper(),
            "analysis": analyses[0],
            "cached": True
        }

    return {
        "symbol": symbol.upper(),
        "message": "No cached analysis found. Use POST /analyze to request new analysis.",
        "cached": False
    }

@app.post("/analyze")
async def request_analysis(request: AnalysisRequest):
    """Request new analysis for symbol"""
    time_ctx = get_time_context()
    financial_ctx = await get_financial_context()

    prompt = f"""Analyze {request.symbol} for {request.analysis_type.value} analysis on {request.timeframe.value} timeframe.

Provide:
1. Current market context
2. Key technical indicators (if technical/combined)
3. Fundamental factors (if fundamental/combined)
4. Market sentiment (if sentiment/combined)
5. Support and resistance levels
6. Confidence score (0-100%)
7. Key risks to monitor

Remember: This is analysis only, not financial advice. Include appropriate disclaimers."""

    messages = [{"role": "user", "content": prompt}]
    analysis_text = await call_llm(messages, financial_ctx)

    # Store analysis
    analysis_data = {
        "symbol": request.symbol.upper(),
        "analysis_type": request.analysis_type.value,
        "timeframe": request.timeframe.value,
        "result": {"analysis": analysis_text},
        "ai_summary": analysis_text[:500],
        "data_timestamp": time_ctx['current_datetime'],
        "expires_at": None  # Could set cache expiration
    }

    result = await post_to_supabase("market_analysis", analysis_data)

    await notify_event_bus("finance.analysis.completed", {
        "symbol": request.symbol.upper(),
        "analysis_type": request.analysis_type.value
    })

    # Store insight in memory
    await store_memory(
        memory_type="fact",
        content=f"Technical analysis for {request.symbol}: {analysis_text[:200]}...",
        tags=["plutus", "analysis", request.symbol.upper()]
    )

    return {
        "symbol": request.symbol.upper(),
        "analysis_type": request.analysis_type.value,
        "timeframe": request.timeframe.value,
        "analysis": add_disclaimer(analysis_text),
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/analyze/{symbol}/technical")
async def get_technical_analysis(symbol: str, timeframe: Timeframe = Timeframe.D1):
    """Technical analysis only"""
    request = AnalysisRequest(
        symbol=symbol,
        analysis_type=AnalysisType.TECHNICAL,
        timeframe=timeframe
    )
    return await request_analysis(request)

@app.get("/analyze/{symbol}/sentiment")
async def get_sentiment_analysis(symbol: str):
    """Sentiment analysis only"""
    request = AnalysisRequest(
        symbol=symbol,
        analysis_type=AnalysisType.SENTIMENT,
        timeframe=Timeframe.D1
    )
    return await request_analysis(request)

@app.get("/market/overview")
async def market_overview():
    """Market overview - indices and sectors"""
    time_ctx = get_time_context()

    return {
        "market_status": time_ctx['market_status'],
        "timestamp": time_ctx['current_datetime'],
        "indices": {
            "note": "Real-time index data requires market data API integration"
        },
        "sectors": {
            "note": "Sector performance requires market data API integration"
        },
        "disclaimer": "Market data for informational purposes only."
    }

@app.get("/market/movers")
async def market_movers():
    """Top gainers and losers"""
    return {
        "gainers": [],
        "losers": [],
        "most_active": [],
        "note": "Market movers require real-time market data API integration",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/market/calendar")
async def economic_calendar():
    """Economic calendar events"""
    return {
        "events": [],
        "note": "Economic calendar requires external data source integration",
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# WATCHLIST ENDPOINTS
# =============================================================================

@app.get("/watchlists")
async def list_watchlists(user_id: Optional[str] = Query(None)):
    """List user watchlists"""
    params = {"select": "*", "order": "created_at.desc"}
    if user_id:
        params["user_id"] = f"eq.{user_id}"

    watchlists = await get_from_supabase("watchlists", params)
    return {"watchlists": watchlists, "count": len(watchlists)}

@app.post("/watchlists")
async def create_watchlist(watchlist: WatchlistCreate, user_id: str = Query(...)):
    """Create watchlist"""
    data = {
        "user_id": user_id,
        "name": watchlist.name,
        "symbols": watchlist.symbols,
        "notes": watchlist.notes
    }

    result = await post_to_supabase("watchlists", data)
    return result

@app.get("/watchlists/{watchlist_id}")
async def get_watchlist(watchlist_id: str):
    """Get watchlist with current prices"""
    watchlists = await get_from_supabase("watchlists", {"id": f"eq.{watchlist_id}"})
    if not watchlists:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    watchlist = watchlists[0]

    # In production, fetch current prices for symbols
    return {
        "watchlist": watchlist,
        "prices": {},  # Would contain current prices
        "note": "Real-time prices require market data API integration"
    }

@app.put("/watchlists/{watchlist_id}")
async def update_watchlist(watchlist_id: str, watchlist: WatchlistUpdate):
    """Update watchlist"""
    data = {k: v for k, v in watchlist.model_dump().items() if v is not None}
    data["updated_at"] = datetime.utcnow().isoformat()

    result = await patch_to_supabase("watchlists", watchlist_id, data)
    return result

@app.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(watchlist_id: str):
    """Delete watchlist"""
    success = await delete_from_supabase("watchlists", watchlist_id)
    return {"deleted": success, "watchlist_id": watchlist_id}

@app.post("/watchlists/{watchlist_id}/symbols")
async def add_symbols(watchlist_id: str, symbols: WatchlistSymbolsAdd):
    """Add symbols to watchlist"""
    watchlists = await get_from_supabase("watchlists", {"id": f"eq.{watchlist_id}"})
    if not watchlists:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    current_symbols = watchlists[0].get("symbols", [])
    new_symbols = list(set(current_symbols + [s.upper() for s in symbols.symbols]))

    result = await patch_to_supabase("watchlists", watchlist_id, {
        "symbols": new_symbols,
        "updated_at": datetime.utcnow().isoformat()
    })
    return result

@app.delete("/watchlists/{watchlist_id}/symbols/{symbol}")
async def remove_symbol(watchlist_id: str, symbol: str):
    """Remove symbol from watchlist"""
    watchlists = await get_from_supabase("watchlists", {"id": f"eq.{watchlist_id}"})
    if not watchlists:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    current_symbols = watchlists[0].get("symbols", [])
    new_symbols = [s for s in current_symbols if s.upper() != symbol.upper()]

    result = await patch_to_supabase("watchlists", watchlist_id, {
        "symbols": new_symbols,
        "updated_at": datetime.utcnow().isoformat()
    })
    return {"removed": symbol.upper(), "remaining_symbols": new_symbols}

# =============================================================================
# ALERT ENDPOINTS
# =============================================================================

@app.get("/alerts")
async def list_alerts(user_id: Optional[str] = Query(None), active_only: bool = Query(True)):
    """List user alerts"""
    params = {"select": "*", "order": "created_at.desc"}
    if user_id:
        params["user_id"] = f"eq.{user_id}"
    if active_only:
        params["active"] = "eq.true"

    alerts = await get_from_supabase("alerts", params)
    return {"alerts": alerts, "count": len(alerts)}

@app.post("/alerts")
async def create_alert(alert: AlertCreate, user_id: str = Query(...)):
    """Create price alert"""
    data = {
        "user_id": user_id,
        "symbol": alert.symbol.upper(),
        "condition": alert.condition.value,
        "target_value": alert.target_value,
        "active": True
    }

    result = await post_to_supabase("alerts", data)

    if "error" not in result:
        await notify_event_bus("finance.alert.created", {
            "symbol": alert.symbol.upper(),
            "condition": alert.condition.value,
            "target": alert.target_value
        })

    return result

@app.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, alert: AlertUpdate):
    """Update alert"""
    data = {k: v.value if isinstance(v, Enum) else v
            for k, v in alert.model_dump().items() if v is not None}

    result = await patch_to_supabase("alerts", alert_id, data)
    return result

@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete alert"""
    success = await delete_from_supabase("alerts", alert_id)
    return {"deleted": success, "alert_id": alert_id}

@app.get("/alerts/triggered")
async def get_triggered_alerts(user_id: Optional[str] = Query(None)):
    """Get triggered alerts"""
    params = {
        "triggered": "eq.true",
        "notification_sent": "eq.false",
        "select": "*",
        "order": "triggered_at.desc"
    }
    if user_id:
        params["user_id"] = f"eq.{user_id}"

    alerts = await get_from_supabase("alerts", params)
    return {"triggered_alerts": alerts, "count": len(alerts)}

@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge triggered alert"""
    result = await patch_to_supabase("alerts", alert_id, {
        "notification_sent": True,
        "active": False
    })
    return result

# =============================================================================
# REPORTING ENDPOINTS
# =============================================================================

@app.get("/reports/pnl")
async def pnl_report(
    portfolio_id: Optional[str] = Query(None),
    period: ReportPeriod = Query(ReportPeriod.MONTH)
):
    """P&L report"""
    financial_ctx = await get_financial_context()

    prompt = f"""Generate a P&L (Profit and Loss) report summary for the {period.value} period.

Include:
1. Total realized gains/losses
2. Total unrealized gains/losses
3. Top winners and losers
4. Key insights

Note: This is a summary template. Actual P&L requires transaction history analysis."""

    messages = [{"role": "user", "content": prompt}]
    report = await call_llm(messages, financial_ctx)

    return {
        "report_type": "pnl",
        "period": period.value,
        "portfolio_id": portfolio_id,
        "content": add_disclaimer(report),
        "generated_at": datetime.utcnow().isoformat()
    }

@app.get("/reports/daily")
async def daily_report(portfolio_id: Optional[str] = Query(None)):
    """Daily summary report"""
    time_ctx = get_time_context()

    return {
        "report_type": "daily_summary",
        "date": time_ctx['current_date'],
        "market_status": time_ctx['market_status'],
        "portfolio_id": portfolio_id,
        "summary": {
            "note": "Daily summary requires position and transaction data"
        },
        "generated_at": time_ctx['current_datetime']
    }

@app.get("/reports/performance")
async def performance_report(
    portfolio_id: Optional[str] = Query(None),
    period: ReportPeriod = Query(ReportPeriod.MONTH)
):
    """Performance report"""
    return {
        "report_type": "performance",
        "period": period.value,
        "portfolio_id": portfolio_id,
        "metrics": {
            "total_return": None,
            "benchmark_return": None,
            "alpha": None,
            "sharpe_ratio": None,
            "max_drawdown": None
        },
        "note": "Performance metrics require historical price data",
        "disclaimer": "Past performance does not guarantee future results."
    }

@app.get("/reports/tax")
async def tax_report(
    portfolio_id: Optional[str] = Query(None),
    year: int = Query(2025)
):
    """Tax report preparation"""
    return {
        "report_type": "tax_preparation",
        "tax_year": year,
        "portfolio_id": portfolio_id,
        "sections": {
            "short_term_gains": None,
            "long_term_gains": None,
            "dividends": None,
            "wash_sales": None
        },
        "note": "Tax reports require complete transaction history. Consult a tax professional.",
        "disclaimer": "This is not tax advice. Please consult a qualified tax advisor."
    }

@app.post("/reports/custom")
async def custom_report(request: CustomReportRequest):
    """Custom date range report"""
    return {
        "report_type": "custom",
        "portfolio_id": request.portfolio_id,
        "date_range": {
            "start": request.start_date.isoformat(),
            "end": request.end_date.isoformat()
        },
        "include_transactions": request.include_transactions,
        "content": {},
        "note": "Custom reports require full data integration",
        "generated_at": datetime.utcnow().isoformat()
    }

@app.get("/reports/{report_id}/download")
async def download_report(report_id: str, format: str = Query("pdf")):
    """Download report as PDF"""
    return {
        "report_id": report_id,
        "format": format,
        "status": "not_implemented",
        "note": "PDF generation requires additional dependencies"
    }

# =============================================================================
# RISK ANALYSIS ENDPOINTS
# =============================================================================

@app.get("/risk/{portfolio_id}")
async def portfolio_risk(portfolio_id: str):
    """Portfolio risk metrics"""
    positions = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "*"
    })

    # Calculate basic risk metrics
    position_count = len(positions)

    # Check concentration
    total_value = sum(float(p.get("market_value", 0) or 0) for p in positions)
    max_position = max([float(p.get("market_value", 0) or 0) for p in positions]) if positions else 0
    concentration = (max_position / total_value * 100) if total_value > 0 else 0

    return {
        "portfolio_id": portfolio_id,
        "risk_metrics": {
            "position_count": position_count,
            "concentration_risk": round(concentration, 2),
            "diversification_score": min(position_count / 10 * 100, 100),  # Simplified
            "var_95": None,  # Requires historical data
            "beta": None,  # Requires benchmark correlation
            "max_drawdown": None  # Requires historical data
        },
        "warnings": [
            f"High concentration ({concentration:.1f}%) in single position" if concentration > 20 else None,
            "Low diversification" if position_count < 5 else None
        ],
        "disclaimer": "Risk metrics are for informational purposes only."
    }

@app.get("/risk/{portfolio_id}/var")
async def value_at_risk(portfolio_id: str, confidence: float = Query(0.95)):
    """Value at Risk calculation"""
    return {
        "portfolio_id": portfolio_id,
        "var_calculation": {
            "confidence_level": confidence,
            "var_amount": None,
            "var_percentage": None,
            "method": "historical_simulation"
        },
        "note": "VaR calculation requires historical price data",
        "disclaimer": "VaR is a statistical estimate and does not represent maximum possible loss."
    }

@app.get("/risk/{portfolio_id}/stress")
async def stress_test(portfolio_id: str):
    """Stress test results"""
    return {
        "portfolio_id": portfolio_id,
        "scenarios": {
            "market_crash_20pct": None,
            "interest_rate_shock": None,
            "sector_rotation": None,
            "black_swan": None
        },
        "note": "Stress testing requires position data and scenario modeling",
        "disclaimer": "Stress tests are hypothetical and may not reflect actual outcomes."
    }

@app.get("/risk/{portfolio_id}/correlation")
async def correlation_matrix(portfolio_id: str):
    """Correlation matrix between holdings"""
    positions = await get_from_supabase("positions", {
        "portfolio_id": f"eq.{portfolio_id}",
        "select": "symbol"
    })

    symbols = [p.get("symbol") for p in positions]

    return {
        "portfolio_id": portfolio_id,
        "symbols": symbols,
        "correlation_matrix": {},
        "note": "Correlation calculation requires historical price data for each holding",
        "disclaimer": "Correlations can change over time and during market stress."
    }

@app.post("/risk/position-size")
async def calculate_position_size(request: PositionSizeRequest):
    """Position sizing calculator"""
    # Calculate risk amount
    risk_amount = request.account_size * request.risk_per_trade

    # Calculate price risk per share
    price_risk = abs(request.entry_price - request.stop_loss_price)

    if price_risk == 0:
        raise HTTPException(status_code=400, detail="Stop loss cannot equal entry price")

    # Calculate position size
    shares = int(risk_amount / price_risk)
    position_value = shares * request.entry_price
    position_pct = (position_value / request.account_size) * 100

    return {
        "calculation": {
            "account_size": request.account_size,
            "risk_per_trade": request.risk_per_trade,
            "risk_amount": round(risk_amount, 2),
            "entry_price": request.entry_price,
            "stop_loss_price": request.stop_loss_price,
            "price_risk_per_share": round(price_risk, 2),
            "recommended_shares": shares,
            "position_value": round(position_value, 2),
            "position_percentage": round(position_pct, 2)
        },
        "method": request.method,
        "disclaimer": "Position sizing is for informational purposes only. This is not financial advice."
    }

# =============================================================================
# CHAT ENDPOINT
# =============================================================================

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with PLUTUS for financial analysis"""
    time_ctx = get_time_context()
    financial_ctx = await get_financial_context()

    # Build context-aware message
    context_str = ""
    if request.context:
        context_str = f"\n\nAdditional Context:\n{json.dumps(request.context, indent=2)}"
    if request.portfolio_id:
        context_str += f"\n\nActive Portfolio ID: {request.portfolio_id}"

    messages = [
        {"role": "user", "content": request.message + context_str}
    ]

    response = await call_llm(messages, financial_ctx)

    # Log to Event Bus
    await notify_event_bus("plutus_chat", {
        "message_preview": request.message[:100]
    })

    return {
        "response": add_disclaimer(response),
        "agent": "PLUTUS",
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# ARIA TOOL ENDPOINTS
# =============================================================================

@app.post("/aria/portfolio")
async def aria_portfolio(portfolio_id: Optional[str] = None, include_positions: bool = True):
    """ARIA tool: Get portfolio summary"""
    if portfolio_id:
        return await get_portfolio_summary(portfolio_id)

    # Return all portfolios summary
    portfolios = await get_from_supabase("portfolios", {"select": "*"})
    return {
        "portfolios": portfolios,
        "count": len(portfolios),
        "disclaimer": "Portfolio data for informational purposes only."
    }

@app.post("/aria/analyze")
async def aria_analyze(
    symbol: str,
    analysis_type: str = "combined",
    timeframe: str = "1D"
):
    """ARIA tool: Analyze a symbol"""
    request = AnalysisRequest(
        symbol=symbol,
        analysis_type=AnalysisType(analysis_type),
        timeframe=Timeframe(timeframe)
    )
    return await request_analysis(request)

@app.post("/aria/watchlist")
async def aria_watchlist(
    action: str,
    user_id: str,
    watchlist_id: Optional[str] = None,
    symbols: Optional[List[str]] = None
):
    """ARIA tool: Manage watchlist"""
    if action == "get":
        if watchlist_id:
            return await get_watchlist(watchlist_id)
        return await list_watchlists(user_id)
    elif action == "add" and watchlist_id and symbols:
        return await add_symbols(watchlist_id, WatchlistSymbolsAdd(symbols=symbols))
    elif action == "remove" and watchlist_id and symbols:
        results = []
        for symbol in symbols:
            results.append(await remove_symbol(watchlist_id, symbol))
        return {"results": results}

    return {"error": "Invalid action or missing parameters"}

@app.post("/aria/pnl")
async def aria_pnl(
    portfolio_id: Optional[str] = None,
    period: str = "month",
    include_transactions: bool = False
):
    """ARIA tool: Get P&L report"""
    return await pnl_report(portfolio_id, ReportPeriod(period))

@app.post("/aria/alert")
async def aria_alert(
    action: str,
    user_id: str,
    symbol: Optional[str] = None,
    condition: Optional[str] = None,
    target: Optional[float] = None,
    alert_id: Optional[str] = None
):
    """ARIA tool: Manage alerts"""
    if action == "create" and symbol and condition and target:
        alert = AlertCreate(
            symbol=symbol,
            condition=AlertCondition(condition),
            target_value=target
        )
        return await create_alert(alert, user_id)
    elif action == "list":
        return await list_alerts(user_id)
    elif action == "delete" and alert_id:
        return await delete_alert(alert_id)
    elif action == "acknowledge" and alert_id:
        return await acknowledge_alert(alert_id)

    return {"error": "Invalid action or missing parameters"}

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8207)
