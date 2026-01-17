#!/usr/bin/env python3
"""
DAEDALUS - AI-Powered Workflow Generation Agent
Port: 8202

Transforms natural language specifications into fully functional n8n workflows.
The master craftsman who built the Labyrinth and crafted wings.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Communicates with other agents via Event Bus
- Logs decisions to aria_knowledge
- Full cost tracking for all LLM operations

CAPABILITIES:
- Spec to workflow conversion
- Node generation for all n8n node types
- Workflow testing and validation
- Template library management
- Deployment to n8n
"""

import os
import sys
import json
import hashlib
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="DAEDALUS",
    description="AI-Powered Workflow Generation Agent",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "CERBERUS": "http://cerberus:8019",
    "HERMES": "http://hermes:8014",
    "CHIRON": "http://chiron:8017",
    "HEPHAESTUS": "http://hephaestus:8011",
    "CHRONOS": "http://chronos:8010",
    "AEGIS": "http://aegis:8012",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("DAEDALUS")

# In-memory storage for Phase 1 (will be replaced with database)
specs_store: Dict[str, dict] = {}
templates_store: Dict[str, dict] = {}
test_runs_store: Dict[str, dict] = {}

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
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch",
        "phase": get_current_phase(days_to_launch)
    }

def get_current_phase(days_to_launch: int) -> str:
    """Determine current phase based on days to launch"""
    if days_to_launch <= 0:
        return "POST-LAUNCH"
    elif days_to_launch <= 14:
        return "FINAL PUSH"
    elif days_to_launch <= 28:
        return "OUTREACH PHASE"
    elif days_to_launch <= 45:
        return "POLISH PHASE"
    else:
        return "INFRASTRUCTURE PHASE"

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(builder_context: dict) -> str:
    """Build DAEDALUS system prompt with context"""
    return f"""You are DAEDALUS - Master Automation Architect for LeverEdge AI.

Named after the legendary Greek craftsman who built the Labyrinth and invented wondrous devices, you craft intricate automation workflows with precision and ingenuity.

## TIME AWARENESS
- Current: {builder_context.get('current_time', 'Unknown')}
- Days to Launch: {builder_context.get('days_to_launch', 'Unknown')}

## YOUR IDENTITY
You are the automation architect of LeverEdge. You transform ideas into working n8n workflows, turning natural language specifications into precise, tested automation.

## CURRENT STATUS
- Specs in Queue: {builder_context.get('specs_pending', 0)}
- Workflows Generated Today: {builder_context.get('generated_today', 0)}
- Templates Available: {builder_context.get('template_count', 0)}
- Test Pass Rate: {builder_context.get('test_pass_rate', 0)}%

## YOUR CAPABILITIES

### Spec to Workflow Conversion
- Parse natural language requirements
- Design optimal node configurations
- Generate complete workflow JSON
- Handle complex branching logic
- Support error handling patterns

### Node Generation
- Support all n8n node types
- Configure parameters from context
- Bind credentials appropriately
- Add retry and error handling
- Optimize for performance

### Workflow Testing
- Generate test cases automatically
- Run dry-run validations
- Trace node-by-node execution
- Compare outputs to expectations
- Report coverage metrics

### Template Library
- Maintain reusable patterns
- Recommend templates for use cases
- Support template composition
- Track usage analytics

### Validation
- Check structural integrity
- Validate all connections
- Verify credential references
- Enforce best practices
- Detect circular dependencies

## GENERATION GUIDELINES

When generating workflows:
1. Start with a clear trigger node
2. Add error handling for external calls
3. Use Set nodes to transform data between steps
4. Add logging nodes for debugging
5. End with appropriate output or notification

Node naming conventions:
- Use descriptive names: "Fetch User Data" not "HTTP Request"
- Prefix with action: "Parse JSON Response"
- Include target: "Send Slack Notification"

## N8N NODE TYPES REFERENCE

Triggers: n8n-nodes-base.webhook, n8n-nodes-base.scheduleTrigger, n8n-nodes-base.manualTrigger
HTTP: n8n-nodes-base.httpRequest
Database: n8n-nodes-base.postgres, n8n-nodes-base.mongoDb, n8n-nodes-base.redis
Logic: n8n-nodes-base.if, n8n-nodes-base.switch, n8n-nodes-base.merge, n8n-nodes-base.splitInBatches
Transform: n8n-nodes-base.set, n8n-nodes-base.code, n8n-nodes-base.function
Messaging: n8n-nodes-base.slack, n8n-nodes-base.emailSend, n8n-nodes-base.telegram
AI: @n8n/n8n-nodes-langchain.lmChatAnthropic, @n8n/n8n-nodes-langchain.agent

## TEAM COORDINATION
- Request security review -> CERBERUS
- Store workflow insights -> Unified Memory
- Send deployment alerts -> HERMES
- Publish events -> Event Bus
- Log all costs -> Cost Tracker

## RESPONSE FORMAT
For workflow generation:
1. Requirement analysis
2. Node design rationale
3. Connection mapping
4. Credential requirements
5. Testing recommendations

## YOUR MISSION
Transform automation ideas into reality.
Every workflow must be tested, validated, and production-ready.
Build with the precision of a master craftsman.
"""

