#!/usr/bin/env python3
"""
VARYS SCHEDULER - Automated Intelligence Briefings

Runs on schedule:
- Daily briefing at 7am
- Portfolio updates on changes
- Competitor alerts
- Opportunity pipeline
"""

import os
import sys
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.append('/opt/leveredge/control-plane/shared')
from watcher_base import ScheduledTaskBase

VARYS_URL = os.getenv("VARYS_URL", "http://varys:8112")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
WATCHDOG_URL = os.getenv("WATCHDOG_URL", "http://watchdog:8240")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")

class VarysDailyBriefing(ScheduledTaskBase):
    """Daily intelligence briefing"""

    def get_name(self) -> str:
        return "VARYS_SCHEDULER"

    def get_schedule(self) -> Dict[str, Any]:
        return {"type": "daily", "hour": 7, "minute": 0}

    async def execute(self) -> Optional[Dict[str, Any]]:
        """Generate and send daily briefing"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Try to get briefing from VARYS
                try:
                    response = await client.get(f"{VARYS_URL}/daily-briefing")
                    if response.status_code == 200:
                        briefing = response.json()
                    else:
                        briefing = {"summary": "VARYS service unavailable - no briefing generated"}
                except:
                    briefing = {"summary": "VARYS service unavailable - no briefing generated"}

                # Send via HERMES
                await client.post(
                    f"{HERMES_URL}/notify",
                    json={
                        "channel": "daily_briefing",
                        "title": f"Daily Intelligence Briefing - {datetime.now().strftime('%Y-%m-%d')}",
                        "message": briefing.get("summary", "No briefing available"),
                        "details": briefing
                    }
                )

                return briefing

        except Exception as e:
            return {"error": str(e)}

# =============================================================================
# HEARTBEAT SENDER
# =============================================================================

async def send_heartbeats(scheduler: VarysDailyBriefing):
    """Send periodic heartbeats to WATCHDOG"""
    while scheduler.running:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{WATCHDOG_URL}/heartbeat",
                    json={
                        "watcher_name": "VARYS_SCHEDULER",
                        "state": "running",
                        "last_check": datetime.utcnow().isoformat(),
                        "checks_performed": scheduler.run_count,
                        "alerts_sent": 0,
                        "errors": scheduler.errors[-10:]
                    }
                )
        except:
            pass
        await asyncio.sleep(30)

# =============================================================================
# GSD CLEANUP REMINDER
# =============================================================================

LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")

async def check_gsd_cleanups():
    """Periodic check for incomplete GSD cleanups - runs every 2 hours"""
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{LCIS_URL}/validate/pending-cleanups")
                data = response.json()

                if data.get("count", 0) > 0:
                    specs = [p["spec"] for p in data["pending_cleanups"]]
                    await client.post(
                        f"{HERMES_URL}/alert",
                        json={
                            "severity": "info",
                            "source": "LCIS",
                            "title": f"GSD Cleanup Reminder: {len(specs)} specs pending",
                            "message": f"Move to done/: {', '.join(specs)}"
                        }
                    )
        except Exception as e:
            print(f"[VARYS] GSD cleanup check error: {e}")

        await asyncio.sleep(7200)  # Every 2 hours

# =============================================================================
# MAIN
# =============================================================================

async def main():
    scheduler = VarysDailyBriefing()

    # Run scheduler, heartbeat, and GSD cleanup reminder
    await asyncio.gather(
        scheduler.run(),
        send_heartbeats(scheduler),
        check_gsd_cleanups()
    )

if __name__ == "__main__":
    asyncio.run(main())
