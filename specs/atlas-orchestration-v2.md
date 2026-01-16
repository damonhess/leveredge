# ATLAS Orchestration Engine V2

## Executive Summary

ATLAS becomes the central nervous system for all agent orchestration. It receives structured intents from any interface (ARIA, Telegram, CLI, API), executes single or chained agent calls, handles errors gracefully, tracks costs, and returns unified responses.

**Design Principles:**
- Zero LLM cost in ATLAS (rules-based execution only)
- Single responsibility: ATLAS orchestrates, agents specialize
- Interface-agnostic: works from any entry point
- Fault-tolerant: graceful degradation, retry logic
- Observable: full audit trail via Event Bus
- Extensible: add agents without changing ATLAS core

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTRY POINTS                              │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│    ARIA     │  Telegram   │    CLI      │    API      │  Cron   │
│  (Web/App)  │  (HERMES)   │  (Direct)   │  (Webhook)  │ (Timed) │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴────┬────┘
       │             │             │             │           │
       └─────────────┴─────────────┴─────────────┴───────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │         ATLAS            │
                    │   Orchestration Engine   │
                    │                          │
                    │  • Intent Validation     │
                    │  • Execution Planning    │
                    │  • Agent Dispatch        │
                    │  • Response Collection   │
                    │  • Error Handling        │
                    │  • Cost Aggregation      │
                    └────────────┬─────────────┘
                                 │
          ┌──────────┬──────────┼──────────┬──────────┐
          ▼          ▼          ▼          ▼          ▼
     ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
     │ SCHOLAR ││ CHIRON  ││ VARYS   ││ SCRIBE  ││  ...    │
     │Research ││ Strategy││ Project ││ Content ││ Future  │
     └─────────┘└─────────┘└─────────┘└─────────┘└─────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       EVENT BUS          │
                    │   (Audit & Monitoring)   │
                    └──────────────────────────┘
```

---

## Intent Schema

Every request to ATLAS uses a standardized intent object. Interfaces extract user intent into this format.

### Intent Object Structure

```typescript
interface Intent {
  // Metadata
  intent_id: string;          // UUID for tracking
  source: string;             // "aria" | "telegram" | "cli" | "api" | "cron"
  user_id?: string;           // For user-specific context
  timestamp: string;          // ISO 8601
  
  // Execution Plan
  type: "single" | "chain" | "parallel" | "conditional";
  steps: Step[];
  
  // Options
  options?: {
    timeout_ms?: number;      // Max execution time (default: 120000)
    retry_count?: number;     // Retries per step (default: 1)
    fail_fast?: boolean;      // Stop on first error (default: true)
    include_reasoning?: boolean; // Include agent reasoning in response
  };
  
  // Context
  context?: {
    conversation_id?: string;
    previous_messages?: Message[];
    user_preferences?: object;
    portfolio_context?: object;
    time_context?: object;
  };
  
  // Callback
  callback?: {
    type: "sync" | "webhook" | "event_bus";
    url?: string;             // For webhook callbacks
    format?: "full" | "summary" | "raw";
  };
}

interface Step {
  step_id: string;            // Unique within intent
  agent: string;              // "scholar" | "chiron" | "varys" | etc.
  action: string;             // Endpoint: "chat" | "deep-research" | "sprint-plan" | etc.
  
  params: {
    [key: string]: any;       // Action-specific parameters
  };
  
  // For chains: reference previous step outputs
  input_from?: string;        // step_id to pull input from
  input_template?: string;    // Template with {{STEP_ID.field}} placeholders
  
  // Conditional execution
  condition?: {
    field: string;            // e.g., "steps.step1.output.confidence"
    operator: "eq" | "ne" | "gt" | "lt" | "contains" | "exists";
    value: any;
  };
  
