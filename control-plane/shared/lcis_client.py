"""
LCIS Client - Mandatory consultation before any action

ALL AGENTS MUST USE THIS before:
- Building anything
- Editing files
- Deploying services
- Creating resources
- Deleting anything

Usage:
    from lcis_client import consult, must_consult, before_deploy

    @must_consult("build", "my-service")
    async def build_service():
        ...

    # Or manually:
    result = await consult("edit", "/path/to/file", "Adding feature X")
    if not result.proceed:
        raise BlockedByLCIS(result.blockers)
"""

import os
import httpx
import functools
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Callable, Any, Dict

LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")


@dataclass
class ConsultationResult:
    consultation_id: str
    proceed: bool
    blockers: List[str]
    warnings: List[str]
    recommendations: List[str]
    relevant_lessons: List[dict]
    must_acknowledge: bool


class BlockedByLCIS(Exception):
    """Raised when LCIS blocks an action"""
    def __init__(self, blockers: List[str]):
        self.blockers = blockers
        super().__init__(f"Action blocked by LCIS: {blockers}")


async def consult(action: str, target: str, context: str = None,
                  agent: str = "UNKNOWN") -> ConsultationResult:
    """
    Consult LCIS before taking an action.

    Args:
        action: What you're doing (build, edit, deploy, delete, create)
        target: What you're acting on (service name, file path, etc.)
        context: Additional context about why/what
        agent: Your agent name

    Returns:
        ConsultationResult with proceed flag and any warnings/blockers
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{LCIS_URL}/consult",
                json={
                    "action": action,
                    "target": target,
                    "context": context,
                    "agent": agent
                }
            )
            data = response.json()

            result = ConsultationResult(
                consultation_id=data.get("consultation_id", ""),
                proceed=data.get("proceed", True),
                blockers=data.get("blockers", []),
                warnings=data.get("warnings", []),
                recommendations=data.get("recommendations", []),
                relevant_lessons=data.get("relevant_lessons", []),
                must_acknowledge=data.get("must_acknowledge", False)
            )

            # Log consultation results
            if result.blockers:
                print(f"[LCIS] BLOCKED for {action} {target}:")
                for b in result.blockers:
                    print(f"  {b}")

            if result.warnings:
                print(f"[LCIS] Warnings for {action} {target}:")
                for w in result.warnings:
                    print(f"  {w}")

            if result.recommendations:
                print(f"[LCIS] Recommendations:")
                for r in result.recommendations:
                    print(f"  {r}")

            return result

    except Exception as e:
        # If LCIS is down, log but don't block
        print(f"[LCIS] Consultation failed (proceeding with caution): {e}")
        return ConsultationResult(
            consultation_id="offline",
            proceed=True,
            blockers=[],
            warnings=["LCIS offline - proceeding without consultation"],
            recommendations=[],
            relevant_lessons=[],
            must_acknowledge=False
        )


def must_consult(action: str, target: str):
    """
    Decorator that forces LCIS consultation before function execution.

    Usage:
        @must_consult("build", "my-agent")
        async def build_my_agent():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            agent_name = kwargs.get("agent", func.__module__.split(".")[-1].upper())
            context = kwargs.get("context", func.__doc__ or "")

            result = await consult(action, target, context, agent_name)

            if not result.proceed:
                raise BlockedByLCIS(result.blockers)

            if result.must_acknowledge:
                # In automated context, log the acknowledgment
                print(f"[LCIS] Acknowledged {len(result.warnings)} warnings for {action} {target}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def report_outcome(consultation_id: str, success: bool,
                         notes: str = None, error: str = None):
    """
    Report the outcome of an action back to LCIS.
    This closes the loop and enables learning.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{LCIS_URL}/outcome",
                json={
                    "consultation_id": consultation_id,
                    "success": success,
                    "notes": notes,
                    "error": error,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
    except:
        pass


async def ingest_lesson(content: str, lesson_type: str, domain: str,
                       agent: str, tags: List[str] = None,
                       solution: str = None, severity: str = "medium"):
    """
    Ingest a lesson directly into LCIS.

    Args:
        content: The lesson content
        lesson_type: failure, success, pattern, warning, insight
        domain: THE_KEEP, SENTINELS, CHANCERY, ARIA_SANCTUM, ALCHEMY
        agent: Source agent name
        tags: List of tags
        solution: How to fix/avoid (for failures)
        severity: critical, high, medium, low
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{LCIS_URL}/ingest",
                json={
                    "content": content,
                    "type": lesson_type,
                    "domain": domain,
                    "source_agent": agent,
                    "source_type": "agent_report",
                    "tags": tags or [],
                    "solution": solution,
                    "severity": severity
                }
            )
    except Exception as e:
        print(f"[LCIS] Failed to ingest lesson: {e}")


# Convenience functions for common actions
async def before_build(target: str, agent: str) -> ConsultationResult:
    """Consult LCIS before building something"""
    return await consult("build", target, agent=agent)


async def before_edit(filepath: str, agent: str) -> ConsultationResult:
    """Consult LCIS before editing a file"""
    return await consult("edit", filepath, agent=agent)


async def before_deploy(service: str, env: str, agent: str) -> ConsultationResult:
    """Consult LCIS before deploying"""
    return await consult("deploy", f"{service}:{env}", agent=agent)


async def before_delete(target: str, agent: str) -> ConsultationResult:
    """Consult LCIS before deleting something"""
    return await consult("delete", target, agent=agent)


async def get_agent_context(agent: str) -> Dict[str, Any]:
    """Get LCIS context for an agent - failures to avoid, rules to follow"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LCIS_URL}/context/{agent}")
            return response.json()
    except Exception as e:
        print(f"[LCIS] Failed to get agent context: {e}")
        return {"agent": agent, "failures_to_avoid": [], "rules_to_follow": []}
