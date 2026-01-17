#!/usr/bin/env python3
"""
Log Collector - Background task that collects logs from agent sources
Monitors /tmp/*.log files and aggregates them into the central store.
"""

import asyncio
import json
import glob
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set
import aiofiles

# Configuration
AGGREGATED_DIR = Path("/opt/leveredge/monitoring/logs/aggregated")
LOG_SOURCES = ["/tmp/*.log"]

# Track file positions to avoid re-reading
file_positions: Dict[str, int] = {}

# Track known files to detect new ones
known_files: Set[str] = set()


class LogCollector:
    """Collects logs from various agent sources"""

    def __init__(self):
        self.file_positions: Dict[str, int] = {}
        self.aggregated_dir = AGGREGATED_DIR
        self.aggregated_dir.mkdir(parents=True, exist_ok=True)

    def parse_log_line(self, line: str, source_file: str) -> Optional[dict]:
        """Parse a log line into structured format"""
        line = line.strip()
        if not line:
            return None

        # Try JSON format first
        if line.startswith("{"):
            try:
                entry = json.loads(line)
                if "timestamp" not in entry:
                    entry["timestamp"] = datetime.utcnow().isoformat()
                if "source" not in entry:
                    entry["source"] = source_file
                return entry
            except json.JSONDecodeError:
                pass

        # Try common log formats
        # Format: YYYY-MM-DD HH:MM:SS - LEVEL - AGENT - Message
        pattern1 = r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*[-|]\s*(\w+)\s*[-|]\s*(\w+)\s*[-|]\s*(.+)$"
        match = re.match(pattern1, line)
        if match:
            return {
                "timestamp": match.group(1),
                "level": match.group(2).upper(),
                "agent": match.group(3),
                "message": match.group(4),
                "source": source_file
            }

        # Format: [LEVEL] AGENT: Message
        pattern2 = r"^\[(\w+)\]\s+(\w+):\s*(.+)$"
        match = re.match(pattern2, line)
        if match:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "level": match.group(1).upper(),
                "agent": match.group(2),
                "message": match.group(3),
                "source": source_file
            }

        # Format: LEVEL - Message (extract agent from filename)
        pattern3 = r"^(\w+)\s*[-:]\s*(.+)$"
        match = re.match(pattern3, line)
        if match:
            level_candidate = match.group(1).upper()
            if level_candidate in ["DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"]:
                agent = self._extract_agent_from_filename(source_file)
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": level_candidate,
                    "agent": agent,
                    "message": match.group(2),
                    "source": source_file
                }

        # Default: treat entire line as message
        agent = self._extract_agent_from_filename(source_file)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "agent": agent,
            "message": line,
            "source": source_file
        }

    def _extract_agent_from_filename(self, filepath: str) -> str:
        """Extract agent name from log filename"""
        filename = os.path.basename(filepath)
        # Remove .log extension and common suffixes
        name = filename.replace(".log", "").replace("_log", "").replace("-log", "")
        # Handle patterns like agent_name.log or agent-name.log
        name = name.replace("-", "_").upper()
        return name if name else "UNKNOWN"

    async def collect_from_file(self, filepath: str) -> list:
        """Collect new log entries from a specific file"""
        entries = []

        if not os.path.exists(filepath):
            return entries

        # Get current position
        current_pos = self.file_positions.get(filepath, 0)

        # Check if file was truncated (position > file size)
        file_size = os.path.getsize(filepath)
        if current_pos > file_size:
            current_pos = 0

        try:
            async with aiofiles.open(filepath, "r") as f:
                await f.seek(current_pos)
                content = await f.read()
                new_pos = await f.tell()

                for line in content.split("\n"):
                    entry = self.parse_log_line(line, filepath)
                    if entry:
                        entries.append(entry)

                self.file_positions[filepath] = new_pos

        except Exception as e:
            print(f"Error reading {filepath}: {e}")

        return entries

    async def collect_all(self) -> int:
        """Collect logs from all configured sources"""
        total_collected = 0
        today = datetime.utcnow().strftime("%Y-%m-%d")
        output_file = self.aggregated_dir / f"{today}.log"

        all_entries = []

        # Collect from all source patterns
        for pattern in LOG_SOURCES:
            for filepath in glob.glob(pattern):
                entries = await self.collect_from_file(filepath)
                all_entries.extend(entries)

        if all_entries:
            # Write to aggregated file
            async with aiofiles.open(output_file, "a") as f:
                for entry in all_entries:
                    await f.write(json.dumps(entry) + "\n")

            total_collected = len(all_entries)

            # Check for errors and send alerts
            await self._check_errors(all_entries)

        return total_collected

    async def _check_errors(self, entries: list):
        """Check for error entries and trigger alerts"""
        from alerter import check_and_alert, LogEntry

        for entry in entries:
            level = entry.get("level", "").upper()
            if level in ["ERROR", "CRITICAL", "FATAL"]:
                log_entry = LogEntry(
                    timestamp=entry.get("timestamp", datetime.utcnow().isoformat()),
                    level=level,
                    agent=entry.get("agent", "unknown"),
                    message=entry.get("message", ""),
                    source=entry.get("source")
                )
                await check_and_alert(log_entry)


async def run_collector():
    """Run the log collector as a standalone process"""
    collector = LogCollector()
    print("Starting log collector...")

    while True:
        try:
            count = await collector.collect_all()
            if count > 0:
                print(f"Collected {count} log entries")
        except Exception as e:
            print(f"Error in collection cycle: {e}")

        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run_collector())