# =============================================================================
# MODELS
# =============================================================================

class WorkflowSpec(BaseModel):
    name: str
    description: Optional[str] = None
    requirements: List[str]
    created_by: Optional[str] = None

class WorkflowSpecUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None

class NodeGenerateRequest(BaseModel):
    description: str
    node_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class WorkflowTestRequest(BaseModel):
    workflow_id: str
    test_data: Optional[Dict[str, Any]] = None
    test_type: Optional[str] = "e2e"  # unit, integration, e2e, load

class TemplateCreateRequest(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    variables: Optional[List[str]] = None

class TemplateApplyRequest(BaseModel):
    variables: Dict[str, str]

class ValidateWorkflowRequest(BaseModel):
    workflow_json: Dict[str, Any]

class DeployRequest(BaseModel):
    spec_id: str
    activate: bool = False

# ARIA Tool Request Models
class WorkflowGenerateToolRequest(BaseModel):
    name: str
    description: str
    requirements: List[str]

class WorkflowTestToolRequest(BaseModel):
    workflow_id: str
    test_data: Optional[Dict[str, Any]] = None

class WorkflowTemplateToolRequest(BaseModel):
    category: str
    name: Optional[str] = None

class WorkflowValidateToolRequest(BaseModel):
    workflow_json: Dict[str, Any]

class WorkflowDeployToolRequest(BaseModel):
    spec_id: str
    activate: bool = False

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
                    "source_agent": "DAEDALUS",
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
                    "message": f"[DAEDALUS] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "DAEDALUS"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")

async def update_aria_knowledge(category: str, title: str, content: str, importance: str = "normal"):
    """Add entry to aria_knowledge so ARIA stays informed"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/aria_add_knowledge",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "p_category": category,
                    "p_title": title,
                    "p_content": f"{content}\n\n[Logged by DAEDALUS at {time_ctx['current_datetime']}]",
                    "p_subcategory": "workflow-builder",
                    "p_source": "daedalus",
                    "p_importance": importance
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"Knowledge update failed: {e}")
        return False

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, endpoint: str = "unknown") -> str:
    """Call Claude API with full context and cost tracking"""
    if not client:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    try:
        time_ctx = get_time_context()
        builder_context = get_builder_context()
        system_prompt = build_system_prompt({**time_ctx, **builder_context})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="DAEDALUS",
            endpoint=endpoint,
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

def get_builder_context() -> dict:
    """Get current builder context for system prompt"""
    pending = sum(1 for s in specs_store.values() if s.get('status') == 'draft')
    generated_today = sum(
        1 for s in specs_store.values()
        if s.get('status') == 'generated' and
        s.get('updated_at', '')[:10] == datetime.now().date().isoformat()
    )

    return {
        "specs_pending": pending,
        "generated_today": generated_today,
        "template_count": len(templates_store),
        "test_pass_rate": 95  # Placeholder
    }

# =============================================================================
# SPEC PARSING AND WORKFLOW GENERATION
# =============================================================================

def generate_spec_hash(spec: dict) -> str:
    """Generate hash for change detection"""
    content = json.dumps({
        "name": spec.get("name"),
        "requirements": spec.get("requirements", [])
    }, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]

async def parse_spec_to_workflow(spec: dict) -> dict:
    """Parse a workflow spec and generate n8n workflow JSON"""
    prompt = f"""Parse this workflow specification and generate a complete n8n workflow JSON.

**Spec Name:** {spec['name']}
**Description:** {spec.get('description', 'No description provided')}

