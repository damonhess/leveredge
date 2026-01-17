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
from collections import defaultdict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import jinja2

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SENTINEL_URL = os.getenv("SENTINEL_URL", "http://sentinel:8019")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
UNIFIED_MEMORY_URL = os.getenv("UNIFIED_MEMORY_URL", "http://unified-memory:8021")

# Parallel execution limits
DEFAULT_CONCURRENCY = int(os.getenv("DEFAULT_CONCURRENCY", "5"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "10"))
MIN_CONCURRENCY = 1

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


class BatchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some succeeded, some failed
    FAILED = "failed"    # All failed
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH STORAGE (In-Memory)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BatchTask:
    """A single task within a batch."""
    task_id: str
    chain: str
    input: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cost: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_ms(self) -> Optional[int]:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "chain": self.chain,
            "input": self.input,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "cost": round(self.cost, 6),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms
        }


@dataclass
class Batch:
    """A batch of parallel tasks."""
    batch_id: str
    tasks: List[BatchTask]
    concurrency: int
    callback_url: Optional[str] = None
    source: str = "api"
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_cost: float = 0.0

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def completed_count(self) -> int:
        return len([t for t in self.tasks if t.status == TaskStatus.COMPLETED])

    @property
    def failed_count(self) -> int:
        return len([t for t in self.tasks if t.status == TaskStatus.FAILED])

    @property
    def pending_count(self) -> int:
        return len([t for t in self.tasks if t.status == TaskStatus.PENDING])

    @property
    def running_count(self) -> int:
        return len([t for t in self.tasks if t.status == TaskStatus.RUNNING])

    @property
    def progress_percent(self) -> float:
        finished = self.completed_count + self.failed_count
        return (finished / self.total_tasks * 100) if self.total_tasks > 0 else 0

    @property
    def duration_ms(self) -> Optional[int]:
        if self.started_at:
            end = self.completed_at or datetime.utcnow()
            return int((end - self.started_at).total_seconds() * 1000)
        return None

    def to_status_dict(self) -> dict:
        """Lightweight status dict for progress checks."""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "total_tasks": self.total_tasks,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "pending": self.pending_count,
            "running": self.running_count,
            "progress_percent": round(self.progress_percent, 1),
            "total_cost": round(self.total_cost, 6),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms
        }

    def to_results_dict(self) -> dict:
        """Full results dict including all task outputs."""
        results = []
        errors = []

        for task in self.tasks:
            if task.status == TaskStatus.COMPLETED:
                results.append({
                    "task_id": task.task_id,
                    "chain": task.chain,
                    "input": task.input,
                    "result": task.result,
                    "cost": task.cost,
                    "duration_ms": task.duration_ms
                })
            elif task.status == TaskStatus.FAILED:
                errors.append({
                    "task_id": task.task_id,
                    "chain": task.chain,
                    "input": task.input,
                    "error": task.error,
                    "duration_ms": task.duration_ms
                })

        return {
            **self.to_status_dict(),
            "results": results,
            "errors": errors,
            "tasks": [t.to_dict() for t in self.tasks]
        }


class BatchStore:
    """In-memory store for batch executions."""

    def __init__(self, max_batches: int = 100):
        self._batches: Dict[str, Batch] = {}
        self._max_batches = max_batches
        self._lock = asyncio.Lock()

    async def create(self, batch: Batch) -> None:
        async with self._lock:
            # Clean up old batches if at limit
            if len(self._batches) >= self._max_batches:
                oldest_id = min(
                    self._batches.keys(),
                    key=lambda k: self._batches[k].created_at
                )
                del self._batches[oldest_id]

            self._batches[batch.batch_id] = batch

    async def get(self, batch_id: str) -> Optional[Batch]:
        return self._batches.get(batch_id)

    async def update(self, batch: Batch) -> None:
        async with self._lock:
            self._batches[batch.batch_id] = batch

    async def list_active(self) -> List[Batch]:
        return [
            b for b in self._batches.values()
            if b.status in (BatchStatus.PENDING, BatchStatus.RUNNING)
        ]

    async def list_all(self, limit: int = 20) -> List[Batch]:
        batches = sorted(
            self._batches.values(),
            key=lambda b: b.created_at,
            reverse=True
        )
        return batches[:limit]


batch_store = BatchStore()


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
        
        # FIX: Resolve templates in params values (e.g., {{input.topic}})
        for key, value in list(params.items()):
            if isinstance(value, str) and "{{" in value:
                params[key] = template_engine.resolve(value, context, input_data)
        
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
batch_executor = None  # Initialized in startup


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


# ─────────────────────────────────────────────────────────────────────────────
# PARALLEL EXECUTION MODELS
# ─────────────────────────────────────────────────────────────────────────────

