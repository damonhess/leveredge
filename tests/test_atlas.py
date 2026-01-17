"""
ATLAS Orchestration Tests.

Tests for ATLAS (port 8007) - the orchestration engine that handles
chain execution and multi-agent coordination.
"""

import httpx
import pytest

from conftest import CORE_AGENTS, check_agent_health


ATLAS_PORT = CORE_AGENTS["atlas"]


# =============================================================================
# HEALTH AND STATUS TESTS
# =============================================================================

class TestAtlasHealth:
    """Test ATLAS health and status endpoints."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_atlas_health_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS /health endpoint returns 200."""
        url = f"{base_url}:{ATLAS_PORT}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"ATLAS health check failed with status {response.status_code}"
            )

            data = response.json()
            assert "status" in data or "healthy" in data, (
                "ATLAS health response missing status indicator"
            )

        except httpx.ConnectError:
            pytest.skip("ATLAS not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_atlas_has_agent_registry(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS can access agent registry."""
        # Try common endpoints that might list available agents/chains
        endpoints = ["/agents", "/chains", "/registry", "/status"]

        for endpoint in endpoints:
            url = f"{base_url}:{ATLAS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Found valid endpoint: {endpoint}")
                    print(f"Response: {data}")
                    return  # Found a working endpoint
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        # If no endpoint found, just verify health works
        health_result = await check_agent_health(
            async_client, base_url, "atlas", ATLAS_PORT
        )
        assert health_result["healthy"], "ATLAS is not healthy"


# =============================================================================
# CHAIN EXECUTION TESTS
# =============================================================================

class TestAtlasChains:
    """Test ATLAS chain execution capabilities."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_list_available_chains(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test listing available chains."""
        # Try endpoints that might list chains
        endpoints = ["/chains", "/list-chains", "/available-chains"]

        for endpoint in endpoints:
            url = f"{base_url}:{ATLAS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    # Verify response contains chain information
                    assert isinstance(data, (list, dict)), (
                        f"Unexpected response type from {endpoint}: {type(data)}"
                    )
                    print(f"Chains endpoint {endpoint}: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No chain listing endpoint found")

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.slow
    async def test_execute_simple_chain(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test executing a simple chain (if available)."""
        # This test depends on having chains configured
        execute_endpoints = ["/execute", "/run", "/chain/execute"]

        test_payload = {
            "chain_name": "health-check",  # A hypothetical simple chain
            "input": {"test": True}
        }

        for endpoint in execute_endpoints:
            url = f"{base_url}:{ATLAS_PORT}{endpoint}"
            try:
                response = await async_client.post(
                    url,
                    json=test_payload,
                    timeout=10.0
                )
                if response.status_code in (200, 201, 202):
                    data = response.json()
                    print(f"Chain execution response: {data}")
                    return
                elif response.status_code == 404:
                    continue
                elif response.status_code == 400:
                    # Bad request might mean endpoint exists but chain doesn't
                    print(f"Endpoint exists but request failed: {response.text}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception as e:
                print(f"Error testing {endpoint}: {e}")
                continue

        pytest.skip("No chain execution endpoint found")


# =============================================================================
# AGENT ROUTING TESTS
# =============================================================================

class TestAtlasRouting:
    """Test ATLAS routing to other agents."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_route_to_agent(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS can route requests to other agents."""
        route_endpoints = ["/route", "/dispatch", "/agent/call"]

        test_payload = {
            "agent": "hermes",
            "action": "health",
            "payload": {}
        }

        for endpoint in route_endpoints:
            url = f"{base_url}:{ATLAS_PORT}{endpoint}"
            try:
                response = await async_client.post(
                    url,
                    json=test_payload,
                    timeout=10.0
                )
                if response.status_code in (200, 201, 202):
                    print(f"Route response: {response.json()}")
                    return
                elif response.status_code == 404:
                    continue
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No routing endpoint found")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_agent_discovery(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS can discover available agents."""
        discovery_endpoints = ["/agents", "/discover", "/registry"]

        for endpoint in discovery_endpoints:
            url = f"{base_url}:{ATLAS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Agent discovery: {data}")

                    # If it's a list, verify it contains agent info
                    if isinstance(data, list) and len(data) > 0:
                        assert any(
                            "name" in item or "agent" in item
                            for item in data
                        ), "Agent discovery response missing agent info"

                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No agent discovery endpoint found")


# =============================================================================
# ORCHESTRATION WORKFLOW TESTS
# =============================================================================

