#!/usr/bin/env python3
"""
ATLAS - The Titan Who Holds Up The Heavens

Port: 8007

The orchestration engine for LeverEdge. Executes chains, coordinates
agents, handles parallel batch processing, and tracks costs.

CAPABILITIES:
- Chain execution (sequential and parallel steps)
- Multi-agent coordination
- Parallel batch processing with concurrency control
- Cost tracking per execution
- Real-time status updates via Event Bus
- Graceful error handling and rollback
"""

import asyncio
import os
import sys
import json
import yaml
import uuid
import re
from datetime import datetime, date
from typing import Dict, Optional, List, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import traceback

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add shared modules
sys.path.append('/opt/leveredge/control-plane/shared')
try:
    from cost_tracker import CostTracker, log_llm_usage
except ImportError:
    # Fallback if cost_tracker not available
    class CostTracker:
        def __init__(self, agent): pass
        async def log(self, *args, **kwargs): pass
    async def log_llm_usage(*args, **kwargs): pass

# ===============================================================================
# CONFIGURATION
# ===============================================================================

ATLAS_PORT = 8007
REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8014")

# Launch tracking
LAUNCH_DATE = date(2026, 3, 1)

# Execution limits
MAX_CHAIN_DEPTH = 10
MAX_PARALLEL_TASKS = 20
DEFAULT_TIMEOUT = 180  # seconds
MAX_BATCH_SIZE = 100

# ===============================================================================
# ENUMS AND DATA CLASSES
# ===============================================================================

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Some steps succeeded, some failed


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    step_id: str
    agent: str
    action: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    cost: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ExecutionResult:
    intent_id: str
    chain_name: Optional[str]
    status: ExecutionStatus
    step_results: List[StepResult] = field(default_factory=list)
    final_output: Any = None
    total_cost: float = 0.0
    total_duration_ms: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BatchTask:
    task_id: str
    chain_name: Optional[str]
    steps: Optional[List[dict]]
    input: dict
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[ExecutionResult] = None


@dataclass
class BatchExecution:
    batch_id: str
    tasks: List[BatchTask]
    concurrency: int
    status: ExecutionStatus = ExecutionStatus.PENDING
    completed: int = 0
    failed: int = 0
    total_cost: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    callback_url: Optional[str] = None


# In-memory storage for batch executions
batch_store: Dict[str, BatchExecution] = {}

# ===============================================================================
# REGISTRY LOADER
# ===============================================================================

class RegistryLoader:
    """Loads and caches the agent registry."""

    def __init__(self):
        self._registry = None
        self._last_loaded = None
        self._cache_ttl = 60  # Reload every 60 seconds

    def load(self) -> dict:
        """Load registry, using cache if fresh."""
        now = datetime.utcnow()

        if self._registry and self._last_loaded:
            age = (now - self._last_loaded).total_seconds()
            if age < self._cache_ttl:
                return self._registry

        try:
            with open(REGISTRY_PATH) as f:
                self._registry = yaml.safe_load(f)
                self._last_loaded = now
                return self._registry
        except Exception as e:
            if self._registry:
                return self._registry  # Return stale cache
            raise RuntimeError(f"Failed to load registry: {e}")

    def get_chain(self, name: str) -> Optional[dict]:
        """Get chain definition by name."""
        registry = self.load()
        return registry.get("chains", {}).get(name)

    def get_agent(self, name: str) -> Optional[dict]:
        """Get agent definition by name."""
        registry = self.load()
        return registry.get("agents", {}).get(name.lower())

    def list_chains(self) -> List[dict]:
        """List all available chains."""
        registry = self.load()
        chains = registry.get("chains", {})
        return [
            {
                "name": name,
                "description": chain.get("description", ""),
                "complexity": chain.get("complexity", "simple"),
                "estimated_cost": chain.get("estimated_cost", 0),
                "estimated_time_ms": chain.get("estimated_time_ms", 0)
            }
            for name, chain in chains.items()
        ]

    def list_agents(self) -> List[dict]:
        """List all available agents."""
        registry = self.load()
        agents = registry.get("agents", {})
        return [
            {
                "name": name,
                "description": agent.get("description", ""),
                "category": agent.get("category", ""),
                "llm_powered": agent.get("llm_powered", False),
                "url": agent.get("connection", {}).get("url", ""),
                "actions": list(agent.get("actions", {}).keys())
            }
            for name, agent in agents.items()
        ]