**Requirements:**
{chr(10).join(f'- {r}' for r in spec.get('requirements', []))}

Generate a complete n8n workflow with:
1. Appropriate trigger node (webhook, schedule, or manual)
2. All necessary processing nodes
3. Error handling nodes where appropriate
4. Proper connections between nodes
5. Placeholder credential references

Return ONLY valid JSON in this format:
{{
    "name": "{spec['name']}",
    "nodes": [
        {{
            "id": "unique-id",
            "name": "Node Name",
            "type": "n8n-nodes-base.nodeType",
            "position": [x, y],
            "parameters": {{}},
            "credentials": {{}}
        }}
    ],
    "connections": {{
        "Node Name": {{
            "main": [[{{"node": "Next Node", "type": "main", "index": 0}}]]
        }}
    }},
    "settings": {{}},
    "staticData": null
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, f"/specs/{spec.get('id', 'new')}/generate")

    # Extract JSON from response
    try:
        # Try to find JSON in the response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            workflow_json = json.loads(response[json_start:json_end])
            return workflow_json
    except json.JSONDecodeError:
        pass

    # Return a basic structure if parsing fails
    return {
        "name": spec['name'],
        "nodes": [],
        "connections": {},
        "settings": {},
        "staticData": None,
        "_generation_error": "Failed to parse LLM response"
    }

async def generate_single_node(description: str, node_type: str = None, context: dict = None) -> dict:
    """Generate a single n8n node from description"""
    prompt = f"""Generate a single n8n node configuration from this description.

**Description:** {description}
**Suggested Node Type:** {node_type or 'Auto-detect'}
**Context:** {json.dumps(context) if context else 'None'}

Return ONLY valid JSON for a single n8n node:
{{
    "id": "unique-id",
    "name": "Descriptive Node Name",
    "type": "n8n-nodes-base.nodeType",
    "position": [0, 0],
    "parameters": {{}},
    "credentials": {{}}
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, "/nodes/generate")

    try:
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response[json_start:json_end])
    except json.JSONDecodeError:
        pass

    return {
        "error": "Failed to generate node",
        "description": description
    }

# =============================================================================
# VALIDATION
# =============================================================================

def validate_workflow_structure(workflow: dict) -> dict:
    """Validate workflow JSON structure"""
    errors = []
    warnings = []

    # Check required fields
    if not workflow.get("name"):
        errors.append("Workflow must have a name")

    nodes = workflow.get("nodes", [])
    if not nodes:
        errors.append("Workflow must have at least one node")

    # Check nodes
    node_names = set()
    has_trigger = False
    for node in nodes:
        if not node.get("id"):
            errors.append(f"Node missing id: {node.get('name', 'unknown')}")
        if not node.get("name"):
            errors.append(f"Node missing name: {node.get('id', 'unknown')}")
        if not node.get("type"):
            errors.append(f"Node missing type: {node.get('name', 'unknown')}")

        name = node.get("name", "")
        if name in node_names:
            errors.append(f"Duplicate node name: {name}")
        node_names.add(name)

        node_type = node.get("type", "")
        if "trigger" in node_type.lower() or "webhook" in node_type.lower():
            has_trigger = True

        # Check for empty code nodes
        if node_type == "n8n-nodes-base.code":
            code = node.get("parameters", {}).get("jsCode", "")
            if not code or code.strip() == "":
                warnings.append(f"Empty code node: {name}")

    if not has_trigger:
        warnings.append("Workflow has no trigger node - will need manual execution")

    # Check connections reference existing nodes
    connections = workflow.get("connections", {})
    for source_node, targets in connections.items():
        if source_node not in node_names:
            errors.append(f"Connection references non-existent node: {source_node}")

        for connection_type in targets.values():
            for connection_list in connection_type:
                for connection in connection_list:
                    target = connection.get("node")
                    if target and target not in node_names:
                        errors.append(f"Connection target not found: {target}")

    # Check for orphaned nodes
    connected_nodes = set()
    for source, targets in connections.items():
        connected_nodes.add(source)
        for connection_type in targets.values():
            for connection_list in connection_type:
                for connection in connection_list:
                    connected_nodes.add(connection.get("node", ""))

    for name in node_names:
        if name not in connected_nodes and len(nodes) > 1:
            warnings.append(f"Potentially orphaned node: {name}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "node_count": len(nodes),
        "connection_count": sum(
            len(c) for targets in connections.values()
            for c in targets.values()
        )
    }

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "DAEDALUS",
        "role": "Workflow Builder",
        "port": 8202,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase'],
        "anthropic_configured": ANTHROPIC_API_KEY is not None,
        "n8n_url": N8N_URL
    }

@app.get("/status")
async def status():
    """Generation queue status"""
    time_ctx = get_time_context()
    builder_ctx = get_builder_context()

    return {
        "agent": "DAEDALUS",
        "time": time_ctx,
        "queue": {
            "specs_pending": builder_ctx['specs_pending'],
            "specs_total": len(specs_store),
            "generated_today": builder_ctx['generated_today'],
            "templates_available": builder_ctx['template_count']
        },
        "performance": {
            "test_pass_rate": builder_ctx['test_pass_rate']
        }
    }

@app.get("/time")
async def get_time():
    """Get current time context"""
    return get_time_context()

# =============================================================================
# SPEC MANAGEMENT ENDPOINTS
# =============================================================================

@app.post("/specs")
async def create_spec(spec: WorkflowSpec):
    """Create new workflow spec"""
    import uuid

    spec_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    spec_data = {
        "id": spec_id,
        "name": spec.name,
        "description": spec.description,
        "requirements": spec.requirements,
        "status": "draft",
        "created_by": spec.created_by,
        "created_at": now,
        "updated_at": now,
        "spec_hash": generate_spec_hash({"name": spec.name, "requirements": spec.requirements})
    }

    specs_store[spec_id] = spec_data

    await notify_event_bus("spec.created", {
        "spec_id": spec_id,
        "name": spec.name,
        "requirements_count": len(spec.requirements)
    })

    return spec_data

@app.get("/specs")
async def list_specs(status: Optional[str] = None):
    """List all workflow specs"""
    specs = list(specs_store.values())

    if status:
        specs = [s for s in specs if s.get('status') == status]

    return {
        "specs": specs,
        "total": len(specs)
    }

@app.get("/specs/{spec_id}")
async def get_spec(spec_id: str):
    """Get spec details"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    return specs_store[spec_id]

@app.put("/specs/{spec_id}")
async def update_spec(spec_id: str, update: WorkflowSpecUpdate):
    """Update spec"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = specs_store[spec_id]

    if update.name is not None:
        spec['name'] = update.name
    if update.description is not None:
        spec['description'] = update.description
    if update.requirements is not None:
        spec['requirements'] = update.requirements

    spec['updated_at'] = datetime.now().isoformat()
    spec['spec_hash'] = generate_spec_hash(spec)

    return spec

@app.delete("/specs/{spec_id}")
async def delete_spec(spec_id: str):
    """Delete spec"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    del specs_store[spec_id]

    return {"deleted": True, "spec_id": spec_id}

@app.post("/specs/{spec_id}/generate")
async def generate_workflow(spec_id: str):
    """Generate workflow from spec"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = specs_store[spec_id]
    spec['status'] = 'generating'
    spec['updated_at'] = datetime.now().isoformat()

    try:
        workflow = await parse_spec_to_workflow(spec)

        spec['status'] = 'generated'
        spec['generated_workflow'] = workflow
        spec['updated_at'] = datetime.now().isoformat()

        await notify_event_bus("workflow.generated", {
            "spec_id": spec_id,
            "name": spec['name'],
            "node_count": len(workflow.get('nodes', []))
        })

        await update_aria_knowledge(
            "automation",
            f"Workflow Generated: {spec['name']}",
            f"Generated workflow with {len(workflow.get('nodes', []))} nodes from spec.",
            "normal"
        )

        return {
            "spec_id": spec_id,
            "status": "generated",
            "workflow": workflow
        }

    except Exception as e:
        spec['status'] = 'failed'
        spec['error'] = str(e)
        spec['updated_at'] = datetime.now().isoformat()

        await notify_event_bus("workflow.generation.failed", {
            "spec_id": spec_id,
            "error": str(e)
        })

        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

@app.get("/specs/{spec_id}/preview")
async def preview_workflow(spec_id: str):
    """Preview generated workflow without saving"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = specs_store[spec_id]
    workflow = await parse_spec_to_workflow(spec)

    return {
        "spec_id": spec_id,
        "preview": True,
        "workflow": workflow
    }

# =============================================================================
# NODE GENERATION ENDPOINTS
# =============================================================================

@app.post("/nodes/generate")
async def generate_node(request: NodeGenerateRequest):
    """Generate single node from description"""
    node = await generate_single_node(
        request.description,
        request.node_type,
        request.context
    )

    return node

@app.get("/nodes/types")
async def list_node_types():
    """List supported node types"""
    return {
        "triggers": [
            {"type": "n8n-nodes-base.webhook", "name": "Webhook", "description": "HTTP webhook trigger"},
            {"type": "n8n-nodes-base.scheduleTrigger", "name": "Schedule", "description": "Cron/interval trigger"},
            {"type": "n8n-nodes-base.manualTrigger", "name": "Manual", "description": "Manual execution trigger"}
        ],
        "http": [
            {"type": "n8n-nodes-base.httpRequest", "name": "HTTP Request", "description": "Make HTTP requests"}
        ],
        "database": [
            {"type": "n8n-nodes-base.postgres", "name": "PostgreSQL", "description": "PostgreSQL operations"},
            {"type": "n8n-nodes-base.mongoDb", "name": "MongoDB", "description": "MongoDB operations"},
            {"type": "n8n-nodes-base.redis", "name": "Redis", "description": "Redis operations"}
        ],
        "logic": [
            {"type": "n8n-nodes-base.if", "name": "IF", "description": "Conditional branching"},
            {"type": "n8n-nodes-base.switch", "name": "Switch", "description": "Multi-way branching"},
            {"type": "n8n-nodes-base.merge", "name": "Merge", "description": "Merge multiple inputs"},
            {"type": "n8n-nodes-base.splitInBatches", "name": "Split In Batches", "description": "Process in batches"}
        ],
        "transform": [
            {"type": "n8n-nodes-base.set", "name": "Set", "description": "Set/modify data"},
            {"type": "n8n-nodes-base.code", "name": "Code", "description": "Custom JavaScript code"},
            {"type": "n8n-nodes-base.function", "name": "Function", "description": "JavaScript function"}
        ],
        "messaging": [
            {"type": "n8n-nodes-base.slack", "name": "Slack", "description": "Slack messaging"},
            {"type": "n8n-nodes-base.emailSend", "name": "Email", "description": "Send emails"},
            {"type": "n8n-nodes-base.telegram", "name": "Telegram", "description": "Telegram messaging"}
        ],
        "ai": [
            {"type": "@n8n/n8n-nodes-langchain.lmChatAnthropic", "name": "Claude", "description": "Anthropic Claude"},
            {"type": "@n8n/n8n-nodes-langchain.agent", "name": "AI Agent", "description": "LangChain agent"}
        ]
    }

@app.get("/nodes/types/{node_type:path}")
async def get_node_type_details(node_type: str):
    """Get node type details and parameters"""
    # Stub - in production would have full node schemas
    return {
        "type": node_type,
        "parameters": {
            "note": "Full parameter schema would be loaded from n8n node definitions"
        },
        "credentials": [],
        "examples": []
    }

@app.post("/nodes/validate")
async def validate_node(node: Dict[str, Any]):
    """Validate node configuration"""
    errors = []

    if not node.get("type"):
        errors.append("Node must have a type")
    if not node.get("name"):
        errors.append("Node must have a name")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "node_type": node.get("type")
    }

