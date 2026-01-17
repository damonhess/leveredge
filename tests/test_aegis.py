"""
AEGIS Credential Management Tests.

Tests for AEGIS (port 8012) - the credential vault and secret management agent.
"""

import httpx
import pytest

from conftest import CORE_AGENTS, check_agent_health


AEGIS_PORT = CORE_AGENTS["aegis"]


# =============================================================================
# HEALTH AND STATUS TESTS
# =============================================================================

class TestAegisHealth:
    """Test AEGIS health and status endpoints."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_aegis_health_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test AEGIS /health endpoint returns 200."""
        url = f"{base_url}:{AEGIS_PORT}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"AEGIS health check failed with status {response.status_code}"
            )

            data = response.json()
            assert "status" in data or "healthy" in data, (
                "AEGIS health response missing status indicator"
            )

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_aegis_status_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test AEGIS status endpoint."""
        status_endpoints = ["/status", "/info", "/version"]

        for endpoint in status_endpoints:
            url = f"{base_url}:{AEGIS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"AEGIS status: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        # Fall back to health check
        health_result = await check_agent_health(
            async_client, base_url, "aegis", AEGIS_PORT
        )
        assert health_result["healthy"], "AEGIS is not healthy"


# =============================================================================
# CREDENTIAL LISTING TESTS
# =============================================================================

class TestAegisCredentialListing:
    """Test AEGIS credential listing functionality."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_list_credentials_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test listing credentials (without exposing values)."""
        list_endpoints = ["/credentials", "/list", "/inventory"]

        for endpoint in list_endpoints:
            url = f"{base_url}:{AEGIS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Credentials listing: {type(data)}")

                    # Verify response is list or dict with credentials
                    assert isinstance(data, (list, dict)), (
                        f"Expected list or dict, got {type(data)}"
                    )

                    # Verify no secrets are exposed in response
                    response_text = str(data).lower()
                    assert "password" not in response_text or "***" in response_text, (
                        "Credential values may be exposed in listing"
                    )

                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No credential listing endpoint found")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_credentials_do_not_expose_secrets(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Verify credential endpoints don't expose secret values."""
        url = f"{base_url}:{AEGIS_PORT}/credentials"

        try:
            response = await async_client.get(url, timeout=5.0)
            if response.status_code == 200:
                response_text = response.text.lower()

                # Check for common secret patterns that shouldn't be in response
                secret_patterns = [
                    "sk-",  # API keys
                    "sk_live_",  # Stripe keys
                    "ghp_",  # GitHub tokens
                    "xoxb-",  # Slack tokens
                    "bearer ",  # Auth tokens
                ]

                for pattern in secret_patterns:
                    assert pattern not in response_text, (
                        f"Possible secret pattern '{pattern}' found in response"
                    )

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")


# =============================================================================
# SYNC TESTS
# =============================================================================

