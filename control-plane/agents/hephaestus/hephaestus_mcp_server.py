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
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASS = os.getenv("N8N_PASS", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")

ALLOWED_PATHS = [
    "/opt/leveredge/",
    "/home/damon/shared/",
    "/tmp/leveredge/",
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
            description="Call another LeverEdge agent (CHRONOS, HADES, AEGIS, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": ["chronos", "hades", "aegis", "atlas"],
                        "description": "Which agent to call"
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to perform"
                    },
                    "payload": {
                        "type": "object",
                        "description": "Additional data to send",
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
                    auth=(N8N_USER, N8N_PASS),
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
                    auth=(N8N_USER, N8N_PASS),
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
                    auth=(N8N_USER, N8N_PASS),
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

            agent_urls = {
                "chronos": "https://control.n8n.leveredgeai.com/webhook/chronos",
                "hades": "https://control.n8n.leveredgeai.com/webhook/hades",
                "aegis": "https://control.n8n.leveredgeai.com/webhook/aegis",
                "atlas": "https://control.n8n.leveredgeai.com/webhook/atlas",
            }

            url = agent_urls.get(agent)
            if not url:
                return [TextContent(type="text", text=f"ERROR: Unknown agent: {agent}")]

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json={"action": action, **payload},
                    timeout=90.0
                )

                await log_to_event_bus("agent_called", agent, {"action": action})
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

        else:
            return [TextContent(type="text", text=f"ERROR: Unknown tool: {name}")]

    except Exception as e:
        await log_to_event_bus("tool_error", name, {"error": str(e)})
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]


# ============ SSE TRANSPORT ============

sse = SseServerTransport("/messages/")

async def handle_sse(request):
    """Handle SSE connections from Claude"""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run(
            streams[0], streams[1], mcp.create_initialization_options()
        )

async def handle_messages(request):
    """Handle POST messages"""
    await sse.handle_post_message(request.scope, request.receive, request._send)

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

# Create Starlette app with routes
app = Starlette(
    debug=True,
    routes=[
        Route("/health", health),
        Route("/sse", handle_sse),
        Route("/messages/", handle_messages, methods=["POST"]),
    ]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