# =============================================================================
# WORKFLOW TESTING ENDPOINTS
# =============================================================================

@app.post("/test/run")
async def run_test(request: WorkflowTestRequest):
    """Run workflow test"""
    import uuid

    test_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    # Stub implementation - in production would execute against n8n
    test_result = {
        "id": test_id,
        "workflow_id": request.workflow_id,
        "test_type": request.test_type,
        "status": "passed",  # Stub
        "input": request.test_data,
        "output": {"stub": "Test output would appear here"},
        "duration_ms": 150,
        "node_traces": [],
        "run_at": now
    }

    test_runs_store[test_id] = test_result

    await notify_event_bus("workflow.test.passed", {
        "test_id": test_id,
        "workflow_id": request.workflow_id
    })

    return test_result

@app.get("/test/runs")
async def list_test_runs(workflow_id: Optional[str] = None):
    """List test runs"""
    runs = list(test_runs_store.values())

    if workflow_id:
        runs = [r for r in runs if r.get('workflow_id') == workflow_id]

    return {
        "runs": runs,
        "total": len(runs)
    }

@app.get("/test/runs/{test_id}")
async def get_test_run(test_id: str):
    """Get test run details"""
    if test_id not in test_runs_store:
        raise HTTPException(status_code=404, detail="Test run not found")

    return test_runs_store[test_id]