  // Step-specific options
  options?: {
    timeout_ms?: number;
    required?: boolean;       // If false, failure doesn't stop chain
    fallback_agent?: string;  // Try this agent if primary fails
  };
}
```

### Example Intents

#### Single Agent Call
```json
{
  "intent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "source": "aria",
  "timestamp": "2026-01-17T15:30:00Z",
  "type": "single",
  "steps": [
    {
      "step_id": "research",
      "agent": "scholar",
      "action": "deep-research",
      "params": {
        "question": "What are water utility compliance pain points?",
        "depth": "comprehensive"
      }
    }
  ]
}
```

#### Chain: Research → Plan
```json
{
  "intent_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "source": "aria",
  "timestamp": "2026-01-17T15:30:00Z",
  "type": "chain",
  "steps": [
    {
      "step_id": "research",
      "agent": "scholar",
      "action": "deep-research",
      "params": {
        "question": "Water utility compliance pain points and gaps"
      }
    },
    {
      "step_id": "plan",
      "agent": "chiron",
      "action": "sprint-plan",
      "input_from": "research",
      "input_template": "Based on this research:\n\n{{research.output.research}}\n\nCreate a sprint plan to address the top 3 pain points.",
      "params": {
        "time_available": "this week",
        "energy_level": "high"
      }
    }
  ],
  "options": {
    "timeout_ms": 180000,
    "include_reasoning": true
  }
}
```

#### Parallel: Multiple Research Streams
```json
{
  "intent_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "source": "aria",
  "timestamp": "2026-01-17T15:30:00Z",
  "type": "parallel",
  "steps": [
    {
      "step_id": "competitors",
      "agent": "scholar",
      "action": "competitors",
      "params": { "niche": "compliance automation" }
    },
    {
      "step_id": "market_size",
      "agent": "scholar",
      "action": "market-size",
      "params": { "market": "water utility compliance software" }
    },
    {
      "step_id": "pain_points",
      "agent": "scholar",
      "action": "pain-discovery",
      "params": { "role": "compliance officer", "industry": "water utilities" }
    }
  ]
}
```

#### Hybrid: Parallel Research → Single Synthesis
```json
{
  "intent_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "source": "aria",
  "timestamp": "2026-01-17T15:30:00Z",
  "type": "chain",
  "steps": [
    {
      "step_id": "parallel_research",
      "type": "parallel",
      "substeps": [
        {
          "step_id": "competitors",
          "agent": "scholar",
          "action": "competitors",
          "params": { "niche": "compliance automation" }
        },
        {
          "step_id": "pricing",
          "agent": "scholar",
          "action": "deep-research",
          "params": { "question": "compliance automation pricing models" }
        }
      ]
    },
    {
      "step_id": "strategy",
      "agent": "chiron",
      "action": "chat",
      "input_template": "Competitor analysis:\n{{parallel_research.competitors.output}}\n\nPricing research:\n{{parallel_research.pricing.output}}\n\nRecommend our positioning and pricing strategy.",
      "params": {}
    }
  ]
}
```

#### Conditional: Research → Decide Path
```json
{
  "intent_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "source": "aria",
  "type": "chain",
  "steps": [
    {
      "step_id": "validate",
      "agent": "scholar",
      "action": "validate-assumption",
      "params": {
        "assumption": "Water utilities spend >$50K/year on compliance"
      }
    },
    {
      "step_id": "go_plan",
      "agent": "chiron",
      "action": "sprint-plan",
      "condition": {
        "field": "validate.output.verdict",
        "operator": "eq",
        "value": "validated"
      },
      "input_template": "Assumption validated! {{validate.output.evidence_for}}\n\nCreate aggressive market entry plan.",
      "params": {}
    },
    {
      "step_id": "pivot_research",
      "agent": "scholar",
      "action": "niche",
      "condition": {
        "field": "validate.output.verdict",
        "operator": "ne",
        "value": "validated"
      },
      "params": {
        "niche": "alternative compliance verticals"
      }
    }
  ]
}
```

---

## ATLAS Implementation

### Directory Structure

```
/opt/leveredge/control-plane/agents/atlas/
├── atlas.py                 # Main FastAPI application
├── orchestrator.py          # Core execution engine
├── intent_parser.py         # Intent validation & normalization
├── agent_registry.py        # Agent capabilities & endpoints
├── executor.py              # Step execution logic
├── response_aggregator.py   # Collect & format responses
├── cost_tracker.py          # Aggregate costs across chain
├── error_handler.py         # Retry logic, fallbacks
├── requirements.txt
├── Dockerfile
└── tests/
    ├── test_single.py
    ├── test_chain.py
    ├── test_parallel.py
    └── test_conditional.py
```

### Agent Registry

```python
# agent_registry.py
"""
Central registry of all available agents and their capabilities.
ATLAS uses this to validate intents and route requests.
"""

