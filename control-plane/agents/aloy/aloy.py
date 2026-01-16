#!/usr/bin/env python3
"""
ALOY - Audit & Anomaly Detection Agent
Port: 8015

Monitors Event Bus for suspicious patterns and generates audit reports.
"""

import os
import httpx
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

app = FastAPI(title="ALOY", description="Audit & Anomaly Detection Agent", version="1.0.0")

# Configuration
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
DB_PATH = os.getenv("ALOY_DB_PATH", "/app/data/aloy.db")

# Anomaly detection rules (Option A - simple rule-based)
ANOMALY_RULES = {
    "high_failure_rate": {
        "description": "More than 10 failures in 5 minutes",
        "threshold": 10,
        "window_minutes": 5,
        "severity": "warning",
        "pattern": "failed"
    },
    "forbidden_attempt": {
        "description": "Blocked or forbidden action detected",
        "severity": "critical",
        "patterns": ["blocked", "forbidden", "denied", "unauthorized"]
    },
    "mass_deletion": {
        "description": "More than 5 delete actions in 1 minute",
        "threshold": 5,
        "window_minutes": 1,
        "severity": "critical",
        "pattern": "delete"
    },
    "rapid_changes": {
        "description": "More than 20 changes in 1 minute",
        "threshold": 20,
        "window_minutes": 1,
        "severity": "warning",
        "patterns": ["created", "updated", "modified"]
    }
}

# Database setup
def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT,
            event_count INTEGER,
            sample_events TEXT,
            detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            acknowledged INTEGER DEFAULT 0,
            acknowledged_at TEXT,
            acknowledged_by TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_type TEXT NOT NULL,
            events_analyzed INTEGER,
            anomalies_found INTEGER,
            started_at TEXT,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'completed'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Models
class AuditReportRequest(BaseModel):
    start_date: Optional[str] = None  # ISO format
    end_date: Optional[str] = None
    agent_filter: Optional[str] = None

class AnomalyAck(BaseModel):
    acknowledged_by: str = "system"

# Helpers
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "ALOY",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

async def send_alert_to_hermes(severity: str, message: str, rule_name: str):
    """Send anomaly alert via HERMES"""
    try:
        async with httpx.AsyncClient() as client:
            priority = "critical" if severity == "critical" else "high" if severity == "warning" else "normal"
            await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "message": f"[ANOMALY] {rule_name}: {message}",
                    "priority": priority
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES alert failed: {e}")

async def fetch_recent_events(minutes: int = 60, agent: str = None) -> List[Dict]:
    """Fetch recent events from Event Bus"""
    try:
        async with httpx.AsyncClient() as client:
            params = {"limit": 500}
            if agent:
                params["source_agent"] = agent
            resp = await client.get(
                f"{EVENT_BUS_URL}/events",
                params=params,
                timeout=10.0
            )
            if resp.status_code == 200:
                events = resp.json().get("events", [])
                # Filter by time window
                cutoff = datetime.utcnow() - timedelta(minutes=minutes)
                cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
                return [e for e in events if e.get("timestamp", "") >= cutoff_str]
    except Exception as e:
        print(f"Failed to fetch events: {e}")
    return []

async def check_anomaly_rules(events: List[Dict]) -> List[Dict]:
    """Check events against anomaly rules"""
    anomalies = []
    now = datetime.utcnow()

    for rule_name, rule in ANOMALY_RULES.items():
        matching_events = []

        # Pattern matching
        patterns = rule.get("patterns", [rule.get("pattern", "")])
        for event in events:
            action = event.get("action", "").lower()
            details_str = str(event.get("details", {})).lower()

            for pattern in patterns:
                if pattern and (pattern in action or pattern in details_str):
                    matching_events.append(event)
                    break

        # Check thresholds for time-windowed rules
        if "window_minutes" in rule:
            window = timedelta(minutes=rule["window_minutes"])
            cutoff = now - window
            cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

            windowed_events = [e for e in matching_events if e.get("timestamp", "") >= cutoff_str]

            threshold = rule.get("threshold", 1)
            if len(windowed_events) >= threshold:
                anomalies.append({
                    "rule_name": rule_name,
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "event_count": len(windowed_events),
                    "sample_events": windowed_events[:3]  # First 3 as sample
                })

        # Instant match rules (no threshold)
        elif matching_events and "threshold" not in rule:
            anomalies.append({
                "rule_name": rule_name,
                "severity": rule["severity"],
                "description": rule["description"],
                "event_count": len(matching_events),
                "sample_events": matching_events[:3]
            })

    return anomalies

# Endpoints
@app.get("/health")
async def health():
    # Count recent anomalies
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM anomalies WHERE detected_at > datetime('now', '-24 hours')")
    recent_anomalies = c.fetchone()[0]
    conn.close()

    return {
        "status": "healthy",
        "agent": "ALOY",
        "port": 8015,
        "rules_active": len(ANOMALY_RULES),
        "anomalies_24h": recent_anomalies,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/audit/recent")
async def get_recent_audit(hours: int = 24):
    """Get recent audit events from Event Bus"""
    events = await fetch_recent_events(minutes=hours * 60)

    # Group by agent
    by_agent = {}
    for event in events:
        agent = event.get("source_agent", "unknown")
        if agent not in by_agent:
            by_agent[agent] = []
        by_agent[agent].append(event)

    # Summarize actions
    action_counts = {}
    for event in events:
        action = event.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "total_events": len(events),
        "time_range_hours": hours,
        "events_by_agent": {k: len(v) for k, v in by_agent.items()},
        "action_counts": action_counts,
        "sample_events": events[:10]
    }

