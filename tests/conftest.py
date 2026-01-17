"""
Shared fixtures for Leveredge integration tests.

This module provides common fixtures for testing agents, including:
- HTTP clients (sync and async)
- Agent port mappings
- Common test data
- Health check utilities
"""

import asyncio
import os
from typing import Any

import httpx
import pytest


# =============================================================================
# AGENT PORT MAPPINGS
# =============================================================================

CORE_AGENTS = {
    "atlas": 8007,
    "hades": 8008,
    "chronos": 8010,
    "hephaestus": 8011,
    "aegis": 8012,
    "athena": 8013,
    "hermes": 8014,
    "aloy": 8015,
    "argus": 8016,
    "chiron": 8017,
    "scholar": 8018,
    "sentinel": 8019,
    "event_bus": 8099,
}

SECURITY_AGENTS = {
    "cerberus": 8020,
    "port_manager": 8021,
}

CREATIVE_AGENTS = {
    "muse": 8030,
    "calliope": 8031,
    "thalia": 8032,
    "erato": 8033,
    "clio": 8034,
}

PERSONAL_AGENTS = {
    "gym_coach": 8110,
    "nutritionist": 8101,
    "meal_planner": 8102,
    "academic_guide": 8103,
    "eros": 8104,
}

BUSINESS_AGENTS = {
    "heracles": 8200,
    "librarian": 8201,
    "daedalus": 8202,
    "themis": 8203,
    "mentor": 8204,
    "plutus": 8205,
    "procurement": 8206,
    "hephaestus_server": 8207,
    "atlas_infra": 8208,
    "iris": 8209,
}

ALL_AGENTS = {
    **CORE_AGENTS,
    **SECURITY_AGENTS,
    **CREATIVE_AGENTS,
    **PERSONAL_AGENTS,
    **BUSINESS_AGENTS,
}


# =============================================================================
# CONFIGURATION
# =============================================================================

@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for agent APIs."""
    return os.getenv("LEVEREDGE_BASE_URL", "http://localhost")


@pytest.fixture(scope="session")
def timeout() -> float:
    """Default timeout for HTTP requests."""
    return float(os.getenv("LEVEREDGE_TEST_TIMEOUT", "10.0"))


# =============================================================================
# HTTP CLIENTS
# =============================================================================

@pytest.fixture(scope="session")
def sync_client():
    """Synchronous HTTP client for tests."""
    with httpx.Client(timeout=30.0) as client:
        yield client


@pytest.fixture
async def async_client():
    """Asynchronous HTTP client for tests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


# =============================================================================
# PORT MAPPING FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def core_agents() -> dict[str, int]:
    """Core agent port mappings."""
    return CORE_AGENTS.copy()


@pytest.fixture(scope="session")
def security_agents() -> dict[str, int]:
    """Security fleet port mappings."""
    return SECURITY_AGENTS.copy()


@pytest.fixture(scope="session")
def creative_agents() -> dict[str, int]:
    """Creative fleet port mappings."""
    return CREATIVE_AGENTS.copy()


@pytest.fixture(scope="session")
def personal_agents() -> dict[str, int]:
    """Personal fleet port mappings."""
    return PERSONAL_AGENTS.copy()


@pytest.fixture(scope="session")
def business_agents() -> dict[str, int]:
    """Business fleet port mappings."""
    return BUSINESS_AGENTS.copy()


@pytest.fixture(scope="session")
def all_agents() -> dict[str, int]:
    """All agent port mappings."""
    return ALL_AGENTS.copy()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_agent_url(base_url: str, agent_name: str, port: int | None = None) -> str:
    """
    Construct the base URL for an agent.

    Args:
        base_url: Base URL (e.g., http://localhost)
        agent_name: Name of the agent
        port: Port number (if None, looks up from ALL_AGENTS)

    Returns:
        Full URL for the agent
    """
    if port is None:
        port = ALL_AGENTS.get(agent_name)
        if port is None:
            raise ValueError(f"Unknown agent: {agent_name}")
    return f"{base_url}:{port}"


async def check_agent_health(
    client: httpx.AsyncClient,
    base_url: str,
    agent_name: str,
    port: int,
    timeout: float = 5.0
) -> dict[str, Any]:
    """
    Check health of an agent.

    Args:
        client: HTTP client
        base_url: Base URL
        agent_name: Name of the agent
        port: Port number
        timeout: Request timeout

    Returns:
        Dict with health check results
    """
    url = f"{base_url}:{port}/health"
    result = {
        "agent": agent_name,
        "port": port,
        "healthy": False,
        "status_code": None,
        "response": None,
        "error": None,
    }

    try:
        response = await client.get(url, timeout=timeout)
        result["status_code"] = response.status_code
        result["healthy"] = response.status_code == 200

        try:
            result["response"] = response.json()
        except Exception:
            result["response"] = response.text

    except httpx.ConnectError as e:
        result["error"] = f"Connection refused: {e}"
    except httpx.TimeoutException as e:
        result["error"] = f"Timeout: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error: {type(e).__name__}: {e}"

    return result


@pytest.fixture
def check_health():
    """Fixture providing health check function."""
    return check_agent_health


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_event() -> dict:
    """Sample event for Event Bus tests."""
    return {
        "event": "test.integration",
        "source": "integration_tests",
        "data": {
            "test_id": "pytest_integration",
            "timestamp": "2026-01-17T12:00:00Z",
            "message": "Integration test event"
        }
    }


@pytest.fixture
def sample_notification() -> dict:
    """Sample notification for HERMES tests."""
    return {
        "channel": "event_bus",  # Use event_bus to avoid sending real notifications
        "message": "Integration test notification",
        "priority": "normal",
        "source": "integration_tests"
    }


@pytest.fixture
def sample_backup_request() -> dict:
    """Sample backup request for CHRONOS tests."""
    return {
        "type": "test",
        "component": "integration_tests",
        "description": "Integration test backup"
    }


@pytest.fixture
def sample_credential_query() -> dict:
    """Sample query for AEGIS tests."""
    return {
        "type": "list",
        "filters": {}
    }


# =============================================================================
# SKIP CONDITIONS
# =============================================================================

def agent_available(agent_name: str, port: int, base_url: str = "http://localhost") -> bool:
    """
    Check if an agent is available (synchronous check).

    Args:
        agent_name: Name of the agent
        port: Port number
        base_url: Base URL

    Returns:
        True if agent responds to health check
    """
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{base_url}:{port}/health")
            return response.status_code == 200
    except Exception:
        return False


def skip_if_agent_unavailable(agent_name: str, port: int):
    """
    Decorator to skip test if agent is not available.

    Usage:
        @skip_if_agent_unavailable("atlas", 8007)
        def test_atlas_feature():
            ...
    """
    return pytest.mark.skipif(
        not agent_available(agent_name, port),
        reason=f"Agent {agent_name} not available on port {port}"
    )


# =============================================================================
# ASYNC UTILITIES
# =============================================================================

@pytest.fixture
def event_loop_policy():
    """Set event loop policy for async tests."""
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# CLEANUP FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test (if needed)."""
    yield
    # Add cleanup logic here if tests create resources that need cleanup
    pass
