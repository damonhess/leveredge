#!/usr/bin/env python3
"""
HERMES - Notification & Approval Agent
Port: 8014

Handles Telegram notifications for human-in-the-loop approvals.
"""

import os
import json
import httpx
import asyncio
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

app = FastAPI(title="HERMES", description="Notification & Approval Agent", version="1.0.0")

# Configuration
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DB_PATH = os.getenv("HERMES_DB_PATH", "/app/data/hermes.db")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_APPROVAL_TIMEOUT", "300"))  # 5 minutes

# Try to load token from file if not in env
if not TELEGRAM_TOKEN:
    token_file = Path("/run/secrets/telegram_token")
    if token_file.exists():
        TELEGRAM_TOKEN = token_file.read_text().strip()
    else:
        # Try local file
        local_token = Path("/app/.telegram_token")
        if local_token.exists():
            TELEGRAM_TOKEN = local_token.read_text().strip()

# Try to load chat ID from file if not in env
if not TELEGRAM_CHAT_ID:
    chat_file = Path("/run/secrets/telegram_chat_id")
    if chat_file.exists():
        TELEGRAM_CHAT_ID = chat_file.read_text().strip()
    else:
        local_chat = Path("/app/.telegram_chat_id")
        if local_chat.exists():
            TELEGRAM_CHAT_ID = local_chat.read_text().strip()

# Pending approvals in memory (for quick lookup)
pending_approvals: Dict[str, Dict] = {}

# Database setup
def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id TEXT UNIQUE NOT NULL,
            message TEXT NOT NULL,
            priority TEXT DEFAULT 'normal',
            channel TEXT DEFAULT 'telegram',
            status TEXT DEFAULT 'sent',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            delivered_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT UNIQUE NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            requesting_agent TEXT,
            status TEXT DEFAULT 'pending',
            approved INTEGER,
            responder TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            responded_at TEXT,
            timeout_seconds INTEGER DEFAULT 300
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Models
class NotifyRequest(BaseModel):
    message: str
    priority: str = "normal"  # low, normal, high, critical
    channel: str = "telegram"

class ApprovalRequest(BaseModel):
    action: str
    details: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 300
    requesting_agent: str = "unknown"

class ApprovalResponse(BaseModel):
    approval_id: str
    approved: bool
    responder: Optional[str] = None
    response_time_seconds: Optional[float] = None

# Helpers
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "HERMES",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

def get_priority_emoji(priority: str) -> str:
    return {
        "low": "📋",
        "normal": "📨",
        "high": "⚠️",
        "critical": "🚨"
    }.get(priority, "📨")

async def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram Bot API"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured (missing token or chat_id)")
        return False

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": parse_mode
                },
                timeout=10.0
            )
            return resp.status_code == 200
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False

async def get_telegram_updates(offset: int = 0) -> List[Dict]:
    """Get updates from Telegram Bot API"""
    if not TELEGRAM_TOKEN:
        return []

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 5},
                timeout=15.0
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", [])
    except Exception as e:
        print(f"Failed to get Telegram updates: {e}")
    return []

# Background task to poll for approval responses
last_update_id = 0

async def poll_telegram_responses():
    """Poll Telegram for approval responses"""
    global last_update_id

    while True:
        try:
            updates = await get_telegram_updates(offset=last_update_id + 1)

            for update in updates:
                last_update_id = update.get("update_id", last_update_id)
                message = update.get("message", {})
                text = message.get("text", "").lower().strip()

                # Check for approval responses
                if text in ["yes", "approve", "ok", "y", "1"]:
                    # Find oldest pending approval and approve it
                    for approval_id, approval in list(pending_approvals.items()):
                        if approval["status"] == "pending":
                            approval["status"] = "approved"
                            approval["approved"] = True
                            approval["responded_at"] = datetime.utcnow().isoformat()
                            await send_telegram_message(f"✅ Approved: {approval['action']}")
                            break

                elif text in ["no", "deny", "reject", "n", "0"]:
                    for approval_id, approval in list(pending_approvals.items()):
                        if approval["status"] == "pending":
                            approval["status"] = "denied"
                            approval["approved"] = False
                            approval["responded_at"] = datetime.utcnow().isoformat()
                            await send_telegram_message(f"❌ Denied: {approval['action']}")
                            break

        except Exception as e:
            print(f"Polling error: {e}")

        await asyncio.sleep(2)  # Poll every 2 seconds

# Lifespan handler for background polling
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background polling task
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        task = asyncio.create_task(poll_telegram_responses())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    else:
        yield

app = FastAPI(
    title="HERMES",
    description="Notification & Approval Agent",
    version="1.0.0",
    lifespan=lifespan
)

# Endpoints
@app.get("/health")
async def health():
    telegram_configured = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

    # Count pending approvals
    pending_count = len([a for a in pending_approvals.values() if a["status"] == "pending"])

    return {
        "status": "healthy",
        "agent": "HERMES",
        "port": 8014,
        "telegram_configured": telegram_configured,
        "pending_approvals": pending_count,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/notify")
async def notify(req: NotifyRequest):
    """Send a notification without waiting for response"""
    notification_id = str(uuid.uuid4())[:8]
    emoji = get_priority_emoji(req.priority)

    formatted_message = f"{emoji} <b>LeverEdge Alert</b>\n\n{req.message}"

    success = await send_telegram_message(formatted_message)

    # Record in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO notifications (notification_id, message, priority, channel, status, delivered_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        notification_id,
        req.message,
        req.priority,
        req.channel,
        "delivered" if success else "failed",
        datetime.utcnow().isoformat() if success else None
    ))
    conn.commit()
    conn.close()

    await log_to_event_bus(
        "notification_sent",
        target=req.channel,
        details={"notification_id": notification_id, "priority": req.priority, "success": success}
    )

    return {
        "notification_id": notification_id,
        "status": "delivered" if success else "failed",
        "channel": req.channel
    }