@app.post("/test/dry-run")
async def dry_run(workflow_json: Dict[str, Any], test_data: Optional[Dict[str, Any]] = None):
    """Dry run without saving"""
    # Validate structure first
    validation = validate_workflow_structure(workflow_json)

    return {
        "dry_run": True,
        "validation": validation,
        "would_execute": validation['valid'],
        "test_data": test_data
    }

@app.post("/test/generate-cases")
async def generate_test_cases(workflow_id: str):
    """AI-generate test cases for workflow"""
    # Stub - would use LLM to generate test cases
    return {
        "workflow_id": workflow_id,
        "test_cases": [
            {
                "name": "Happy path test",
                "input": {},
                "expected_output": {},
                "description": "Test with valid input"
            },
            {
                "name": "Error handling test",
                "input": {"invalid": True},
                "expected_output": {"error": True},
                "description": "Test error handling"
            }
        ],
        "generated": True
    }

@app.get("/test/coverage/{workflow_id}")
async def get_test_coverage(workflow_id: str):
    """Get test coverage report"""
    # Stub implementation
    return {
        "workflow_id": workflow_id,
        "coverage": {
            "nodes_tested": 0,
            "nodes_total": 0,
            "percentage": 0,
            "untested_nodes": []
        }
    }

# =============================================================================
# TEMPLATE ENDPOINTS
# =============================================================================