@app.post("/audit/report")
async def generate_audit_report(req: AuditReportRequest):
    """Generate a detailed audit report"""
    # Default to last 24 hours
    end_date = req.end_date or datetime.utcnow().isoformat()
    start_date = req.start_date or (datetime.utcnow() - timedelta(hours=24)).isoformat()

    events = await fetch_recent_events(minutes=1440)  # Max 24 hours

    # Apply filters
    if req.agent_filter:
        events = [e for e in events if e.get("source_agent") == req.agent_filter]

    # Build report
    report = {
        "report_generated": datetime.utcnow().isoformat(),
        "period": {
            "start": start_date,
            "end": end_date
        },
        "summary": {
            "total_events": len(events),
            "unique_agents": len(set(e.get("source_agent") for e in events)),
            "unique_actions": len(set(e.get("action") for e in events))
        },
        "by_agent": {},
        "by_action": {},
        "by_hour": {},
        "anomalies_detected": []
    }

    # Group by agent
    for event in events:
        agent = event.get("source_agent", "unknown")
        if agent not in report["by_agent"]:
            report["by_agent"][agent] = {"count": 0, "actions": {}}
        report["by_agent"][agent]["count"] += 1
        action = event.get("action", "unknown")
        report["by_agent"][agent]["actions"][action] = report["by_agent"][agent]["actions"].get(action, 0) + 1

    # Group by action
    for event in events:
        action = event.get("action", "unknown")
        report["by_action"][action] = report["by_action"].get(action, 0) + 1

    # Log audit report generation
    await log_to_event_bus(
        "audit_report_generated",
        details={
            "events_analyzed": len(events),
            "period_start": start_date,
            "period_end": end_date
        }
    )

    return report

@app.get("/anomalies")
async def list_anomalies(acknowledged: Optional[bool] = None, limit: int = 50):
    """List detected anomalies"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = "SELECT id, rule_name, severity, description, event_count, detected_at, acknowledged FROM anomalies"
    params = []

    if acknowledged is not None:
        query += " WHERE acknowledged = ?"
        params.append(1 if acknowledged else 0)

    query += " ORDER BY detected_at DESC LIMIT ?"
    params.append(limit)

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    return {
        "anomalies": [
            {
                "id": r[0],
                "rule_name": r[1],
                "severity": r[2],
                "description": r[3],
                "event_count": r[4],
                "detected_at": r[5],
                "acknowledged": bool(r[6])
            }
            for r in rows
        ],
        "count": len(rows)
    }

@app.post("/anomalies/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(anomaly_id: int, ack: AnomalyAck):
    """Acknowledge an anomaly"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE anomalies
        SET acknowledged = 1, acknowledged_at = ?, acknowledged_by = ?
        WHERE id = ?
    ''', (datetime.utcnow().isoformat(), ack.acknowledged_by, anomaly_id))
    conn.commit()

    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")

    conn.close()

    await log_to_event_bus(
        "anomaly_acknowledged",
        target=str(anomaly_id),
        details={"acknowledged_by": ack.acknowledged_by}
    )

    return {"status": "acknowledged", "anomaly_id": anomaly_id}

@app.post("/analyze")
async def run_analysis():
    """Manually trigger anomaly analysis"""
    import json

    # Fetch recent events
    events = await fetch_recent_events(minutes=60)

    # Check rules
    anomalies = await check_anomaly_rules(events)

    # Store detected anomalies
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for anomaly in anomalies:
        c.execute('''
            INSERT INTO anomalies (rule_name, severity, description, event_count, sample_events)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            anomaly["rule_name"],
            anomaly["severity"],
            anomaly["description"],
            anomaly["event_count"],
            json.dumps(anomaly["sample_events"])
        ))

        # Alert on critical anomalies
        if anomaly["severity"] == "critical":
            await send_alert_to_hermes(
                anomaly["severity"],
                f"{anomaly['description']} ({anomaly['event_count']} events)",
                anomaly["rule_name"]
            )

    # Record analysis run
    c.execute('''
        INSERT INTO audit_runs (run_type, events_analyzed, anomalies_found, started_at)
        VALUES (?, ?, ?, ?)
    ''', ("manual", len(events), len(anomalies), datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

    await log_to_event_bus(
        "analysis_completed",
        details={
            "events_analyzed": len(events),
            "anomalies_found": len(anomalies),
            "anomaly_types": [a["rule_name"] for a in anomalies]
        }
    )

    return {
        "status": "completed",
        "events_analyzed": len(events),
        "anomalies_found": len(anomalies),
        "anomalies": anomalies
    }

@app.get("/rules")
async def list_rules():
    """List active anomaly detection rules"""
    return {
        "rules": [
            {
                "name": name,
                "description": rule["description"],
                "severity": rule["severity"],
                "threshold": rule.get("threshold"),
                "window_minutes": rule.get("window_minutes")
            }
            for name, rule in ANOMALY_RULES.items()
        ],
        "count": len(ANOMALY_RULES)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8015)
