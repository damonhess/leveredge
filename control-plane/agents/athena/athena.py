#!/usr/bin/env python3
"""
ATHENA - Documentation Agent
Port: 8013

Generates and maintains documentation from system state and Event Bus data.
Option A: Manual trigger only, no LLM.
"""

import os
import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from jinja2 import Environment, FileSystemLoader

app = FastAPI(title="ATHENA", description="Documentation Agent", version="1.0.0")

# Configuration
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
DOCS_PATH = Path(os.getenv("DOCS_PATH", "/opt/leveredge"))
TEMPLATE_PATH = Path("/app/templates")

# Setup Jinja2 templates
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_PATH)))

# Models
class ReportRequest(BaseModel):
    report_type: str  # daily, weekly, custom
    date_range_hours: int = 24
    output_path: Optional[str] = None

class UpdateDocRequest(BaseModel):
    content: Optional[str] = None
    append: Optional[str] = None

# Helpers
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "ATHENA",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

async def fetch_events(hours: int = 24) -> List[Dict]:
    """Fetch events from Event Bus"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{EVENT_BUS_URL}/events",
                params={"limit": 1000},
                timeout=10.0
            )
            if resp.status_code == 200:
                events = resp.json().get("events", [])
                # Filter by time
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
                return [e for e in events if e.get("timestamp", "") >= cutoff_str]
    except Exception as e:
        print(f"Failed to fetch events: {e}")
    return []

async def fetch_agent_status() -> Dict:
    """Fetch status from all agents via ARGUS"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "http://argus:8016/status",
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"Failed to fetch agent status: {e}")
    return {}

def generate_activity_summary(events: List[Dict]) -> Dict:
    """Generate activity summary from events"""
    summary = {
        "total_events": len(events),
        "by_agent": {},
        "by_action": {},
        "timeline": []
    }

    for event in events:
        agent = event.get("source_agent", "unknown")
        action = event.get("action", "unknown")

        if agent not in summary["by_agent"]:
            summary["by_agent"][agent] = 0
        summary["by_agent"][agent] += 1

        if action not in summary["by_action"]:
            summary["by_action"][action] = 0
        summary["by_action"][action] += 1

    # Get top 10 most recent events for timeline
    summary["timeline"] = [
        {
            "time": e.get("timestamp"),
            "agent": e.get("source_agent"),
            "action": e.get("action"),
            "target": e.get("target")
        }
        for e in events[:10]
    ]

    return summary

# Endpoints
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "ATHENA",
        "port": 8013,
        "docs_path": str(DOCS_PATH),
        "templates_available": TEMPLATE_PATH.exists(),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/docs")
async def list_docs():
    """List available documentation files"""
    docs = []

    # Find markdown files in docs path
    for pattern in ["*.md", "docs/*.md"]:
        for f in DOCS_PATH.glob(pattern):
            if f.is_file():
                docs.append({
                    "name": f.name,
                    "path": str(f.relative_to(DOCS_PATH)),
                    "size_bytes": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })

    return {"docs": docs, "count": len(docs)}

@app.get("/docs/{doc_name}", response_class=PlainTextResponse)
async def get_doc(doc_name: str):
    """Read a documentation file"""
    # Security: only allow reading specific docs
    allowed_docs = [
        "ARCHITECTURE.md",
        "LESSONS-LEARNED.md",
        "FUTURE-VISION-AND-EXPLORATION.md",
        "GSD-PHASE-4-AGENTS.md"
    ]

    if doc_name not in allowed_docs:
        raise HTTPException(status_code=403, detail=f"Access to '{doc_name}' not allowed")

    doc_path = DOCS_PATH / doc_name
    if not doc_path.exists():
        raise HTTPException(status_code=404, detail=f"Document '{doc_name}' not found")

    return doc_path.read_text()

@app.post("/generate/report")
async def generate_report(req: ReportRequest):
    """Generate a documentation report"""
    # Fetch data
    events = await fetch_events(hours=req.date_range_hours)
    agent_status = await fetch_agent_status()
    activity = generate_activity_summary(events)

    # Build report content
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "report_type": req.report_type,
        "period_hours": req.date_range_hours,
        "system_status": agent_status.get("overall_status", "unknown"),
        "activity_summary": activity,
        "agent_statuses": agent_status.get("agents", [])
    }

    # Generate markdown report
    report_md = f"""# LeverEdge System Report

**Generated:** {report['generated_at']}
**Period:** Last {req.date_range_hours} hours
**System Status:** {report['system_status']}

## Activity Summary

- **Total Events:** {activity['total_events']}
- **Active Agents:** {len(activity['by_agent'])}
- **Action Types:** {len(activity['by_action'])}

### Events by Agent

| Agent | Event Count |
|-------|-------------|
"""
    for agent, count in sorted(activity['by_agent'].items(), key=lambda x: -x[1]):
        report_md += f"| {agent} | {count} |\n"

    report_md += """
### Top Actions

| Action | Count |
|--------|-------|
"""
    for action, count in sorted(activity['by_action'].items(), key=lambda x: -x[1])[:10]:
        report_md += f"| {action} | {count} |\n"

    report_md += """
### Recent Timeline

| Time | Agent | Action | Target |
|------|-------|--------|--------|
"""
    for item in activity['timeline']:
        report_md += f"| {item['time']} | {item['agent']} | {item['action']} | {item['target'] or '-'} |\n"

    report_md += """
### Agent Health

| Agent | Status | Response Time |
|-------|--------|---------------|
"""
    for agent in report['agent_statuses']:
        rt = f"{agent.get('response_time_ms', '-'):.1f}ms" if agent.get('response_time_ms') else "-"
        report_md += f"| {agent['name']} | {agent['status']} | {rt} |\n"

    report_md += f"""
---
*Generated by ATHENA Documentation Agent*
"""

    # Save if output path specified
    if req.output_path:
        output_file = DOCS_PATH / req.output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report_md)

    await log_to_event_bus(
        "report_generated",
        target=req.report_type,
        details={
            "period_hours": req.date_range_hours,
            "events_analyzed": activity['total_events'],
            "output_path": req.output_path
        }
    )

    return {
        "status": "generated",
        "report_type": req.report_type,
        "events_analyzed": activity['total_events'],
        "output_path": req.output_path,
        "content": report_md
    }

