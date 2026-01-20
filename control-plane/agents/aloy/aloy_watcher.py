#!/usr/bin/env python3
"""
ALOY WATCHER V2 - Active Anomaly Detection

Actively monitors for:
- 500 errors in aria-chat logs
- Data loss (conversations/messages disappearing)
- Schema mismatches between dev/prod
- Service health degradation
- Error rate spikes

Sends alerts via HERMES when issues detected.
"""

import os
import sys
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

sys.path.append('/opt/leveredge/control-plane/shared')
from watcher_base import WatcherBase, Alert, AlertSeverity

import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ALOY-WATCHER")

# =============================================================================
# CONFIGURATION
# =============================================================================

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
WATCHDOG_URL = os.getenv("WATCHDOG_URL", "http://watchdog:8240")
LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")

# Services to monitor
MONITORED_SERVICES = {
    "aria-chat-dev": {"health_url": "http://aria-chat-dev:8113/health", "logs_container": "aria-chat-dev"},
    "aria-chat-prod": {"health_url": "http://aria-chat-prod:8113/health", "logs_container": "aria-chat-prod"},
}

# Database containers for schema checks
DB_CONTAINERS = {
    "dev": "supabase-db-dev",
    "prod": "supabase-db-prod"
}

# Tables to monitor for data loss
MONITORED_TABLES = [
    "aria_conversations",
    "aria_messages",
    "aria_unified_conversations",
    "aria_unified_messages"
]

# =============================================================================
# ALOY WATCHER V2
# =============================================================================

