#!/usr/bin/env python3
"""
API Gateway - Rate Limiter & External API Gateway
Port: 8070

A rate limiter and API gateway for all external API calls with:
- Rate limit tracking for OpenAI (10K TPM) and Anthropic
- Per-agent quotas
- Request queuing when near limits
- Cost tracking integration
"""

import os
import json
import httpx
import asyncio
import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from pydantic import BaseModel, Field


# =============================================================================
# Configuration
# =============================================================================

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
COST_TRACKER_URL = os.getenv("COST_TRACKER_URL", "")  # Optional external cost tracker

# Rate limit configurations (tokens per minute)
RATE_LIMITS = {
    "openai": {
        "tpm": int(os.getenv("OPENAI_TPM_LIMIT", "10000")),  # Tokens per minute
        "rpm": int(os.getenv("OPENAI_RPM_LIMIT", "500")),     # Requests per minute
        "daily_tokens": int(os.getenv("OPENAI_DAILY_LIMIT", "1000000")),
    },
    "anthropic": {
        "tpm": int(os.getenv("ANTHROPIC_TPM_LIMIT", "40000")),  # Anthropic has higher limits
        "rpm": int(os.getenv("ANTHROPIC_RPM_LIMIT", "1000")),
        "daily_tokens": int(os.getenv("ANTHROPIC_DAILY_LIMIT", "2000000")),
    },
    "google": {
        "tpm": int(os.getenv("GOOGLE_TPM_LIMIT", "32000")),
        "rpm": int(os.getenv("GOOGLE_RPM_LIMIT", "360")),
        "daily_tokens": int(os.getenv("GOOGLE_DAILY_LIMIT", "1500000")),
    }
}

# Per-agent quota limits (percentage of total)
AGENT_QUOTA_PERCENT = float(os.getenv("AGENT_QUOTA_PERCENT", "20"))  # Each agent can use up to 20% by default

# Queue settings
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "100"))
QUEUE_TIMEOUT = int(os.getenv("QUEUE_TIMEOUT", "30"))  # seconds

# Pricing for cost tracking (per 1M tokens)
PRICING = {
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    },
    "anthropic": {
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
        "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
        "claude-sonnet": {"input": 3.00, "output": 15.00},
        "claude-opus": {"input": 15.00, "output": 75.00},
        "claude-haiku": {"input": 0.25, "output": 1.25},
    },
    "google": {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    }
}


# =============================================================================
# Data Classes & Models
# =============================================================================

class ServiceType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int
    tokens: float = field(default=0)
    last_update: float = field(default_factory=time.time)
    refill_rate: float = field(default=0)  # tokens per second

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.refill_rate = self.capacity / 60.0  # Refill over 1 minute

    def consume(self, amount: int) -> bool:
        """Try to consume tokens, returns True if successful"""
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

    def available(self) -> float:
        """Get available tokens"""
        self._refill()
        return self.tokens

    def time_until_available(self, amount: int) -> float:
        """Calculate seconds until requested tokens are available"""
        self._refill()
        if self.tokens >= amount:
            return 0
        needed = amount - self.tokens
        return needed / self.refill_rate


@dataclass
class ServiceLimits:
    """Rate limits for a service"""
    tpm_bucket: TokenBucket
    rpm_bucket: TokenBucket
    daily_tokens_used: int = 0
    daily_limit: int = 0
    last_daily_reset: datetime = field(default_factory=lambda: datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))

    def reset_daily_if_needed(self):
        """Reset daily counters if it's a new day"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if today > self.last_daily_reset:
            self.daily_tokens_used = 0
            self.last_daily_reset = today


@dataclass
class AgentQuota:
    """Per-agent quota tracking"""
    agent_id: str
    tokens_used_today: int = 0
    requests_today: int = 0
    cost_today: float = 0.0
    last_reset: datetime = field(default_factory=lambda: datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))

    def reset_if_needed(self):
        """Reset counters if it's a new day"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if today > self.last_reset:
            self.tokens_used_today = 0
            self.requests_today = 0
            self.cost_today = 0.0
            self.last_reset = today


@dataclass
class QueuedRequest:
    """A request waiting in the queue"""
    id: str
    service: str
    agent_id: str
    estimated_tokens: int
    request_data: Dict[str, Any]
    created_at: datetime
    future: asyncio.Future