@app.post("/generate/architecture")
async def generate_architecture():
    """Generate/update ARCHITECTURE.md from current system state"""
    agent_status = await fetch_agent_status()
    events = await fetch_events(hours=24)

    # Count events by agent
    event_counts = {}
    for e in events:
        agent = e.get("source_agent", "unknown")
        event_counts[agent] = event_counts.get(agent, 0) + 1

    content = f"""# LeverEdge Architecture

**Auto-generated by ATHENA**
**Last Updated:** {datetime.utcnow().isoformat()}

## System Overview

LeverEdge is an AI-powered automation infrastructure built on n8n workflows and FastAPI agents.

## Active Agents

| Agent | Port | Status | Events (24h) | Description |
|-------|------|--------|--------------|-------------|
"""

    agent_info = {
        "ATLAS": {"port": "n8n", "desc": "AI Router - routes requests to appropriate agents"},
        "HEPHAESTUS": {"port": "8011", "desc": "MCP Server - remote execution for Claude"},
        "AEGIS": {"port": "8012", "desc": "Credential Manager - secure credential storage"},
        "CHRONOS": {"port": "8010", "desc": "Backup Manager - automated backups"},
        "HADES": {"port": "8008", "desc": "Rollback System - emergency recovery"},
        "HERMES": {"port": "8014", "desc": "Notifications - Telegram alerts and approvals"},
        "ARGUS": {"port": "8016", "desc": "Monitoring - system health and metrics"},
        "ALOY": {"port": "8015", "desc": "Audit - anomaly detection and audit logs"},
        "ATHENA": {"port": "8013", "desc": "Documentation - report generation"},
    }

    for agent in agent_status.get("agents", []):
        name = agent["name"].upper()
        info = agent_info.get(name, {"port": "?", "desc": "Unknown"})
        events_24h = event_counts.get(name, 0)
        content += f"| {name} | {info['port']} | {agent['status']} | {events_24h} | {info['desc']} |\n"

    content += f"""
## Infrastructure

- **Control Plane n8n:** control.n8n.leveredgeai.com (port 5679)
- **Event Bus:** localhost:8099 (SQLite-backed)
- **Docker Network:** control-plane-net
- **Backup Location:** /opt/leveredge/shared/backups/

## Architecture Pattern

```
Option A: Remote Execution (Current)

Claude Desktop (Brain)
    |
    v
ATLAS (Router) --> Agents (Hands)
    |                   |
    v                   v
Event Bus <-------- All Actions Logged
```

## Recent Activity

| Agent | Actions (24h) |
|-------|---------------|
"""
    for agent, count in sorted(event_counts.items(), key=lambda x: -x[1])[:10]:
        content += f"| {agent} | {count} |\n"

    content += """
---
*This document is auto-generated. Manual edits will be overwritten.*
"""

    await log_to_event_bus(
        "architecture_generated",
        details={"agents_documented": len(agent_status.get("agents", []))}
    )

    return {
        "status": "generated",
        "agents_documented": len(agent_status.get("agents", [])),
        "content": content
    }

@app.post("/update/{doc_name}")
async def update_doc(doc_name: str, req: UpdateDocRequest):
    """Update a documentation file"""
    # Security: only allow updating specific docs
    allowed_updates = ["SESSION-LOG.md", "NOTES.md"]

    if doc_name not in allowed_updates:
        raise HTTPException(status_code=403, detail=f"Updates to '{doc_name}' not allowed via API")

    doc_path = DOCS_PATH / doc_name

    if req.content:
        # Full replacement
        doc_path.write_text(req.content)
    elif req.append:
        # Append mode
        existing = doc_path.read_text() if doc_path.exists() else ""
        doc_path.write_text(existing + "\n" + req.append)
    else:
        raise HTTPException(status_code=400, detail="Provide either 'content' or 'append'")

    await log_to_event_bus(
        "doc_updated",
        target=doc_name,
        details={"mode": "replace" if req.content else "append"}
    )

    return {"status": "updated", "doc_name": doc_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