registry = RegistryLoader()

# ===============================================================================
# TEMPLATE ENGINE
# ===============================================================================

class TemplateEngine:
    """Simple template engine for chain step inputs."""

    @staticmethod
    def render(template: str, context: dict) -> str:
        """Render a template string with context variables."""
        if not template:
            return template

        result = template

        # Handle {{variable}} syntax
        pattern = r'\{\{([^}]+)\}\}'

        def replace_var(match):
            path = match.group(1).strip()
            value = TemplateEngine._resolve_path(path, context)
            if value is None:
                return match.group(0)  # Keep original if not found
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value)

        result = re.sub(pattern, replace_var, result)
        return result

    @staticmethod
    def render_dict(obj: Any, context: dict) -> Any:
        """Recursively render templates in a dict/list structure."""
        if isinstance(obj, str):
            return TemplateEngine.render(obj, context)
        elif isinstance(obj, dict):
            return {k: TemplateEngine.render_dict(v, context) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [TemplateEngine.render_dict(item, context) for item in obj]
        return obj

    @staticmethod
    def _resolve_path(path: str, context: dict) -> Any:
        """Resolve a dotted path like 'steps.research.output.data'."""
        parts = path.split('.')
        current = context

        for part in parts:
            if isinstance(current, dict):
                # Handle array index like 'items[0]'
                if '[' in part:
                    key, idx = part.split('[')
                    idx = int(idx.rstrip(']'))
                    current = current.get(key, [])
                    if isinstance(current, list) and len(current) > idx:
                        current = current[idx]
                    else:
                        return None
                else:
                    current = current.get(part)
            else:
                return None

            if current is None:
                return None

        return current


# ===============================================================================
# AGENT CALLER
# ===============================================================================

class AgentCaller:
    """Handles calling individual agents."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)

    async def call(
        self,
        agent_name: str,
        action: str,
        params: dict,
        timeout: Optional[int] = None
    ) -> dict:
        """Call an agent action and return the result."""

        agent_config = registry.get_agent(agent_name)
        if not agent_config:
            raise ValueError(f"Agent '{agent_name}' not found in registry")

        action_config = agent_config.get("actions", {}).get(action)
        if not action_config:
            raise ValueError(f"Action '{action}' not found for agent '{agent_name}'")

        # Build URL - use localhost instead of container name
        base_url = agent_config["connection"]["url"]
        # Convert http://agent-name:port to http://localhost:port
        if "://" in base_url:
            parts = base_url.split("://")
            host_port = parts[1]
            if ":" in host_port:
                port = host_port.split(":")[1].split("/")[0]
                base_url = f"http://localhost:{port}"

        endpoint = action_config["endpoint"]

        # Handle path parameters like /framework/{name}
        for key, value in params.items():
            if f"{{{key}}}" in endpoint:
                endpoint = endpoint.replace(f"{{{key}}}", str(value))

        url = f"{base_url}{endpoint}"
        method = action_config.get("method", "POST").upper()

        # Determine timeout
        action_timeout = timeout or action_config.get("timeout_ms", 60000) / 1000

        try:
            if method == "GET":
                response = await self.client.get(url, params=params, timeout=action_timeout)
            else:
                response = await self.client.post(url, json=params, timeout=action_timeout)

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise TimeoutError(f"Agent '{agent_name}/{action}' timed out after {action_timeout}s")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Agent '{agent_name}/{action}' returned {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Failed to call '{agent_name}/{action}': {str(e)}")

    async def close(self):
        await self.client.aclose()


agent_caller = AgentCaller()

# ===============================================================================
# CHAIN EXECUTOR
# ===============================================================================

class ChainExecutor:
    """Executes chains with step-by-step processing."""

    def __init__(self):
        self.template = TemplateEngine()

    async def execute(
        self,
        chain_name: Optional[str] = None,
        steps: Optional[List[dict]] = None,
        input_data: dict = None,
        options: dict = None
    ) -> ExecutionResult:
        """Execute a chain (by name or ad-hoc steps)."""

        intent_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        result = ExecutionResult(
            intent_id=intent_id,
            chain_name=chain_name,
            status=ExecutionStatus.RUNNING,
            started_at=started_at.isoformat()
        )

        try:
            # Get chain definition
            if chain_name:
                chain_def = registry.get_chain(chain_name)
                if not chain_def:
                    raise ValueError(f"Chain '{chain_name}' not found")
                steps = chain_def.get("steps", [])

            if not steps:
                raise ValueError("No steps provided")

            # Build execution context
            context = {
                "input": input_data or {},
                "steps": {},
                "options": options or {}
            }

            # Execute steps
            for step in steps:
                step_result = await self._execute_step(step, context)
                result.step_results.append(step_result)
                result.total_cost += step_result.cost

                # Store step output in context for subsequent steps
                context["steps"][step["id"]] = {
                    "output": step_result.output,
                    "status": step_result.status.value
                }

                # Check for failure
                if step_result.status == StepStatus.FAILED:
                    # Check if step is optional
                    if not step.get("optional", False):
                        result.status = ExecutionStatus.FAILED
                        result.error = f"Step '{step['id']}' failed: {step_result.error}"
                        break

            # Determine final status
            if result.status != ExecutionStatus.FAILED:
                failed_count = sum(1 for sr in result.step_results if sr.status == StepStatus.FAILED)
                if failed_count > 0:
                    result.status = ExecutionStatus.PARTIAL
                else:
                    result.status = ExecutionStatus.COMPLETED

            # Apply output template if defined
            chain_def = registry.get_chain(chain_name) if chain_name else {}
            output_template = chain_def.get("output_template") if chain_def else None
            if output_template:
                result.final_output = self.template.render(output_template, context)
            else:
                # Use last step's output
                if result.step_results:
                    result.final_output = result.step_results[-1].output

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            traceback.print_exc()

        finally:
            completed_at = datetime.utcnow()
            result.completed_at = completed_at.isoformat()
            result.total_duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Log to event bus
            await self._log_execution(result)

        return result

    async def _execute_step(self, step: dict, context: dict) -> StepResult:
        """Execute a single step."""

        step_id = step.get("id", str(uuid.uuid4()))
        started_at = datetime.utcnow()

        result = StepResult(
            step_id=step_id,
            agent=step.get("agent", ""),
            action=step.get("action", ""),
            status=StepStatus.RUNNING,
            started_at=started_at.isoformat()
        )

        try:
            # Check condition
            condition = step.get("condition")
            if condition and not self._evaluate_condition(condition, context):
                result.status = StepStatus.SKIPPED
                result.output = {"skipped": True, "reason": "Condition not met"}
                return result

            # Handle parallel substeps
            if step.get("type") == "parallel":
                result = await self._execute_parallel_substeps(step, context, result)
                return result

            # Build params from step definition
            params = {}

            # Add params from step config
            for param in step.get("params", {}):
                if isinstance(param, dict):
                    param_name = param.get("name")
                    param_value = param.get("value") or param.get("default")
                else:
                    continue
                if param_value:
                    params[param_name] = self.template.render_dict(param_value, context)

            # Handle input_template
            input_template = step.get("input_template")
            if input_template:
                rendered = self.template.render(input_template, context)
                # If the action expects a 'message' or specific param
                action_config = registry.get_agent(step["agent"])
                if action_config:
                    action_def = action_config.get("actions", {}).get(step["action"], {})
                    action_params = action_def.get("params", [])
                    # Find the first required string param
                    for p in action_params:
                        if p.get("required") and p.get("type") == "string":
                            params[p["name"]] = rendered
                            break
                    else:
                        params["message"] = rendered  # fallback

            # Direct params override
            if step.get("params") and isinstance(step["params"], dict):
                for k, v in step["params"].items():
                    params[k] = self.template.render_dict(v, context)

            # Call the agent
            output = await agent_caller.call(
                agent_name=step["agent"],
                action=step["action"],
                params=params,
                timeout=step.get("timeout_ms", None)
            )

            result.status = StepStatus.COMPLETED
            result.output = output

            # Extract cost if present
            if isinstance(output, dict):
                result.cost = output.get("cost", 0) or output.get("total_cost", 0) or 0

        except Exception as e:
            result.status = StepStatus.FAILED
            result.error = str(e)
            traceback.print_exc()

        finally:
            completed_at = datetime.utcnow()
            result.completed_at = completed_at.isoformat()
            result.duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        return result

    async def _execute_parallel_substeps(
        self,
        step: dict,
        context: dict,
        parent_result: StepResult
    ) -> StepResult:
        """Execute parallel substeps concurrently."""

        substeps = step.get("substeps", [])
        if not substeps:
            parent_result.status = StepStatus.COMPLETED
            parent_result.output = {}
            return parent_result

        # Create tasks for all substeps
        async def run_substep(substep):
            return await self._execute_step(substep, context)

        tasks = [run_substep(s) for s in substeps]
        substep_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        outputs = {}
        total_cost = 0
        all_completed = True

        for substep, result in zip(substeps, substep_results):
            substep_id = substep.get("id", "unknown")

            if isinstance(result, Exception):
                outputs[substep_id] = {"error": str(result)}
                all_completed = False
            elif isinstance(result, StepResult):
                outputs[substep_id] = {"output": result.output, "status": result.status.value}
                total_cost += result.cost
                if result.status == StepStatus.FAILED:
                    all_completed = False

        parent_result.output = outputs
        parent_result.cost = total_cost
        parent_result.status = StepStatus.COMPLETED if all_completed else StepStatus.FAILED

        # Store parallel results in context
        context["steps"][step["id"]] = outputs

        return parent_result

    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        """Evaluate a step condition."""
        field_path = condition.get("field", "")
        operator = condition.get("operator", "exists")
        expected = condition.get("value")

        actual = TemplateEngine._resolve_path(field_path, context)

        if operator == "exists":
            return actual is not None
        elif operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "contains":
            return expected in str(actual) if actual else False
        elif operator == "gt":
            return float(actual) > float(expected) if actual else False
        elif operator == "lt":
            return float(actual) < float(expected) if actual else False

        return True

    async def _log_execution(self, result: ExecutionResult):
        """Log execution to event bus."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{EVENT_BUS_URL}/publish",
                    json={
                        "event_type": "chain_execution_completed",
                        "source": "ATLAS",
                        "data": {
                            "intent_id": result.intent_id,
                            "chain_name": result.chain_name,
                            "status": result.status.value,
                            "total_cost": result.total_cost,
                            "duration_ms": result.total_duration_ms,
                            "step_count": len(result.step_results)
                        }
                    },
                    timeout=2.0
                )
        except:
            pass  # Don't fail execution due to logging failure


