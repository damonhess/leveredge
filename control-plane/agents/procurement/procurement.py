#!/usr/bin/env python3
"""
PROCUREMENT EXPERT - AI-Powered Shopping Research & Purchase Intelligence Agent
Port: 8206

Named after Hermes - the messenger god, also god of commerce, trade, and merchants.
Helps users make informed buying decisions through product research, price comparison,
deal tracking, and purchase history management.

CORE CAPABILITIES:
- Shopping research across vendors
- Price comparison and tracking
- Deal and coupon discovery
- Purchase history with warranty tracking
- Wishlist management with budget tracking

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Communicates with other agents via Event Bus
- Logs decisions to Unified Memory
- Cost tracking for all LLM operations
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="PROCUREMENT EXPERT",
    description="AI-Powered Shopping Research & Purchase Intelligence Agent",
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
    "CHRONOS": "http://chronos:8010",
    "HERMES": "http://hermes:8014",
    "FORTUNA": "http://fortuna:8200",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("PROCUREMENT_EXPERT")

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
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch"
    }


def get_upcoming_sales() -> List[str]:
    """Get list of upcoming sales events"""
    # This would be populated from a config or database in production
    return [
        "Presidents Day Sales (Feb 17)",
        "Spring Sales (March)",
        "Amazon Spring Sale (March)"
    ]


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(shopping_context: dict) -> str:
    """Build the PROCUREMENT EXPERT system prompt"""
    return f"""You are PROCUREMENT EXPERT - Smart Shopping Agent for LeverEdge AI.

Named after Hermes, the messenger god and deity of commerce and trade, you help users make intelligent purchasing decisions through research, price comparison, and deal tracking.

## TIME AWARENESS
- Current: {shopping_context['current_time']}
- Upcoming Sales: {', '.join(shopping_context.get('upcoming_sales', []))}

## YOUR IDENTITY
You are the commerce intelligence brain of LeverEdge. You research products, track prices, find deals, and ensure users never overpay or miss a good deal.

## CURRENT CONTEXT
- Active Wishlists: {shopping_context.get('active_wishlists', 0)}
- Tracked Products: {shopping_context.get('tracked_products', 0)}
- Pending Deals: {shopping_context.get('active_deals', 0)}
- Expiring Warranties: {shopping_context.get('expiring_warranties', 0)}

## YOUR CAPABILITIES

### Shopping Research
- Search and compare products across vendors
- Extract and normalize specifications
- Aggregate reviews and ratings
- Recommend alternatives at various price points
- Analyze product quality and value

### Price Comparison
- Track prices across multiple retailers
- Analyze historical price trends
- Calculate true total cost (shipping, tax)
- Identify best time to buy
- Detect fake discounts vs. real deals

### Deal Tracking
- Monitor wishlists for price drops
- Find applicable coupon codes
- Alert on flash sales
- Score deal quality
- Track limited-time offers

### Purchase History
- Log all purchases with receipts
- Track warranty expirations
- Calculate spending by category
- Suggest reorders for consumables
- Monitor return windows

### Warranty Management
- Track warranty periods
- Alert before expiration
- Store warranty documents
- Recommend extended warranties

## TEAM COORDINATION
- Store purchase insights -> Unified Memory
- Calendar reminders for warranties -> CHRONOS
- Send deal alerts -> HERMES
- Budget tracking -> FORTUNA (Finance Agent)
- Publish events -> Event Bus

## RESPONSE FORMAT
For product research:
1. Product overview and specs
2. Price comparison table
3. Pros and cons analysis
4. Value recommendation
5. Best purchase timing

For deal alerts:
1. Deal summary
2. Discount analysis (real vs. fake)
3. Historical price context
4. Time sensitivity
5. Action recommendation