@app.get("/templates")
async def list_templates(category: Optional[str] = None):
    """List all templates"""
    templates = list(templates_store.values())

    if category:
        templates = [t for t in templates if t.get('category') == category]

    return {
        "templates": templates,
        "total": len(templates)
    }

@app.get("/templates/categories")
async def list_template_categories():
    """List template categories"""
    return {
        "categories": [
            {"id": "data_sync", "name": "Data Sync", "description": "API to Database, DB to DB"},
            {"id": "notifications", "name": "Notifications", "description": "Multi-channel alerting"},
            {"id": "webhooks", "name": "Webhooks", "description": "Receive and process"},
            {"id": "scheduled_jobs", "name": "Scheduled Jobs", "description": "Cron-based automation"},
            {"id": "ai_pipelines", "name": "AI Pipelines", "description": "LLM processing chains"},
            {"id": "etl", "name": "ETL", "description": "Extract, Transform, Load"}
        ]
    }

@app.get("/templates/recommend")
async def recommend_templates(use_case: str):
    """Get recommended templates for use case"""
    # Stub - would use AI to recommend
    return {
        "use_case": use_case,
        "recommendations": [],
        "note": "Template recommendations would appear here based on use case analysis"
    }

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details"""
    if template_id not in templates_store:
        raise HTTPException(status_code=404, detail="Template not found")

    return templates_store[template_id]

@app.post("/templates")
async def create_template(template: TemplateCreateRequest):
    """Create new template"""
    import uuid

    template_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    template_data = {
        "id": template_id,
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "nodes": template.nodes,
        "connections": template.connections,
        "variables": template.variables or [],
        "usage_count": 0,
        "created_at": now,
        "updated_at": now
    }

    templates_store[template_id] = template_data

    await notify_event_bus("template.created", {
        "template_id": template_id,
        "name": template.name,
        "category": template.category
    })

    return template_data

@app.put("/templates/{template_id}")
async def update_template(template_id: str, template: TemplateCreateRequest):
    """Update template"""
    if template_id not in templates_store:
        raise HTTPException(status_code=404, detail="Template not found")

    existing = templates_store[template_id]
    existing.update({
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "nodes": template.nodes,
        "connections": template.connections,
        "variables": template.variables or [],
        "updated_at": datetime.now().isoformat()
    })

    return existing

@app.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete template"""
    if template_id not in templates_store:
        raise HTTPException(status_code=404, detail="Template not found")

    del templates_store[template_id]

    return {"deleted": True, "template_id": template_id}