chain_executor = ChainExecutor()

# ===============================================================================
# BATCH EXECUTOR
# ===============================================================================

class BatchExecutor:
    """Handles parallel batch execution of multiple chains."""

    async def execute_batch(
        self,
        tasks: List[dict],
        concurrency: int = 5,
        callback_url: Optional[str] = None
    ) -> str:
        """Start a batch execution and return batch_id."""

        batch_id = str(uuid.uuid4())

        # Create batch tasks
        batch_tasks = [
            BatchTask(
                task_id=str(uuid.uuid4()),
                chain_name=t.get("chain") or t.get("chain_name"),
                steps=t.get("steps"),
                input=t.get("input", {})
            )
            for t in tasks[:MAX_BATCH_SIZE]
        ]

        batch = BatchExecution(
            batch_id=batch_id,
            tasks=batch_tasks,
            concurrency=min(concurrency, MAX_PARALLEL_TASKS),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow().isoformat(),
            callback_url=callback_url
        )

        batch_store[batch_id] = batch

        # Start background execution
        asyncio.create_task(self._run_batch(batch))

        return batch_id

    async def _run_batch(self, batch: BatchExecution):
        """Run batch tasks with concurrency control."""

        semaphore = asyncio.Semaphore(batch.concurrency)

        async def run_task(task: BatchTask):
            async with semaphore:
                task.status = ExecutionStatus.RUNNING
                try:
                    result = await chain_executor.execute(
                        chain_name=task.chain_name,
                        steps=task.steps,
                        input_data=task.input
                    )
                    task.result = result
                    task.status = result.status
                    batch.total_cost += result.total_cost

                    if result.status == ExecutionStatus.COMPLETED:
                        batch.completed += 1
                    else:
                        batch.failed += 1

                except Exception as e:
                    task.status = ExecutionStatus.FAILED
                    task.result = ExecutionResult(
                        intent_id=str(uuid.uuid4()),
                        chain_name=task.chain_name,
                        status=ExecutionStatus.FAILED,
                        error=str(e)
                    )
                    batch.failed += 1

        # Run all tasks
        await asyncio.gather(*[run_task(t) for t in batch.tasks])

        # Update batch status
        batch.completed_at = datetime.utcnow().isoformat()
        if batch.failed == 0:
            batch.status = ExecutionStatus.COMPLETED
        elif batch.completed == 0:
            batch.status = ExecutionStatus.FAILED
        else:
            batch.status = ExecutionStatus.PARTIAL

        # Call callback if provided
        if batch.callback_url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        batch.callback_url,
                        json={
                            "batch_id": batch.batch_id,
                            "status": batch.status.value,
                            "completed": batch.completed,
                            "failed": batch.failed,
                            "total_cost": batch.total_cost
                        },
                        timeout=10.0
                    )
            except:
                pass

        # Log completion
        await self._log_batch_completion(batch)

    async def _log_batch_completion(self, batch: BatchExecution):
        """Log batch completion to event bus."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{EVENT_BUS_URL}/publish",
                    json={
                        "event_type": "batch_execution_completed",
                        "source": "ATLAS",
                        "data": {
                            "batch_id": batch.batch_id,
                            "status": batch.status.value,
                            "completed": batch.completed,
                            "failed": batch.failed,
                            "total_tasks": len(batch.tasks),
                            "total_cost": batch.total_cost
                        }
                    },
                    timeout=2.0
                )
        except:
            pass

    def get_batch_status(self, batch_id: str) -> Optional[dict]:
        """Get batch execution status."""
        batch = batch_store.get(batch_id)
        if not batch:
            return None

        return {
            "batch_id": batch.batch_id,
            "status": batch.status.value,
            "completed": batch.completed,
            "failed": batch.failed,
            "pending": len(batch.tasks) - batch.completed - batch.failed,
            "running": sum(1 for t in batch.tasks if t.status == ExecutionStatus.RUNNING),
            "total_tasks": len(batch.tasks),
            "progress_percent": round((batch.completed + batch.failed) / len(batch.tasks) * 100, 1),
            "total_cost": batch.total_cost,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at
        }

    def get_batch_results(self, batch_id: str) -> Optional[dict]:
        """Get full batch results."""
        batch = batch_store.get(batch_id)
        if not batch:
            return None

        return {
            "batch_id": batch.batch_id,
            "status": batch.status.value,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "chain_name": t.chain_name,
                    "status": t.status.value,
                    "result": asdict(t.result) if t.result else None
                }
                for t in batch.tasks
            ],
            "total_cost": batch.total_cost,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at
        }

    def list_batches(self, limit: int = 20, active_only: bool = False) -> List[dict]:
        """List recent batch executions."""
        batches = list(batch_store.values())

        if active_only:
            batches = [b for b in batches if b.status == ExecutionStatus.RUNNING]

        # Sort by started_at descending
        batches.sort(key=lambda b: b.started_at or "", reverse=True)

        return [self.get_batch_status(b.batch_id) for b in batches[:limit]]


batch_executor = BatchExecutor()

# ===============================================================================
# PYDANTIC MODELS
# ===============================================================================

class ExecuteRequest(BaseModel):
    chain_name: Optional[str] = None
    steps: Optional[List[dict]] = None
    input: dict = Field(default_factory=dict)
    options: Optional[dict] = None


class BatchExecuteRequest(BaseModel):
    tasks: List[dict]
    concurrency: int = Field(default=5, ge=1, le=MAX_PARALLEL_TASKS)
    callback_url: Optional[str] = None


class DirectCallRequest(BaseModel):
    agent: str
    action: str
    params: dict = Field(default_factory=dict)

# ===============================================================================
# FASTAPI APPLICATION
# ===============================================================================

app = FastAPI(
    title="ATLAS - Orchestration Engine",
    description="The Titan who holds up the heavens. Chain execution and multi-agent coordination.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# HEALTH & STATUS
# -----------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    today = date.today()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "status": "healthy",
        "agent": "ATLAS",
        "role": "Orchestration Engine",
        "port": ATLAS_PORT,
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "days_to_launch": days_to_launch,
        "registry_loaded": registry._registry is not None,
        "active_batches": sum(1 for b in batch_store.values() if b.status == ExecutionStatus.RUNNING)
    }


@app.get("/status")
async def status():
    """Detailed status."""
    chains = registry.list_chains()
    agents = registry.list_agents()

    return {
        "atlas": {
            "status": "healthy",
            "version": "2.0.0",
            "uptime": "running"
        },
        "registry": {
            "chains_count": len(chains),
            "agents_count": len(agents),
            "last_loaded": registry._last_loaded.isoformat() if registry._last_loaded else None
        },
        "batches": {
            "active": sum(1 for b in batch_store.values() if b.status == ExecutionStatus.RUNNING),
            "total": len(batch_store)
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics."""
    active_batches = sum(1 for b in batch_store.values() if b.status == ExecutionStatus.RUNNING)
    total_batches = len(batch_store)
    completed_batches = sum(1 for b in batch_store.values() if b.status == ExecutionStatus.COMPLETED)

    return f"""# HELP atlas_active_batches Number of currently running batch executions
# TYPE atlas_active_batches gauge
atlas_active_batches {active_batches}

# HELP atlas_total_batches Total number of batch executions
# TYPE atlas_total_batches counter
atlas_total_batches {total_batches}

# HELP atlas_completed_batches Number of completed batch executions
# TYPE atlas_completed_batches counter
atlas_completed_batches {completed_batches}

# HELP atlas_chains_available Number of chains defined in registry
# TYPE atlas_chains_available gauge
atlas_chains_available {len(registry.list_chains())}

# HELP atlas_agents_available Number of agents defined in registry
# TYPE atlas_agents_available gauge
atlas_agents_available {len(registry.list_agents())}
"""