## YOUR MISSION
Help users spend smarter, not more.
Find the best value, not just the lowest price.
Track everything so nothing expires forgotten.
"""


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

# Product Models
class ProductCreate(BaseModel):
    name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


# Research Models
class ResearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    budget: Optional[float] = None
    requirements: Optional[List[str]] = None


# Price Models
class CompareRequest(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    include_shipping: bool = True


class PriceCheckRequest(BaseModel):
    product_id: str
    vendors: Optional[List[str]] = None


# Deal Models
class DealTrackRequest(BaseModel):
    product_id: str
    target_price: Optional[float] = None
    vendor: Optional[str] = None


class DealVerifyRequest(BaseModel):
    deal_id: str


class CouponSearchRequest(BaseModel):
    vendor: Optional[str] = None
    category: Optional[str] = None
    product_id: Optional[str] = None


# Purchase Models
class PurchaseCreate(BaseModel):
    user_id: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    vendor: str
    price: float
    currency: str = "USD"
    quantity: int = 1
    purchase_date: str  # ISO date string
    warranty_months: Optional[int] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None


class PurchaseUpdate(BaseModel):
    vendor: Optional[str] = None
    price: Optional[float] = None
    warranty_months: Optional[int] = None
    receipt_url: Optional[str] = None
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class ReceiptUpload(BaseModel):
    purchase_id: str
    receipt_url: str


# Wishlist Models
class WishlistCreate(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = None
    budget: Optional[float] = None


class WishlistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[float] = None
    is_active: Optional[bool] = None


class WishlistItemAdd(BaseModel):
    product_id: str
    target_price: Optional[float] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


# Vendor Models
class VendorCreate(BaseModel):
    name: str
    url: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    notes: Optional[str] = None
    categories: Optional[List[str]] = None
    price_match_policy: bool = False
    free_shipping_threshold: Optional[float] = None
    return_policy_days: Optional[int] = None


class VendorUpdate(BaseModel):
    url: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    notes: Optional[str] = None
    categories: Optional[List[str]] = None
    price_match_policy: Optional[bool] = None
    free_shipping_threshold: Optional[float] = None
    return_policy_days: Optional[int] = None


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
                    "source_agent": "PROCUREMENT_EXPERT",
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
                    "message": f"[PROCUREMENT EXPERT] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "PROCUREMENT_EXPERT"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")


async def store_memory(memory_type: str, content: str, category: str = "shopping",
                       source_type: str = "agent_result", tags: List[str] = None):
    """Store memory in Unified Memory system"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/store_unified_memory",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "p_memory_type": memory_type,
                    "p_content": content,
                    "p_category": category,
                    "p_source_type": source_type,
                    "p_tags": tags or ["procurement-expert"]
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"Memory store failed: {e}")


# =============================================================================
# DATABASE HELPERS
# =============================================================================

async def db_query(table: str, params: dict = None, single: bool = False) -> Any:
    """Execute a database query"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={value}")
            url += "?" + "&".join(query_parts)

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if single and isinstance(data, list):
                    return data[0] if data else None
                return data
            return None
    except Exception as e:
        print(f"Database query failed: {e}")
        return None


async def db_insert(table: str, data: dict) -> dict:
    """Insert record into database"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
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
            if resp.status_code in [200, 201]:
                result = resp.json()
                return result[0] if isinstance(result, list) else result
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")


async def db_update(table: str, id: str, data: dict) -> dict:
    """Update record in database"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                timeout=10.0
            )
            if resp.status_code == 200:
                result = resp.json()
                return result[0] if isinstance(result, list) else result
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")


async def db_delete(table: str, id: str) -> bool:
    """Delete record from database"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.delete(
                f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )
            return resp.status_code in [200, 204]
    except Exception as e:
        print(f"Database delete failed: {e}")
        return False


# =============================================================================
# SHOPPING CONTEXT
# =============================================================================

async def get_shopping_context(user_id: str = None) -> dict:
    """Get current shopping context for system prompt"""
    time_ctx = get_time_context()

    # Fetch counts from database (with defaults if queries fail)
    active_wishlists = 0
    tracked_products = 0
    active_deals = 0
    expiring_warranties = 0

    try:
        # Get product count
        products = await db_query("products", {"select": "count"})
        if products:
            tracked_products = len(products) if isinstance(products, list) else 0

        # Get active deals count
        deals = await db_query("deals", {
            "select": "count",
            "valid_until": f"gt.{time_ctx['current_datetime']}"
        })
        if deals:
            active_deals = len(deals) if isinstance(deals, list) else 0

        # Get wishlists count
        if user_id:
            wishlists = await db_query("wishlists", {
                "select": "count",
                "user_id": f"eq.{user_id}",
                "is_active": "eq.true"
            })
            if wishlists:
                active_wishlists = len(wishlists) if isinstance(wishlists, list) else 0

    except Exception as e:
        print(f"Error fetching shopping context: {e}")

    return {
        "current_time": time_ctx['current_datetime'],
        "upcoming_sales": get_upcoming_sales(),
        "active_wishlists": active_wishlists,
        "tracked_products": tracked_products,
        "active_deals": active_deals,
        "expiring_warranties": expiring_warranties
    }


# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, shopping_ctx: dict) -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        system_prompt = build_system_prompt(shopping_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="PROCUREMENT_EXPERT",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "PROCUREMENT_EXPERT",
        "role": "Shopping Research & Purchase Intelligence",
        "port": 8206,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "launch_status": time_ctx['launch_status']
    }


@app.get("/status")
async def status():
    """Service status with stats"""
    time_ctx = get_time_context()
    shopping_ctx = await get_shopping_context()

    return {
        "agent": "PROCUREMENT_EXPERT",
        "status": "operational",
        "version": "1.0.0",
        "time_context": time_ctx,
        "shopping_context": shopping_ctx,
        "capabilities": [
            "product_research",
            "price_comparison",
            "deal_tracking",
            "purchase_history",
            "warranty_management",
            "wishlist_management"
        ]
    }


@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    # Fetch basic metrics
    shopping_ctx = await get_shopping_context()

    metrics_text = f"""# HELP procurement_products_total Total tracked products
# TYPE procurement_products_total gauge
procurement_products_total {shopping_ctx['tracked_products']}

# HELP procurement_deals_active Active deals count
# TYPE procurement_deals_active gauge
procurement_deals_active {shopping_ctx['active_deals']}

# HELP procurement_wishlists_active Active wishlists count
# TYPE procurement_wishlists_active gauge
procurement_wishlists_active {shopping_ctx['active_wishlists']}

# HELP procurement_health Agent health status
# TYPE procurement_health gauge
procurement_health 1
"""
    return metrics_text


# =============================================================================
# PRODUCT RESEARCH ENDPOINTS
# =============================================================================

@app.post("/research")
async def research_product(req: ResearchRequest):
    """Research a product (AI-powered)"""
    shopping_ctx = await get_shopping_context()

    prompt = f"""Research this product/category for a user:

Query: {req.query}
Category: {req.category or 'Not specified'}
Budget: ${req.budget if req.budget else 'Not specified'}
Requirements: {', '.join(req.requirements) if req.requirements else 'None specified'}

Provide:
1. Product recommendations (top 3-5 options)
2. Key specifications comparison
3. Price ranges across major retailers
4. Pros and cons for each option
5. Best value recommendation
6. Best timing to buy (upcoming sales?)

Be thorough but concise. Focus on actionable purchasing guidance.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, shopping_ctx)

    # Store research in memory
    await store_memory(
        memory_type="fact",
        content=f"Product research for '{req.query}': {response[:500]}...",
        category="shopping",
        tags=["procurement-expert", "research", req.category or "general"]
    )

    # Notify event bus
    await notify_event_bus("shop.research.completed", {
        "query": req.query,
        "category": req.category
    })

    return {
        "research": response,
        "query": req.query,
        "category": req.category,
        "budget": req.budget,
        "agent": "PROCUREMENT_EXPERT",
        "timestamp": shopping_ctx['current_time']
    }


@app.get("/products")
async def list_products(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    limit: int = Query(50, le=100)
):
    """List tracked products"""
    params = {"select": "*", "limit": str(limit), "order": "created_at.desc"}

    if category:
        params["category"] = f"eq.{category}"
    if brand:
        params["brand"] = f"eq.{brand}"

    products = await db_query("products", params)
    return {"products": products or [], "count": len(products) if products else 0}


@app.get("/products/{product_id}")
async def get_product(product_id: str):
    """Product detail with price history"""
    product = await db_query("products", {"id": f"eq.{product_id}"}, single=True)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get price history
    prices = await db_query("price_history", {
        "product_id": f"eq.{product_id}",
        "order": "scraped_at.desc",
        "limit": "30"
    })

    return {
        "product": product,
        "price_history": prices or [],
        "price_count": len(prices) if prices else 0
    }


@app.post("/products")
async def create_product(product: ProductCreate):
    """Add product to tracking"""
    data = product.model_dump(exclude_none=True)
    result = await db_insert("products", data)

    await notify_event_bus("shop.product.added", {
        "product_id": result.get("id"),
        "name": product.name,
        "category": product.category
    })

    return {"product": result, "message": "Product added to tracking"}


@app.put("/products/{product_id}")
async def update_product(product_id: str, product: ProductUpdate):
    """Update product info"""
    data = product.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")

    data["updated_at"] = datetime.utcnow().isoformat()
    result = await db_update("products", product_id, data)

    return {"product": result, "message": "Product updated"}


@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    """Remove product"""
    success = await db_delete("products", product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found or delete failed")

    return {"message": "Product removed", "product_id": product_id}


@app.get("/products/search")
async def search_products(
    q: str = Query(..., min_length=2),
    category: Optional[str] = None,
    limit: int = Query(20, le=50)
):
    """Search products by name/category"""
    # Use text search if available, otherwise filter
    params = {
        "select": "*",
        "name": f"ilike.*{q}*",
        "limit": str(limit)
    }

    if category:
        params["category"] = f"eq.{category}"

    products = await db_query("products", params)
    return {"products": products or [], "query": q, "count": len(products) if products else 0}


# =============================================================================
# PRICE COMPARISON ENDPOINTS
# =============================================================================

@app.post("/compare")
async def compare_prices(req: CompareRequest):
    """Compare prices across vendors"""
    shopping_ctx = await get_shopping_context()

    # Get product details if ID provided
    product_info = ""
    if req.product_id:
        product = await db_query("products", {"id": f"eq.{req.product_id}"}, single=True)
        if product:
            product_info = f"Product: {product.get('name')} ({product.get('brand', 'Unknown brand')})"

    prompt = f"""Compare prices for this product across major retailers:

{product_info if product_info else f"Product: {req.product_name or 'Unknown'}"}
Include Shipping: {req.include_shipping}

Provide:
1. Price comparison table (Retailer | Price | Shipping | Total | In Stock)
2. Best overall value
3. Historical price context (is this a good price?)
4. Recommendation (buy now or wait?)
5. Any active coupons or promotions

Focus on major retailers: Amazon, Best Buy, Walmart, Target, Costco, Home Depot, etc.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, shopping_ctx)

    await notify_event_bus("shop.compare.completed", {
        "product_id": req.product_id,
        "product_name": req.product_name
    })

    return {
        "comparison": response,
        "product_id": req.product_id,
        "product_name": req.product_name,
        "include_shipping": req.include_shipping,
        "agent": "PROCUREMENT_EXPERT",
        "timestamp": shopping_ctx['current_time']
    }


@app.get("/prices/{product_id}")
async def get_price_history(product_id: str, days: int = Query(30, le=365)):
    """Price history for product"""
    prices = await db_query("price_history", {
        "product_id": f"eq.{product_id}",
        "order": "scraped_at.desc",
        "limit": str(days * 5)  # Assume ~5 vendors per day
    })

    if not prices:
        return {"product_id": product_id, "prices": [], "summary": None}

    # Calculate summary stats
    all_prices = [p['price'] for p in prices if p.get('price')]
    summary = None
    if all_prices:
        summary = {
            "current_lowest": min(all_prices),
            "current_highest": max(all_prices),
            "average": sum(all_prices) / len(all_prices),
            "data_points": len(all_prices)
        }

    return {
        "product_id": product_id,
        "prices": prices,
        "summary": summary
    }


@app.get("/prices/lowest")
async def get_lowest_prices(limit: int = Query(20, le=50)):
    """Current lowest prices across tracked products"""
    # This would use a more sophisticated query in production
    # For now, get recent prices and find lowest per product
    prices = await db_query("price_history", {
        "select": "*",
        "order": "price.asc",
        "limit": str(limit)
    })

    return {"lowest_prices": prices or []}


@app.get("/prices/trends")
async def get_price_trends(product_id: Optional[str] = None, days: int = Query(30, le=90)):
    """Price trend analysis"""
    shopping_ctx = await get_shopping_context()

    params = {
        "order": "scraped_at.desc",
        "limit": str(days * 10)
    }
    if product_id:
        params["product_id"] = f"eq.{product_id}"

    prices = await db_query("price_history", params)

    # AI analysis of trends
    if prices:
        prompt = f"""Analyze these price trends:

Data Points: {len(prices)}
Time Period: Last {days} days
Product Filter: {product_id or 'All products'}

Sample data: {json.dumps(prices[:10], default=str)}

Provide:
1. Overall trend (rising/falling/stable)
2. Best time to buy patterns
3. Vendor price comparison
4. Recommendations
"""
        messages = [{"role": "user", "content": prompt}]
        analysis = await call_llm(messages, shopping_ctx)
    else:
        analysis = "Insufficient price data for trend analysis."

    return {
        "product_id": product_id,
        "days": days,
        "data_points": len(prices) if prices else 0,
        "analysis": analysis
    }