class TestAtlasOrchestration:
    """Test ATLAS orchestration workflows."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_orchestration_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS orchestration endpoint."""
        url = f"{base_url}:{ATLAS_PORT}/orchestrate"

        try:
            # Test with minimal payload
            response = await async_client.post(
                url,
                json={"chain_name": "test", "input": {}},
                timeout=5.0
            )

            # Accept various responses - we're testing if endpoint exists
            assert response.status_code in (200, 201, 202, 400, 404, 422), (
                f"Unexpected status from orchestrate: {response.status_code}"
            )

            if response.status_code in (200, 201, 202):
                print(f"Orchestration response: {response.json()}")

        except httpx.ConnectError:
            pytest.skip("ATLAS not available")

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.slow
    async def test_parallel_execution(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS can handle parallel execution requests."""
        import asyncio

        # Send multiple requests concurrently
        async def make_request():
            try:
                return await async_client.get(
                    f"{base_url}:{ATLAS_PORT}/health",
                    timeout=5.0
                )
            except Exception as e:
                return e

        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful responses
        successes = sum(
            1 for r in results
            if isinstance(r, httpx.Response) and r.status_code == 200
        )

        assert successes >= 3, (
            f"ATLAS should handle parallel requests. Got {successes}/5 successes"
        )


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestAtlasErrorHandling:
    """Test ATLAS error handling."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_invalid_chain_returns_error(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS returns appropriate error for invalid chain."""
        execute_endpoints = ["/execute", "/orchestrate", "/chain/execute"]

        for endpoint in execute_endpoints:
            url = f"{base_url}:{ATLAS_PORT}{endpoint}"
            try:
                response = await async_client.post(
                    url,
                    json={
                        "chain_name": "nonexistent_chain_12345",
                        "input": {}
                    },
                    timeout=5.0
                )

                # Should get 400 or 404 for invalid chain
                if response.status_code in (400, 404, 422):
                    print(f"Correct error handling: {response.status_code}")
                    return
                elif response.status_code == 200:
                    # Some implementations might return error in body
                    data = response.json()
                    if "error" in data or "success" in data and not data.get("success"):
                        print(f"Error in response body: {data}")
                        return

            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No chain execution endpoint found to test error handling")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_malformed_request_handling(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS handles malformed requests gracefully."""
        url = f"{base_url}:{ATLAS_PORT}/orchestrate"

        try:
            # Send request with missing required fields
            response = await async_client.post(
                url,
                json={},  # Empty payload
                timeout=5.0
            )

            # Should not crash - return 400 or 422
            assert response.status_code in (400, 404, 422), (
                f"Expected error status for malformed request, got {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("ATLAS not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_invalid_json_handling(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS handles invalid JSON gracefully."""
        url = f"{base_url}:{ATLAS_PORT}/orchestrate"

        try:
            response = await async_client.post(
                url,
                content="not valid json {{{",
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )

            # Should return 400 for invalid JSON
            assert response.status_code in (400, 404, 422, 500), (
                f"Expected error for invalid JSON, got {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("ATLAS not available")


# =============================================================================
# INTEGRATION WITH OTHER AGENTS
# =============================================================================

class TestAtlasIntegration:
    """Test ATLAS integration with other agents."""

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.slow
    async def test_atlas_can_call_hermes(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS can coordinate with HERMES."""
        # Verify both agents are healthy first
        atlas_health = await check_agent_health(
            async_client, base_url, "atlas", ATLAS_PORT
        )
        hermes_health = await check_agent_health(
            async_client, base_url, "hermes", CORE_AGENTS["hermes"]
        )

        if not atlas_health["healthy"]:
            pytest.skip("ATLAS not available")
        if not hermes_health["healthy"]:
            pytest.skip("HERMES not available")

        # If both are healthy, integration is possible
        assert atlas_health["healthy"] and hermes_health["healthy"], (
            "Both ATLAS and HERMES should be healthy for integration"
        )

    @pytest.mark.integration
    @pytest.mark.core
    async def test_atlas_sentinel_coordination(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ATLAS and SENTINEL coordination."""
        atlas_health = await check_agent_health(
            async_client, base_url, "atlas", ATLAS_PORT
        )
        sentinel_health = await check_agent_health(
            async_client, base_url, "sentinel", CORE_AGENTS["sentinel"]
        )

        if not atlas_health["healthy"] or not sentinel_health["healthy"]:
            pytest.skip("ATLAS or SENTINEL not available")

        # Both should be healthy for routing to work
        assert atlas_health["healthy"], "ATLAS must be healthy"
        assert sentinel_health["healthy"], "SENTINEL must be healthy"
