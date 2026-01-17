#!/usr/bin/env python3
"""
Error Alerter for Log Aggregation System
Detects error patterns and sends alerts to HERMES.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict
from dataclasses import dataclass, field
from pydantic import BaseModel

import aiohttp

# Configuration
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8060")

# Alert thresholds
ERROR_THRESHOLD = 5  # Number of errors before alerting
THRESHOLD_WINDOW = 300  # seconds (5 minutes)
COOLDOWN_PERIOD = 600  # seconds (10 minutes) between similar alerts


class LogEntry(BaseModel):
    """Log entry schema"""
    timestamp: str
    level: str
    agent: str
    message: str
    source: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class AlertState:
    """Track alert state to prevent spam"""
    error_counts: Dict[str, list] = field(default_factory=lambda: defaultdict(list))
    last_alerts: Dict[str, datetime] = field(default_factory=dict)


# Global alert state
_alert_state = AlertState()


async def send_to_hermes(
    title: str,
    message: str,
    level: str = "error",
    agent: str = "log-aggregator",
    metadata: Optional[dict] = None
) -> bool:
    """
    Send an alert to HERMES.

    Args:
        title: Alert title
        message: Alert message
        level: Alert level (info, warning, error, critical)
        agent: Source agent
        metadata: Additional context

    Returns:
        True if alert was sent successfully
    """
    payload = {
        "title": title,
        "message": message,
        "level": level,
        "source": agent,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Try the alerts endpoint first
            async with session.post(
                f"{HERMES_URL}/api/alerts",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 201, 202]:
                    print(f"Alert sent to HERMES: {title}")
                    return True

            # Fallback to messages endpoint
            async with session.post(
                f"{HERMES_URL}/api/messages",
                json={
                    "channel": "alerts",
                    "content": f"[{level.upper()}] {title}\n\n{message}",
                    "source": agent,
                    "metadata": metadata
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 201, 202]:
                    print(f"Alert sent to HERMES via messages: {title}")
                    return True

    except aiohttp.ClientError as e:
        print(f"Failed to send alert to HERMES: {e}")
    except Exception as e:
        print(f"Unexpected error sending alert: {e}")

    return False


def _get_alert_key(entry: LogEntry) -> str:
    """Generate a key for grouping similar alerts"""
    # Use agent + first 50 chars of message to group similar errors
    msg_prefix = entry.message[:50] if entry.message else "unknown"
    return f"{entry.agent}:{msg_prefix}"


def _should_alert(alert_key: str) -> bool:
    """Check if we should send an alert based on cooldown"""
    last_alert = _alert_state.last_alerts.get(alert_key)

    if last_alert is None:
        return True

    cooldown = timedelta(seconds=COOLDOWN_PERIOD)
    return datetime.utcnow() - last_alert > cooldown


def _record_error(entry: LogEntry):
    """Record an error occurrence for threshold tracking"""
    alert_key = _get_alert_key(entry)
    now = datetime.utcnow()

    # Clean old entries outside the window
    window = timedelta(seconds=THRESHOLD_WINDOW)
    _alert_state.error_counts[alert_key] = [
        ts for ts in _alert_state.error_counts[alert_key]
        if now - ts < window
    ]

    # Add current error
    _alert_state.error_counts[alert_key].append(now)


def _get_error_count(entry: LogEntry) -> int:
    """Get the count of similar errors in the threshold window"""
    alert_key = _get_alert_key(entry)
    return len(_alert_state.error_counts.get(alert_key, []))


async def check_and_alert(entry: LogEntry):
    """
    Check if a log entry should trigger an alert and send it.

    Logic:
    - CRITICAL/FATAL: Always alert immediately
    - ERROR: Alert if threshold exceeded in window
    - Respect cooldown to prevent spam
    """
    level = entry.level.upper()
    alert_key = _get_alert_key(entry)

    # Record the error
    _record_error(entry)

    # Determine if we should alert
    should_send = False
    alert_reason = ""

    if level in ["CRITICAL", "FATAL"]:
        # Always alert on critical/fatal
        if _should_alert(alert_key):
            should_send = True
            alert_reason = "Critical error detected"
    elif level == "ERROR":
        error_count = _get_error_count(entry)
        if error_count >= ERROR_THRESHOLD and _should_alert(alert_key):
            should_send = True
            alert_reason = f"Error threshold exceeded ({error_count} errors in {THRESHOLD_WINDOW}s)"

    if should_send:
        title = f"[{level}] {entry.agent}: Error Alert"
        message = f"""
Agent: {entry.agent}
Level: {level}
Time: {entry.timestamp}
Reason: {alert_reason}

Message:
{entry.message}