# -----------------------------------------------------------------------------
# CHAIN OPERATIONS
# -----------------------------------------------------------------------------

@app.get("/chains")
async def list_chains():
    """List all available chains."""
    chains = registry.list_chains()
    return {
        "chains": chains,
        "count": len(chains)
    }


@app.get("/chains/{chain_name}")
async def get_chain(chain_name: str):
    """Get chain definition."""
    chain = registry.get_chain(chain_name)
    if not chain:
        raise HTTPException(404, f"Chain '{chain_name}' not found")
    return {"chain": chain_name, "definition": chain}


@app.post("/execute")
async def execute_chain(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """Execute a chain."""

    if not request.chain_name and not request.steps:
        raise HTTPException(400, "Either chain_name or steps must be provided")

    result = await chain_executor.execute(
        chain_name=request.chain_name,
        steps=request.steps,
        input_data=request.input,
        options=request.options
    )

    return {
        "intent_id": result.intent_id,
        "status": result.status.value,
        "chain_name": result.chain_name,
        "step_results": [asdict(sr) for sr in result.step_results],
        "final_output": result.final_output,
        "total_cost": result.total_cost,
        "total_duration_ms": result.total_duration_ms,
        "error": result.error
    }

# -----------------------------------------------------------------------------
# BATCH OPERATIONS
# -----------------------------------------------------------------------------

@app.post("/execute-parallel")
async def execute_parallel(request: BatchExecuteRequest):
    """Execute multiple chains in parallel."""

    if not request.tasks:
        raise HTTPException(400, "No tasks provided")

    if len(request.tasks) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"Maximum {MAX_BATCH_SIZE} tasks per batch")

    batch_id = await batch_executor.execute_batch(
        tasks=request.tasks,
        concurrency=request.concurrency,
        callback_url=request.callback_url
    )

    return {
        "batch_id": batch_id,
        "status": "running",
        "total_tasks": len(request.tasks),
        "concurrency": request.concurrency,
        "message": f"Batch execution started. Use /batch/{batch_id}/status to check progress."
    }


