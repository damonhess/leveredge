#!/usr/bin/env python3
"""
HEPHAESTUS - Actual MCP Server
Speaks MCP protocol (JSON-RPC over SSE)
Claude Web connectors can connect to this.
"""

import os
import json
import subprocess
import httpx
from pathlib import Path
from datetime import datetime

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, CallToolResult
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse

# Configuration
N8N_URLS = {
    "control": os.getenv("N8N_CONTROL_URL", "https://control.n8n.leveredgeai.com"),
    "prod": os.getenv("N8N_PROD_URL", "https://n8n.leveredgeai.com"),
}
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")

# OLYMPUS Orchestration URLs
SENTINEL_URL = os.getenv("SENTINEL_URL", "http://localhost:8019")
ATLAS_URL = os.getenv("ATLAS_URL", "http://localhost:8007")

def get_n8n_headers():
    """Get headers for n8n API authentication"""
    return {"X-N8N-API-KEY": N8N_API_KEY}

ALLOWED_PATHS = [
    "/opt/leveredge",
    "/home/damon/shared",
    "/tmp/leveredge",
]

# Initialize MCP Server
mcp = Server("hephaestus")

# ============ HELPER FUNCTIONS ============

async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    """Log action to Event Bus"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "HEPHAESTUS",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

def check_path_allowed(path: str) -> bool:
    """Check if path is within allowed directories"""
    path = os.path.abspath(path)
    return any(path.startswith(allowed) for allowed in ALLOWED_PATHS)

# ============ MCP TOOLS ============

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of available tools"""
    return [
        Tool(
            name="create_file",
            description="Create a file at the specified path with given content. Only works within /opt/leveredge/",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path where file should be created"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="read_file",
            description="Read contents of a file. Only works within /opt/leveredge/",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path of file to read"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="list_directory",
            description="List contents of a directory. Only works within /opt/leveredge/",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path of directory to list"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="run_command",
            description="Execute a whitelisted shell command. Limited to safe operations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory for command",
                        "default": "/opt/leveredge"
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="list_workflows",
            description="List all n8n workflows in the specified instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "enum": ["control", "prod"],
                        "description": "Which n8n instance to query",
                        "default": "control"
                    }
                }
            }
        ),
        Tool(
            name="create_workflow",
            description="Create a new n8n workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the workflow"
                    },
                    "nodes": {
                        "type": "array",
                        "description": "Array of node configurations"
                    },
                    "connections": {
                        "type": "object",
                        "description": "Node connections object"
                    },
                    "target": {
                        "type": "string",
                        "enum": ["control", "prod"],
                        "default": "control"
                    }
                },
                "required": ["name", "nodes", "connections"]
            }
        ),
        Tool(
            name="activate_workflow",
            description="Activate an n8n workflow by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ID of workflow to activate"
                    },
                    "target": {
                        "type": "string",
                        "enum": ["control", "prod"],
                        "default": "control"
                    }
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="call_agent",
            description="Call another LeverEdge agent. SCHOLAR for research (deep-research, market-size, competitors). CHIRON for planning (sprint-plan, break-down, prioritize, chat). Also CHRONOS, HADES, AEGIS, ATLAS for infrastructure.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": ["scholar", "chiron", "chronos", "hades", "aegis", "atlas"],
                        "description": "Which agent to call"
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to perform. SCHOLAR: deep-research, market-size, competitors, niche, lead, validate-assumption. CHIRON: sprint-plan, break-down, prioritize, chat, decide, fear-check."
                    },
                    "payload": {
                        "type": "object",
                        "description": "Additional data to send. SCHOLAR deep-research: {question: '...'}. CHIRON sprint-plan: {goals: [...], time_available: '...'}.",
                        "default": {}
                    }
                },
                "required": ["agent", "action"]
            }
        ),
        Tool(
            name="git_commit",
            description="Commit changes to git repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to git repository",
                        "default": "/opt/leveredge"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to add (empty for all)",
                        "default": []
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="orchestrate",
            description="Execute orchestration through OLYMPUS (ATLAS/SENTINEL). Run pre-defined chains like research-and-plan, or single agent calls. Use this to have agents do work automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chain_name": {
                        "type": "string",
                        "description": "Pre-defined chain to execute",
                        "enum": ["research-and-plan", "validate-and-decide", "comprehensive-market-analysis", "niche-evaluation", "weekly-planning", "fear-to-action"]
                    },
                    "input": {
                        "type": "object",
                        "description": "Input data for the chain. For research-and-plan: {topic: '...'}. For validate-and-decide: {assumption: '...'}. For fear-to-action: {situation: '...'}"
                    },
                    "agent": {
                        "type": "string",
                        "description": "For single agent calls: scholar, chiron, hermes, chronos, hades, aegis, argus"
                    },
                    "action": {
                        "type": "string",
                        "description": "For single agent calls: the action to perform (e.g., deep-research, sprint-plan, chat)"
                    },
                    "params": {
                        "type": "object",
                        "description": "Parameters for single agent action"
                    }
                }
            }
        ),
        Tool(
            name="list_chains",
            description="List available orchestration chains that can be used with the orchestrate tool",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="list_agents",
            description="List available agents that can be called through orchestration",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    try:
        if name == "create_file":
            path = arguments["path"]
            content = arguments["content"]

            if not check_path_allowed(path):
                return [TextContent(type="text", text=f"ERROR: Path not allowed: {path}")]

            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

            await log_to_event_bus("file_created", path, {"size": len(content)})
            return [TextContent(type="text", text=f"Created {path} ({len(content)} bytes)")]

        elif name == "read_file":
            path = arguments["path"]

            if not check_path_allowed(path):
                return [TextContent(type="text", text=f"ERROR: Path not allowed: {path}")]

            content = Path(path).read_text()
            return [TextContent(type="text", text=content)]

        elif name == "list_directory":
            path = arguments["path"]

            if not check_path_allowed(path):
                return [TextContent(type="text", text=f"ERROR: Path not allowed: {path}")]

            p = Path(path)
            if not p.is_dir():
                return [TextContent(type="text", text=f"ERROR: Not a directory: {path}")]

            entries = []
            for entry in sorted(p.iterdir()):
                entry_type = "dir" if entry.is_dir() else "file"
                entries.append(f"{entry_type}: {entry.name}")

            return [TextContent(type="text", text="\n".join(entries))]

        elif name == "run_command":
            command = arguments["command"]
            working_dir = arguments.get("working_dir", "/opt/leveredge")

            # Whitelist check
            safe_prefixes = ["ls", "cat", "grep", "find", "head", "tail", "git status", "git log", "git diff", "docker ps", "docker logs"]
            if not any(command.strip().startswith(prefix) for prefix in safe_prefixes):
                await log_to_event_bus("command_blocked", command, {"reason": "not whitelisted"})
                return [TextContent(type="text", text=f"ERROR: Command not in whitelist. Allowed: {safe_prefixes}")]

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=working_dir
            )

            await log_to_event_bus("command_executed", command, {"exit_code": result.returncode})

            output = f"Exit code: {result.returncode}\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}"

            return [TextContent(type="text", text=output)]

        elif name == "list_workflows":
            target = arguments.get("target", "control")
            n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{n8n_url}/api/v1/workflows",
                    headers=get_n8n_headers(),
                    timeout=30.0
                )

                if resp.status_code != 200:
                    return [TextContent(type="text", text=f"ERROR: {resp.status_code} - {resp.text}")]

                workflows = resp.json().get("data", [])
                lines = [f"Found {len(workflows)} workflows:\n"]
                for wf in workflows:
                    status = "✓" if wf.get("active") else "○"
                    lines.append(f"{status} {wf['name']} (ID: {wf['id']})")

                return [TextContent(type="text", text="\n".join(lines))]

        elif name == "create_workflow":
            target = arguments.get("target", "control")
            n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

            workflow_data = {
                "name": arguments["name"],
                "nodes": arguments["nodes"],
                "connections": arguments["connections"],
                "settings": {}
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{n8n_url}/api/v1/workflows",
                    headers=get_n8n_headers(),
                    json=workflow_data,
                    timeout=30.0
                )

                if resp.status_code not in [200, 201]:
                    return [TextContent(type="text", text=f"ERROR: {resp.status_code} - {resp.text}")]

                result = resp.json()
                await log_to_event_bus("workflow_created", result.get("id"), {"name": arguments["name"]})
                return [TextContent(type="text", text=f"Created workflow '{arguments['name']}' with ID: {result.get('id')}")]

        elif name == "activate_workflow":
            target = arguments.get("target", "control")
            workflow_id = arguments["workflow_id"]
            n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"{n8n_url}/api/v1/workflows/{workflow_id}",
                    headers=get_n8n_headers(),
                    json={"active": True},
                    timeout=10.0
                )

                if resp.status_code != 200:
                    return [TextContent(type="text", text=f"ERROR: {resp.status_code} - {resp.text}")]

                await log_to_event_bus("workflow_activated", workflow_id)
                return [TextContent(type="text", text=f"Activated workflow {workflow_id}")]

        elif name == "call_agent":
            agent = arguments["agent"].lower()
            action = arguments["action"]
            payload = arguments.get("payload", {})

            # Webhook-based agents (n8n workflows)
            webhook_agents = {
                "chronos": "https://control.n8n.leveredgeai.com/webhook/chronos",
                "hades": "https://control.n8n.leveredgeai.com/webhook/hades",
                "aegis": "https://control.n8n.leveredgeai.com/webhook/aegis",
                "atlas": "https://control.n8n.leveredgeai.com/webhook/atlas",
            }

            # HTTP-based agents (Python FastAPI services)
            http_agents = {
                "scholar": {"base_url": "http://scholar:8018", "port": 8018},
                "chiron": {"base_url": "http://chiron:8017", "port": 8017},
            }

            # Check if HTTP-based agent
            if agent in http_agents:
                agent_config = http_agents[agent]
                # Map action to endpoint: deep_research -> /deep-research
                endpoint = f"/{action.replace('_', '-')}"
                url = f"{agent_config['base_url']}{endpoint}"

                async with httpx.AsyncClient() as client:
                    try:
                        resp = await client.post(
                            url,
                            json=payload,
                            timeout=120.0  # Longer timeout for LLM agents
                        )
                        await log_to_event_bus("agent_called", agent, {"action": action, "type": "http"})

                        # Parse and format response
                        try:
                            data = resp.json()
                            # Extract main content field
                            content = (data.get("research") or
                                      data.get("sprint_plan") or
                                      data.get("breakdown") or
                                      data.get("prioritization") or
                                      data.get("response") or
                                      data.get("fear_analysis") or
                                      data.get("decision_analysis") or
                                      data.get("hype") or
                                      json.dumps(data, indent=2))
                            return [TextContent(type="text", text=f"**{agent.upper()}** ({action}):\n\n{content}")]
                        except:
                            return [TextContent(type="text", text=f"**{agent.upper()}** ({action}):\n\n{resp.text}")]

                    except httpx.TimeoutException:
                        await log_to_event_bus("agent_timeout", agent, {"action": action})
                        return [TextContent(type="text", text=f"ERROR: Agent {agent} timed out")]
                    except httpx.ConnectError:
                        return [TextContent(type="text", text=f"ERROR: Cannot connect to agent {agent}. Is it running?")]
                    except Exception as e:
                        await log_to_event_bus("agent_error", agent, {"action": action, "error": str(e)})
                        return [TextContent(type="text", text=f"ERROR: Agent {agent} error: {str(e)}")]

            # Check webhook-based agent
            url = webhook_agents.get(agent)
            if not url:
                available = list(webhook_agents.keys()) + list(http_agents.keys())
                return [TextContent(type="text", text=f"ERROR: Unknown agent: {agent}. Available: {', '.join(available)}")]

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={"action": action, **payload},
                    timeout=90.0
                )

                await log_to_event_bus("agent_called", agent, {"action": action, "type": "webhook"})
                return [TextContent(type="text", text=f"Agent {agent} response:\n{resp.text}")]

        elif name == "git_commit":
            repo_path = arguments.get("repo_path", "/opt/leveredge")
            message = arguments["message"]
            files = arguments.get("files", [])

            if not check_path_allowed(repo_path):
                return [TextContent(type="text", text=f"ERROR: Path not allowed: {repo_path}")]

            # Add files
            add_cmd = f"git add {' '.join(files) if files else '.'}"
            subprocess.run(add_cmd, shell=True, cwd=repo_path, check=True)

            # Commit
            result = subprocess.run(
                f'git commit -m "{message}"',
                shell=True,
                cwd=repo_path,
                capture_output=True,
                text=True
            )

            await log_to_event_bus("git_commit", repo_path, {"message": message})
            return [TextContent(type="text", text=f"Git commit result:\n{result.stdout}\n{result.stderr}")]

        elif name == "orchestrate":
            # Determine request type
            if arguments.get("chain_name"):
                # Chain execution
                request = {
                    "source": "hephaestus",
                    "chain_name": arguments["chain_name"],
                    "input": arguments.get("input", {})
                }
            elif arguments.get("agent") and arguments.get("action"):
                # Single agent call
                request = {
                    "source": "hephaestus",
                    "type": "single",
                    "steps": [{
                        "id": f"{arguments['agent']}_{arguments['action']}",
                        "agent": arguments["agent"],
                        "action": arguments["action"],
                        "params": arguments.get("params", {})
                    }]
                }
            else:
                return [TextContent(type="text", text="ERROR: Must provide either chain_name or agent+action")]

            # Execute through SENTINEL with fallback to ATLAS
            async with httpx.AsyncClient(timeout=180.0) as client:
                try:
                    response = await client.post(
                        f"{SENTINEL_URL}/orchestrate",
                        json=request
                    )
                    result = response.json()
                except httpx.ConnectError:
                    # Fallback to ATLAS directly if SENTINEL is down
                    try:
                        response = await client.post(
                            f"{ATLAS_URL}/execute",
                            json=request
                        )
                        result = response.json()
                        result["_fallback"] = "atlas_direct"
                    except Exception as e:
                        return [TextContent(type="text", text=f"ERROR: Both SENTINEL and ATLAS unreachable: {e}")]
                except Exception as e:
                    return [TextContent(type="text", text=f"ERROR: Orchestration failed: {e}")]

                # Format response
                if result.get("status") == "failed":
                    error_msg = result.get("error", "Unknown error")
                    errors = result.get("errors", [])
                    if errors:
                        error_msg = "\n".join([e.get("error", str(e)) for e in errors])
                    return [TextContent(type="text", text=f"Orchestration failed:\n{error_msg}")]

                # Extract useful content
                outputs = result.get("step_outputs", result.get("step_results", {}))
                formatted_parts = []

                for step_id, step in outputs.items():
                    output = step.get("output", step)
                    content = (output.get("response") or
                              output.get("research") or
                              output.get("sprint_plan") or
                              output.get("pricing_strategy") or
                              output.get("fear_analysis") or
                              output.get("hype") or
                              output.get("daily_priorities") or
                              json.dumps(output, indent=2) if isinstance(output, dict) else str(output))
                    agent = step.get("agent", step_id).upper()
                    formatted_parts.append(f"**{agent}:**\n{content}")

                response_text = "\n\n---\n\n".join(formatted_parts)

                # Add metadata
                cost = result.get("total_cost", 0)
                duration = result.get("duration_ms", 0)
                routed_to = result.get("_routed_to", "unknown")
                fallback = result.get("_fallback", "")

                meta = []
                if cost > 0:
                    meta.append(f"${cost:.4f}")
                if duration > 0:
                    meta.append(f"{duration}ms")
                meta.append(f"via {routed_to}")
                if fallback:
                    meta.append(f"(fallback: {fallback})")

                if meta:
                    response_text += f"\n\n*{' | '.join(meta)}*"

                await log_to_event_bus("orchestration_executed", arguments.get("chain_name") or f"{arguments.get('agent')}/{arguments.get('action')}", {"status": result.get("status")})
                return [TextContent(type="text", text=response_text)]

        elif name == "list_chains":
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(f"{ATLAS_URL}/chains")
                    chains = response.json()
                    return [TextContent(type="text", text=json.dumps(chains, indent=2))]
                except:
                    # Fallback list
                    chains = {
                        "chains": [
                            {"name": "research-and-plan", "description": "Research topic, then create action plan"},
                            {"name": "validate-and-decide", "description": "Validate assumption, then decide next steps"},
                            {"name": "comprehensive-market-analysis", "description": "Parallel research, then synthesis"},
                            {"name": "niche-evaluation", "description": "Compare niches, recommend best"},
                            {"name": "weekly-planning", "description": "Review, research blockers, plan week"},
                            {"name": "fear-to-action", "description": "Analyze fear, find evidence, create action plan"}
                        ]
                    }
                    return [TextContent(type="text", text=json.dumps(chains, indent=2))]

        elif name == "list_agents":
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(f"{ATLAS_URL}/agents")
                    agents = response.json()
                    return [TextContent(type="text", text=json.dumps(agents, indent=2))]
                except:
                    # Fallback list
                    agents = {
                        "agents": [
                            {"name": "scholar", "description": "Market research with web search"},
                            {"name": "chiron", "description": "Business strategy and ADHD planning"},
                            {"name": "hermes", "description": "Notifications"},
                            {"name": "chronos", "description": "Backups"},
                            {"name": "hades", "description": "Rollback"},
                            {"name": "aegis", "description": "Credentials"},
                            {"name": "argus", "description": "Monitoring"},
                            {"name": "aloy", "description": "Audit"},
                            {"name": "athena", "description": "Documentation"}
                        ]
                    }
                    return [TextContent(type="text", text=json.dumps(agents, indent=2))]

        else:
            return [TextContent(type="text", text=f"ERROR: Unknown tool: {name}")]

    except Exception as e:
        await log_to_event_bus("tool_error", name, {"error": str(e)})
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]


