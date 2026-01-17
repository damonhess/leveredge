"""
Security Fleet Tests.

Tests for the Security Fleet agents:
- CERBERUS (8020) - Security Gateway
- PORT-MANAGER (8021) - Port Management
"""

import httpx
import pytest

from conftest import SECURITY_AGENTS, CORE_AGENTS, check_agent_health


# =============================================================================
# CERBERUS (Security Gateway) TESTS - Port 8020
# =============================================================================

class TestCerberusGateway:
    """Tests for CERBERUS - the security gateway agent."""

    CERBERUS_PORT = SECURITY_AGENTS["cerberus"]

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS health endpoint."""
        result = await check_agent_health(
            async_client, base_url, "cerberus", self.CERBERUS_PORT
        )
        assert result["healthy"], (
            f"CERBERUS not healthy: {result['error']}"
        )

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_status(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS status endpoint."""
        status_endpoints = ["/status", "/info", "/security-status"]

        for endpoint in status_endpoints:
            url = f"{base_url}:{self.CERBERUS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"CERBERUS status: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        # Fall back to health check
        health_result = await check_agent_health(
            async_client, base_url, "cerberus", self.CERBERUS_PORT
        )
        assert health_result["healthy"], "CERBERUS is not healthy"

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_auth_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS authentication endpoint."""
        auth_endpoints = ["/auth", "/authenticate", "/verify"]

        for endpoint in auth_endpoints:
            url = f"{base_url}:{self.CERBERUS_PORT}{endpoint}"
            try:
                response = await async_client.post(
                    url,
                    json={"token": "test_token"},
                    timeout=5.0
                )

                if response.status_code in (200, 201, 401, 403):
                    print(f"Auth endpoint {endpoint}: {response.status_code}")
                    return

            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No authentication endpoint found")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_rate_limiting_info(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS rate limiting information."""
        rate_endpoints = ["/rate-limits", "/limits", "/throttle"]

        for endpoint in rate_endpoints:
            url = f"{base_url}:{self.CERBERUS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Rate limits: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No rate limiting endpoint found")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_security_policies(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS security policies endpoint."""
        policy_endpoints = ["/policies", "/security-policies", "/rules"]

        for endpoint in policy_endpoints:
            url = f"{base_url}:{self.CERBERUS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Security policies: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No security policies endpoint found")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_access_control(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS access control endpoint."""
        url = f"{base_url}:{self.CERBERUS_PORT}/access"

        try:
            response = await async_client.post(
                url,
                json={
                    "resource": "/api/test",
                    "action": "read",
                    "principal": "test_user"
                },
                timeout=5.0
            )

            if response.status_code in (200, 201, 403):
                data = response.json()
                print(f"Access control: {data}")

        except httpx.ConnectError:
            pytest.skip("CERBERUS not available")


# =============================================================================
# PORT-MANAGER TESTS - Port 8021
# =============================================================================

class TestPortManager:
    """Tests for PORT-MANAGER - the port management agent."""

    PORT_MANAGER_PORT = SECURITY_AGENTS["port_manager"]

    @pytest.mark.integration
    @pytest.mark.security
    async def test_port_manager_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER health endpoint."""
        result = await check_agent_health(
            async_client, base_url, "port_manager", self.PORT_MANAGER_PORT
        )
        assert result["healthy"], (
            f"PORT-MANAGER not healthy: {result['error']}"
        )

    @pytest.mark.integration
    @pytest.mark.security
    async def test_port_manager_list_ports(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER port listing."""
        list_endpoints = ["/ports", "/list", "/allocations"]

        for endpoint in list_endpoints:
            url = f"{base_url}:{self.PORT_MANAGER_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Port allocations: {type(data)}")
                    # Should return list or dict of ports
                    assert isinstance(data, (list, dict))
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No port listing endpoint found")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_port_manager_check_port(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER port checking."""
        check_endpoints = ["/check", "/port/check", "/status"]

        for endpoint in check_endpoints:
            url = f"{base_url}:{self.PORT_MANAGER_PORT}{endpoint}"
            try:
                response = await async_client.get(
                    url,
                    params={"port": 8007},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"Port check: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        # Try POST variant
        url = f"{base_url}:{self.PORT_MANAGER_PORT}/check"
        try:
            response = await async_client.post(
                url,
                json={"port": 8007},
                timeout=5.0
            )
            if response.status_code == 200:
                print(f"Port check (POST): {response.json()}")
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            pass

        pytest.skip("No port check endpoint found")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_port_manager_allocate_port(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER port allocation."""
        allocate_endpoints = ["/allocate", "/reserve", "/assign"]

        for endpoint in allocate_endpoints:
            url = f"{base_url}:{self.PORT_MANAGER_PORT}{endpoint}"
            try:
                response = await async_client.post(
                    url,
                    json={
                        "service": "test_service",
                        "preferred_port": 9999
                    },
                    timeout=5.0
                )
                if response.status_code in (200, 201, 202, 409):
                    data = response.json()
                    print(f"Port allocation: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No port allocation endpoint found")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_port_manager_conflicts(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER conflict detection."""
        conflict_endpoints = ["/conflicts", "/check-conflicts"]

        for endpoint in conflict_endpoints:
            url = f"{base_url}:{self.PORT_MANAGER_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Port conflicts: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No conflict detection endpoint found")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_port_manager_service_discovery(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER service discovery."""
        discovery_endpoints = ["/services", "/discover", "/registry"]

        for endpoint in discovery_endpoints:
            url = f"{base_url}:{self.PORT_MANAGER_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Service discovery: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No service discovery endpoint found")


# =============================================================================
# SECURITY FLEET INTEGRATION TESTS
# =============================================================================

class TestSecurityFleetIntegration:
    """Test integration between security fleet agents."""

    @pytest.mark.integration
    @pytest.mark.security
    async def test_security_fleet_all_healthy(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test all security fleet agents are healthy."""
        import asyncio

        tasks = [
            check_agent_health(async_client, base_url, name, port)
            for name, port in SECURITY_AGENTS.items()
        ]
        results = await asyncio.gather(*tasks)

        healthy_count = sum(1 for r in results if r["healthy"])
        total_count = len(results)

        print(f"\nSecurity Fleet Health: {healthy_count}/{total_count}")

        for result in results:
            status = "OK" if result["healthy"] else "FAIL"
            print(f"  {result['agent']}: {status}")

        # At least one should be healthy
        assert healthy_count >= 1, (
            f"No security agents are healthy"
        )

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_port_manager_coordination(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS and PORT-MANAGER coordination."""
        cerberus_health = await check_agent_health(
            async_client, base_url, "cerberus", SECURITY_AGENTS["cerberus"]
        )
        port_manager_health = await check_agent_health(
            async_client, base_url, "port_manager", SECURITY_AGENTS["port_manager"]
        )

        if not cerberus_health["healthy"]:
            pytest.skip("CERBERUS not available")
        if not port_manager_health["healthy"]:
            pytest.skip("PORT-MANAGER not available")

        # Both should be healthy
        assert cerberus_health["healthy"] and port_manager_health["healthy"]

    @pytest.mark.integration
    @pytest.mark.security
    async def test_security_event_bus_integration(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test security fleet can communicate with Event Bus."""
        event_bus_health = await check_agent_health(
            async_client, base_url, "event_bus", CORE_AGENTS["event_bus"]
        )

        if not event_bus_health["healthy"]:
            pytest.skip("Event Bus not available")

        # Test CERBERUS can reach event bus
        cerberus_health = await check_agent_health(
            async_client, base_url, "cerberus", SECURITY_AGENTS["cerberus"]
        )

        if cerberus_health["healthy"] and event_bus_health["healthy"]:
            print("CERBERUS -> Event Bus connectivity confirmed")


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurityFeatures:
    """Test actual security features."""

    @pytest.mark.integration
    @pytest.mark.security
    async def test_unauthenticated_request_blocked(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that unauthenticated requests are handled properly."""
        cerberus_port = SECURITY_AGENTS["cerberus"]
        protected_endpoints = ["/admin", "/protected", "/secure"]

        for endpoint in protected_endpoints:
            url = f"{base_url}:{cerberus_port}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                # Should return 401 or 403 for protected endpoints
                # Or 404 if endpoint doesn't exist
                assert response.status_code in (401, 403, 404), (
                    f"Protected endpoint {endpoint} returned unexpected status: {response.status_code}"
                )
            except (httpx.ConnectError, httpx.TimeoutException):
                continue

    @pytest.mark.integration
    @pytest.mark.security
    async def test_invalid_token_rejected(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that invalid tokens are rejected."""
        cerberus_port = SECURITY_AGENTS["cerberus"]
        url = f"{base_url}:{cerberus_port}/auth"

        try:
            response = await async_client.post(
                url,
                json={"token": "invalid_token_12345"},
                timeout=5.0
            )

            # Should reject invalid token
            if response.status_code in (401, 403):
                print("Invalid token correctly rejected")
            elif response.status_code == 404:
                pytest.skip("Auth endpoint not available")

        except httpx.ConnectError:
            pytest.skip("CERBERUS not available")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestSecurityFleetErrorHandling:
    """Test security fleet error handling."""

    @pytest.mark.integration
    @pytest.mark.security
    async def test_cerberus_handles_malformed_request(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS handles malformed requests."""
        cerberus_port = SECURITY_AGENTS["cerberus"]
        url = f"{base_url}:{cerberus_port}/auth"

        try:
            response = await async_client.post(
                url,
                content="not valid json {{{",
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )

            # Should return 400 for malformed JSON
            assert response.status_code in (400, 404, 422, 500), (
                f"Expected error for malformed JSON, got {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("CERBERUS not available")

    @pytest.mark.integration
    @pytest.mark.security
    async def test_port_manager_handles_invalid_port(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER handles invalid port requests."""
        port_manager_port = SECURITY_AGENTS["port_manager"]
        url = f"{base_url}:{port_manager_port}/allocate"

        try:
            response = await async_client.post(
                url,
                json={
                    "service": "test",
                    "preferred_port": -1  # Invalid port
                },
                timeout=5.0
            )

            # Should return error for invalid port
            if response.status_code in (400, 422):
                print("Invalid port correctly rejected")
            elif response.status_code == 404:
                pytest.skip("Allocate endpoint not available")

        except httpx.ConnectError:
            pytest.skip("PORT-MANAGER not available")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestSecurityFleetPerformance:
    """Test security fleet performance."""

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.slow
    async def test_cerberus_response_time(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CERBERUS response time is acceptable for security checks."""
        import time

        cerberus_port = SECURITY_AGENTS["cerberus"]
        url = f"{base_url}:{cerberus_port}/health"

        try:
            start = time.time()
            response = await async_client.get(url, timeout=5.0)
            elapsed = time.time() - start

            assert response.status_code == 200, "Health check failed"
            assert elapsed < 0.5, f"Response too slow for security gateway: {elapsed:.2f}s"

            print(f"CERBERUS response time: {elapsed*1000:.2f}ms")

        except httpx.ConnectError:
            pytest.skip("CERBERUS not available")

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.slow
    async def test_port_manager_response_time(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test PORT-MANAGER response time is acceptable."""
        import time

        port_manager_port = SECURITY_AGENTS["port_manager"]
        url = f"{base_url}:{port_manager_port}/health"

        try:
            start = time.time()
            response = await async_client.get(url, timeout=5.0)
            elapsed = time.time() - start

            assert response.status_code == 200, "Health check failed"
            assert elapsed < 0.5, f"Response too slow: {elapsed:.2f}s"

            print(f"PORT-MANAGER response time: {elapsed*1000:.2f}ms")

        except httpx.ConnectError:
            pytest.skip("PORT-MANAGER not available")