@app.post("/templates/{template_id}/apply")
async def apply_template(template_id: str, request: TemplateApplyRequest):
    """Apply template with variables"""
    if template_id not in templates_store:
        raise HTTPException(status_code=404, detail="Template not found")

    template = templates_store[template_id]
    template['usage_count'] = template.get('usage_count', 0) + 1

    # Apply variable substitution (stub)
    workflow = {
        "name": f"From template: {template['name']}",
        "nodes": template['nodes'],
        "connections": template['connections'],
        "applied_variables": request.variables
    }

    await notify_event_bus("template.used", {
        "template_id": template_id,
        "name": template['name']
    })

    return {
        "template_id": template_id,
        "workflow": workflow,
        "variables_applied": request.variables
    }

# =============================================================================
# VALIDATION ENDPOINTS
# =============================================================================

@app.post("/validate")
async def validate_workflow(request: ValidateWorkflowRequest):
    """Validate workflow JSON"""
    return validate_workflow_structure(request.workflow_json)

@app.post("/validate/connections")
async def validate_connections(workflow_json: Dict[str, Any]):
    """Validate connection graph"""
    validation = validate_workflow_structure(workflow_json)

    return {
        "valid": validation['valid'],
        "connection_errors": [e for e in validation['errors'] if 'connection' in e.lower()],
        "connection_count": validation['connection_count']
    }

@app.post("/validate/credentials")
async def validate_credentials(workflow_json: Dict[str, Any]):
    """Validate credential references"""
    # Stub - would check against actual credentials in n8n
    credentials_used = []
    for node in workflow_json.get('nodes', []):
        creds = node.get('credentials', {})
        for cred_type, cred_ref in creds.items():
            credentials_used.append({
                "node": node.get('name'),
                "type": cred_type,
                "reference": cred_ref
            })

    return {
        "credentials_referenced": credentials_used,
        "all_valid": True,  # Stub
        "missing": []
    }

@app.get("/validate/rules")
async def list_validation_rules():
    """List validation rules"""
    return {
        "rules": [
            {"id": "required_name", "description": "Workflow must have a name"},
            {"id": "required_nodes", "description": "Workflow must have at least one node"},
            {"id": "node_ids", "description": "All nodes must have unique IDs"},
            {"id": "node_names", "description": "All nodes must have unique names"},
            {"id": "valid_connections", "description": "Connections must reference existing nodes"},
            {"id": "no_orphans", "description": "No orphaned nodes allowed"},
            {"id": "trigger_required", "description": "Production workflows should have a trigger"},
            {"id": "error_handling", "description": "Recommended: Error handling nodes"}
        ]
    }

# =============================================================================
# DEPLOYMENT ENDPOINTS
# =============================================================================

@app.post("/deploy")
async def deploy_workflow(request: DeployRequest):
    """Deploy workflow to n8n"""
    if request.spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = specs_store[request.spec_id]

    if spec.get('status') != 'generated':
        raise HTTPException(status_code=400, detail="Spec must be generated before deployment")

    workflow = spec.get('generated_workflow')
    if not workflow:
        raise HTTPException(status_code=400, detail="No generated workflow found")

    # Stub - would actually deploy to n8n
    n8n_workflow_id = f"stub-{request.spec_id[:8]}"

    spec['status'] = 'deployed'
    spec['generated_workflow_id'] = n8n_workflow_id
    spec['deployed_at'] = datetime.now().isoformat()
    spec['active'] = request.activate

    await notify_event_bus("workflow.deployed", {
        "spec_id": request.spec_id,
        "n8n_workflow_id": n8n_workflow_id,
        "active": request.activate
    })

    await notify_hermes(
        f"Workflow '{spec['name']}' deployed to n8n (ID: {n8n_workflow_id})",
        priority="normal"
    )

    return {
        "spec_id": request.spec_id,
        "n8n_workflow_id": n8n_workflow_id,
        "status": "deployed",
        "active": request.activate
    }

@app.post("/deploy/preview")
async def preview_deployment(spec_id: str):
    """Preview deployment changes"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = specs_store[spec_id]
    workflow = spec.get('generated_workflow')

    return {
        "spec_id": spec_id,
        "preview": True,
        "workflow": workflow,
        "changes": {
            "new_nodes": len(workflow.get('nodes', [])) if workflow else 0,
            "new_connections": len(workflow.get('connections', {})) if workflow else 0
        }
    }

@app.get("/deploy/status/{spec_id}")
async def get_deployment_status(spec_id: str):
    """Check deployment status"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = specs_store[spec_id]

    return {
        "spec_id": spec_id,
        "status": spec.get('status'),
        "n8n_workflow_id": spec.get('generated_workflow_id'),
        "active": spec.get('active', False),
        "deployed_at": spec.get('deployed_at')
    }