AGENT_REGISTRY = {
    "scholar": {
        "name": "SCHOLAR",
        "description": "Market research and competitive intelligence",
        "base_url": "http://scholar:8018",
        "health_endpoint": "/health",
        "actions": {
            "research": {
                "endpoint": "/research",
                "method": "POST",
                "params": ["topic", "depth"],
                "timeout_ms": 60000
            },
            "deep-research": {
                "endpoint": "/deep-research",
                "method": "POST",
                "params": ["question", "context"],
                "timeout_ms": 120000
            },
            "competitors": {
                "endpoint": "/competitors",
                "method": "POST",
                "params": ["niche"],
                "timeout_ms": 90000
            },
            "market-size": {
                "endpoint": "/market-size",
                "method": "POST",
                "params": ["market", "geography"],
                "timeout_ms": 90000
            },
            "pain-discovery": {
                "endpoint": "/pain-discovery",
                "method": "POST",
                "params": ["role", "industry"],
                "timeout_ms": 90000
            },
            "validate-assumption": {
                "endpoint": "/validate-assumption",
                "method": "POST",
                "params": ["assumption", "importance"],
                "timeout_ms": 90000
            },
            "icp": {
                "endpoint": "/icp",
                "method": "POST",
                "params": ["niche"],
                "timeout_ms": 60000
            },
            "niche": {
                "endpoint": "/niche",
                "method": "POST",
                "params": ["niche"],
                "timeout_ms": 60000
            }
        }
    },
    "chiron": {
        "name": "CHIRON",
        "description": "Business strategy and ADHD-optimized planning",
        "base_url": "http://chiron:8017",
        "health_endpoint": "/health",
        "actions": {
            "chat": {
                "endpoint": "/chat",
                "method": "POST",
                "params": ["message"],
                "timeout_ms": 60000
            },
            "sprint-plan": {
                "endpoint": "/sprint-plan",
                "method": "POST",
                "params": ["goals", "time_available", "energy_level", "blockers"],
                "timeout_ms": 60000
            },
            "pricing-help": {
                "endpoint": "/pricing-help",
                "method": "POST",
                "params": ["service_description", "client_context", "value_delivered"],
                "timeout_ms": 60000
            },
            "fear-check": {
                "endpoint": "/fear-check",
                "method": "POST",
                "params": ["situation", "what_im_avoiding"],
                "timeout_ms": 45000
            },
            "weekly-review": {
                "endpoint": "/weekly-review",
                "method": "POST",
                "params": ["wins", "losses", "lessons", "next_week_goals"],
                "timeout_ms": 60000
            },
            "framework": {
                "endpoint": "/framework/{name}",
                "method": "GET",
                "params": ["name"],
                "timeout_ms": 10000
            }
        }
    },
    "hermes": {
        "name": "HERMES",
        "description": "Notifications and messaging",
        "base_url": "http://hermes:8014",
        "health_endpoint": "/health",
        "actions": {
            "notify": {
                "endpoint": "/notify",
                "method": "POST",
                "params": ["channel", "message", "priority"],
                "timeout_ms": 10000
            },
            "telegram": {
                "endpoint": "/telegram",
                "method": "POST",
                "params": ["message", "chat_id"],
                "timeout_ms": 10000
            }
        }
    },
    "chronos": {
        "name": "CHRONOS",
        "description": "Backup management",
        "base_url": "http://chronos:8010",
        "health_endpoint": "/health",
        "actions": {
            "backup": {
                "endpoint": "/backup",
                "method": "POST",
                "params": ["target", "tag"],
                "timeout_ms": 300000
            },
            "list": {
                "endpoint": "/list",
                "method": "GET",
                "params": ["target"],
                "timeout_ms": 10000
            }
        }
    },
    "hades": {
        "name": "HADES",
        "description": "Rollback and recovery",
        "base_url": "http://hades:8008",
        "health_endpoint": "/health",
        "actions": {
            "rollback": {
                "endpoint": "/rollback",
                "method": "POST",
                "params": ["target", "backup_id", "confirm"],
                "timeout_ms": 300000
            }
        }
    },
    "aegis": {
        "name": "AEGIS",
        "description": "Credential management",
        "base_url": "http://aegis:8012",
        "health_endpoint": "/health",
        "actions": {
            "list": {
                "endpoint": "/credentials",
                "method": "GET",
                "params": [],
                "timeout_ms": 5000
            },
            "get": {
                "endpoint": "/credentials/{name}",
                "method": "GET",
                "params": ["name"],
                "timeout_ms": 5000
            }
        }
    },
    "argus": {
        "name": "ARGUS",
        "description": "Monitoring and metrics",
        "base_url": "http://argus:8016",
        "health_endpoint": "/health",
        "actions": {
            "status": {
                "endpoint": "/status",
                "method": "GET",
                "params": [],
                "timeout_ms": 10000
            },
            "costs": {
                "endpoint": "/costs",
                "method": "GET",
                "params": ["days"],
                "timeout_ms": 10000
            }
        }
    }
}

def get_agent(agent_name: str) -> dict:
    """Get agent configuration by name."""
    return AGENT_REGISTRY.get(agent_name.lower())

def get_action(agent_name: str, action_name: str) -> dict:
    """Get specific action configuration."""
    agent = get_agent(agent_name)
    if agent:
        return agent.get("actions", {}).get(action_name)
    return None

def list_agents() -> list:
    """List all registered agents."""
    return [
        {"name": k, "description": v["description"]}
        for k, v in AGENT_REGISTRY.items()
    ]

def validate_step(step: dict) -> tuple[bool, str]:
    """Validate a step against registry. Returns (valid, error_message)."""
    agent = get_agent(step.get("agent"))
    if not agent:
        return False, f"Unknown agent: {step.get('agent')}"
    
    action = get_action(step.get("agent"), step.get("action"))
    if not action:
        return False, f"Unknown action '{step.get('action')}' for agent '{step.get('agent')}'"
    
    return True, None
```

### Core Orchestrator

```python
# orchestrator.py
"""
ATLAS Orchestration Engine
Zero LLM cost - pure execution of structured intents
"""

import asyncio
import httpx
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
import json

from agent_registry import get_agent, get_action, validate_step

# Event Bus for logging
EVENT_BUS_URL = "http://event-bus:8099"

