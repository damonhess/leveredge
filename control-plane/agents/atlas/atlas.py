"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           ATLAS ORCHESTRATION ENGINE                           ║
║                              FastAPI Implementation                            ║
║                                                                                ║
║  The programmatic brain of the OLYMPUS orchestration system.                  ║
║  Handles complex chains, parallel execution, and sophisticated error handling. ║
║                                                                                ║
║  Zero LLM cost - pure execution of structured intents.                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import httpx
import yaml
import re
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import jinja2

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SENTINEL_URL = os.getenv("SENTINEL_URL", "http://sentinel:8019")

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class Registry:
    """Loads and caches the agent registry."""
    
    _instance = None
    _registry = None
    _loaded_at = None
    _reload_interval = 60  # Reload every 60 seconds
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, force: bool = False) -> dict:
        """Load registry, with caching."""
        now = datetime.utcnow()
        
        if (not force and 
            self._registry and 
            self._loaded_at and 
            (now - self._loaded_at).seconds < self._reload_interval):
            return self._registry
            
        with open(REGISTRY_PATH) as f:
            self._registry = yaml.safe_load(f)
            self._loaded_at = now
            
        return self._registry
    
    def get_agent(self, name: str) -> Optional[dict]:
        """Get agent configuration."""
        registry = self.load()
        return registry.get("agents", {}).get(name.lower())
    
    def get_action(self, agent_name: str, action_name: str) -> Optional[dict]:
        """Get action configuration."""
        agent = self.get_agent(agent_name)
        if agent:
            return agent.get("actions", {}).get(action_name)
        return None
    
    def get_chain(self, name: str) -> Optional[dict]:
        """Get chain definition."""
        registry = self.load()
        return registry.get("chains", {}).get(name)
    
    def list_agents(self) -> List[dict]:
        """List all agents."""
        registry = self.load()
        return [
            {"name": k, "description": v.get("description")}
            for k, v in registry.get("agents", {}).items()
        ]
    
    def list_chains(self) -> List[dict]:
        """List all chains."""
        registry = self.load()
        return [
            {"name": k, "description": v.get("description"), "complexity": v.get("complexity")}
            for k, v in registry.get("chains", {}).items()
        ]
    
    def get_config(self) -> dict:
        """Get global config."""
        registry = self.load()
        return registry.get("config", {})


registry = Registry()

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class StepResult:
    """Result of a single step execution."""
    step_id: str
    agent: str
    action: str
    status: ExecutionStatus
    output: Any = None
    error: Optional[str] = None
    cost: float = 0.0
    duration_ms: int = 0
    retries: int = 0


