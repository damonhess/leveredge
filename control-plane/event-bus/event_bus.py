#!/usr/bin/env python3
"""
Event Bus API

Lightweight FastAPI service for the event bus.
All agents publish/subscribe through this service.

Location: /opt/leveredge/control-plane/event-bus/event_bus.py
Port: 8099
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import contextmanager

app = FastAPI(title="Event Bus", version="1.0.0")

DB_PATH = Path("/opt/leveredge/control-plane/event-bus/events.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Models
class EventCreate(BaseModel):
    source_agent: str
    action: str
    target: Optional[str] = None
    details: Optional[dict] = None
    source_workflow_id: Optional[str] = None
    source_execution_id: Optional[str] = None
    requires_human: bool = False
    human_question: Optional[str] = None
    human_options: Optional[List[str]] = None
    human_timeout_minutes: Optional[int] = None
    human_fallback: Optional[str] = None

class HumanResponse(BaseModel):
    response: str
    responder: str = "human"

# Endpoints
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "event-bus", "port": 8099}

@app.post("/events")
async def create_event(event: EventCreate):
    """Publish an event to the bus"""

    # Determine subscribed agents
    with get_db() as conn:
        cursor = conn.cursor()

        # Get matching subscriptions
        cursor.execute("""
            SELECT DISTINCT agent_name
            FROM agent_subscriptions
            WHERE enabled = 1
            AND (
                action_pattern = ?
                OR action_pattern = '*'
                OR (action_pattern LIKE '%*' AND ? LIKE REPLACE(action_pattern, '*', '%'))
                OR (action_pattern LIKE '*%' AND ? LIKE REPLACE(action_pattern, '*', '%'))
            )
        """, (event.action, event.action, event.action))

        subscribed = [row['agent_name'] for row in cursor.fetchall()]

        # Insert event
        cursor.execute("""
            INSERT INTO events (
                source_agent, action, target, details,
                source_workflow_id, source_execution_id,
                requires_human, human_question, human_options,
                human_timeout_minutes, human_fallback,
                subscribed_agents, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.source_agent,
            event.action,
            event.target,
            json.dumps(event.details) if event.details else None,
            event.source_workflow_id,
            event.source_execution_id,
            1 if event.requires_human else 0,
            event.human_question,
            json.dumps(event.human_options) if event.human_options else None,
            event.human_timeout_minutes,
            event.human_fallback,
            json.dumps(subscribed),
            'pending'
        ))

        event_id = cursor.lastrowid
        conn.commit()

        # Get the created event
        cursor.execute("SELECT * FROM events WHERE rowid = ?", (event_id,))
        row = cursor.fetchone()

        return {
            "id": row['id'],
            "status": "created",
            "subscribed_agents": subscribed
        }

@app.get("/events")
async def list_events(
    limit: int = 50,
    source_agent: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None
):
    """List recent events"""

    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if source_agent:
            query += " AND source_agent = ?"
            params.append(source_agent)

        if action:
            query += " AND action = ?"
            params.append(action)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            # Parse JSON fields
            if event.get('details'):
                event['details'] = json.loads(event['details'])
            if event.get('subscribed_agents'):
                event['subscribed_agents'] = json.loads(event['subscribed_agents'])
            if event.get('human_options'):
                event['human_options'] = json.loads(event['human_options'])
            if event.get('acknowledged_by'):
                event['acknowledged_by'] = json.loads(event['acknowledged_by'])
            events.append(event)

        return {"events": events, "count": len(events)}

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    """Get a specific event"""

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        event = dict(row)
        if event.get('details'):
            event['details'] = json.loads(event['details'])
        if event.get('subscribed_agents'):
            event['subscribed_agents'] = json.loads(event['subscribed_agents'])

        return event

@app.post("/events/{event_id}/acknowledge")
async def acknowledge_event(event_id: str, agent: str):
    """Mark event as acknowledged by an agent"""

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT acknowledged_by FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        acknowledged = json.loads(row['acknowledged_by'] or '{}')
        acknowledged[agent] = datetime.now().isoformat()

        cursor.execute("""
            UPDATE events
            SET acknowledged_by = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (json.dumps(acknowledged), event_id))

        conn.commit()

        return {"status": "acknowledged", "agent": agent}

@app.post("/events/{event_id}/respond")
async def respond_to_event(event_id: str, response: HumanResponse):
    """Respond to an event that requires human input"""

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        if not row['requires_human']:
            raise HTTPException(status_code=400, detail="Event does not require human response")

        cursor.execute("""
            UPDATE events
            SET human_response = ?,
                human_responded_at = datetime('now'),
                status = 'completed',
                updated_at = datetime('now')
            WHERE id = ?
        """, (response.response, event_id))

        conn.commit()

        return {"status": "responded", "response": response.response}

@app.get("/events/pending/human")
async def get_pending_human_events():
    """Get events waiting for human response"""

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pending_human_requests")

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event.get('human_options'):
                event['human_options'] = json.loads(event['human_options'])
            events.append(event)

        return {"pending": events, "count": len(events)}

@app.get("/agents/{agent}/events")
async def get_agent_events(agent: str, limit: int = 20, unacknowledged_only: bool = False):
    """Get events for a specific agent"""

    with get_db() as conn:
        cursor = conn.cursor()

        if unacknowledged_only:
            cursor.execute("""
                SELECT * FROM events
                WHERE subscribed_agents LIKE ?
                AND NOT (acknowledged_by LIKE ?)
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f'%"{agent}"%', f'%"{agent}"%', limit))
        else:
            cursor.execute("""
                SELECT * FROM events
                WHERE subscribed_agents LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f'%"{agent}"%', limit))

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event.get('details'):
                event['details'] = json.loads(event['details'])
            events.append(event)

        return {"agent": agent, "events": events, "count": len(events)}