class BatchTaskInput(BaseModel):
    """A single task within a batch request."""
    chain: str
    input: Dict[str, Any]
    task_id: Optional[str] = None  # Auto-generated if not provided


class ParallelExecutionRequest(BaseModel):
    """Request for parallel batch execution."""
    tasks: List[BatchTaskInput]
    concurrency: int = Field(default=DEFAULT_CONCURRENCY, ge=MIN_CONCURRENCY, le=MAX_CONCURRENCY)
    callback_url: Optional[str] = None
    source: str = "api"
    batch_id: Optional[str] = None  # Auto-generated if not provided


class ParallelExecutionResponse(BaseModel):
    """Response for parallel batch execution."""
    batch_id: str
    status: str
    total_tasks: int
    concurrency: int
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class BatchExecutor:
    """Executes batches of tasks with concurrency control."""

    def __init__(self, executor: "Executor"):
        self.executor = executor
        self.client = httpx.AsyncClient(timeout=180.0)

    async def execute_batch(self, batch: Batch) -> None:
        """Execute all tasks in a batch with concurrency control."""
        batch.status = BatchStatus.RUNNING
        batch.started_at = datetime.utcnow()
        await batch_store.update(batch)

        # Emit batch started event
        await self.executor.log_event("batch.started", {
            "batch_id": batch.batch_id,
            "total_tasks": batch.total_tasks,
            "concurrency": batch.concurrency
        })

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(batch.concurrency)

        async def execute_with_semaphore(task: BatchTask) -> None:
            async with semaphore:
                await self._execute_single_task(batch, task)

        # Execute all tasks with concurrency limit
        await asyncio.gather(
            *[execute_with_semaphore(task) for task in batch.tasks],
            return_exceptions=True
        )

        # Determine final status
        batch.total_cost = sum(t.cost for t in batch.tasks)
        batch.completed_at = datetime.utcnow()

        if batch.failed_count == 0:
            batch.status = BatchStatus.COMPLETED
        elif batch.completed_count == 0:
            batch.status = BatchStatus.FAILED
        else:
            batch.status = BatchStatus.PARTIAL

        await batch_store.update(batch)

        # Emit batch completed event
        await self.executor.log_event("batch.completed", {
            "batch_id": batch.batch_id,
            "status": batch.status.value,
            "completed": batch.completed_count,
            "failed": batch.failed_count,
            "total_cost": batch.total_cost,
            "duration_ms": batch.duration_ms
        })

        # Store results in Unified Memory
        await self._store_in_unified_memory(batch)

        # Notify HERMES on completion
        await self._notify_completion(batch)

        # Call webhook callback if provided
        if batch.callback_url:
            await self._call_callback(batch)

    async def _execute_single_task(self, batch: Batch, task: BatchTask) -> None:
        """Execute a single task within the batch."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        await batch_store.update(batch)

        # Emit task started event
        await self.executor.log_event("task.started", {
            "batch_id": batch.batch_id,
            "task_id": task.task_id,
            "chain": task.chain
        })

        try:
            # Get chain definition
            chain_def = registry.get_chain(task.chain)
            if not chain_def:
                raise ValueError(f"Chain '{task.chain}' not found")

            # Create execution context
            context = ExecutionContext(
                intent_id=task.task_id,
                source=batch.source
            )

            # Execute the chain
            result = await self.executor.execute_chain(chain_def, task.input, context)

            # Mark task complete
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.cost = context.total_cost
            task.completed_at = datetime.utcnow()

            # Emit task completed event
            await self.executor.log_event("task.completed", {
                "batch_id": batch.batch_id,
                "task_id": task.task_id,
                "chain": task.chain,
                "cost": task.cost,
                "duration_ms": task.duration_ms
            })

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            # Emit task failed event
            await self.executor.log_event("task.failed", {
                "batch_id": batch.batch_id,
                "task_id": task.task_id,
                "chain": task.chain,
                "error": str(e)
            })

        await batch_store.update(batch)

    async def _store_in_unified_memory(self, batch: Batch) -> None:
        """Store batch results in Unified Memory."""
        try:
            await self.client.post(
                f"{UNIFIED_MEMORY_URL}/store",
                json={
                    "type": "batch_result",
                    "batch_id": batch.batch_id,
                    "status": batch.status.value,
                    "results": batch.to_results_dict(),
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
        except Exception:
            pass  # Non-critical, don't fail the batch

    async def _notify_completion(self, batch: Batch) -> None:
        """Notify HERMES of batch completion."""
        try:
            status_emoji = {
                BatchStatus.COMPLETED: "✅",
                BatchStatus.PARTIAL: "⚠️",
                BatchStatus.FAILED: "❌"
            }.get(batch.status, "📊")

            message = (
                f"{status_emoji} Batch {batch.batch_id[:8]} complete\n"
                f"Status: {batch.status.value}\n"
                f"Tasks: {batch.completed_count}/{batch.total_tasks} succeeded\n"
                f"Cost: ${batch.total_cost:.4f}\n"
                f"Duration: {batch.duration_ms/1000:.1f}s"
            )

            await self.client.post(
                f"{HERMES_URL}/notify",
                json={
                    "channel": "event_bus",
                    "message": message,
                    "priority": "high" if batch.failed_count > 0 else "normal"
                },
                timeout=5.0
            )
        except Exception:
            pass  # Non-critical

    async def _call_callback(self, batch: Batch) -> None:
        """Call the webhook callback URL."""
        try:
            await self.client.post(
                batch.callback_url,
                json=batch.to_results_dict(),
                timeout=30.0
            )
        except Exception as e:
            await self.executor.log_event("batch.callback_failed", {
                "batch_id": batch.batch_id,
                "callback_url": batch.callback_url,
                "error": str(e)
            })


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ATLAS Orchestration Engine",
    description="Programmatic orchestration for complex chains and parallel batch execution",
    version="2.1.0"
)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & INFO
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    active_batches = await batch_store.list_active()
    return {
        "status": "healthy",
        "agent": "ATLAS",
        "implementation": "fastapi",
        "version": "2.1.0",
        "capabilities": ["chains", "parallel_batch"],
        "active_batches": len(active_batches),
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
# PARALLEL BATCH EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/execute-parallel", response_model=ParallelExecutionResponse)
async def execute_parallel(
    request: ParallelExecutionRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute multiple chains in parallel with concurrency control.

    Returns immediately with batch_id for tracking. Use /batch/{batch_id}/status
    to check progress and /batch/{batch_id}/results to get outputs.

    Events emitted:
    - batch.started: When batch begins execution
    - task.started: When each task begins
    - task.completed: When each task succeeds
    - task.failed: When each task fails
    - batch.completed: When batch finishes

    Example request:
    ```json
    {
        "tasks": [
            {"chain": "research-and-plan", "input": {"topic": "AI agents"}},
            {"chain": "research-and-plan", "input": {"topic": "MCP servers"}}
        ],
        "concurrency": 5
    }
    ```
    """
    global batch_executor

    # Validate chains exist
    for task_input in request.tasks:
        if not registry.get_chain(task_input.chain):
            raise HTTPException(404, f"Chain '{task_input.chain}' not found")

    # Create batch
    batch_id = request.batch_id or str(uuid4())
    tasks = [
        BatchTask(
            task_id=t.task_id or f"{batch_id[:8]}-{i}",
            chain=t.chain,
            input=t.input
        )
        for i, t in enumerate(request.tasks)
    ]

    batch = Batch(
        batch_id=batch_id,
        tasks=tasks,
        concurrency=min(request.concurrency, MAX_CONCURRENCY),
        callback_url=request.callback_url,
        source=request.source
    )

    await batch_store.create(batch)

    # Execute in background
    background_tasks.add_task(batch_executor.execute_batch, batch)

    return ParallelExecutionResponse(
        batch_id=batch_id,
        status="accepted",
        total_tasks=len(tasks),
        concurrency=batch.concurrency,
        message=f"Batch queued for execution. Track at /batch/{batch_id}/status"
    )


