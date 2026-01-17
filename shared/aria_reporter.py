#!/usr/bin/env python3
"""
ARIA Reporter - Shared module for agents to report to ARIA omniscience.

All agents should use this module to report significant actions, decisions,
errors, and learned facts to the ARIA omniscience system.

Usage:
    from shared.aria_reporter import ARIAReporter

    reporter = ARIAReporter("SOLON")

    # Report an action
    await reporter.report_action(
        action="answered_legal_question",
        target="employment law query",
        details={"jurisdiction": "CA", "confidence": 85}
    )

    # Report a decision
    await reporter.report_decision(
        decision="recommended_attorney_consultation",
        reasoning="Query involves complex fact pattern requiring professional advice",
        outcome="user_directed_to_seek_professional_help"
    )

Location: /opt/leveredge/shared/aria_reporter.py
"""

import os
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ARIAReporter:
    """
    Reporter for agents to emit events to ARIA omniscience system.

    All significant actions and decisions should be reported so ARIA
    maintains comprehensive awareness of system activity.

    This module is designed to be non-blocking and failure-tolerant.
    If reporting fails, the agent continues normally - we never let
    omniscience reporting break agent functionality.
    """

    # Domain mapping for automatic inference
    DOMAIN_MAP = {
        "SOLON": "legal",
        "CROESUS": "tax",
        "PLUTUS": "finance",
        "SCHOLAR": "research",
        "CHIRON": "business",
        "MENTOR": "business",
        "HERACLES": "business",
        "LIBRARIAN": "knowledge",
        "DAEDALUS": "automation",
        "THEMIS": "legal",
        "PROCUREMENT": "business",
        "HEPHAESTUS-SERVER": "infrastructure",
        "ATLAS-INFRA": "infrastructure",
        "IRIS": "news",
        "GYM-COACH": "health",
        "NUTRITIONIST": "health",
        "MEAL-PLANNER": "health",
        "ACADEMIC-GUIDE": "education",
        "EROS": "personal",
        "MUSE": "creative",
        "CALLIOPE": "creative",
        "THALIA": "creative",
        "ERATO": "creative",
        "CLIO": "creative",
        "HERMES": "notifications",
        "AEGIS": "security",
        "CERBERUS": "security",
        "PORT-MANAGER": "infrastructure",
        "CHRONOS": "infrastructure",
        "HADES": "infrastructure",
        "ATHENA": "documentation",
        "ARGUS": "monitoring",
        "ALOY": "audit",
        "SENTINEL": "routing",
        "FILE-PROCESSOR": "processing",
        "VOICE": "interface",
        "MEMORY-V2": "memory",
        "SHIELD-SWORD": "security",
        "GATEWAY": "infrastructure",
    }

    def __init__(self, agent_name: str):
        """
        Initialize reporter for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., "SOLON", "CROESUS")
        """
        self.agent_name = agent_name
        self.event_bus_url = os.environ.get(
            "EVENT_BUS_URL",
            "http://event-bus:8099"
        )
        self.enabled = os.environ.get(
            "ARIA_REPORTING_ENABLED", "true"
        ).lower() == "true"
        self.timeout = float(os.environ.get("ARIA_REPORT_TIMEOUT", "5.0"))

    async def report_action(
        self,
        action: str,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        domain: Optional[str] = None,
        importance: str = "medium",
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Report an action taken by this agent.

        Use this when your agent completes a significant operation.

        Args:
            action: What action was taken (e.g., "answered_question", "analyzed_contract")
            target: What was acted upon (e.g., "employment law query", "service agreement")
            details: Additional structured details about the action
            domain: Domain category (legal, tax, finance, health, etc.) - auto-inferred if not provided
            importance: Priority level (high, medium, low)
            user_id: User associated with this action (if applicable)
            tags: Searchable tags for this action

        Returns:
            True if report was successful, False otherwise

        Example:
            await reporter.report_action(
                action="contract_analyzed",
                target="Service Agreement v2.pdf",
                details={
                    "contract_type": "service",
                    "risk_score": 65,
                    "flagged_clauses": 3
                },
                importance="medium"
            )
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": f"aria.action.{action}",
            "target": target,
            "details": {
                "event_type": "action",
                "action": action,
                "target": target,
                "domain": domain or self._infer_domain(),
                "importance": importance,
                "user_id": user_id,
                "tags": tags or [],
                "timestamp": datetime.utcnow().isoformat(),
                **(details or {})
            }
        }

        return await self._emit_event(event)

    async def report_decision(
        self,
        decision: str,
        reasoning: str,
        outcome: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        domain: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report a decision made by this agent.

        Use this when your agent makes a choice, especially when there were
        alternatives considered or when the reasoning is important.

        Args:
            decision: What was decided
            reasoning: Why this decision was made (important for ARIA context)
            outcome: Result of the decision (if known)
            alternatives: Other options that were considered
            confidence: Agent's confidence in this decision (0-100)
            domain: Domain category - auto-inferred if not provided
            user_id: User associated with this decision

        Returns:
            True if report was successful, False otherwise

        Example:
            await reporter.report_decision(
                decision="recommended_s_corp_election",
                reasoning="Net income > $75K threshold, estimated SE tax savings of $15K annually",
                outcome="tax_planning_strategy_provided",
                alternatives=["maintain_sole_prop", "llc_partnership"],
                confidence=85.0
            )
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": f"aria.decision.{decision.replace(' ', '_').lower()}",
            "details": {
                "event_type": "decision",
                "decision": decision,
                "reasoning": reasoning,
                "outcome": outcome,
                "alternatives": alternatives or [],
                "confidence": confidence,
                "domain": domain or self._infer_domain(),
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        return await self._emit_event(event)

    async def report_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report an error encountered by this agent.

        Use this when your agent encounters a failure. This helps ARIA
        understand system health and can inform users about issues.

        Args:
            error_type: Category of error (e.g., "api_failure", "validation_error")
            error_message: Human-readable error description
            context: Additional context about the error
            recoverable: Whether the agent recovered from this error
            user_id: User affected by this error

        Returns:
            True if report was successful, False otherwise

        Example:
            await reporter.report_error(
                error_type="external_api_failure",
                error_message="CourtListener API returned 503",
                context={"endpoint": "/search", "retry_count": 3},
                recoverable=True
            )
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": f"aria.error.{error_type}",
            "details": {
                "event_type": "error",
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
                "recoverable": recoverable,
                "user_id": user_id,
                "domain": self._infer_domain(),
                "importance": "high",
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        return await self._emit_event(event)

    async def report_fact_learned(
        self,
        fact: str,
        source: str,
        category: str,
        confidence: float = 100.0,
        related_to: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report a new fact learned by this agent.

        Use this when your agent discovers information that should be
        remembered for future context (user preferences, business facts, etc.)

        Args:
            fact: The fact that was learned
            source: Where this fact came from (e.g., "user_statement", "api_response")
            category: Category of fact (person, company, preference, deadline, etc.)
            confidence: How confident we are in this fact (0-100)
            related_to: Related entities or topics
            user_id: User this fact is about (if applicable)

        Returns:
            True if report was successful, False otherwise

        Example:
            await reporter.report_fact_learned(
                fact="User's business is an LLC formed in Nevada",
                source="user_statement",
                category="business",
                confidence=100.0,
                related_to=["tax_planning", "entity_structure"]
            )
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": "aria.fact.learned",
            "details": {
                "event_type": "fact",
                "fact": fact,
                "source": source,
                "category": category,
                "confidence": confidence,
                "related_to": related_to or [],
                "user_id": user_id,
                "domain": self._infer_domain(),
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        return await self._emit_event(event)

    async def report_task_completed(
        self,
        task: str,
        result: str,
        duration_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Report completion of a task.

        Use this when your agent completes a discrete unit of work.

        Args:
            task: What task was completed
            result: Outcome/result of the task
            duration_ms: How long the task took in milliseconds
            details: Additional details about the task
            user_id: User who requested this task

        Returns:
            True if report was successful, False otherwise

        Example:
            await reporter.report_task_completed(
                task="quarterly_tax_estimate",
                result="estimated_liability_$45000",
                duration_ms=2500,
                details={"tax_year": 2026, "quarters_remaining": 2}
            )
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": "aria.task.completed",
            "target": task,
            "details": {
                "event_type": "task",
                "task": task,
                "result": result,
                "duration_ms": duration_ms,
                "domain": self._infer_domain(),
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(details or {})
            }
        }

        return await self._emit_event(event)

    async def report_external_call(
        self,
        service: str,
        endpoint: str,
        success: bool,
        response_time_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Report an external API call made by this agent.

        Use this when calling external services (not other LeverEdge agents).

        Args:
            service: Name of external service (e.g., "courtlistener", "irs_api")
            endpoint: API endpoint called
            success: Whether the call succeeded
            response_time_ms: Response time in milliseconds
            details: Additional call details

        Returns:
            True if report was successful, False otherwise
        """
        if not self.enabled:
            return True

        event = {
            "source_agent": self.agent_name,
            "action": "aria.external_call",
            "target": f"{service}:{endpoint}",
            "details": {
                "event_type": "external_call",
                "service": service,
                "endpoint": endpoint,
                "success": success,
                "response_time_ms": response_time_ms,
                "domain": self._infer_domain(),
                "importance": "low" if success else "medium",
                "timestamp": datetime.utcnow().isoformat(),
                **(details or {})
            }
        }

        return await self._emit_event(event)

    async def _emit_event(self, event: dict) -> bool:
        """
        Emit event to Event Bus.

        This method is designed to be non-blocking and failure-tolerant.
        We never let reporting failures break agent functionality.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.event_bus_url}/events",
                    json=event,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    return True
                else:
                    logger.warning(
                        f"[{self.agent_name}] ARIA report returned {response.status_code}"
                    )
                    return False
        except httpx.TimeoutException:
            logger.warning(f"[{self.agent_name}] ARIA report timed out")
            return False
        except Exception as e:
            # Don't let reporting failures break agent functionality
            logger.warning(f"[{self.agent_name}] Failed to report to ARIA: {e}")
            return False

    def _infer_domain(self) -> str:
        """Infer domain based on agent name."""
        return self.DOMAIN_MAP.get(self.agent_name, "general")


# Convenience function for one-off reports
async def report_to_aria(
    agent: str,
    action: str,
    details: dict,
    domain: str = "general"
) -> bool:
    """
    Quick one-off report to ARIA.

    Use this when you need to report from code that doesn't have
    a persistent ARIAReporter instance.

    Args:
        agent: Agent name
        action: Action taken
        details: Action details
        domain: Domain category

    Returns:
        True if successful

    Example:
        await report_to_aria(
            "CUSTOM_SCRIPT",
            "migration_completed",
            {"tables_migrated": 5, "duration_seconds": 120}
        )
    """
    reporter = ARIAReporter(agent)
    return await reporter.report_action(action, details=details, domain=domain)


# Sync wrapper for non-async contexts
def report_to_aria_sync(
    agent: str,
    action: str,
    details: dict,
    domain: str = "general"
) -> bool:
    """
    Synchronous wrapper for report_to_aria.

    Use this in synchronous code paths where async isn't available.
    Note: This creates an event loop, so prefer the async version when possible.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a task
            asyncio.create_task(report_to_aria(agent, action, details, domain))
            return True
        else:
            return loop.run_until_complete(
                report_to_aria(agent, action, details, domain)
            )
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(report_to_aria(agent, action, details, domain))