@dataclass
class ExecutionContext:
    """Holds state during intent execution."""
    intent_id: str
    source: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    status: ExecutionStatus = ExecutionStatus.RUNNING
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    errors: List[dict] = field(default_factory=list)
    
    def get_step_output(self, step_id: str) -> Any:
        """Get output from a completed step."""
        result = self.step_results.get(step_id)
        return result.output if result else None
    
    def set_step_result(self, result: StepResult):
        """Store step result."""
        self.step_results[result.step_id] = result
    
    def add_error(self, step_id: str, error: str):
        """Add error to context."""
        self.errors.append({
            "step_id": step_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @property
    def total_cost(self) -> float:
        """Sum of all step costs."""
        return sum(r.cost for r in self.step_results.values())
    
    @property
    def duration_ms(self) -> int:
        """Total execution duration."""
        return int((datetime.utcnow() - self.started_at).total_seconds() * 1000)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for response."""
        return {
            "intent_id": self.intent_id,
            "source": self.source,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "total_cost": round(self.total_cost, 6),
            "steps_completed": len([r for r in self.step_results.values() if r.status == ExecutionStatus.COMPLETED]),
            "steps_failed": len([r for r in self.step_results.values() if r.status == ExecutionStatus.FAILED]),
            "step_results": {
                k: {
                    "agent": v.agent,
                    "action": v.action,
                    "status": v.status.value,
                    "output": v.output,
                    "error": v.error,
                    "cost": v.cost,
                    "duration_ms": v.duration_ms
                }
                for k, v in self.step_results.items()
            },
            "errors": self.errors if self.errors else None,
            "timestamp": datetime.utcnow().isoformat()
        }

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TemplateEngine:
    """Resolves templates with step outputs."""
    
    def __init__(self):
        self.env = jinja2.Environment(
            undefined=jinja2.StrictUndefined,
            autoescape=False
        )
        # Add custom filters
        self.env.filters['default'] = lambda x, d: x if x else d
        self.env.filters['join'] = lambda x, d: d.join(x) if isinstance(x, list) else x
    
    def resolve(self, template: str, context: ExecutionContext, input_data: dict) -> str:
        """Resolve template placeholders."""
        
        # Build template context
        template_ctx = {
            "input": input_data,
            "steps": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add step outputs
        for step_id, result in context.step_results.items():
            template_ctx["steps"][step_id] = {
                "output": result.output,
                "agent": result.agent,
                "action": result.action
            }
        
        # Handle nested paths like {{steps.research.output.research}}
        # First, try simple replacement for common patterns
        resolved = template
        
        # Pattern: {{steps.STEP_ID.output.FIELD}}
        pattern = r'\{\{steps\.(\w+)\.output\.(\w+)\}\}'
        for match in re.finditer(pattern, template):
            step_id, field = match.groups()
            if step_id in context.step_results:
                output = context.step_results[step_id].output
                if isinstance(output, dict) and field in output:
                    value = output[field]
                    if isinstance(value, (dict, list)):
                        value = yaml.dump(value, default_flow_style=False)
                    resolved = resolved.replace(match.group(0), str(value))
                elif isinstance(output, dict):
                    # Try to get any available content
                    value = output.get(field, output.get('response', str(output)))
                    resolved = resolved.replace(match.group(0), str(value))
        
        # Pattern: {{steps.STEP_ID.output}} (entire output)
        pattern = r'\{\{steps\.(\w+)\.output\}\}'
        for match in re.finditer(pattern, resolved):
            step_id = match.group(1)
            if step_id in context.step_results:
                output = context.step_results[step_id].output
                if isinstance(output, dict):
                    value = yaml.dump(output, default_flow_style=False)
                else:
                    value = str(output)
                resolved = resolved.replace(match.group(0), value)
        
        # Pattern: {{input.FIELD}}
        pattern = r'\{\{input\.(\w+)\}\}'
        for match in re.finditer(pattern, resolved):
            field = match.group(1)
            if field in input_data:
                value = input_data[field]
                if isinstance(value, (dict, list)):
                    value = yaml.dump(value, default_flow_style=False)
                resolved = resolved.replace(match.group(0), str(value))
        
        return resolved


template_engine = TemplateEngine()

# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class Executor:
    """Executes agent calls and chains."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=180.0)
        self.config = registry.get_config()
    
    async def execute_step(
        self, 
        step: dict, 
        context: ExecutionContext,
        input_data: dict
    ) -> StepResult:
        """Execute a single step."""
        
        step_id = step.get("id") or step.get("step_id") or str(uuid4())[:8]
        agent_name = step.get("agent")
        action_name = step.get("action")
        
        start_time = datetime.utcnow()
        
        # Get configurations
        agent = registry.get_agent(agent_name)
        action = registry.get_action(agent_name, action_name)
        
        if not agent or not action:
            return StepResult(
                step_id=step_id,
                agent=agent_name,
                action=action_name,
                status=ExecutionStatus.FAILED,
                error=f"Unknown agent/action: {agent_name}/{action_name}",
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
        
        # Build URL
        endpoint = action["endpoint"]
        base_url = agent["connection"]["url"]
        
        # Handle path parameters
        if "{" in endpoint:
            params = step.get("params", {})
            for key, value in params.items():
                endpoint = endpoint.replace(f"{{{key}}}", str(value))
        
        url = f"{base_url}{endpoint}"
        method = action.get("method", "POST")
        timeout = (step.get("options", {}).get("timeout_ms") or 
                  action.get("timeout_ms") or 
                  self.config.get("default_timeout_ms", 60000)) / 1000
        
        # Build request body
        params = step.get("params", {}).copy()
        
        # Resolve input template if present
        if "input_template" in step:
            resolved = template_engine.resolve(step["input_template"], context, input_data)
            params["message"] = resolved
        
        # Make request with retries
        max_retries = self.config.get("retry_attempts", 2)
        retry_delay = self.config.get("retry_delay_ms", 1000) / 1000
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if method == "GET":
                    response = await self.client.get(url, params=params, timeout=timeout)
                else:
                    response = await self.client.post(url, json=params, timeout=timeout)
                
                response.raise_for_status()
                result = response.json()
                
                # Extract cost if present
                cost = result.pop("_cost", result.pop("total_cost", 0))
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                return StepResult(
                    step_id=step_id,
                    agent=agent_name,
                    action=action_name,
                    status=ExecutionStatus.COMPLETED,
                    output=result,
                    cost=cost,
                    duration_ms=duration_ms,
                    retries=attempt
                )
                
            except httpx.TimeoutException as e:
                last_error = f"Timeout after {timeout}s"
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            except Exception as e:
                last_error = str(e)
            
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
        
        # All retries failed
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return StepResult(
            step_id=step_id,
            agent=agent_name,
            action=action_name,
            status=ExecutionStatus.FAILED,
            error=last_error,
            duration_ms=duration_ms,
            retries=max_retries
        )
    
    async def execute_parallel(
        self,
        substeps: List[dict],
        context: ExecutionContext,
        input_data: dict
    ) -> Dict[str, StepResult]:
        """Execute multiple steps in parallel."""
        
        tasks = [self.execute_step(step, context, input_data) for step in substeps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for i, step in enumerate(substeps):
            step_id = step.get("id") or step.get("step_id") or f"parallel_{i}"
            
            if isinstance(results[i], Exception):
                output[step_id] = StepResult(
                    step_id=step_id,
                    agent=step.get("agent", "unknown"),
                    action=step.get("action", "unknown"),
                    status=ExecutionStatus.FAILED,
                    error=str(results[i])
                )
            else:
                output[step_id] = results[i]
            
            context.set_step_result(output[step_id])
        
        return output
    
    async def execute_chain(
        self,
        chain_def: dict,
        input_data: dict,
        context: ExecutionContext
    ) -> dict:
        """Execute a chain of steps."""
        
        steps = chain_def.get("steps", [])
        
        for step in steps:
            # Check condition
            if not self._check_condition(step, context):
                continue
            
            # Handle parallel substeps
            if step.get("type") == "parallel":
                substeps = step.get("substeps", [])
                parallel_results = await self.execute_parallel(substeps, context, input_data)
                
                # Store parallel results as nested
                context.set_step_result(StepResult(
                    step_id=step.get("id", "parallel"),
                    agent="parallel",
                    action="execute",
                    status=ExecutionStatus.COMPLETED,
                    output={k: v.output for k, v in parallel_results.items()}
                ))
            else:
                result = await self.execute_step(step, context, input_data)
                context.set_step_result(result)
                
                # Check if we should fail fast
                if result.status == ExecutionStatus.FAILED:
                    fail_fast = chain_def.get("options", {}).get("fail_fast", True)
                    if fail_fast:
                        context.status = ExecutionStatus.FAILED
                        break
        
        # Determine final status
        failed_steps = [r for r in context.step_results.values() if r.status == ExecutionStatus.FAILED]
        if failed_steps:
            context.status = ExecutionStatus.PARTIAL if len(failed_steps) < len(steps) else ExecutionStatus.FAILED
        else:
            context.status = ExecutionStatus.COMPLETED
        
        # Format output using template if provided
        output = context.to_dict()
        if "output_template" in chain_def:
            output["formatted_output"] = template_engine.resolve(
                chain_def["output_template"], 
                context, 
                input_data
            )
        
        return output
    
    def _check_condition(self, step: dict, context: ExecutionContext) -> bool:
        """Check if step condition is met."""
        condition = step.get("condition")
        if not condition:
            return True
        
        field_path = condition["field"].split(".")
        value = None
        
        # Navigate to value
        if field_path[0] == "steps":
            step_id = field_path[1]
            if step_id in context.step_results:
                result = context.step_results[step_id]
                value = result.output
                for key in field_path[2:]:
                    if isinstance(value, dict):
                        value = value.get(key)
        elif field_path[0] == "input":
            # Would need input_data passed in
            pass
        
        # Evaluate
        operator = condition["operator"]
        target = condition["value"]
        
        if operator == "eq":
            return value == target
        elif operator == "ne":
            return value != target
        elif operator == "gt":
            return value > target
        elif operator == "lt":
            return value < target
        elif operator == "contains":
            return target in value if value else False
        elif operator == "exists":
            return value is not None
        
        return False
    
    async def log_event(self, event_type: str, data: dict):
        """Log event to Event Bus."""
        try:
            await self.client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "ATLAS",
                    "data": data
                },
                timeout=2.0
            )
        except:
            pass


executor = Executor()

# ═══════════════════════════════════════════════════════════════════════════════
# API MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Step(BaseModel):
    id: Optional[str] = None
    step_id: Optional[str] = None
    agent: str
    action: str
    params: Dict[str, Any] = {}
    input_template: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class ParallelStep(BaseModel):
    id: Optional[str] = None
    type: str = "parallel"
    substeps: List[Step]

class Intent(BaseModel):
    intent_id: Optional[str] = None
    source: str = "api"
    type: str = "single"  # single, chain
    chain_name: Optional[str] = None  # For pre-defined chains
    steps: Optional[List[Dict[str, Any]]] = None  # For ad-hoc chains
    input: Dict[str, Any] = {}
    options: Optional[Dict[str, Any]] = None

class QuickRequest(BaseModel):
    message: str
    source: str = "api"
    context: Dict[str, Any] = {}

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ATLAS Orchestration Engine",
    description="Programmatic orchestration for complex chains and parallel execution",
    version="2.0.0"
)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & INFO
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "agent": "ATLAS",
        "implementation": "fastapi",
        "version": "2.0.0",
        "registry_loaded": registry._loaded_at.isoformat() if registry._loaded_at else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/agents")
async def list_agents():
    """List available agents."""
    return {
        "agents": registry.list_agents(),
        "count": len(registry.list_agents())
    }

@app.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get agent details."""
    agent = registry.get_agent(agent_name)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    return agent

@app.get("/chains")
async def list_chains():
    """List available chains."""
    return {
        "chains": registry.list_chains(),
        "count": len(registry.list_chains())
    }

@app.get("/chains/{chain_name}")
async def get_chain(chain_name: str):
    """Get chain definition."""
    chain = registry.get_chain(chain_name)
    if not chain:
        raise HTTPException(404, f"Chain '{chain_name}' not found")
    return chain

# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/execute")
async def execute_intent(intent: Intent, background_tasks: BackgroundTasks):
    """
    Execute an orchestration intent.
    
    Supports:
    - Single agent calls
    - Pre-defined chains (by name)
    - Ad-hoc chains (custom steps)
    """
    intent_id = intent.intent_id or str(uuid4())
    context = ExecutionContext(intent_id=intent_id, source=intent.source)
    
    # Log start
    await executor.log_event("orchestration_started", {
        "intent_id": intent_id,
        "type": intent.type,
        "chain_name": intent.chain_name
    })
    
    try:
        if intent.chain_name:
            # Execute pre-defined chain
            chain_def = registry.get_chain(intent.chain_name)
            if not chain_def:
                raise HTTPException(404, f"Chain '{intent.chain_name}' not found")
            
            result = await executor.execute_chain(chain_def, intent.input, context)
            
        elif intent.type == "single" and intent.steps:
            # Execute single step
            step = intent.steps[0]
            step_result = await executor.execute_step(step, context, intent.input)
            context.set_step_result(step_result)
            context.status = step_result.status
            result = context.to_dict()
            
        elif intent.steps:
            # Execute ad-hoc chain
            chain_def = {"steps": intent.steps, "options": intent.options or {}}
            result = await executor.execute_chain(chain_def, intent.input, context)
            
        else:
            raise HTTPException(400, "Intent must have chain_name or steps")
        
        # Log completion
        background_tasks.add_task(
            executor.log_event,
            "orchestration_completed",
            {
                "intent_id": intent_id,
                "status": context.status.value,
                "duration_ms": context.duration_ms,
                "total_cost": context.total_cost
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        context.status = ExecutionStatus.FAILED
        context.add_error("executor", str(e))
        
        background_tasks.add_task(
            executor.log_event,
            "orchestration_failed",
            {"intent_id": intent_id, "error": str(e)}
        )
        
        return context.to_dict()

# ─────────────────────────────────────────────────────────────────────────────
# QUICK ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/quick/research-and-plan")
async def quick_research_and_plan(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Research something, then create action plan."""
    intent = Intent(
        source=request.source,
        chain_name="research-and-plan",
        input={"topic": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/validate-and-decide")
async def quick_validate_and_decide(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Validate assumption, then decide next steps."""
    intent = Intent(
        source=request.source,
        chain_name="validate-and-decide",
        input={"assumption": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/comprehensive-analysis")
async def quick_comprehensive_analysis(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Full market analysis with parallel research."""
    intent = Intent(
        source=request.source,
        chain_name="comprehensive-market-analysis",
        input={"market": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/weekly-planning")
async def quick_weekly_planning(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Weekly planning session."""
    intent = Intent(
        source=request.source,
        chain_name="weekly-planning",
        input=request.context
    )
    return await execute_intent(intent, background_tasks)

@app.post("/quick/fear-to-action")
async def quick_fear_to_action(request: QuickRequest, background_tasks: BackgroundTasks):
    """Quick: Transform fear into action."""
    intent = Intent(
        source=request.source,
        chain_name="fear-to-action",
        input={"situation": request.message, **request.context}
    )
    return await execute_intent(intent, background_tasks)

# ─────────────────────────────────────────────────────────────────────────────
# RELOAD
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/reload")
async def reload_registry():
    """Force reload of agent registry."""
    registry.load(force=True)
    return {
        "reloaded": True,
        "timestamp": datetime.utcnow().isoformat(),
        "agents": len(registry.list_agents()),
        "chains": len(registry.list_chains())
    }

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    registry.load()
    await executor.log_event("agent_started", {
        "agent": "ATLAS",
        "implementation": "fastapi",
        "version": "2.0.0"
    })