class ProxyRequest(BaseModel):
    """Request to proxy through the gateway"""
    service: ServiceType = Field(..., description="Target service (openai, anthropic, google)")
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(default="POST", description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str = Field(default="unknown", description="ID of requesting agent")
    estimated_tokens: int = Field(default=1000, description="Estimated token usage")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10 (1=highest)")


class ProxyResponse(BaseModel):
    """Response from proxy request"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0
    queue_time_ms: int = 0
    request_time_ms: int = 0


class LimitStatus(BaseModel):
    """Current rate limit status"""
    service: str
    tpm_available: float
    tpm_limit: int
    rpm_available: float
    rpm_limit: int
    daily_tokens_used: int
    daily_limit: int
    daily_percent_used: float
    queue_size: int


# =============================================================================
# Gateway State
# =============================================================================

class GatewayState:
    """Global gateway state"""

    def __init__(self):
        # Service rate limits
        self.service_limits: Dict[str, ServiceLimits] = {}
        for service, config in RATE_LIMITS.items():
            self.service_limits[service] = ServiceLimits(
                tpm_bucket=TokenBucket(capacity=config["tpm"]),
                rpm_bucket=TokenBucket(capacity=config["rpm"]),
                daily_limit=config["daily_tokens"]
            )

        # Per-agent quotas
        self.agent_quotas: Dict[str, AgentQuota] = defaultdict(lambda: AgentQuota(agent_id="unknown"))

        # Request queues (per service)
        self.queues: Dict[str, asyncio.PriorityQueue] = {
            service: asyncio.PriorityQueue(maxsize=MAX_QUEUE_SIZE)
            for service in RATE_LIMITS.keys()
        }

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "queued_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_by_service": defaultdict(int),
            "requests_by_agent": defaultdict(int),
            "tokens_by_service": defaultdict(int),
            "tokens_by_agent": defaultdict(int),
            "cost_by_service": defaultdict(float),
            "cost_by_agent": defaultdict(float),
            "start_time": datetime.utcnow().isoformat(),
        }

        # Active HTTP client
        self.http_client: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Initialize async resources"""
        self.http_client = httpx.AsyncClient(timeout=60.0)
        # Start queue processors
        for service in RATE_LIMITS.keys():
            asyncio.create_task(self._process_queue(service))

    async def stop(self):
        """Cleanup async resources"""
        if self.http_client:
            await self.http_client.aclose()

    async def _process_queue(self, service: str):
        """Background task to process queued requests"""
        queue = self.queues[service]
        limits = self.service_limits[service]

        while True:
            try:
                # Get next request from queue
                priority, created_at, request = await queue.get()

                # Check if request has timed out
                elapsed = (datetime.utcnow() - created_at).total_seconds()
                if elapsed > QUEUE_TIMEOUT:
                    request.future.set_exception(
                        HTTPException(status_code=408, detail="Request timed out in queue")
                    )
                    continue

                # Wait for rate limit availability
                wait_time = limits.tpm_bucket.time_until_available(request.estimated_tokens)
                if wait_time > 0:
                    await asyncio.sleep(min(wait_time, 1.0))

                # Mark request as ready to proceed
                request.future.set_result(True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Queue processor error for {service}: {e}")
                await asyncio.sleep(1)


# Global state instance
state: Optional[GatewayState] = None


# =============================================================================
# Lifespan Management
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global state
    state = GatewayState()
    await state.start()
    yield
    await state.stop()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="API Gateway",
    description="Rate Limiter & External API Gateway for LeverEdge",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# Helper Functions
# =============================================================================

def get_base_url(service: str) -> str:
    """Get base URL for a service"""
    urls = {
        "openai": "https://api.openai.com",
        "anthropic": "https://api.anthropic.com",
        "google": "https://generativelanguage.googleapis.com"
    }
    return urls.get(service, "")


def calculate_cost(service: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a request"""
    service_pricing = PRICING.get(service, {})
    model_pricing = service_pricing.get(model, {"input": 0, "output": 0})

    input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (output_tokens / 1_000_000) * model_pricing["output"]

    return round(input_cost + output_cost, 6)


def extract_token_usage(service: str, response_data: Dict[str, Any]) -> tuple:
    """Extract token usage from API response"""
    if service == "openai":
        usage = response_data.get("usage", {})
        return usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    elif service == "anthropic":
        usage = response_data.get("usage", {})
        return usage.get("input_tokens", 0), usage.get("output_tokens", 0)

    elif service == "google":
        usage = response_data.get("usageMetadata", {})
        return usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)

    return 0, 0


def extract_model(service: str, request_body: Dict[str, Any]) -> str:
    """Extract model name from request"""
    if service == "openai":
        return request_body.get("model", "gpt-4o")
    elif service == "anthropic":
        return request_body.get("model", "claude-sonnet")
    elif service == "google":
        return request_body.get("model", "gemini-1.5-flash")
    return "unknown"


async def log_to_event_bus(action: str, target: str = "", details: dict = None):
    """Log event to event bus"""
    if not state or not state.http_client:
        return
    try:
        await state.http_client.post(
            f"{EVENT_BUS_URL}/events",
            json={
                "source_agent": "API-GATEWAY",
                "action": action,
                "target": target,
                "details": details or {}
            },
            timeout=5.0
        )
    except Exception as e:
        print(f"Event bus log failed: {e}")


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    queue_sizes = {
        service: state.queues[service].qsize()
        for service in RATE_LIMITS.keys()
    } if state else {}

    return {
        "status": "healthy",
        "service": "API-GATEWAY",
        "port": 8070,
        "timestamp": datetime.utcnow().isoformat(),
        "queue_sizes": queue_sizes,
        "uptime_seconds": (datetime.utcnow() - datetime.fromisoformat(state.stats["start_time"])).total_seconds() if state else 0
    }


@app.get("/limits")
async def get_all_limits():
    """Get current rate limit status for all services"""
    if not state:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    limits = {}
    for service, service_limits in state.service_limits.items():
        service_limits.reset_daily_if_needed()
        limits[service] = LimitStatus(
            service=service,
            tpm_available=round(service_limits.tpm_bucket.available(), 2),
            tpm_limit=service_limits.tpm_bucket.capacity,
            rpm_available=round(service_limits.rpm_bucket.available(), 2),
            rpm_limit=service_limits.rpm_bucket.capacity,
            daily_tokens_used=service_limits.daily_tokens_used,
            daily_limit=service_limits.daily_limit,
            daily_percent_used=round((service_limits.daily_tokens_used / service_limits.daily_limit) * 100, 2) if service_limits.daily_limit > 0 else 0,
            queue_size=state.queues[service].qsize()
        )

    return {"limits": limits, "timestamp": datetime.utcnow().isoformat()}


@app.get("/limits/{service}")
async def get_service_limits(service: str):
    """Get rate limit status for a specific service"""
    if not state:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    service = service.lower()
    if service not in state.service_limits:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

    service_limits = state.service_limits[service]
    service_limits.reset_daily_if_needed()

    # Get per-agent breakdown
    agent_usage = {}
    for agent_id, quota in state.agent_quotas.items():
        quota.reset_if_needed()
        agent_usage[agent_id] = {
            "tokens_today": quota.tokens_used_today,
            "requests_today": quota.requests_today,
            "cost_today": round(quota.cost_today, 4)
        }

    return {
        "service": service,
        "limits": LimitStatus(
            service=service,
            tpm_available=round(service_limits.tpm_bucket.available(), 2),
            tpm_limit=service_limits.tpm_bucket.capacity,
            rpm_available=round(service_limits.rpm_bucket.available(), 2),
            rpm_limit=service_limits.rpm_bucket.capacity,
            daily_tokens_used=service_limits.daily_tokens_used,
            daily_limit=service_limits.daily_limit,
            daily_percent_used=round((service_limits.daily_tokens_used / service_limits.daily_limit) * 100, 2) if service_limits.daily_limit > 0 else 0,
            queue_size=state.queues[service].qsize()
        ),
        "agent_usage": agent_usage,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/request", response_model=ProxyResponse)
async def proxy_request(req: ProxyRequest):
    """Proxy a request through the gateway with rate limiting"""
    if not state:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    start_time = time.time()
    queue_time = 0
    service = req.service.value

    # Get service limits
    limits = state.service_limits.get(service)
    if not limits:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")

    # Reset daily limits if needed
    limits.reset_daily_if_needed()

    # Get/create agent quota
    agent_quota = state.agent_quotas[req.agent_id]
    agent_quota.agent_id = req.agent_id
    agent_quota.reset_if_needed()

    # Check daily limit
    if limits.daily_tokens_used + req.estimated_tokens > limits.daily_limit:
        state.stats["failed_requests"] += 1
        return ProxyResponse(
            success=False,
            status_code=429,
            error=f"Daily token limit exceeded for {service}",
            queue_time_ms=0,
            request_time_ms=int((time.time() - start_time) * 1000)
        )

    # Check per-agent quota (as percentage of daily limit)
    max_agent_tokens = int(limits.daily_limit * (AGENT_QUOTA_PERCENT / 100))
    if agent_quota.tokens_used_today + req.estimated_tokens > max_agent_tokens:
        state.stats["failed_requests"] += 1
        return ProxyResponse(
            success=False,
            status_code=429,
            error=f"Agent {req.agent_id} quota exceeded ({AGENT_QUOTA_PERCENT}% of daily limit)",
            queue_time_ms=0,
            request_time_ms=int((time.time() - start_time) * 1000)
        )

    # Try to acquire rate limit tokens
    if not limits.rpm_bucket.consume(1):
        # Queue the request
        if state.queues[service].full():
            state.stats["failed_requests"] += 1
            return ProxyResponse(
                success=False,
                status_code=503,
                error="Request queue is full",
                queue_time_ms=0,
                request_time_ms=int((time.time() - start_time) * 1000)
            )

        # Add to queue
        queue_start = time.time()
        future = asyncio.Future()
        queued_req = QueuedRequest(
            id=f"{req.agent_id}-{int(time.time()*1000)}",
            service=service,
            agent_id=req.agent_id,
            estimated_tokens=req.estimated_tokens,
            request_data=req.body,
            created_at=datetime.utcnow(),
            future=future
        )

        await state.queues[service].put((req.priority, queued_req.created_at, queued_req))
        state.stats["queued_requests"] += 1

        try:
            await asyncio.wait_for(future, timeout=QUEUE_TIMEOUT)
        except asyncio.TimeoutError:
            state.stats["failed_requests"] += 1
            return ProxyResponse(
                success=False,
                status_code=408,
                error="Request timed out in queue",
                queue_time_ms=int((time.time() - queue_start) * 1000),
                request_time_ms=int((time.time() - start_time) * 1000)
            )

        queue_time = int((time.time() - queue_start) * 1000)

    # Consume TPM tokens
    limits.tpm_bucket.consume(req.estimated_tokens)

    # Make the actual request
    request_start = time.time()
    try:
        base_url = get_base_url(service)
        url = f"{base_url}{req.endpoint}"

        response = await state.http_client.request(
            method=req.method,
            url=url,
            headers=req.headers,
            json=req.body if req.method in ["POST", "PUT", "PATCH"] else None,
            params=req.body if req.method == "GET" else None
        )

        response_data = response.json() if response.content else {}

        # Extract actual token usage
        input_tokens, output_tokens = extract_token_usage(service, response_data)
        total_tokens = input_tokens + output_tokens

        # Calculate cost
        model = extract_model(service, req.body)
        cost = calculate_cost(service, model, input_tokens, output_tokens)

        # Update stats
        state.stats["total_requests"] += 1
        state.stats["successful_requests"] += 1
        state.stats["total_tokens"] += total_tokens
        state.stats["total_cost"] += cost
        state.stats["requests_by_service"][service] += 1
        state.stats["requests_by_agent"][req.agent_id] += 1
        state.stats["tokens_by_service"][service] += total_tokens
        state.stats["tokens_by_agent"][req.agent_id] += total_tokens
        state.stats["cost_by_service"][service] += cost
        state.stats["cost_by_agent"][req.agent_id] += cost

        # Update daily counters
        limits.daily_tokens_used += total_tokens
        agent_quota.tokens_used_today += total_tokens
        agent_quota.requests_today += 1
        agent_quota.cost_today += cost

        # Log to event bus
        await log_to_event_bus(
            "api_request",
            target=service,
            details={
                "agent_id": req.agent_id,
                "endpoint": req.endpoint,
                "model": model,
                "tokens": total_tokens,
                "cost": cost
            }
        )

        return ProxyResponse(
            success=True,
            status_code=response.status_code,
            data=response_data,
            tokens_used=total_tokens,
            cost=cost,
            queue_time_ms=queue_time,
            request_time_ms=int((time.time() - request_start) * 1000)
        )

    except httpx.HTTPError as e:
        state.stats["total_requests"] += 1
        state.stats["failed_requests"] += 1

        return ProxyResponse(
            success=False,
            status_code=500,
            error=str(e),
            queue_time_ms=queue_time,
            request_time_ms=int((time.time() - request_start) * 1000)
        )


@app.get("/stats")
async def get_stats():
    """Get usage statistics"""
    if not state:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    uptime = (datetime.utcnow() - datetime.fromisoformat(state.stats["start_time"])).total_seconds()

    return {
        "summary": {
            "total_requests": state.stats["total_requests"],
            "successful_requests": state.stats["successful_requests"],
            "failed_requests": state.stats["failed_requests"],
            "success_rate": round(
                (state.stats["successful_requests"] / state.stats["total_requests"] * 100)
                if state.stats["total_requests"] > 0 else 0, 2
            ),
            "queued_requests": state.stats["queued_requests"],
            "total_tokens": state.stats["total_tokens"],
            "total_cost": round(state.stats["total_cost"], 4),
            "uptime_seconds": int(uptime),
            "start_time": state.stats["start_time"]
        },
        "by_service": {
            service: {
                "requests": state.stats["requests_by_service"].get(service, 0),
                "tokens": state.stats["tokens_by_service"].get(service, 0),
                "cost": round(state.stats["cost_by_service"].get(service, 0), 4)
            }
            for service in RATE_LIMITS.keys()
        },
        "by_agent": {
            agent_id: {
                "requests": state.stats["requests_by_agent"].get(agent_id, 0),
                "tokens": state.stats["tokens_by_agent"].get(agent_id, 0),
                "cost": round(state.stats["cost_by_agent"].get(agent_id, 0), 4)
            }
            for agent_id in state.stats["requests_by_agent"].keys()
        },
        "current_quotas": {
            agent_id: {
                "tokens_today": quota.tokens_used_today,
                "requests_today": quota.requests_today,
                "cost_today": round(quota.cost_today, 4)
            }
            for agent_id, quota in state.agent_quotas.items()
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/stats/agent/{agent_id}")
async def get_agent_stats(agent_id: str):
    """Get statistics for a specific agent"""
    if not state:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    quota = state.agent_quotas.get(agent_id)
    if not quota:
        return {
            "agent_id": agent_id,
            "found": False,
            "message": "No usage recorded for this agent"
        }

    quota.reset_if_needed()

    return {
        "agent_id": agent_id,
        "found": True,
        "today": {
            "tokens": quota.tokens_used_today,
            "requests": quota.requests_today,
            "cost": round(quota.cost_today, 4)
        },
        "lifetime": {
            "requests": state.stats["requests_by_agent"].get(agent_id, 0),
            "tokens": state.stats["tokens_by_agent"].get(agent_id, 0),
            "cost": round(state.stats["cost_by_agent"].get(agent_id, 0), 4)
        },
        "quota_percent_used": round(
            (quota.tokens_used_today / (state.service_limits["openai"].daily_limit * AGENT_QUOTA_PERCENT / 100)) * 100, 2
        ) if state.service_limits["openai"].daily_limit > 0 else 0,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/reset/daily")
async def reset_daily_counters():
    """Manually reset daily counters (admin endpoint)"""
    if not state:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    # Reset service limits
    for limits in state.service_limits.values():
        limits.daily_tokens_used = 0
        limits.last_daily_reset = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Reset agent quotas
    for quota in state.agent_quotas.values():
        quota.tokens_used_today = 0
        quota.requests_today = 0
        quota.cost_today = 0.0
        quota.last_reset = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    await log_to_event_bus("daily_reset", details={"manual": True})

    return {"status": "ok", "message": "Daily counters reset", "timestamp": datetime.utcnow().isoformat()}


@app.get("/queue/{service}")
async def get_queue_status(service: str):
    """Get queue status for a service"""
    if not state:
        raise HTTPException(status_code=503, detail="Gateway not initialized")

    service = service.lower()
    if service not in state.queues:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service}")

    queue = state.queues[service]
    limits = state.service_limits[service]

    return {
        "service": service,
        "queue_size": queue.qsize(),
        "max_queue_size": MAX_QUEUE_SIZE,
        "queue_timeout_seconds": QUEUE_TIMEOUT,
        "tpm_available": round(limits.tpm_bucket.available(), 2),
        "rpm_available": round(limits.rpm_bucket.available(), 2),
        "estimated_wait_seconds": round(limits.tpm_bucket.time_until_available(1000), 2),
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070)
