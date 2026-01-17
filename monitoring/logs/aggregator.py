#!/usr/bin/env python3
"""
Log Aggregation System - Main FastAPI Application
Collects, stores, and provides search capabilities for agent logs.
Port: 8062
"""

import asyncio
import json
import os
import re
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
import aiofiles
import aiohttp

# Configuration
AGGREGATED_DIR = Path("/opt/leveredge/monitoring/logs/aggregated")
STATIC_DIR = Path("/opt/leveredge/monitoring/logs/static")
LOG_SOURCES = ["/tmp/*.log"]
RETENTION_DAYS = 7
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8060")
COLLECT_INTERVAL = 30  # seconds

# Ensure directories exist
AGGREGATED_DIR.mkdir(parents=True, exist_ok=True)


class LogEntry(BaseModel):
    """Schema for log entries"""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    level: str = "INFO"
    agent: str = "unknown"
    message: str
    source: Optional[str] = None
    metadata: Optional[dict] = None


class LogFilter(BaseModel):
    """Filter parameters for log queries"""
    agent: Optional[str] = None
    level: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: int = 100
    offset: int = 0


# Global state for background task
collector_task = None


async def collect_logs_periodically():
    """Background task that periodically collects logs from agent sources"""
    from log_collector import LogCollector
    collector = LogCollector()

    while True:
        try:
            await collector.collect_all()
        except Exception as e:
            print(f"Error collecting logs: {e}")
        await asyncio.sleep(COLLECT_INTERVAL)


async def rotate_old_logs():
    """Remove logs older than RETENTION_DAYS"""
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)

    for log_file in AGGREGATED_DIR.glob("*.log"):
        try:
            # Check file modification time
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                log_file.unlink()
                print(f"Rotated old log file: {log_file}")
        except Exception as e:
            print(f"Error rotating {log_file}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global collector_task

    # Start background log collection
    collector_task = asyncio.create_task(collect_logs_periodically())

    # Schedule daily log rotation
    asyncio.create_task(daily_rotation_task())

    yield

    # Cleanup
    if collector_task:
        collector_task.cancel()
        try:
            await collector_task
        except asyncio.CancelledError:
            pass


async def daily_rotation_task():
    """Run log rotation daily"""
    while True:
        await rotate_old_logs()
        await asyncio.sleep(86400)  # 24 hours


app = FastAPI(
    title="Log Aggregation System",
    description="Central log collection and search for all agents",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "log-aggregator",
        "timestamp": datetime.utcnow().isoformat(),
        "aggregated_dir": str(AGGREGATED_DIR),
        "retention_days": RETENTION_DAYS
    }


@app.get("/", response_class=HTMLResponse)
async def web_ui():
    """Serve the web UI for viewing logs"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Log Viewer</h1><p>Static files not found</p>")


@app.post("/api/logs")
async def ingest_log(entry: LogEntry, background_tasks: BackgroundTasks):
    """Ingest a log entry"""
    from alerter import check_and_alert

    # Write to aggregated log file
    today = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = AGGREGATED_DIR / f"{today}.log"

    log_line = json.dumps({
        "timestamp": entry.timestamp,
        "level": entry.level,
        "agent": entry.agent,
        "message": entry.message,
        "source": entry.source,
        "metadata": entry.metadata
    }) + "\n"

    async with aiofiles.open(log_file, "a") as f:
        await f.write(log_line)

    # Check for errors and alert if needed
    if entry.level.upper() in ["ERROR", "CRITICAL", "FATAL"]:
        background_tasks.add_task(check_and_alert, entry)

    return {"status": "ingested", "timestamp": entry.timestamp}


@app.get("/api/logs")
async def get_logs(
    agent: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0
):
    """Get recent logs with optional filters"""
    from search import search_logs

    logs = await search_logs(
        agent=agent,
        level=level,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )

    return {
        "logs": logs,
        "count": len(logs),
        "limit": limit,
        "offset": offset
    }


@app.get("/api/logs/search")
async def search_logs_endpoint(
    q: str = Query(..., description="Search query"),
    agent: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = Query(default=100, le=1000)
):
    """Search logs by text query"""
    from search import text_search

    results = await text_search(
        query=q,
        agent=agent,
        level=level,
        limit=limit
    )

    return {
        "query": q,
        "results": results,
        "count": len(results)
    }


@app.get("/api/logs/agent/{agent_name}")
async def get_agent_logs(
    agent_name: str,
    level: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0
):
    """Get logs for a specific agent"""
    from search import search_logs

    logs = await search_logs(
        agent=agent_name,
        level=level,
        limit=limit,
        offset=offset
    )

    return {
        "agent": agent_name,
        "logs": logs,
        "count": len(logs)
    }


@app.get("/api/agents")
async def list_agents():
    """List all agents that have submitted logs"""
    agents = set()

    for log_file in AGGREGATED_DIR.glob("*.log"):
        try:
            async with aiofiles.open(log_file, "r") as f:
                async for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if "agent" in entry:
                            agents.add(entry["agent"])
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

    return {"agents": sorted(list(agents))}


@app.get("/api/stats")
async def get_stats():
    """Get log statistics"""
    stats = {
        "total_logs": 0,
        "by_level": {},
        "by_agent": {},
        "log_files": []
    }

    for log_file in sorted(AGGREGATED_DIR.glob("*.log")):
        file_stats = {
            "name": log_file.name,
            "size_bytes": log_file.stat().st_size,
            "count": 0
        }

        try:
            async with aiofiles.open(log_file, "r") as f:
                async for line in f:
                    try:
                        entry = json.loads(line.strip())
                        file_stats["count"] += 1
                        stats["total_logs"] += 1

                        level = entry.get("level", "UNKNOWN")
                        stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

                        agent = entry.get("agent", "unknown")
                        stats["by_agent"][agent] = stats["by_agent"].get(agent, 0) + 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

        stats["log_files"].append(file_stats)

    return stats


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8062)