# ============ SSE TRANSPORT ============

sse = SseServerTransport("/messages/")

async def health(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "agent": "HEPHAESTUS",
        "protocol": "MCP",
        "transport": "SSE",
        "port": 8011,
        "timestamp": datetime.utcnow().isoformat()
    })

# Create Starlette app with just health endpoint
starlette_app = Starlette(
    debug=True,
    routes=[
        Route("/health", health),
    ]
)

# CORS configuration for Claude.ai
CORS_HEADERS = [
    [b"access-control-allow-origin", b"https://claude.ai"],
    [b"access-control-allow-methods", b"GET, POST, OPTIONS"],
    [b"access-control-allow-headers", b"Content-Type, Authorization, X-Requested-With, Accept, Cache-Control"],
    [b"access-control-allow-credentials", b"true"],
    [b"access-control-max-age", b"86400"],
]

async def send_with_cors(send, scope):
    """Wrap send to add CORS headers to responses"""
    async def cors_send(message):
        if message["type"] == "http.response.start":
            headers = list(message.get("headers", []))
            headers.extend(CORS_HEADERS)
            message = {**message, "headers": headers}
        await send(message)
    return cors_send

async def receive_body(receive):
    """Helper to receive full request body"""
    body = b""
    while True:
        message = await receive()
        if message["type"] == "http.request":
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        elif message["type"] == "http.disconnect":
            break
    return body