@app.post("/prices/check")
async def force_price_check(req: PriceCheckRequest):
    """Force price check for product"""
    # In production, this would trigger actual price scraping
    # For now, we acknowledge the request

    await notify_event_bus("shop.price.check_requested", {
        "product_id": req.product_id,
        "vendors": req.vendors
    })

    return {
        "message": "Price check requested",
        "product_id": req.product_id,
        "vendors": req.vendors or ["all"],
        "status": "queued"
    }


# =============================================================================
# DEAL TRACKING ENDPOINTS
# =============================================================================

@app.get("/deals")
async def list_deals(
    vendor: Optional[str] = None,
    min_discount: Optional[float] = None,
    limit: int = Query(50, le=100)
):
    """List active deals"""
    time_ctx = get_time_context()
    params = {
        "select": "*",
        "valid_until": f"gt.{time_ctx['current_datetime']}",
        "order": "discount_percent.desc",
        "limit": str(limit)
    }

    if vendor:
        params["vendor"] = f"eq.{vendor}"
    if min_discount:
        params["discount_percent"] = f"gte.{min_discount}"

    deals = await db_query("deals", params)
    return {"deals": deals or [], "count": len(deals) if deals else 0}


@app.get("/deals/{deal_id}")
async def get_deal(deal_id: str):
    """Deal detail"""
    deal = await db_query("deals", {"id": f"eq.{deal_id}"}, single=True)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Get associated product
    product = None
    if deal.get("product_id"):
        product = await db_query("products", {"id": f"eq.{deal['product_id']}"}, single=True)

    return {"deal": deal, "product": product}


@app.post("/deals/track")
async def track_deal(req: DealTrackRequest):
    """Track a deal / set price alert"""
    # Get product info
    product = await db_query("products", {"id": f"eq.{req.product_id}"}, single=True)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # In production, this would create an alert/tracking entry
    await notify_event_bus("shop.deal.tracking_started", {
        "product_id": req.product_id,
        "product_name": product.get("name"),
        "target_price": req.target_price,
        "vendor": req.vendor
    })

    # Store in memory
    await store_memory(
        memory_type="fact",
        content=f"Tracking deal for {product.get('name')}: target price ${req.target_price or 'any drop'}",
        category="shopping",
        tags=["procurement-expert", "deal-tracking"]
    )

    return {
        "message": "Deal tracking started",
        "product_id": req.product_id,
        "product_name": product.get("name"),
        "target_price": req.target_price,
        "vendor": req.vendor
    }


@app.get("/deals/expiring")
async def get_expiring_deals(hours: int = Query(24, le=168)):
    """Deals expiring soon"""
    time_ctx = get_time_context()
    now = datetime.fromisoformat(time_ctx['current_datetime'].replace('Z', '+00:00'))
    expiry_window = (now + timedelta(hours=hours)).isoformat()

    params = {
        "select": "*",
        "valid_until": f"gt.{time_ctx['current_datetime']}",
        "valid_until": f"lt.{expiry_window}",
        "order": "valid_until.asc"
    }

    deals = await db_query("deals", params)
    return {"deals": deals or [], "hours_window": hours}


@app.post("/deals/verify")
async def verify_deal(req: DealVerifyRequest):
    """Verify deal is still active"""
    deal = await db_query("deals", {"id": f"eq.{req.deal_id}"}, single=True)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # In production, this would actually verify the deal
    time_ctx = get_time_context()
    is_valid = deal.get("valid_until", "") > time_ctx['current_datetime']

    return {
        "deal_id": req.deal_id,
        "is_valid": is_valid,
        "verified_at": time_ctx['current_datetime'],
        "deal": deal
    }