Source: {entry.source or 'Unknown'}
"""

        success = await send_to_hermes(
            title=title,
            message=message.strip(),
            level=level.lower(),
            agent=entry.agent,
            metadata={
                "original_timestamp": entry.timestamp,
                "source_file": entry.source,
                "error_count": _get_error_count(entry),
                "original_metadata": entry.metadata
            }
        )

        if success:
            _alert_state.last_alerts[alert_key] = datetime.utcnow()


async def send_daily_summary():
    """Send a daily summary of errors to HERMES"""
    from search import get_error_summary

    summary = await get_error_summary(hours=24)

    if summary["total_errors"] == 0:
        return

    # Build summary message
    message_parts = [
        f"Total Errors: {summary['total_errors']}",
        "",
        "Errors by Agent:"
    ]

    for agent, count in sorted(summary["by_agent"].items(), key=lambda x: -x[1]):
        message_parts.append(f"  - {agent}: {count}")

    if summary["top_errors"]:
        message_parts.extend(["", "Top Error Patterns:"])
        for i, error in enumerate(summary["top_errors"][:5], 1):
            msg = error["sample"].get("message", "Unknown")[:100]
            message_parts.append(f"  {i}. ({error['count']}x) {msg}")

    await send_to_hermes(
        title="Daily Error Summary",
        message="\n".join(message_parts),
        level="info",
        agent="log-aggregator",
        metadata=summary
    )


async def check_agent_health():
    """Check if any agents have stopped logging (potential issues)"""
    from search import search_logs
    from datetime import datetime, timedelta

    # Get recent logs
    recent = await search_logs(limit=1000)

    # Group by agent with most recent timestamp
    agent_last_seen = {}

    for entry in recent:
        agent = entry.get("agent", "unknown")
        timestamp = entry.get("timestamp", "")

        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if agent not in agent_last_seen or ts > agent_last_seen[agent]:
                agent_last_seen[agent] = ts
        except ValueError:
            continue

    # Check for agents that haven't logged in 30 minutes
    threshold = datetime.utcnow() - timedelta(minutes=30)
    silent_agents = []

    for agent, last_seen in agent_last_seen.items():
        if last_seen < threshold:
            silent_agents.append({
                "agent": agent,
                "last_seen": last_seen.isoformat(),
                "minutes_ago": int((datetime.utcnow() - last_seen).total_seconds() / 60)
            })

    if silent_agents:
        message = "The following agents have not logged in 30+ minutes:\n\n"
        for sa in silent_agents:
            message += f"- {sa['agent']}: last seen {sa['minutes_ago']} minutes ago\n"

        await send_to_hermes(
            title="Agent Health Warning: Silent Agents Detected",
            message=message,
            level="warning",
            agent="log-aggregator",
            metadata={"silent_agents": silent_agents}
        )


class AlertPatternMatcher:
    """Match log entries against predefined alert patterns"""

    def __init__(self):
        self.patterns = [
            {
                "name": "database_connection",
                "keywords": ["database", "connection", "refused", "timeout", "postgresql", "mysql"],
                "level": "critical",
                "title": "Database Connection Issue"
            },
            {
                "name": "out_of_memory",
                "keywords": ["out of memory", "oom", "memory error", "heap", "allocation failed"],
                "level": "critical",
                "title": "Memory Issue Detected"
            },
            {
                "name": "authentication",
                "keywords": ["authentication failed", "unauthorized", "invalid token", "401", "403"],
                "level": "error",
                "title": "Authentication Failure"
            },
            {
                "name": "rate_limit",
                "keywords": ["rate limit", "too many requests", "429", "throttle"],
                "level": "warning",
                "title": "Rate Limit Hit"
            },
            {
                "name": "disk_space",
                "keywords": ["disk full", "no space left", "disk quota", "storage"],
                "level": "critical",
                "title": "Disk Space Issue"
            }
        ]

    def match(self, message: str) -> Optional[dict]:
        """Check if message matches any pattern"""
        message_lower = message.lower()

        for pattern in self.patterns:
            for keyword in pattern["keywords"]:
                if keyword in message_lower:
                    return pattern

        return None


# Global pattern matcher
_pattern_matcher = AlertPatternMatcher()


async def check_patterns(entry: LogEntry):
    """Check log entry against alert patterns"""
    pattern = _pattern_matcher.match(entry.message)

    if pattern:
        alert_key = f"pattern:{pattern['name']}:{entry.agent}"

        if _should_alert(alert_key):
            await send_to_hermes(
                title=f"{pattern['title']} - {entry.agent}",
                message=f"Pattern matched: {pattern['name']}\n\nOriginal message:\n{entry.message}",
                level=pattern["level"],
                agent=entry.agent,
                metadata={
                    "pattern": pattern["name"],
                    "original_entry": entry.dict()
                }
            )
            _alert_state.last_alerts[alert_key] = datetime.utcnow()
