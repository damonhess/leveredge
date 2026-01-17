#!/usr/bin/env python3
"""
Search Functionality for Log Aggregation System
Provides text search and filtered queries across aggregated logs.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import aiofiles

# Configuration
AGGREGATED_DIR = Path("/opt/leveredge/monitoring/logs/aggregated")


async def search_logs(
    agent: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[dict]:
    """
    Search logs with filters.

    Args:
        agent: Filter by agent name (case-insensitive)
        level: Filter by log level (case-insensitive)
        start_time: Filter logs after this timestamp (ISO format)
        end_time: Filter logs before this timestamp (ISO format)
        limit: Maximum number of results to return
        offset: Number of results to skip

    Returns:
        List of matching log entries
    """
    results = []
    skipped = 0

    # Parse time filters
    start_dt = None
    end_dt = None

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            pass

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Determine which log files to search
    log_files = sorted(AGGREGATED_DIR.glob("*.log"), reverse=True)

    for log_file in log_files:
        if len(results) >= limit:
            break

        try:
            async with aiofiles.open(log_file, "r") as f:
                # Read all lines and reverse for most recent first
                lines = await f.readlines()

                for line in reversed(lines):
                    if len(results) >= limit:
                        break

                    try:
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    # Apply filters
                    if agent and entry.get("agent", "").upper() != agent.upper():
                        continue

                    if level and entry.get("level", "").upper() != level.upper():
                        continue

                    if start_dt or end_dt:
                        try:
                            entry_time = datetime.fromisoformat(
                                entry.get("timestamp", "").replace("Z", "+00:00")
                            )
                            if start_dt and entry_time < start_dt:
                                continue
                            if end_dt and entry_time > end_dt:
                                continue
                        except ValueError:
                            continue

                    # Handle offset
                    if skipped < offset:
                        skipped += 1
                        continue

                    results.append(entry)

        except Exception as e:
            print(f"Error reading {log_file}: {e}")
            continue

    return results


async def text_search(
    query: str,
    agent: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """
    Full-text search across log messages.

    Args:
        query: Search query (supports regex)
        agent: Optional agent filter
        level: Optional level filter
        limit: Maximum results

    Returns:
        List of matching log entries
    """
    results = []

    # Compile search pattern (case-insensitive)
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        # If invalid regex, escape and try literal match
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    log_files = sorted(AGGREGATED_DIR.glob("*.log"), reverse=True)

    for log_file in log_files:
        if len(results) >= limit:
            break

        try:
            async with aiofiles.open(log_file, "r") as f:
                lines = await f.readlines()

                for line in reversed(lines):
                    if len(results) >= limit:
                        break

                    try:
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    # Apply filters
                    if agent and entry.get("agent", "").upper() != agent.upper():
                        continue

                    if level and entry.get("level", "").upper() != level.upper():
                        continue

                    # Search in message
                    message = entry.get("message", "")
                    if pattern.search(message):
                        # Highlight matches
                        entry["_highlights"] = pattern.findall(message)
                        results.append(entry)
                        continue

                    # Also search in metadata if present
                    metadata = entry.get("metadata")
                    if metadata:
                        metadata_str = json.dumps(metadata)
                        if pattern.search(metadata_str):
                            entry["_highlights"] = pattern.findall(metadata_str)
                            results.append(entry)

        except Exception as e:
            print(f"Error reading {log_file}: {e}")
            continue

    return results


async def get_log_context(
    timestamp: str,
    agent: str,
    before: int = 5,
    after: int = 5
) -> dict:
    """
    Get log entries around a specific timestamp for context.

    Args:
        timestamp: The timestamp to center on
        agent: Agent name to filter
        before: Number of entries before
        after: Number of entries after

    Returns:
        Dict with before, target, and after entries
    """
    all_entries = await search_logs(agent=agent, limit=1000)

    # Find the target entry
    target_idx = None
    target_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    for i, entry in enumerate(all_entries):
        try:
            entry_dt = datetime.fromisoformat(
                entry.get("timestamp", "").replace("Z", "+00:00")
            )
            if abs((entry_dt - target_dt).total_seconds()) < 1:
                target_idx = i
                break
        except ValueError:
            continue

    if target_idx is None:
        return {"before": [], "target": None, "after": []}

    return {
        "before": all_entries[max(0, target_idx - before):target_idx],
        "target": all_entries[target_idx],
        "after": all_entries[target_idx + 1:target_idx + 1 + after]
    }


async def aggregate_by_time(
    agent: Optional[str] = None,
    level: Optional[str] = None,
    interval: str = "hour",
    days: int = 7
) -> List[dict]:
    """
    Aggregate log counts by time interval.

    Args:
        agent: Optional agent filter
        level: Optional level filter
        interval: 'hour' or 'day'
        days: Number of days to look back

    Returns:
        List of time buckets with counts
    """
    start_time = datetime.utcnow() - timedelta(days=days)
    all_logs = await search_logs(
        agent=agent,
        level=level,
        start_time=start_time.isoformat(),
        limit=10000
    )

    # Group by interval
    buckets = {}

    for entry in all_logs:
        try:
            entry_dt = datetime.fromisoformat(
                entry.get("timestamp", "").replace("Z", "+00:00")
            )

            if interval == "hour":
                bucket_key = entry_dt.strftime("%Y-%m-%d %H:00")
            else:
                bucket_key = entry_dt.strftime("%Y-%m-%d")

            if bucket_key not in buckets:
                buckets[bucket_key] = {"time": bucket_key, "count": 0, "by_level": {}}

            buckets[bucket_key]["count"] += 1
            lvl = entry.get("level", "UNKNOWN")
            buckets[bucket_key]["by_level"][lvl] = buckets[bucket_key]["by_level"].get(lvl, 0) + 1

        except ValueError:
            continue

    return sorted(buckets.values(), key=lambda x: x["time"], reverse=True)


async def get_error_summary(hours: int = 24) -> dict:
    """
    Get a summary of errors in the last N hours.

    Args:
        hours: Number of hours to look back

    Returns:
        Summary dict with error counts by agent
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)

    errors = await search_logs(
        level="ERROR",
        start_time=start_time.isoformat(),
        limit=1000
    )

    criticals = await search_logs(
        level="CRITICAL",
        start_time=start_time.isoformat(),
        limit=1000
    )

    all_errors = errors + criticals

    by_agent = {}
    error_messages = {}

    for entry in all_errors:
        agent = entry.get("agent", "unknown")
        message = entry.get("message", "")

        if agent not in by_agent:
            by_agent[agent] = 0
        by_agent[agent] += 1

        # Group similar error messages
        msg_key = message[:100] if len(message) > 100 else message
        if msg_key not in error_messages:
            error_messages[msg_key] = {"count": 0, "agents": set(), "sample": entry}
        error_messages[msg_key]["count"] += 1
        error_messages[msg_key]["agents"].add(agent)

    # Convert sets to lists for JSON serialization
    for key in error_messages:
        error_messages[key]["agents"] = list(error_messages[key]["agents"])

    return {
        "total_errors": len(all_errors),
        "by_agent": by_agent,
        "top_errors": sorted(
            error_messages.values(),
            key=lambda x: x["count"],
            reverse=True
        )[:10],
        "time_range_hours": hours
    }