@app.post("/request-approval", response_model=ApprovalResponse)
async def request_approval(req: ApprovalRequest):
    """Request approval and wait for response"""
    approval_id = str(uuid.uuid4())[:8]

    # Format approval message
    details_str = ""
    if req.details:
        details_str = "\n".join([f"• {k}: {v}" for k, v in req.details.items()])

    message = f"""🔔 <b>Approval Required</b>

<b>Action:</b> {req.action}
<b>Requested by:</b> {req.requesting_agent}

{details_str}

Reply <b>yes</b> to approve or <b>no</b> to deny.
<i>Timeout: {req.timeout_seconds} seconds</i>"""

    # Store in pending approvals
    approval_data = {
        "approval_id": approval_id,
        "action": req.action,
        "details": req.details,
        "requesting_agent": req.requesting_agent,
        "status": "pending",
        "approved": None,
        "created_at": datetime.utcnow().isoformat(),
        "responded_at": None,
        "timeout_seconds": req.timeout_seconds
    }
    pending_approvals[approval_id] = approval_data

    # Record in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO approvals (approval_id, action, details, requesting_agent, timeout_seconds)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        approval_id,
        req.action,
        json.dumps(req.details) if req.details else None,
        req.requesting_agent,
        req.timeout_seconds
    ))
    conn.commit()
    conn.close()

    # Send Telegram message
    await send_telegram_message(message)

    await log_to_event_bus(
        "approval_requested",
        target=req.requesting_agent,
        details={"approval_id": approval_id, "action": req.action}
    )

    # Wait for response with timeout
    start_time = datetime.utcnow()
    while True:
        approval = pending_approvals.get(approval_id, {})

        if approval.get("status") in ["approved", "denied"]:
            # Calculate response time
            responded_at = datetime.fromisoformat(approval["responded_at"])
            created_at = datetime.fromisoformat(approval["created_at"])
            response_time = (responded_at - created_at).total_seconds()

            # Update database
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                UPDATE approvals
                SET status = ?, approved = ?, responded_at = ?
                WHERE approval_id = ?
            ''', (
                approval["status"],
                1 if approval["approved"] else 0,
                approval["responded_at"],
                approval_id
            ))
            conn.commit()
            conn.close()

            await log_to_event_bus(
                "approval_responded",
                target=req.requesting_agent,
                details={
                    "approval_id": approval_id,
                    "approved": approval["approved"],
                    "response_time": response_time
                }
            )

            # Clean up
            del pending_approvals[approval_id]

            return ApprovalResponse(
                approval_id=approval_id,
                approved=approval["approved"],
                responder="telegram_user",
                response_time_seconds=response_time
            )

        # Check timeout
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        if elapsed >= req.timeout_seconds:
            # Timeout - deny by default
            approval_data["status"] = "timeout"
            approval_data["approved"] = False
            approval_data["responded_at"] = datetime.utcnow().isoformat()

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                UPDATE approvals
                SET status = 'timeout', approved = 0, responded_at = ?
                WHERE approval_id = ?
            ''', (approval_data["responded_at"], approval_id))
            conn.commit()
            conn.close()

            await send_telegram_message(f"⏰ Approval timeout: {req.action}")

            await log_to_event_bus(
                "approval_timeout",
                target=req.requesting_agent,
                details={"approval_id": approval_id, "action": req.action}
            )

            del pending_approvals[approval_id]

            return ApprovalResponse(
                approval_id=approval_id,
                approved=False,
                responder=None,
                response_time_seconds=elapsed
            )

        await asyncio.sleep(1)

@app.get("/pending")
async def list_pending():
    """List all pending approval requests"""
    pending = [
        {
            "approval_id": a["approval_id"],
            "action": a["action"],
            "requesting_agent": a["requesting_agent"],
            "created_at": a["created_at"],
            "timeout_seconds": a["timeout_seconds"]
        }
        for a in pending_approvals.values()
        if a["status"] == "pending"
    ]
    return {"pending": pending, "count": len(pending)}

@app.get("/history")
async def get_history(limit: int = 50):
    """Get notification and approval history"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get recent notifications
    c.execute('''
        SELECT notification_id, message, priority, status, created_at
        FROM notifications ORDER BY created_at DESC LIMIT ?
    ''', (limit,))
    notifications = [
        {"notification_id": r[0], "message": r[1], "priority": r[2], "status": r[3], "created_at": r[4]}
        for r in c.fetchall()
    ]

    # Get recent approvals
    c.execute('''
        SELECT approval_id, action, requesting_agent, status, approved, created_at, responded_at
        FROM approvals ORDER BY created_at DESC LIMIT ?
    ''', (limit,))
    approvals = [
        {
            "approval_id": r[0], "action": r[1], "requesting_agent": r[2],
            "status": r[3], "approved": bool(r[4]), "created_at": r[5], "responded_at": r[6]
        }
        for r in c.fetchall()
    ]

    conn.close()

    return {
        "notifications": notifications,
        "approvals": approvals
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8014)