@app.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """
    Get status of a parallel batch execution.

    Returns progress including:
    - Overall batch status
    - Task counts (completed, failed, pending, running)
    - Progress percentage
    - Total cost so far
    - Duration

    Poll this endpoint to track progress of long-running batches.
    """
    batch = await batch_store.get(batch_id)
    if not batch:
        raise HTTPException(404, f"Batch '{batch_id}' not found")

    return batch.to_status_dict()


@app.get("/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """
    Get full results of a parallel batch execution.

    Returns:
    - Status information
    - Array of successful results with outputs
    - Array of failures with error messages
    - All task details

    Best called after batch reaches completed/partial/failed status.
    """
    batch = await batch_store.get(batch_id)
    if not batch:
        raise HTTPException(404, f"Batch '{batch_id}' not found")

    return batch.to_results_dict()


@app.get("/batches")
async def list_batches(limit: int = 20, active_only: bool = False):
    """
    List batch executions.

    - active_only=true: Only running/pending batches
    - active_only=false: All recent batches
    """
    if active_only:
        batches = await batch_store.list_active()
    else:
        batches = await batch_store.list_all(limit=limit)

    return {
        "batches": [b.to_status_dict() for b in batches],
        "count": len(batches)
    }


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
    global batch_executor

    registry.load()
    batch_executor = BatchExecutor(executor)

    await executor.log_event("agent_started", {
        "agent": "ATLAS",
        "implementation": "fastapi",
        "version": "2.1.0",
        "capabilities": ["chains", "parallel_batch"]
    })