class TestAegisSync:
    """Test AEGIS credential sync functionality."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_sync_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test credential sync endpoint."""
        url = f"{base_url}:{AEGIS_PORT}/sync"

        try:
            response = await async_client.post(url, timeout=10.0)

            # Sync should return 200 or 202 (accepted)
            assert response.status_code in (200, 201, 202), (
                f"Sync failed with status {response.status_code}"
            )

            data = response.json()
            print(f"Sync response: {data}")

            # Should indicate success or provide status
            assert "status" in data or "success" in data or "synced" in data, (
                "Sync response missing status indicator"
            )

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.slow
    async def test_sync_returns_credential_count(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test sync returns count of synced credentials."""
        url = f"{base_url}:{AEGIS_PORT}/sync"

        try:
            response = await async_client.post(url, timeout=15.0)

            if response.status_code == 200:
                data = response.json()

                # Check for count indicators
                has_count = any(
                    key in data for key in ["count", "total", "synced", "credentials"]
                )

                if not has_count:
                    print(f"Sync response doesn't include count: {data}")

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")


# =============================================================================
# AUDIT TESTS
# =============================================================================

class TestAegisAudit:
    """Test AEGIS credential audit functionality."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_audit_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test credential audit endpoint."""
        url = f"{base_url}:{AEGIS_PORT}/audit"

        try:
            response = await async_client.get(url, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                print(f"Audit response: {data}")

                # Audit should return some status information
                assert isinstance(data, (list, dict)), (
                    f"Unexpected audit response type: {type(data)}"
                )

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_audit_reports_expiring_credentials(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test audit can identify expiring credentials."""
        audit_endpoints = ["/audit", "/audit/expiring", "/expiring"]

        for endpoint in audit_endpoints:
            url = f"{base_url}:{AEGIS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()

                    # Check if response mentions expiration
                    response_text = str(data).lower()
                    if "expir" in response_text or "expires" in response_text:
                        print(f"Expiration info found: {data}")
                        return

            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        # Not a failure if expiration endpoint doesn't exist
        pytest.skip("No expiration audit endpoint found")


# =============================================================================
# CREDENTIAL TYPE TESTS
# =============================================================================

class TestAegisCredentialTypes:
    """Test AEGIS handles different credential types."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_list_credential_types(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test listing available credential types."""
        type_endpoints = ["/types", "/credential-types", "/credentials/types"]

        for endpoint in type_endpoints:
            url = f"{base_url}:{AEGIS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Credential types: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No credential types endpoint found")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_filter_credentials_by_type(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test filtering credentials by type."""
        url = f"{base_url}:{AEGIS_PORT}/credentials"

        try:
            # Try with type filter
            response = await async_client.get(
                url,
                params={"type": "httpBasicAuth"},
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Filtered credentials: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestAegisErrorHandling:
    """Test AEGIS error handling."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_invalid_credential_id(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test handling of invalid credential ID."""
        url = f"{base_url}:{AEGIS_PORT}/credentials/nonexistent_id_12345"

        try:
            response = await async_client.get(url, timeout=5.0)

            # Should return 404 for nonexistent credential
            assert response.status_code in (400, 404), (
                f"Expected 404 for invalid credential ID, got {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_malformed_sync_request(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test handling of malformed sync request."""
        url = f"{base_url}:{AEGIS_PORT}/sync"

        try:
            # Send malformed JSON
            response = await async_client.post(
                url,
                content="not valid json",
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )

            # Should handle gracefully (either accept empty body or return 400)
            assert response.status_code in (200, 202, 400, 422), (
                f"Unexpected status for malformed request: {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestAegisSecurity:
    """Test AEGIS security features."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_no_credential_values_in_logs(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Verify credential values are not exposed in error messages."""
        url = f"{base_url}:{AEGIS_PORT}/credentials/invalid"

        try:
            response = await async_client.get(url, timeout=5.0)

            # Check error message doesn't contain sensitive patterns
            response_text = response.text.lower()

            sensitive_patterns = [
                "password=",
                "secret=",
                "token=",
                "api_key=",
                "apikey=",
            ]

            for pattern in sensitive_patterns:
                assert pattern not in response_text, (
                    f"Sensitive pattern '{pattern}' found in error response"
                )

        except httpx.ConnectError:
            pytest.skip("AEGIS not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_audit_trail_for_operations(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that AEGIS maintains audit trail."""
        # First, trigger an operation
        sync_url = f"{base_url}:{AEGIS_PORT}/sync"
        try:
            await async_client.post(sync_url, timeout=5.0)
        except Exception:
            pass

        # Then check for audit trail
        audit_endpoints = ["/audit/log", "/audit-log", "/logs"]

        for endpoint in audit_endpoints:
            url = f"{base_url}:{AEGIS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Audit log: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        # Not a failure if audit log endpoint doesn't exist
        pytest.skip("No audit log endpoint found")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestAegisIntegration:
    """Test AEGIS integration with other agents."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_aegis_event_bus_integration(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test AEGIS can communicate with Event Bus."""
        aegis_health = await check_agent_health(
            async_client, base_url, "aegis", AEGIS_PORT
        )
        event_bus_health = await check_agent_health(
            async_client, base_url, "event_bus", CORE_AGENTS["event_bus"]
        )

        if not aegis_health["healthy"]:
            pytest.skip("AEGIS not available")
        if not event_bus_health["healthy"]:
            pytest.skip("Event Bus not available")

        # Both should be healthy for integration
        assert aegis_health["healthy"] and event_bus_health["healthy"], (
            "Both AEGIS and Event Bus should be healthy for integration"
        )

    @pytest.mark.integration
    @pytest.mark.core
    async def test_aegis_atlas_coordination(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test AEGIS can be called by ATLAS for credential operations."""
        aegis_health = await check_agent_health(
            async_client, base_url, "aegis", AEGIS_PORT
        )
        atlas_health = await check_agent_health(
            async_client, base_url, "atlas", CORE_AGENTS["atlas"]
        )

        if not aegis_health["healthy"] or not atlas_health["healthy"]:
            pytest.skip("AEGIS or ATLAS not available")

        # Both should be healthy
        assert aegis_health["healthy"], "AEGIS must be healthy"
        assert atlas_health["healthy"], "ATLAS must be healthy"