@app.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get batch execution status."""
    status = batch_executor.get_batch_status(batch_id)
    if not status:
        raise HTTPException(404, f"Batch '{batch_id}' not found")
    return status


@app.get("/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Get full batch results."""
    results = batch_executor.get_batch_results(batch_id)
    if not results:
        raise HTTPException(404, f"Batch '{batch_id}' not found")
    return results


@app.get("/batches")
async def list_batches(limit: int = 20, active_only: bool = False):
    """List recent batch executions."""
    batches = batch_executor.list_batches(limit=limit, active_only=active_only)
    return {
        "batches": batches,
        "count": len(batches)
    }

# -----------------------------------------------------------------------------
# AGENT OPERATIONS
# -----------------------------------------------------------------------------

@app.get("/agents")
async def list_agents():
    """List all available agents."""
    agents = registry.list_agents()
    return {
        "agents": agents,
        "count": len(agents)
    }


@app.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get agent definition."""
    agent = registry.get_agent(agent_name)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    return {"agent": agent_name, "definition": agent}


@app.post("/call")
async def direct_call(request: DirectCallRequest):
    """Direct call to an agent (bypasses chain execution)."""
    try:
        result = await agent_caller.call(
            agent_name=request.agent,
            action=request.action,
            params=request.params
        )
        return {
            "agent": request.agent,
            "action": request.action,
            "result": result
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except TimeoutError as e:
        raise HTTPException(504, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))

# -----------------------------------------------------------------------------
# REGISTRY OPERATIONS
# -----------------------------------------------------------------------------

@app.post("/registry/reload")
async def reload_registry():
    """Force reload the registry."""
    registry._last_loaded = None  # Force reload
    registry.load()
    return {
        "status": "reloaded",
        "chains": len(registry.list_chains()),
        "agents": len(registry.list_agents()),
        "timestamp": datetime.utcnow().isoformat()
    }

# -----------------------------------------------------------------------------
# LIFECYCLE
# -----------------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    # Load registry
    registry.load()

    # Log startup
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": "agent_started",
                    "source": "ATLAS",
                    "data": {
                        "agent": "ATLAS",
                        "port": ATLAS_PORT,
                        "version": "2.0.0",
                        "chains": len(registry.list_chains()),
                        "agents": len(registry.list_agents())
                    }
                },
                timeout=2.0
            )
    except:
        pass

    print(f"ATLAS Orchestration Engine started on port {ATLAS_PORT}")
    print(f"   Chains: {len(registry.list_chains())}")
    print(f"   Agents: {len(registry.list_agents())}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    await agent_caller.close()

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=ATLAS_PORT)