@app.get("/coupons")
async def list_coupons(
    vendor: Optional[str] = None,
    limit: int = Query(50, le=100)
):
    """Available coupons"""
    time_ctx = get_time_context()
    params = {
        "select": "*",
        "coupon_code": "not.is.null",
        "valid_until": f"gt.{time_ctx['current_datetime']}",
        "limit": str(limit)
    }

    if vendor:
        params["vendor"] = f"eq.{vendor}"

    coupons = await db_query("deals", params)
    return {"coupons": coupons or [], "count": len(coupons) if coupons else 0}


@app.post("/coupons/search")
async def search_coupons(req: CouponSearchRequest):
    """Search for coupons"""
    shopping_ctx = await get_shopping_context()

    prompt = f"""Search for available coupons and promo codes:

Vendor: {req.vendor or 'Any'}
Category: {req.category or 'Any'}
Product: {req.product_id or 'Any'}

Find:
1. Active coupon codes
2. Cashback offers
3. Stacking opportunities
4. Student/military discounts
5. Credit card offers

Note any restrictions or expiration dates.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, shopping_ctx)

    return {
        "coupons": response,
        "vendor": req.vendor,
        "category": req.category,
        "timestamp": shopping_ctx['current_time']
    }


# =============================================================================
# PURCHASE HISTORY ENDPOINTS
# =============================================================================

@app.post("/purchases")
async def log_purchase(purchase: PurchaseCreate):
    """Log a purchase"""
    data = purchase.model_dump(exclude_none=True)

    # Calculate warranty expiration if warranty_months provided
    if purchase.warranty_months:
        purchase_date = datetime.fromisoformat(purchase.purchase_date)
        # Approximate months as 30 days each
        warranty_expires = purchase_date + timedelta(days=purchase.warranty_months * 30)
        data["warranty_expires"] = warranty_expires.date().isoformat()

    result = await db_insert("purchases", data)

    # Store in memory
    await store_memory(
        memory_type="decision",
        content=f"Purchased {purchase.product_name or 'item'} from {purchase.vendor} for ${purchase.price}",
        category="shopping",
        source_type="user_action",
        tags=["procurement-expert", "purchase"]
    )

    # Notify event bus
    await notify_event_bus("shop.purchase.logged", {
        "purchase_id": result.get("id"),
        "vendor": purchase.vendor,
        "price": purchase.price
    })

    return {"purchase": result, "message": "Purchase logged"}


@app.get("/purchases")
async def list_purchases(
    user_id: str,
    vendor: Optional[str] = None,
    limit: int = Query(50, le=100)
):
    """List user purchases"""
    params = {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "order": "purchase_date.desc",
        "limit": str(limit)
    }

    if vendor:
        params["vendor"] = f"eq.{vendor}"

    purchases = await db_query("purchases", params)
    return {"purchases": purchases or [], "count": len(purchases) if purchases else 0}


@app.get("/purchases/{purchase_id}")
async def get_purchase(purchase_id: str):
    """Purchase detail"""
    purchase = await db_query("purchases", {"id": f"eq.{purchase_id}"}, single=True)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")

    # Get associated product if exists
    product = None
    if purchase.get("product_id"):
        product = await db_query("products", {"id": f"eq.{purchase['product_id']}"}, single=True)

    return {"purchase": purchase, "product": product}


@app.put("/purchases/{purchase_id}")
async def update_purchase(purchase_id: str, purchase: PurchaseUpdate):
    """Update purchase info"""
    data = purchase.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")

    result = await db_update("purchases", purchase_id, data)
    return {"purchase": result, "message": "Purchase updated"}


@app.get("/purchases/warranty")
async def check_warranty_status(user_id: str, product_id: Optional[str] = None):
    """Check warranty status"""
    params = {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "warranty_expires": "not.is.null"
    }

    if product_id:
        params["product_id"] = f"eq.{product_id}"

    purchases = await db_query("purchases", params)

    # Categorize by status
    time_ctx = get_time_context()
    today = time_ctx['current_date']

    active = []
    expired = []
    expiring_soon = []

    for p in (purchases or []):
        expires = p.get("warranty_expires", "")
        if expires < today:
            expired.append(p)
        elif expires <= (datetime.fromisoformat(today) + timedelta(days=30)).date().isoformat():
            expiring_soon.append(p)
        else:
            active.append(p)

    return {
        "active_warranties": active,
        "expiring_soon": expiring_soon,
        "expired": expired,
        "total": len(purchases) if purchases else 0
    }


@app.get("/purchases/expiring")
async def get_expiring_warranties(user_id: str, days: int = Query(30, le=90)):
    """Warranties expiring soon"""
    time_ctx = get_time_context()
    today = datetime.fromisoformat(time_ctx['current_date'])
    expiry_window = (today + timedelta(days=days)).date().isoformat()

    params = {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "warranty_expires": f"gte.{time_ctx['current_date']}",
        "warranty_expires": f"lte.{expiry_window}",
        "order": "warranty_expires.asc"
    }

    purchases = await db_query("purchases", params)

    # Send alerts for items expiring soon
    if purchases:
        for p in purchases[:3]:  # Alert for first 3
            await notify_event_bus("shop.warranty.expiring", {
                "purchase_id": p.get("id"),
                "expires": p.get("warranty_expires")
            })

    return {"expiring_warranties": purchases or [], "days_window": days}


@app.get("/purchases/stats")
async def get_purchase_stats(user_id: str, days: int = Query(365, le=730)):
    """Purchase statistics"""
    time_ctx = get_time_context()
    start_date = (datetime.fromisoformat(time_ctx['current_date']) - timedelta(days=days)).date().isoformat()

    params = {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "purchase_date": f"gte.{start_date}"
    }

    purchases = await db_query("purchases", params)

    if not purchases:
        return {
            "total_spent": 0,
            "purchase_count": 0,
            "average_purchase": 0,
            "by_vendor": {},
            "days": days
        }

    # Calculate stats
    total_spent = sum(p.get("price", 0) * p.get("quantity", 1) for p in purchases)
    purchase_count = len(purchases)

    # Group by vendor
    by_vendor = {}
    for p in purchases:
        vendor = p.get("vendor", "Unknown")
        if vendor not in by_vendor:
            by_vendor[vendor] = {"count": 0, "total": 0}
        by_vendor[vendor]["count"] += 1
        by_vendor[vendor]["total"] += p.get("price", 0) * p.get("quantity", 1)

    return {
        "total_spent": round(total_spent, 2),
        "purchase_count": purchase_count,
        "average_purchase": round(total_spent / purchase_count, 2) if purchase_count else 0,
        "by_vendor": by_vendor,
        "days": days
    }


@app.post("/purchases/receipt")
async def upload_receipt(req: ReceiptUpload):
    """Upload receipt"""
    result = await db_update("purchases", req.purchase_id, {"receipt_url": req.receipt_url})

    if not result:
        raise HTTPException(status_code=404, detail="Purchase not found")

    return {"message": "Receipt uploaded", "purchase_id": req.purchase_id}


# =============================================================================
# WISHLIST ENDPOINTS
# =============================================================================

@app.get("/wishlists")
async def list_wishlists(user_id: str, active_only: bool = True):
    """List user wishlists"""
    params = {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "order": "created_at.desc"
    }

    if active_only:
        params["is_active"] = "eq.true"

    wishlists = await db_query("wishlists", params)
    return {"wishlists": wishlists or [], "count": len(wishlists) if wishlists else 0}


@app.post("/wishlists")
async def create_wishlist(wishlist: WishlistCreate):
    """Create wishlist"""
    data = wishlist.model_dump(exclude_none=True)
    data["items"] = []
    result = await db_insert("wishlists", data)

    await notify_event_bus("shop.wishlist.created", {
        "wishlist_id": result.get("id"),
        "name": wishlist.name
    })

    return {"wishlist": result, "message": "Wishlist created"}


@app.get("/wishlists/{wishlist_id}")
async def get_wishlist(wishlist_id: str):
    """Wishlist detail"""
    wishlist = await db_query("wishlists", {"id": f"eq.{wishlist_id}"}, single=True)
    if not wishlist:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    # Get product details for items
    items = wishlist.get("items", [])
    enriched_items = []
    for item in items:
        product = await db_query("products", {"id": f"eq.{item.get('product_id')}"}, single=True)
        enriched_items.append({**item, "product": product})

    wishlist["enriched_items"] = enriched_items
    return {"wishlist": wishlist}


@app.put("/wishlists/{wishlist_id}")
async def update_wishlist(wishlist_id: str, wishlist: WishlistUpdate):
    """Update wishlist"""
    data = wishlist.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")

    data["updated_at"] = datetime.utcnow().isoformat()
    result = await db_update("wishlists", wishlist_id, data)

    await notify_event_bus("shop.wishlist.updated", {"wishlist_id": wishlist_id})

    return {"wishlist": result, "message": "Wishlist updated"}


@app.delete("/wishlists/{wishlist_id}")
async def delete_wishlist(wishlist_id: str):
    """Delete wishlist"""
    success = await db_delete("wishlists", wishlist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Wishlist not found or delete failed")

    return {"message": "Wishlist deleted", "wishlist_id": wishlist_id}


@app.post("/wishlists/{wishlist_id}/items")
async def add_wishlist_item(wishlist_id: str, item: WishlistItemAdd):
    """Add item to wishlist"""
    wishlist = await db_query("wishlists", {"id": f"eq.{wishlist_id}"}, single=True)
    if not wishlist:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    items = wishlist.get("items", [])
    new_item = {
        "product_id": item.product_id,
        "target_price": item.target_price,
        "priority": item.priority or 3,
        "added_at": datetime.utcnow().isoformat()
    }
    items.append(new_item)

    result = await db_update("wishlists", wishlist_id, {
        "items": items,
        "updated_at": datetime.utcnow().isoformat()
    })

    await notify_event_bus("shop.wishlist.item_added", {
        "wishlist_id": wishlist_id,
        "product_id": item.product_id
    })

    return {"wishlist": result, "message": "Item added to wishlist"}


@app.delete("/wishlists/{wishlist_id}/items/{product_id}")
async def remove_wishlist_item(wishlist_id: str, product_id: str):
    """Remove item from wishlist"""
    wishlist = await db_query("wishlists", {"id": f"eq.{wishlist_id}"}, single=True)
    if not wishlist:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    items = wishlist.get("items", [])
    items = [i for i in items if i.get("product_id") != product_id]

    result = await db_update("wishlists", wishlist_id, {
        "items": items,
        "updated_at": datetime.utcnow().isoformat()
    })

    return {"wishlist": result, "message": "Item removed from wishlist"}


# =============================================================================
# VENDOR ENDPOINTS
# =============================================================================

@app.get("/vendors")
async def list_vendors(category: Optional[str] = None, limit: int = Query(50, le=100)):
    """List vendors"""
    params = {
        "select": "*",
        "order": "rating.desc.nullslast",
        "limit": str(limit)
    }

    if category:
        params["categories"] = f"cs.{{{category}}}"

    vendors = await db_query("vendors", params)
    return {"vendors": vendors or [], "count": len(vendors) if vendors else 0}


@app.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: str):
    """Vendor detail"""
    vendor = await db_query("vendors", {"id": f"eq.{vendor_id}"}, single=True)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return {"vendor": vendor}


@app.post("/vendors")
async def create_vendor(vendor: VendorCreate):
    """Add vendor"""
    data = vendor.model_dump(exclude_none=True)
    result = await db_insert("vendors", data)

    return {"vendor": result, "message": "Vendor added"}


@app.put("/vendors/{vendor_id}")
async def update_vendor(vendor_id: str, vendor: VendorUpdate):
    """Update vendor"""
    data = vendor.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")

    data["updated_at"] = datetime.utcnow().isoformat()
    result = await db_update("vendors", vendor_id, data)

    return {"vendor": result, "message": "Vendor updated"}


@app.get("/vendors/best")
async def get_best_vendors(category: str):
    """Best vendors by category"""
    params = {
        "select": "*",
        "categories": f"cs.{{{category}}}",
        "order": "rating.desc.nullslast",
        "limit": "10"
    }

    vendors = await db_query("vendors", params)

    # AI analysis of best vendors
    shopping_ctx = await get_shopping_context()

    if vendors:
        prompt = f"""Analyze and rank these vendors for {category}:

Vendors: {json.dumps(vendors, default=str)}

Provide:
1. Best overall for value
2. Best for customer service
3. Best return policy
4. Best for price matching
5. Recommendation based on user needs
"""
        messages = [{"role": "user", "content": prompt}]
        analysis = await call_llm(messages, shopping_ctx)
    else:
        analysis = f"No vendors found for category: {category}"

    return {
        "category": category,
        "vendors": vendors or [],
        "analysis": analysis
    }


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8206)
