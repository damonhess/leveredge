#!/usr/bin/env python3
"""
COACH CHANNEL MCP Server - Claude Code Side
Allows Claude Code to receive instructions and respond to Launch Coach.

Usage:
  python coach_channel_mcp.py

MCP Config (add to ~/.config/claude-code/config.json):
{
  "mcpServers": {
    "coach-channel": {
      "command": "python",
      "args": ["/opt/leveredge/control-plane/agents/coach-channel/coach_channel_mcp.py"]
    }
  }
}
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional

import httpx

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54321")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0")


def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


async def coach_receive_instructions(limit: int = 10, mark_read: bool = True) -> dict:
    """Check for instructions from Launch Coach."""
    async with httpx.AsyncClient() as client:
        # Get pending messages to CLAUDE_CODE
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/coach_channel",
            headers=get_headers(),
            params={
                "to_agent": "eq.CLAUDE_CODE",
                "status": "eq.pending",
                "order": "created_at.asc",
                "limit": limit
            }
        )
        messages = response.json() if response.status_code == 200 else []

        # Mark as read
        if mark_read and messages:
            for m in messages:
                await client.patch(
                    f"{SUPABASE_URL}/rest/v1/coach_channel?id=eq.{m['id']}",
                    headers=get_headers(),
                    json={"status": "read", "read_at": datetime.now(timezone.utc).isoformat()}
                )

        return {
            "instructions": messages,
            "count": len(messages),
            "coach_says": messages[0]["content"] if messages else "No pending instructions"
        }


async def coach_respond(
    message: str,
    message_type: str = "response",
    subject: Optional[str] = None,
    reply_to: Optional[str] = None,
    context: Optional[dict] = None
) -> dict:
    """Send a response back to Launch Coach."""
    async with httpx.AsyncClient() as client:
        # Get thread_id if replying
        thread_id = None
        if reply_to:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/coach_channel",
                headers=get_headers(),
                params={"id": f"eq.{reply_to}", "select": "thread_id"}
            )
            rows = resp.json() if resp.status_code == 200 else []
            if rows:
                thread_id = rows[0].get("thread_id")

        payload = {
            "from_agent": "CLAUDE_CODE",
            "to_agent": "LAUNCH_COACH",
            "message_type": message_type,
            "subject": subject,
            "content": message,
            "reply_to": reply_to,
            "thread_id": thread_id,
            "context": context or {},
            "status": "pending"
        }

        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/coach_channel",
            headers=get_headers(),
            json=payload
        )

        if response.status_code in [200, 201]:
            data = response.json()
            msg_id = data[0]["id"] if isinstance(data, list) else data.get("id")
            return {"status": "sent", "message_id": msg_id, "to": "LAUNCH_COACH"}
        else:
            return {"status": "error", "error": response.text}


async def coach_acknowledge(message_id: str, notes: Optional[str] = None) -> dict:
    """Acknowledge receipt of an instruction."""
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{SUPABASE_URL}/rest/v1/coach_channel?id=eq.{message_id}",
            headers=get_headers(),
            json={"status": "acknowledged", "acknowledged_at": datetime.now(timezone.utc).isoformat()}
        )

        if notes:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/coach_channel",
                headers=get_headers(),
                json={
                    "from_agent": "CLAUDE_CODE",
                    "to_agent": "LAUNCH_COACH",
                    "message_type": "status",
                    "content": notes,
                    "reply_to": message_id,
                    "status": "pending"
                }
            )

        return {"status": "acknowledged", "message_id": message_id}


# ============ MCP PROTOCOL HANDLER ============

TOOLS = [
    {
        "name": "coach_receive_instructions",
        "description": "Check for instructions from Launch Coach. Call this at the start of sessions and periodically to see if you have work to do.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max messages to return", "default": 10},
                "mark_read": {"type": "boolean", "description": "Mark as read", "default": True}
            }
        }
    },
    {
        "name": "coach_respond",
        "description": "Send a response back to Launch Coach. Use this to report progress, ask questions, or mark work complete.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Your response message"},
                "message_type": {
                    "type": "string",
                    "enum": ["response", "status", "question", "completed"],
                    "description": "Type of response",
                    "default": "response"
                },
                "subject": {"type": "string", "description": "Subject line"},
                "reply_to": {"type": "string", "description": "Message ID you're replying to"}
            },
            "required": ["message"]
        }
    },
    {
        "name": "coach_acknowledge",
        "description": "Acknowledge receipt of an instruction. Use this to confirm you've received work.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID of message to acknowledge"},
                "notes": {"type": "string", "description": "Optional acknowledgment notes"}
            },
            "required": ["message_id"]
        }
    }
]


async def handle_tool_call(name: str, arguments: dict) -> str:
    """Handle MCP tool calls."""
    try:
        if name == "coach_receive_instructions":
            result = await coach_receive_instructions(
                limit=arguments.get("limit", 10),
                mark_read=arguments.get("mark_read", True)
            )

            if result["count"] == 0:
                return "📭 No pending instructions from Launch Coach"

            lines = [f"📬 **{result['count']} instruction(s) from Launch Coach**\n"]
            for i, msg in enumerate(result["instructions"], 1):
                lines.append(f"**{i}. [{msg.get('message_type', 'instruction')}]** {msg.get('subject') or 'No subject'}")
                lines.append(f"   ID: `{msg['id']}`")
                lines.append(f"   {msg.get('content', '')[:500]}")
                if msg.get("reference_id"):
                    lines.append(f"   Reference: {msg['reference_id']}")
                lines.append("")

            return "\n".join(lines)

        elif name == "coach_respond":
            result = await coach_respond(
                message=arguments["message"],
                message_type=arguments.get("message_type", "response"),
                subject=arguments.get("subject"),
                reply_to=arguments.get("reply_to")
            )

            if result["status"] == "sent":
                return f"✅ Response sent to Launch Coach\nMessage ID: `{result['message_id']}`"
            else:
                return f"❌ Failed to send: {result.get('error', 'Unknown error')}"

        elif name == "coach_acknowledge":
            result = await coach_acknowledge(
                message_id=arguments["message_id"],
                notes=arguments.get("notes")
            )
            return f"✅ Acknowledged: {result['message_id']}"

        else:
            return f"Unknown tool: {name}"

    except Exception as e:
        return f"Error: {str(e)}"


def send_response(response: dict):
    """Send JSON-RPC response to stdout."""
    print(json.dumps(response), flush=True)


def send_error(id: int, code: int, message: str):
    """Send JSON-RPC error response."""
    send_response({
        "jsonrpc": "2.0",
        "id": id,
        "error": {"code": code, "message": message}
    })


async def main():
    """MCP stdio server main loop."""
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            method = request.get("method")
            req_id = request.get("id")
            params = request.get("params", {})

            if method == "initialize":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "coach-channel",
                            "version": "1.0.0"
                        }
                    }
                })

            elif method == "notifications/initialized":
                pass  # No response needed

            elif method == "tools/list":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": TOOLS}
                })

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await handle_tool_call(tool_name, arguments)
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                })

            else:
                send_error(req_id, -32601, f"Method not found: {method}")

        except json.JSONDecodeError:
            send_error(0, -32700, "Parse error")
        except Exception as e:
            send_error(request.get("id", 0), -32603, str(e))


if __name__ == "__main__":
    asyncio.run(main())