async def send_json_response(send, status, data, content_type="application/json"):
    """Helper to send JSON response with CORS headers"""
    body = json.dumps(data).encode() if isinstance(data, dict) else data
    headers = list(CORS_HEADERS) + [[b"content-type", content_type.encode()]]
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": headers,
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


# Main ASGI app that properly routes SSE connections
# The bug was using request._send which doesn't exist on Starlette Request objects
# This raw ASGI wrapper gets scope, receive, send directly from the ASGI interface
async def app(scope, receive, send):
    """Main ASGI app with SSE support, OAuth discovery, and Claude.ai compatibility"""
    if scope["type"] != "http":
        # Handle lifespan events etc
        return

    path = scope.get("path", "")
    method = scope.get("method", "GET")

    # Handle CORS preflight (OPTIONS)
    if method == "OPTIONS":
        await send({
            "type": "http.response.start",
            "status": 204,
            "headers": CORS_HEADERS,
        })
        await send({
            "type": "http.response.body",
            "body": b"",
        })
        return

    # Wrap send to add CORS headers to all responses
    cors_send = await send_with_cors(send, scope)

    # Health check
    if path == "/health":
        await starlette_app(scope, receive, cors_send)
        return

    # OAuth discovery - protected resource metadata
    if path == "/.well-known/oauth-protected-resource":
        discovery = {
            "resource": "https://hephaestus.leveredgeai.com",
            "authorization_servers": ["https://hephaestus.leveredgeai.com"],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["mcp:tools"]
        }
        await send_json_response(cors_send, 200, discovery)
        return

    # OAuth discovery - authorization server metadata
    if path == "/.well-known/oauth-authorization-server":
        metadata = {
            "issuer": "https://hephaestus.leveredgeai.com",
            "authorization_endpoint": "https://hephaestus.leveredgeai.com/authorize",
            "token_endpoint": "https://hephaestus.leveredgeai.com/token",
            "registration_endpoint": "https://hephaestus.leveredgeai.com/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic", "none"],
            "scopes_supported": ["mcp:tools"],
            "code_challenge_methods_supported": ["S256"]
        }
        await send_json_response(cors_send, 200, metadata)
        return

    # Dynamic client registration (auto-approve for now)
    if path == "/register" and method == "POST":
        body = await receive_body(receive)

        try:
            client_metadata = json.loads(body) if body else {}
        except:
            client_metadata = {}

        # Generate client credentials
        import secrets
        client_id = f"claude_{secrets.token_hex(16)}"
        client_secret = secrets.token_hex(32)

        response = {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_id_issued_at": int(datetime.utcnow().timestamp()),
            "client_secret_expires_at": 0,  # Never expires
            "redirect_uris": client_metadata.get("redirect_uris", []),
            "grant_types": ["authorization_code", "client_credentials"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_basic"
        }
        await send_json_response(cors_send, 201, response)
        return

    # Token endpoint (issue tokens)
    if path == "/token" and method == "POST":
        import secrets
        token = secrets.token_hex(32)
        response = {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "mcp:tools"
        }
        await send_json_response(cors_send, 200, response)
        return

    # Authorization endpoint (for OAuth flow)
    if path == "/authorize":
        from urllib.parse import parse_qs
        query = scope.get("query_string", b"").decode()
        params = parse_qs(query)
        redirect_uri = params.get("redirect_uri", [""])[0]
        state = params.get("state", [""])[0]

        if redirect_uri:
            import secrets
            code = secrets.token_hex(16)
            callback = f"{redirect_uri}?code={code}&state={state}"
            await send({
                "type": "http.response.start",
                "status": 302,
                "headers": [[b"location", callback.encode()]]
            })
            await send({"type": "http.response.body", "body": b""})
            return

        await send_json_response(cors_send, 400, b"Missing redirect_uri", "text/plain")
        return

    # SSE endpoint - handle at BOTH / and /sse for Claude.ai compatibility
    if path in ["/", "/sse"]:
        if method == "GET":
            # Raw ASGI SSE handler - properly passes send callable
            async with sse.connect_sse(scope, receive, cors_send) as streams:
                await mcp.run(
                    streams[0], streams[1], mcp.create_initialization_options()
                )
        elif method == "POST":
            # Message handling
            await sse.handle_post_message(scope, receive, cors_send)
        return

    # Messages endpoint
    if path.startswith("/messages"):
        # Raw ASGI message handler - properly passes send callable
        await sse.handle_post_message(scope, receive, cors_send)
        return

    # 404 Not Found
    await cors_send({
        "type": "http.response.start",
        "status": 404,
        "headers": [[b"content-type", b"text/plain"]],
    })
    await cors_send({
        "type": "http.response.body",
        "body": b"Not Found",
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