class ExecutionContext:
    """Holds state during intent execution."""
    
    def __init__(self, intent: dict):
        self.intent = intent
        self.intent_id = intent.get("intent_id", str(uuid4()))
        self.started_at = datetime.utcnow()
        self.step_outputs: Dict[str, Any] = {}
        self.step_costs: Dict[str, float] = {}
        self.errors: List[dict] = []
        self.status = "running"
    
    def get_step_output(self, step_id: str) -> Any:
        return self.step_outputs.get(step_id)
    
    def set_step_output(self, step_id: str, output: Any, cost: float = 0):
        self.step_outputs[step_id] = output
        self.step_costs[step_id] = cost
    
    def add_error(self, step_id: str, error: str):
        self.errors.append({
            "step_id": step_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @property
    def total_cost(self) -> float:
        return sum(self.step_costs.values())
    
    @property
    def duration_ms(self) -> int:
        return int((datetime.utcnow() - self.started_at).total_seconds() * 1000)


class Orchestrator:
    """Main orchestration engine."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def execute(self, intent: dict) -> dict:
        """Execute an intent and return results."""
        
        # Validate intent
        valid, error = self._validate_intent(intent)
        if not valid:
            return self._error_response(intent, error)
        
        # Create execution context
        ctx = ExecutionContext(intent)
        
        # Log start to Event Bus
        await self._log_event("orchestration_started", {
            "intent_id": ctx.intent_id,
            "type": intent.get("type"),
            "step_count": len(intent.get("steps", []))
        })
        
        try:
            # Execute based on type
            intent_type = intent.get("type", "single")
            
            if intent_type == "single":
                result = await self._execute_single(ctx, intent["steps"][0])
            elif intent_type == "chain":
                result = await self._execute_chain(ctx, intent["steps"])
            elif intent_type == "parallel":
                result = await self._execute_parallel(ctx, intent["steps"])
            elif intent_type == "conditional":
                result = await self._execute_chain(ctx, intent["steps"])  # Conditionals handled in chain
            else:
                return self._error_response(intent, f"Unknown intent type: {intent_type}")
            
            ctx.status = "completed"
            
        except Exception as e:
            ctx.status = "failed"
            ctx.add_error("orchestrator", str(e))
            result = None
        
        # Build response
        response = self._build_response(ctx, result)
        
        # Log completion to Event Bus
        await self._log_event("orchestration_completed", {
            "intent_id": ctx.intent_id,
            "status": ctx.status,
            "duration_ms": ctx.duration_ms,
            "total_cost": ctx.total_cost,
            "error_count": len(ctx.errors)
        })
        
        return response
    
    async def _execute_single(self, ctx: ExecutionContext, step: dict) -> Any:
        """Execute a single agent call."""
        return await self._execute_step(ctx, step)
    
    async def _execute_chain(self, ctx: ExecutionContext, steps: List[dict]) -> Any:
        """Execute steps sequentially, passing outputs forward."""
        
        last_output = None
        
        for step in steps:
            # Check condition if present
            if not self._check_condition(ctx, step):
                continue
            
            # Handle nested parallel
            if step.get("type") == "parallel" and "substeps" in step:
                last_output = await self._execute_parallel(ctx, step["substeps"])
                ctx.set_step_output(step["step_id"], {"substeps": last_output})
                continue
            
            # Resolve input template if present
            resolved_step = self._resolve_input_template(ctx, step)
            
            # Execute step
            last_output = await self._execute_step(ctx, resolved_step)
        
        return last_output
    
    async def _execute_parallel(self, ctx: ExecutionContext, steps: List[dict]) -> Dict[str, Any]:
        """Execute steps in parallel, return all outputs."""
        
        tasks = []
        for step in steps:
            if self._check_condition(ctx, step):
                tasks.append(self._execute_step(ctx, step))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results to step IDs
        output = {}
        for i, step in enumerate([s for s in steps if self._check_condition(ctx, s)]):
            if isinstance(results[i], Exception):
                ctx.add_error(step["step_id"], str(results[i]))
                output[step["step_id"]] = {"error": str(results[i])}
            else:
                output[step["step_id"]] = results[i]
        
        return output
    
    async def _execute_step(self, ctx: ExecutionContext, step: dict) -> Any:
        """Execute a single step by calling the appropriate agent."""
        
        step_id = step.get("step_id", str(uuid4()))
        agent_name = step["agent"]
        action_name = step["action"]
        params = step.get("params", {})
        options = step.get("options", {})
        
        # Get agent config
        agent = get_agent(agent_name)
        action = get_action(agent_name, action_name)
        
        if not agent or not action:
            raise ValueError(f"Invalid agent/action: {agent_name}/{action_name}")
        
        # Build URL
        endpoint = action["endpoint"]
        if "{" in endpoint:
            # Handle path parameters
            for key, value in params.items():
                endpoint = endpoint.replace(f"{{{key}}}", str(value))
        
        url = f"{agent['base_url']}{endpoint}"
        method = action.get("method", "POST")
        timeout = options.get("timeout_ms", action.get("timeout_ms", 60000)) / 1000
        
        # Make request
        try:
            if method == "GET":
                response = await self.client.get(url, params=params, timeout=timeout)
            else:
                response = await self.client.post(url, json=params, timeout=timeout)
            
            response.raise_for_status()
            result = response.json()
            
            # Extract cost if present
            cost = result.get("_cost", result.get("total_cost", 0))
            
            # Store output
            ctx.set_step_output(step_id, {"output": result, "agent": agent_name, "action": action_name}, cost)
            
            return result
            
        except httpx.TimeoutException:
            error = f"Timeout after {timeout}s calling {agent_name}/{action_name}"
            ctx.add_error(step_id, error)
            
            # Try fallback if configured
            fallback = options.get("fallback_agent")
            if fallback:
                step["agent"] = fallback
                return await self._execute_step(ctx, step)
            
            if options.get("required", True):
                raise RuntimeError(error)
            return {"error": error}
            
        except Exception as e:
            error = f"Error calling {agent_name}/{action_name}: {str(e)}"
            ctx.add_error(step_id, error)
            
            if options.get("required", True):
                raise
            return {"error": error}
    
    def _check_condition(self, ctx: ExecutionContext, step: dict) -> bool:
        """Check if step's condition is met."""
        condition = step.get("condition")
        if not condition:
            return True
        
        # Parse field path (e.g., "validate.output.verdict")
        field_path = condition["field"].split(".")
        value = ctx.step_outputs
        
        try:
            for key in field_path:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return False
        except:
            return False
        
        # Evaluate condition
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
    
    def _resolve_input_template(self, ctx: ExecutionContext, step: dict) -> dict:
        """Resolve {{step_id.field}} placeholders in input_template."""
        
        step = step.copy()
        
        # Handle input_from (simple case)
        if "input_from" in step and step["input_from"] in ctx.step_outputs:
            prev_output = ctx.step_outputs[step["input_from"]]
            step["params"] = step.get("params", {})
            step["params"]["_previous"] = prev_output
        
        # Handle input_template (complex case)
        if "input_template" in step:
            template = step["input_template"]
            
            # Find all {{step_id.field.path}} patterns
            import re
            pattern = r'\{\{([^}]+)\}\}'
            matches = re.findall(pattern, template)
            
            for match in matches:
                parts = match.split(".")
                value = ctx.step_outputs
                
                try:
                    for part in parts:
                        if isinstance(value, dict):
                            value = value.get(part, value.get("output", {}).get(part))
                        else:
                            value = str(value)
                            break
                    
                    # Convert to string for template
                    if isinstance(value, dict):
                        value = json.dumps(value, indent=2)
                    elif value is None:
                        value = "[No data]"
                    
                    template = template.replace(f"{{{{{match}}}}}", str(value))
                except:
                    template = template.replace(f"{{{{{match}}}}}", f"[Error resolving {match}]")
            
            # Put resolved template in params
            step["params"] = step.get("params", {})
            step["params"]["message"] = template
        
        return step
    
    def _validate_intent(self, intent: dict) -> tuple[bool, str]:
        """Validate intent structure and agent/actions."""
        
        if not intent.get("steps"):
            return False, "Intent must have at least one step"
        
        for step in intent["steps"]:
            # Handle nested substeps
            if step.get("substeps"):
                for substep in step["substeps"]:
                    valid, error = validate_step(substep)
                    if not valid:
                        return False, error
            else:
                valid, error = validate_step(step)
                if not valid:
                    return False, error
        
        return True, None
    
    def _build_response(self, ctx: ExecutionContext, result: Any) -> dict:
        """Build final response object."""
        
        return {
            "intent_id": ctx.intent_id,
            "status": ctx.status,
            "duration_ms": ctx.duration_ms,
            "total_cost": round(ctx.total_cost, 6),
            "steps_completed": len(ctx.step_outputs),
            "step_outputs": ctx.step_outputs,
            "errors": ctx.errors if ctx.errors else None,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _error_response(self, intent: dict, error: str) -> dict:
        """Build error response."""
        return {
            "intent_id": intent.get("intent_id", str(uuid4())),
            "status": "failed",
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _log_event(self, event_type: str, data: dict):
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
            pass  # Don't fail orchestration on logging errors


# Singleton instance
orchestrator = Orchestrator()
```

### FastAPI Application

```python
# atlas.py
"""
ATLAS - Master Orchestrator API
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime
import os

from orchestrator import orchestrator
from agent_registry import list_agents, AGENT_REGISTRY

app = FastAPI(
    title="ATLAS - Master Orchestrator",
    description="Central nervous system for LeverEdge agent orchestration",
    version="2.0.0"
)

# ============ Models ============

class StepParams(BaseModel):
    """Flexible params for agent actions."""
    class Config:
        extra = "allow"

class Step(BaseModel):
    step_id: str
    agent: str
    action: str
    params: Dict[str, Any] = {}
    input_from: Optional[str] = None
    input_template: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class ParallelStep(BaseModel):
    step_id: str
    type: str = "parallel"
    substeps: List[Step]

class IntentOptions(BaseModel):
    timeout_ms: int = 120000
    retry_count: int = 1
    fail_fast: bool = True
    include_reasoning: bool = False

class IntentContext(BaseModel):
    conversation_id: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None

class Intent(BaseModel):
    intent_id: Optional[str] = None
    source: str = "api"
    type: str = "single"  # single, chain, parallel, conditional
    steps: List[Dict[str, Any]]  # Can be Step or ParallelStep
    options: Optional[IntentOptions] = None
    context: Optional[IntentContext] = None

class QuickRequest(BaseModel):
    """Simplified request for common patterns."""
    message: str
    source: str = "api"

# ============ Endpoints ============

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "agent": "ATLAS",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/agents")
async def get_agents():
    """List available agents and their capabilities."""
    return {
        "agents": list_agents(),
        "count": len(AGENT_REGISTRY)
    }

@app.get("/agents/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed info about a specific agent."""
    agent = AGENT_REGISTRY.get(agent_name.lower())
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return agent

@app.post("/execute")
async def execute_intent(intent: Intent):
    """
    Execute an orchestration intent.
    
    This is the main entry point for all orchestration requests.
    Supports single calls, chains, parallel execution, and conditionals.
    """
    result = await orchestrator.execute(intent.dict())
    return result

@app.post("/quick/research-and-plan")
async def quick_research_and_plan(request: QuickRequest):
    """
    Quick pattern: Research something, then create a plan.
    
    Example: "water utility compliance pain points"
    """
    intent = {
        "source": request.source,
        "type": "chain",
        "steps": [
            {
                "step_id": "research",
                "agent": "scholar",
                "action": "deep-research",
                "params": {"question": request.message}
            },
            {
                "step_id": "plan",
                "agent": "chiron",
                "action": "chat",
                "input_template": f"Based on this research:\n\n{{{{research.output.research}}}}\n\nCreate an actionable plan to address the key findings."
            }
        ]
    }
    return await orchestrator.execute(intent)

@app.post("/quick/validate-and-decide")
async def quick_validate_and_decide(request: QuickRequest):
    """
    Quick pattern: Validate an assumption, then decide next steps.
    
    Example: "water utilities spend >$50K on compliance annually"
    """
    intent = {
        "source": request.source,
        "type": "chain",
        "steps": [
            {
                "step_id": "validate",
                "agent": "scholar",
                "action": "validate-assumption",
                "params": {"assumption": request.message}
            },
            {
                "step_id": "decide",
                "agent": "chiron",
                "action": "chat",
                "input_template": "Assumption: {}\n\nValidation result:\n{{{{validate.output}}}}\n\nBased on this, what should I do next?".format(request.message)
            }
        ]
    }
    return await orchestrator.execute(intent)

@app.post("/quick/comprehensive-analysis")
async def quick_comprehensive_analysis(request: QuickRequest):
    """
    Quick pattern: Parallel research streams, then strategic synthesis.
    
    Example: "compliance automation market"
    """
    intent = {
        "source": request.source,
        "type": "chain",
        "steps": [
            {
                "step_id": "parallel_research",
                "type": "parallel",
                "substeps": [
                    {
                        "step_id": "competitors",
                        "agent": "scholar",
                        "action": "competitors",
                        "params": {"niche": request.message}
                    },
                    {
                        "step_id": "market",
                        "agent": "scholar",
                        "action": "market-size",
                        "params": {"market": request.message}
                    },
                    {
                        "step_id": "pains",
                        "agent": "scholar",
                        "action": "pain-discovery",
                        "params": {"role": "compliance officer", "industry": request.message}
                    }
                ]
            },
            {
                "step_id": "strategy",
                "agent": "chiron",
                "action": "chat",
                "input_template": "I've gathered comprehensive research on '{}':\n\n**Competitors:**\n{{{{parallel_research.competitors.output}}}}\n\n**Market Size:**\n{{{{parallel_research.market.output}}}}\n\n**Pain Points:**\n{{{{parallel_research.pains.output}}}}\n\nSynthesize this into a strategic recommendation.".format(request.message)
            }
        ]
    }
    return await orchestrator.execute(intent)

# ============ Startup ============

@app.on_event("startup")
async def startup():
    """Log startup to Event Bus."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://event-bus:8099/publish",
                json={
                    "event_type": "agent_started",
                    "source": "ATLAS",
                    "data": {"version": "2.0.0"}
                },
                timeout=2.0
            )
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
```

---

## ARIA Integration

### Updated ARIA Pre-Router

ARIA now extracts structured intents and sends them to ATLAS:

```javascript
// ARIA Pre-Router: Extract intent for ATLAS
const message = $json.message;
const messageLower = message.toLowerCase();

// ============ CHAIN DETECTION ============
const chainPatterns = [
  { 
    pattern: /research .+ (then|and then|,\s*then|,\s*and) .*(plan|analyze|recommend|decide|advise|create)/i,
    type: "research_then_plan"
  },
  {
    pattern: /find out .+ (then|and then|,\s*then) .*(plan|recommend|create)/i,
    type: "research_then_plan"
  },
  {
    pattern: /validate .+ (then|and) .*(decide|plan|recommend)/i,
    type: "validate_then_decide"
  },
  {
    pattern: /(comprehensive|full|complete) .*(analysis|research|report)/i,
    type: "comprehensive_analysis"
  },
  {
    pattern: /analyze .+ and .*(recommend|suggest|advise|plan)/i,
    type: "research_then_plan"
  }
];

// Check for chain patterns
for (const { pattern, type } of chainPatterns) {
  if (pattern.test(messageLower)) {
    return {
      json: {
        ...$json,
        route: 'atlas',
        atlas_endpoint: `/quick/${type.replace(/_/g, '-')}`,
        atlas_payload: { message: message, source: 'aria' }
      }
    };
  }
}

// ============ SINGLE AGENT DETECTION ============

// CHIRON triggers
const chironPatterns = [
  /\b(ask chiron|have chiron|tell chiron|chiron,)/i,
  /\b(sprint plan|plan my (week|day)|weekly plan)/i,
  /\b(pricing|how much should i charge|price this)/i,
  /\b(i'm afraid|i'm avoiding|fear check|scared of)/i,
  /\b(weekly review|what did i accomplish)/i,
  /\b(procrastinating|call me out|accountability)/i,
  /\b(business strategy|should i focus|what's important)/i,
  /\b(adhd|staying focused|overwhelmed|paralyzed)/i
];

// SCHOLAR triggers
const scholarPatterns = [
  /\b(ask scholar|have scholar|tell scholar|scholar,)/i,
  /\b(research|look up|find out about|investigate)/i,
  /\b(competitor|competition|who else does)/i,
  /\b(market size|tam|sam|som|how big is the market)/i,
  /\b(icp|ideal customer|who should i target)/i,
  /\b(niche|which industry|what vertical)/i,
  /\b(pain points?|what problems do they have)/i,
  /\b(validate|is it true that|assumption)/i
];

// Check CHIRON
if (chironPatterns.some(p => p.test(messageLower))) {
  // Determine specific action
  let action = 'chat';
  let params = { message: message };
  
  if (/sprint|plan my (week|day)/i.test(messageLower)) {
    action = 'sprint-plan';
    params = { goals: [message], time_available: 'this week' };
  } else if (/pricing|how much|charge/i.test(messageLower)) {
    action = 'pricing-help';
    params = { service_description: message };
  } else if (/afraid|avoiding|fear|scared/i.test(messageLower)) {
    action = 'fear-check';
    params = { situation: message, what_im_avoiding: 'unknown' };
  } else if (/weekly review|accomplish/i.test(messageLower)) {
    action = 'weekly-review';
    params = { wins: [], losses: [], lessons: [] };
  }
  
  return {
    json: {
      ...$json,
      route: 'atlas',
      atlas_endpoint: '/execute',
      atlas_payload: {
        source: 'aria',
        type: 'single',
        steps: [{
          step_id: 'chiron_call',
          agent: 'chiron',
          action: action,
          params: params
        }]
      }
    }
  };
}

// Check SCHOLAR
if (scholarPatterns.some(p => p.test(messageLower))) {
  let action = 'deep-research';
  let params = { question: message };
  
  if (/competitor|competition/i.test(messageLower)) {
    action = 'competitors';
    params = { niche: message };
  } else if (/market size|tam|sam|som/i.test(messageLower)) {
    action = 'market-size';
    params = { market: message };
  } else if (/pain point/i.test(messageLower)) {
    action = 'pain-discovery';
    params = { role: 'compliance officer', industry: 'water utilities' };
  } else if (/validate|assumption/i.test(messageLower)) {
    action = 'validate-assumption';
    params = { assumption: message };
  } else if (/icp|ideal customer/i.test(messageLower)) {
    action = 'icp';
    params = { niche: message };
  }
  
  return {
    json: {
      ...$json,
      route: 'atlas',
      atlas_endpoint: '/execute',
      atlas_payload: {
        source: 'aria',
        type: 'single',
        steps: [{
          step_id: 'scholar_call',
          agent: 'scholar',
          action: action,
          params: params
        }]
      }
    }
  };
}

// ============ DEFAULT: ARIA HANDLES ============
return {
  json: {
    ...$json,
    route: 'aria'
  }
};
```

### ARIA HTTP Node for ATLAS

```
URL: http://atlas:8007{{ $json.atlas_endpoint }}
Method: POST
Body: {{ JSON.stringify($json.atlas_payload) }}
Headers:
  Content-Type: application/json
```

### ARIA Response Formatter for ATLAS Results

```javascript
// Format ATLAS response for human consumption
const atlasResponse = $json;

if (atlasResponse.status === 'failed') {
  return {
    json: {
      message: `❌ **Request Failed**\n\n${atlasResponse.error || 'Unknown error'}\n\nErrors: ${JSON.stringify(atlasResponse.errors)}`,
      mode: 'DEFAULT'
    }
  };
}

// Build formatted response
let formatted = '';
const stepOutputs = atlasResponse.step_outputs || {};
const stepsCompleted = Object.keys(stepOutputs).length;

// Single step
if (stepsCompleted === 1) {
  const stepId = Object.keys(stepOutputs)[0];
  const step = stepOutputs[stepId];
  const agent = step.agent?.toUpperCase() || 'AGENT';
  const output = step.output;
  
  // Extract main content
  const content = output.response || output.research || output.sprint_plan || 
                  output.pricing_strategy || output.fear_analysis || 
                  JSON.stringify(output, null, 2);
  
  formatted = `🤖 **${agent}:**\n\n${content}`;
}
// Chain/parallel (multiple steps)
else {
  formatted = `🔗 **Multi-Agent Analysis** (${stepsCompleted} steps)\n\n`;
  
  for (const [stepId, step] of Object.entries(stepOutputs)) {
    const agent = step.agent?.toUpperCase() || stepId.toUpperCase();
    const output = step.output || step;
    
    // Handle nested substeps
    if (step.substeps) {
      formatted += `### Parallel Research\n\n`;
      for (const [subId, subStep] of Object.entries(step.substeps)) {
        const subAgent = subStep.agent?.toUpperCase() || subId;
        const subContent = subStep.output?.research || subStep.output?.response || 
                          JSON.stringify(subStep.output, null, 2).substring(0, 500);
        formatted += `**${subAgent} (${subId}):**\n${subContent}\n\n`;
      }
    } else {
      const content = output.response || output.research || output.sprint_plan ||
                     output.pricing_strategy || output.fear_analysis ||
                     (typeof output === 'string' ? output : JSON.stringify(output, null, 2));
      formatted += `### ${agent}\n\n${content}\n\n---\n\n`;
    }
  }
}

// Add cost footer
if (atlasResponse.total_cost > 0) {
  formatted += `\n\n*Cost: $${atlasResponse.total_cost.toFixed(4)} | Duration: ${atlasResponse.duration_ms}ms*`;
}

return {
  json: {
    message: formatted,
    atlas_response: atlasResponse,
    mode: 'STRATEGY'
  }
};
```

---

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8007

CMD ["uvicorn", "atlas:app", "--host", "0.0.0.0", "--port", "8007"]
```

### requirements.txt

```
fastapi==0.109.0
uvicorn==0.27.0
httpx==0.26.0
pydantic==2.5.3
```

### docker-compose addition

```yaml
# Add to /opt/leveredge/control-plane/docker-compose.yml

  atlas:
    build: ./agents/atlas
    container_name: atlas
    restart: unless-stopped
    ports:
      - "8007:8007"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
    networks:
      - control-plane-net
      - stack_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8007/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Testing

### Test Single Call
```bash
curl -X POST http://localhost:8007/execute \
  -H "Content-Type: application/json" \
  -d '{
    "type": "single",
    "steps": [{
      "step_id": "test",
      "agent": "chiron",
      "action": "chat",
      "params": {"message": "What should I focus on today?"}
    }]
  }'
```

### Test Chain
```bash
curl -X POST http://localhost:8007/quick/research-and-plan \
  -H "Content-Type: application/json" \
  -d '{"message": "water utility compliance pain points"}'
```

### Test Comprehensive Analysis
```bash
curl -X POST http://localhost:8007/quick/comprehensive-analysis \
  -H "Content-Type: application/json" \
  -d '{"message": "compliance automation market"}'
```

### Test via ARIA
```
"Research AEGIS best practices, then create a plan to enhance our credential manager"
```

---

## Success Criteria

- [ ] ATLAS health endpoint responds
- [ ] Single agent calls work via /execute
- [ ] Chain execution works (SCHOLAR → CHIRON)
- [ ] Parallel execution works
- [ ] Conditional execution works
- [ ] Quick endpoints work (/quick/research-and-plan, etc.)
- [ ] ARIA routes to ATLAS correctly
- [ ] ARIA formats ATLAS responses nicely
- [ ] Cost tracking aggregates across chain
- [ ] Event Bus receives orchestration events
- [ ] Errors handled gracefully with fallbacks

---

## Git Commit

```
ATLAS Orchestration Engine V2 - Central nervous system

- Zero LLM cost orchestration (rules-based execution)
- Supports: single, chain, parallel, conditional intents
- Agent registry with capability discovery
- Template resolution for chained outputs
- Quick endpoints for common patterns
- Full Event Bus integration
- Cost aggregation across chains
- ARIA integration with intent extraction
- Comprehensive error handling with fallbacks
```
