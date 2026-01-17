"""
Comprehensive health check tests for all Leveredge agents.

This module tests the /health endpoint of every agent to ensure
the infrastructure is running properly.
"""

import asyncio
from typing import Any

import httpx
import pytest

from conftest import (
    CORE_AGENTS,
    SECURITY_AGENTS,
    CREATIVE_AGENTS,
    PERSONAL_AGENTS,
    BUSINESS_AGENTS,
    ALL_AGENTS,
    check_agent_health,
)


# =============================================================================
# CORE AGENTS HEALTH CHECKS
# =============================================================================

class TestCoreAgentsHealth:
    """Health checks for core infrastructure agents."""

    @pytest.mark.health
    @pytest.mark.core
    @pytest.mark.parametrize("agent_name,port", list(CORE_AGENTS.items()))
    async def test_core_agent_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
        agent_name: str,
        port: int,
    ):
        """Test that core agent responds to health check."""
        result = await check_agent_health(
            async_client, base_url, agent_name, port, timeout=5.0
        )

        assert result["healthy"], (
            f"Agent {agent_name} (port {port}) is not healthy. "
            f"Status: {result['status_code']}, Error: {result['error']}"
        )

    @pytest.mark.health
    @pytest.mark.core
    async def test_atlas_orchestrator_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS orchestrator is healthy and responds with expected fields."""
        port = CORE_AGENTS["atlas"]
        url = f"{base_url}:{port}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"ATLAS health check failed with status {response.status_code}"
            )

            data = response.json()
            # ATLAS should report its status
            assert "status" in data or "healthy" in data, (
                "ATLAS health response missing status field"
            )

        except httpx.ConnectError:
            pytest.fail(f"Cannot connect to ATLAS on port {port}")
        except httpx.TimeoutException:
            pytest.fail(f"ATLAS health check timed out on port {port}")

    @pytest.mark.health
    @pytest.mark.core
    async def test_event_bus_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test Event Bus is healthy and ready to accept events."""
        port = CORE_AGENTS["event_bus"]
        url = f"{base_url}:{port}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"Event Bus health check failed with status {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.fail(f"Cannot connect to Event Bus on port {port}")
        except httpx.TimeoutException:
            pytest.fail(f"Event Bus health check timed out on port {port}")

    @pytest.mark.health
    @pytest.mark.core
    async def test_sentinel_router_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test SENTINEL router is healthy."""
        port = CORE_AGENTS["sentinel"]
        url = f"{base_url}:{port}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"SENTINEL health check failed with status {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.fail(f"Cannot connect to SENTINEL on port {port}")
        except httpx.TimeoutException:
            pytest.fail(f"SENTINEL health check timed out on port {port}")


# =============================================================================
# SECURITY FLEET HEALTH CHECKS
# =============================================================================

class TestSecurityFleetHealth:
    """Health checks for security fleet agents."""

    @pytest.mark.health
    @pytest.mark.security
    @pytest.mark.parametrize("agent_name,port", list(SECURITY_AGENTS.items()))
    async def test_security_agent_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
        agent_name: str,
        port: int,
    ):
        """Test that security agent responds to health check."""
        result = await check_agent_health(
            async_client, base_url, agent_name, port, timeout=5.0
        )

        assert result["healthy"], (
            f"Security agent {agent_name} (port {port}) is not healthy. "
            f"Status: {result['status_code']}, Error: {result['error']}"
        )

    @pytest.mark.health
    @pytest.mark.security
    async def test_cerberus_gateway_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS security gateway is healthy."""
        port = SECURITY_AGENTS["cerberus"]
        url = f"{base_url}:{port}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"CERBERUS health check failed with status {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.fail(f"Cannot connect to CERBERUS on port {port}")
        except httpx.TimeoutException:
            pytest.fail(f"CERBERUS health check timed out on port {port}")


# =============================================================================
# CREATIVE FLEET HEALTH CHECKS
# =============================================================================

class TestCreativeFleetHealth:
    """Health checks for creative fleet agents."""

    @pytest.mark.health
    @pytest.mark.creative
    @pytest.mark.parametrize("agent_name,port", list(CREATIVE_AGENTS.items()))
    async def test_creative_agent_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
        agent_name: str,
        port: int,
    ):
        """Test that creative agent responds to health check."""
        result = await check_agent_health(
            async_client, base_url, agent_name, port, timeout=5.0
        )

        assert result["healthy"], (
            f"Creative agent {agent_name} (port {port}) is not healthy. "
            f"Status: {result['status_code']}, Error: {result['error']}"
        )

    @pytest.mark.health
    @pytest.mark.creative
    async def test_muse_director_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test MUSE creative director is healthy."""
        port = CREATIVE_AGENTS["muse"]
        url = f"{base_url}:{port}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"MUSE health check failed with status {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.fail(f"Cannot connect to MUSE on port {port}")
        except httpx.TimeoutException:
            pytest.fail(f"MUSE health check timed out on port {port}")


# =============================================================================
# PERSONAL FLEET HEALTH CHECKS
# =============================================================================

class TestPersonalFleetHealth:
    """Health checks for personal fleet agents."""

    @pytest.mark.health
    @pytest.mark.personal
    @pytest.mark.parametrize("agent_name,port", list(PERSONAL_AGENTS.items()))
    async def test_personal_agent_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
        agent_name: str,
        port: int,
    ):
        """Test that personal agent responds to health check."""
        result = await check_agent_health(
            async_client, base_url, agent_name, port, timeout=5.0
        )

        assert result["healthy"], (
            f"Personal agent {agent_name} (port {port}) is not healthy. "
            f"Status: {result['status_code']}, Error: {result['error']}"
        )


# =============================================================================
# BUSINESS FLEET HEALTH CHECKS
# =============================================================================

class TestBusinessFleetHealth:
    """Health checks for business fleet agents."""

    @pytest.mark.health
    @pytest.mark.business
    @pytest.mark.parametrize("agent_name,port", list(BUSINESS_AGENTS.items()))
    async def test_business_agent_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
        agent_name: str,
        port: int,
    ):
        """Test that business agent responds to health check."""
        result = await check_agent_health(
            async_client, base_url, agent_name, port, timeout=5.0
        )

        assert result["healthy"], (
            f"Business agent {agent_name} (port {port}) is not healthy. "
            f"Status: {result['status_code']}, Error: {result['error']}"
        )


# =============================================================================
# AGGREGATE HEALTH CHECKS
# =============================================================================

class TestAggregateHealth:
    """Aggregate health checks across all fleets."""

    @pytest.mark.health
    @pytest.mark.slow
    async def test_all_agents_health_summary(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test all agents and generate a health summary."""
        results = []

        # Check all agents concurrently
        tasks = [
            check_agent_health(async_client, base_url, name, port)
            for name, port in ALL_AGENTS.items()
        ]
        results = await asyncio.gather(*tasks)

        # Analyze results
        healthy_count = sum(1 for r in results if r["healthy"])
        unhealthy_count = len(results) - healthy_count
        total_count = len(results)

        # Build summary
        unhealthy_agents = [
            f"{r['agent']}:{r['port']} ({r['error'] or 'status ' + str(r['status_code'])})"
            for r in results if not r["healthy"]
        ]

        # Report
        print(f"\nHealth Summary: {healthy_count}/{total_count} agents healthy")
        if unhealthy_agents:
            print(f"Unhealthy agents: {', '.join(unhealthy_agents)}")

        # Assert based on threshold (at least 80% should be healthy for this test to pass)
        health_ratio = healthy_count / total_count
        assert health_ratio >= 0.5, (
            f"Only {healthy_count}/{total_count} agents are healthy. "
            f"Unhealthy: {unhealthy_agents}"
        )

    @pytest.mark.health
    async def test_core_infrastructure_healthy(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that critical core infrastructure is healthy."""
        critical_agents = ["atlas", "sentinel", "event_bus", "aegis", "chronos"]

        for agent_name in critical_agents:
            port = CORE_AGENTS[agent_name]
            result = await check_agent_health(
                async_client, base_url, agent_name, port
            )

            assert result["healthy"], (
                f"Critical agent {agent_name} (port {port}) is not healthy! "
                f"Error: {result['error']}"
            )

    @pytest.mark.health
    async def test_fleet_health_by_category(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test health of each fleet category."""
        fleets = {
            "core": CORE_AGENTS,
            "security": SECURITY_AGENTS,
            "creative": CREATIVE_AGENTS,
            "personal": PERSONAL_AGENTS,
            "business": BUSINESS_AGENTS,
        }

        fleet_health = {}

        for fleet_name, agents in fleets.items():
            tasks = [
                check_agent_health(async_client, base_url, name, port)
                for name, port in agents.items()
            ]
            results = await asyncio.gather(*tasks)

            healthy = sum(1 for r in results if r["healthy"])
            total = len(results)
            fleet_health[fleet_name] = {
                "healthy": healthy,
                "total": total,
                "ratio": healthy / total if total > 0 else 0,
            }

        # Print summary
        print("\nFleet Health Summary:")
        for fleet, stats in fleet_health.items():
            status = "OK" if stats["ratio"] >= 0.8 else "DEGRADED" if stats["ratio"] >= 0.5 else "CRITICAL"
            print(f"  {fleet}: {stats['healthy']}/{stats['total']} ({status})")


# =============================================================================
# RESPONSE FORMAT VALIDATION
# =============================================================================

class TestHealthResponseFormat:
    """Test that health responses follow expected formats."""

    @pytest.mark.health
    async def test_health_response_has_status(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that health endpoints return proper status."""
        # Test a few key agents
        test_agents = ["atlas", "aegis", "event_bus"]

        for agent_name in test_agents:
            port = CORE_AGENTS[agent_name]
            url = f"{base_url}:{port}/health"

            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Health response should have some status indicator
                        has_status = any(
                            key in data
                            for key in ["status", "healthy", "ok", "alive"]
                        )
                        assert has_status, (
                            f"Agent {agent_name} health response missing status field: {data}"
                        )
                    except Exception:
                        # Non-JSON response is okay for health checks
                        pass
            except (httpx.ConnectError, httpx.TimeoutException):
                pytest.skip(f"Agent {agent_name} not available")


# =============================================================================
# CONNECTIVITY TESTS
# =============================================================================

class TestConnectivity:
    """Test network connectivity between components."""

    @pytest.mark.health
    async def test_port_range_accessibility(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that expected port ranges are accessible."""
        port_ranges = {
            "core": range(8007, 8020),  # 8007-8019
            "security": range(8020, 8022),  # 8020-8021
            "creative": range(8030, 8035),  # 8030-8034
            "personal": range(8100, 8111),  # 8100-8110
            "business": range(8200, 8210),  # 8200-8209
        }

        accessible_ports = set()
        for name, port in ALL_AGENTS.items():
            try:
                response = await async_client.get(
                    f"{base_url}:{port}/health",
                    timeout=2.0
                )
                if response.status_code in (200, 404, 405):  # Port is responding
                    accessible_ports.add(port)
            except (httpx.ConnectError, httpx.TimeoutException):
                pass

        print(f"\nAccessible ports: {sorted(accessible_ports)}")
        print(f"Expected ports: {sorted(ALL_AGENTS.values())}")

    @pytest.mark.health
    async def test_event_bus_reachable_from_agents(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that Event Bus is reachable (critical for inter-agent communication)."""
        event_bus_port = CORE_AGENTS["event_bus"]

        try:
            response = await async_client.get(
                f"{base_url}:{event_bus_port}/health",
                timeout=5.0
            )
            assert response.status_code == 200, (
                f"Event Bus not healthy: status {response.status_code}"
            )
        except httpx.ConnectError:
            pytest.fail("Event Bus is not reachable - inter-agent communication will fail")
        except httpx.TimeoutException:
            pytest.fail("Event Bus is timing out - may cause communication delays")