class AloyWatcherV2(WatcherBase):
    """Active anomaly detection with polling"""

    def __init__(self):
        super().__init__(poll_interval=60, alert_cooldown=300)  # Check every minute
        # Track previous counts for data loss detection
        self.previous_counts: Dict[str, Dict[str, int]] = {"dev": {}, "prod": {}}
        # Track error counts for rate detection
        self.error_counts: Dict[str, List[datetime]] = defaultdict(list)

    def get_name(self) -> str:
        return "ALOY"

    async def watch_cycle(self) -> List[Alert]:
        """Perform all monitoring checks"""
        alerts = []

        # 1. Check for 500 errors in aria-chat logs
        error_alerts = await self.check_service_logs()
        alerts.extend(error_alerts)

        # 2. Check for data loss
        data_alerts = await self.check_data_integrity()
        alerts.extend(data_alerts)

        # 3. Check schema consistency between dev/prod
        schema_alerts = await self.check_schema_consistency()
        alerts.extend(schema_alerts)

        # 4. Check service health
        health_alerts = await self.check_service_health()
        alerts.extend(health_alerts)

        return alerts

    async def check_service_logs(self) -> List[Alert]:
        """Check aria-chat logs for 500 errors"""
        alerts = []

        for service_name, config in MONITORED_SERVICES.items():
            container = config["logs_container"]
            try:
                # Get last 100 log lines
                result = subprocess.run(
                    ["docker", "logs", "--tail", "100", container],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                logs = result.stdout + result.stderr

                # Count 500 errors
                error_count = 0
                error_lines = []
                for line in logs.split('\n'):
                    line_lower = line.lower()
                    if '500' in line or 'internal server error' in line_lower or 'error' in line_lower:
                        if 'openai' in line_lower or 'api' in line_lower or 'failed' in line_lower:
                            error_count += 1
                            error_lines.append(line[:200])

                # Track error timestamps
                now = datetime.utcnow()
                for _ in range(error_count):
                    self.error_counts[service_name].append(now)

                # Clean old entries (keep last 5 minutes)
                cutoff = now - timedelta(minutes=5)
                self.error_counts[service_name] = [
                    t for t in self.error_counts[service_name] if t > cutoff
                ]

                # Alert if more than 5 errors in 5 minutes
                if len(self.error_counts[service_name]) >= 5:
                    alerts.append(Alert(
                        severity=AlertSeverity.WARNING,
                        source="ALOY",
                        title=f"High Error Rate: {service_name}",
                        message=f"{len(self.error_counts[service_name])} errors in last 5 minutes",
                        target=service_name,
                        details={
                            "error_count": len(self.error_counts[service_name]),
                            "recent_errors": error_lines[-3:]
                        }
                    ))

            except Exception as e:
                logger.error(f"Error checking logs for {service_name}: {e}")

        return alerts

    async def check_data_integrity(self) -> List[Alert]:
        """Check for data loss by monitoring row counts"""
        alerts = []

        for env, container in DB_CONTAINERS.items():
            for table in MONITORED_TABLES:
                try:
                    # Get current count
                    result = subprocess.run(
                        ["docker", "exec", container, "psql", "-U", "postgres", "-d", "postgres",
                         "-t", "-c", f"SELECT COUNT(*) FROM {table};"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode != 0:
                        continue  # Table might not exist in this env

                    current_count = int(result.stdout.strip())
                    prev_count = self.previous_counts[env].get(table, current_count)

                    # Check for significant drop (more than 10% or more than 10 rows)
                    if prev_count > 0:
                        drop = prev_count - current_count
                        drop_pct = (drop / prev_count) * 100

                        if drop > 10 and drop_pct > 10:
                            alerts.append(Alert(
                                severity=AlertSeverity.CRITICAL,
                                source="ALOY",
                                title=f"DATA LOSS DETECTED: {table}",
                                message=f"{env.upper()}: {table} dropped from {prev_count} to {current_count} rows ({drop_pct:.1f}% loss)",
                                target=f"{env}:{table}",
                                details={
                                    "environment": env,
                                    "table": table,
                                    "previous_count": prev_count,
                                    "current_count": current_count,
                                    "rows_lost": drop,
                                    "percent_lost": drop_pct
                                }
                            ))

                    # Update tracking
                    self.previous_counts[env][table] = current_count

                except Exception as e:
                    logger.debug(f"Error checking {env}.{table}: {e}")

        return alerts

    async def check_schema_consistency(self) -> List[Alert]:
        """Check for schema mismatches between dev and prod"""
        alerts = []

        # Tables that should exist in both envs
        critical_tables = ["aria_conversations", "aria_messages"]

        for table in critical_tables:
            try:
                # Get dev schema
                dev_result = subprocess.run(
                    ["docker", "exec", DB_CONTAINERS["dev"], "psql", "-U", "postgres", "-d", "postgres",
                     "-t", "-c", f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position;"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                # Get prod schema
                prod_result = subprocess.run(
                    ["docker", "exec", DB_CONTAINERS["prod"], "psql", "-U", "postgres", "-d", "postgres",
                     "-t", "-c", f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}' ORDER BY ordinal_position;"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                dev_schema = dev_result.stdout.strip()
                prod_schema = prod_result.stdout.strip()

                if dev_schema and prod_schema and dev_schema != prod_schema:
                    alerts.append(Alert(
                        severity=AlertSeverity.WARNING,
                        source="ALOY",
                        title=f"Schema Mismatch: {table}",
                        message=f"DEV and PROD have different schemas for {table}",
                        target=table,
                        details={
                            "table": table,
                            "dev_columns": dev_schema.split('\n')[:10],
                            "prod_columns": prod_schema.split('\n')[:10]
                        }
                    ))

            except Exception as e:
                logger.debug(f"Error checking schema for {table}: {e}")

        return alerts

    async def check_service_health(self) -> List[Alert]:
        """Check health endpoints of monitored services"""
        alerts = []

        async with httpx.AsyncClient(timeout=5.0) as client:
            for service_name, config in MONITORED_SERVICES.items():
                try:
                    response = await client.get(config["health_url"])

                    if response.status_code != 200:
                        alerts.append(Alert(
                            severity=AlertSeverity.CRITICAL,
                            source="ALOY",
                            title=f"Service Unhealthy: {service_name}",
                            message=f"{service_name} returned status {response.status_code}",
                            target=service_name,
                            details={
                                "service": service_name,
                                "status_code": response.status_code,
                                "response": response.text[:500]
                            }
                        ))
                    else:
                        # Check response for issues
                        try:
                            health_data = response.json()
                            if health_data.get("status") != "healthy":
                                alerts.append(Alert(
                                    severity=AlertSeverity.WARNING,
                                    source="ALOY",
                                    title=f"Service Degraded: {service_name}",
                                    message=f"{service_name} reports non-healthy status",
                                    target=service_name,
                                    details=health_data
                                ))
                        except:
                            pass

                except httpx.ConnectError:
                    alerts.append(Alert(
                        severity=AlertSeverity.CRITICAL,
                        source="ALOY",
                        title=f"Service Unreachable: {service_name}",
                        message=f"Cannot connect to {service_name}",
                        target=service_name,
                        details={"service": service_name, "url": config["health_url"]}
                    ))
                except Exception as e:
                    logger.error(f"Error checking health for {service_name}: {e}")

        return alerts

    async def log_to_lcis(self, content: str, lesson_type: str = "insight"):
        """Log findings to LCIS"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{LCIS_URL}/ingest",
                    json={
                        "content": content,
                        "domain": "SENTINELS",
                        "type": lesson_type,
                        "source_agent": "ALOY",
                        "tags": ["monitoring", "anomaly-detection"]
                    }
                )
        except:
            pass


# =============================================================================
# MAIN
# =============================================================================

async def main():
    logger.info("ALOY WATCHER V2 starting...")
    watcher = AloyWatcherV2()
    await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())