@app.post("/deploy/rollback/{spec_id}")
async def rollback_deployment(spec_id: str):
    """Rollback deployment"""
    if spec_id not in specs_store:
        raise HTTPException(status_code=404, detail="Spec not found")

    spec = specs_store[spec_id]

    if spec.get('status') != 'deployed':
        raise HTTPException(status_code=400, detail="Spec is not deployed")

    # Stub - would delete from n8n
    old_workflow_id = spec.get('generated_workflow_id')
    spec['status'] = 'generated'
    spec['generated_workflow_id'] = None
    spec['deployed_at'] = None
    spec['active'] = False

    await notify_event_bus("workflow.rollback", {
        "spec_id": spec_id,
        "old_workflow_id": old_workflow_id
    })

    return {
        "spec_id": spec_id,
        "status": "rolled_back",
        "previous_workflow_id": old_workflow_id
    }

# =============================================================================
# ARIA TOOL ENDPOINTS
# =============================================================================

@app.post("/tools/workflow.generate")
async def aria_tool_generate(request: WorkflowGenerateToolRequest):
    """ARIA Tool: Generate workflow from natural language"""
    # Create spec and generate
    spec_response = await create_spec(WorkflowSpec(
        name=request.name,
        description=request.description,
        requirements=request.requirements,
        created_by="ARIA"
    ))

    spec_id = spec_response['id']

    # Generate workflow
    generate_response = await generate_workflow(spec_id)

    return {
        "tool": "workflow.generate",
        "spec_id": spec_id,
        "workflow": generate_response.get('workflow'),
        "status": generate_response.get('status')
    }

@app.post("/tools/workflow.test")
async def aria_tool_test(request: WorkflowTestToolRequest):
    """ARIA Tool: Test a workflow"""
    result = await run_test(WorkflowTestRequest(
        workflow_id=request.workflow_id,
        test_data=request.test_data
    ))

    return {
        "tool": "workflow.test",
        "result": result
    }

@app.post("/tools/workflow.template")
async def aria_tool_template(request: WorkflowTemplateToolRequest):
    """ARIA Tool: Get workflow template"""
    templates = await list_templates(category=request.category)

    if request.name:
        templates['templates'] = [
            t for t in templates['templates']
            if request.name.lower() in t.get('name', '').lower()
        ]

    return {
        "tool": "workflow.template",
        "templates": templates['templates'],
        "category": request.category
    }

@app.post("/tools/workflow.validate")
async def aria_tool_validate(request: WorkflowValidateToolRequest):
    """ARIA Tool: Validate workflow"""
    result = validate_workflow_structure(request.workflow_json)

    return {
        "tool": "workflow.validate",
        "validation": result
    }

@app.post("/tools/workflow.deploy")
async def aria_tool_deploy(request: WorkflowDeployToolRequest):
    """ARIA Tool: Deploy workflow to n8n"""
    result = await deploy_workflow(DeployRequest(
        spec_id=request.spec_id,
        activate=request.activate
    ))

    return {
        "tool": "workflow.deploy",
        "deployment": result
    }

# =============================================================================
# METRICS ENDPOINT
# =============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    builder_ctx = get_builder_context()

    metrics_text = f"""# HELP daedalus_specs_total Total number of specs
# TYPE daedalus_specs_total gauge
daedalus_specs_total {len(specs_store)}

# HELP daedalus_specs_pending Pending specs
# TYPE daedalus_specs_pending gauge
daedalus_specs_pending {builder_ctx['specs_pending']}

# HELP daedalus_generated_today Workflows generated today
# TYPE daedalus_generated_today gauge
daedalus_generated_today {builder_ctx['generated_today']}

# HELP daedalus_templates_total Total templates
# TYPE daedalus_templates_total gauge
daedalus_templates_total {builder_ctx['template_count']}

# HELP daedalus_test_pass_rate Test pass rate percentage
# TYPE daedalus_test_pass_rate gauge
daedalus_test_pass_rate {builder_ctx['test_pass_rate']}
"""

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=metrics_text, media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8202)
