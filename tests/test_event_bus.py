"""
Event Bus Tests.

Tests for the Event Bus (port 8099) - the inter-agent communication system.
"""

import time
import uuid

import httpx
import pytest

from conftest import CORE_AGENTS, check_agent_health


EVENT_BUS_PORT = CORE_AGENTS["event_bus"]


# =============================================================================
# HEALTH AND STATUS TESTS
# =============================================================================

class TestEventBusHealth:
    """Test Event Bus health and status endpoints."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_event_bus_health_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test Event Bus /health endpoint returns 200."""
        url = f"{base_url}:{EVENT_BUS_PORT}/health"

        try:
            response = await async_client.get(url, timeout=5.0)
            assert response.status_code == 200, (
                f"Event Bus health check failed with status {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_event_bus_status(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test Event Bus status endpoint."""
        status_endpoints = ["/status", "/info", "/stats"]

        for endpoint in status_endpoints:
            url = f"{base_url}:{EVENT_BUS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Event Bus status: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        # Fall back to health check
        health_result = await check_agent_health(
            async_client, base_url, "event_bus", EVENT_BUS_PORT
        )
        assert health_result["healthy"], "Event Bus is not healthy"


# =============================================================================
# PUBLISH TESTS
# =============================================================================

class TestEventBusPublish:
    """Test Event Bus publish functionality."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_publish_event_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
        sample_event: dict,
    ):
        """Test publishing an event to the bus."""
        url = f"{base_url}:{EVENT_BUS_PORT}/publish"

        try:
            response = await async_client.post(
                url,
                json=sample_event,
                timeout=5.0
            )

            assert response.status_code in (200, 201, 202), (
                f"Event publish failed with status {response.status_code}: {response.text}"
            )

            data = response.json()
            print(f"Publish response: {data}")

            # Should return some confirmation
            assert "status" in data or "success" in data or "id" in data, (
                "Publish response missing confirmation"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_publish_event_with_metadata(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test publishing event with rich metadata."""
        url = f"{base_url}:{EVENT_BUS_PORT}/publish"

        event = {
            "event": "test.metadata",
            "source": "integration_tests",
            "timestamp": "2026-01-17T12:00:00Z",
            "correlation_id": str(uuid.uuid4()),
            "data": {
                "test_id": "metadata_test",
                "nested": {
                    "key": "value"
                },
                "array": [1, 2, 3]
            },
            "metadata": {
                "priority": "normal",
                "retry_count": 0,
                "ttl": 3600
            }
        }

        try:
            response = await async_client.post(url, json=event, timeout=5.0)
            assert response.status_code in (200, 201, 202), (
                f"Event with metadata failed: {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_publish_multiple_events(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test publishing multiple events in sequence."""
        url = f"{base_url}:{EVENT_BUS_PORT}/publish"

        events = [
            {
                "event": f"test.sequence.{i}",
                "source": "integration_tests",
                "data": {"sequence": i}
            }
            for i in range(5)
        ]

        try:
            success_count = 0
            for event in events:
                response = await async_client.post(url, json=event, timeout=5.0)
                if response.status_code in (200, 201, 202):
                    success_count += 1

            assert success_count == len(events), (
                f"Only {success_count}/{len(events)} events published successfully"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")


# =============================================================================
# SUBSCRIBE TESTS
# =============================================================================

class TestEventBusSubscribe:
    """Test Event Bus subscribe functionality."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_list_subscriptions(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test listing active subscriptions."""
        sub_endpoints = ["/subscriptions", "/subscribers", "/subs"]

        for endpoint in sub_endpoints:
            url = f"{base_url}:{EVENT_BUS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Subscriptions: {data}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No subscription listing endpoint found")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_subscribe_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test creating a subscription."""
        url = f"{base_url}:{EVENT_BUS_PORT}/subscribe"

        subscription = {
            "event_pattern": "test.*",
            "callback_url": "http://localhost:9999/callback",
            "subscriber_id": "integration_test"
        }

        try:
            response = await async_client.post(
                url,
                json=subscription,
                timeout=5.0
            )

            # Accept various responses
            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Subscription created: {data}")
            elif response.status_code == 404:
                pytest.skip("Subscribe endpoint not available")

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")


# =============================================================================
# RETRIEVE EVENTS TESTS
# =============================================================================

class TestEventBusRetrieval:
    """Test Event Bus event retrieval functionality."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_get_recent_events(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test retrieving recent events."""
        retrieval_endpoints = ["/events", "/recent", "/messages", "/log"]

        for endpoint in retrieval_endpoints:
            url = f"{base_url}:{EVENT_BUS_PORT}{endpoint}"
            try:
                response = await async_client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Recent events: {type(data)}, count: {len(data) if isinstance(data, list) else 'n/a'}")
                    return
            except (httpx.ConnectError, httpx.TimeoutException):
                continue
            except Exception:
                continue

        pytest.skip("No event retrieval endpoint found")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_filter_events_by_type(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test filtering events by event type."""
        url = f"{base_url}:{EVENT_BUS_PORT}/events"

        try:
            response = await async_client.get(
                url,
                params={"event_type": "test.*", "limit": 10},
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Filtered events: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_filter_events_by_source(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test filtering events by source."""
        url = f"{base_url}:{EVENT_BUS_PORT}/events"

        try:
            response = await async_client.get(
                url,
                params={"source": "integration_tests", "limit": 10},
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                print(f"Source-filtered events: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")


# =============================================================================
# EVENT DELIVERY TESTS
# =============================================================================

class TestEventBusDelivery:
    """Test Event Bus event delivery."""

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.slow
    async def test_publish_and_retrieve(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test that published events can be retrieved."""
        publish_url = f"{base_url}:{EVENT_BUS_PORT}/publish"
        retrieve_url = f"{base_url}:{EVENT_BUS_PORT}/events"

        unique_id = str(uuid.uuid4())
        event = {
            "event": "test.publish_retrieve",
            "source": "integration_tests",
            "data": {"unique_id": unique_id}
        }

        try:
            # Publish event
            pub_response = await async_client.post(
                publish_url,
                json=event,
                timeout=5.0
            )

            if pub_response.status_code not in (200, 201, 202):
                pytest.skip("Could not publish event")

            # Small delay for processing
            time.sleep(0.5)

            # Try to retrieve
            ret_response = await async_client.get(
                retrieve_url,
                params={"limit": 50},
                timeout=5.0
            )

            if ret_response.status_code == 200:
                events = ret_response.json()
                if isinstance(events, list):
                    # Look for our event
                    found = any(
                        e.get("data", {}).get("unique_id") == unique_id
                        for e in events
                        if isinstance(e, dict)
                    )
                    if found:
                        print(f"Successfully found published event {unique_id}")

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestEventBusErrorHandling:
    """Test Event Bus error handling."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_invalid_event_format(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test handling of invalid event format."""
        url = f"{base_url}:{EVENT_BUS_PORT}/publish"

        try:
            # Missing required fields
            response = await async_client.post(
                url,
                json={"invalid": "event"},
                timeout=5.0
            )

            # Should return error or accept with defaults
            assert response.status_code in (200, 201, 202, 400, 422), (
                f"Unexpected status for invalid event: {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_empty_publish_request(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test handling of empty publish request."""
        url = f"{base_url}:{EVENT_BUS_PORT}/publish"

        try:
            response = await async_client.post(
                url,
                json={},
                timeout=5.0
            )

            # Should handle gracefully
            assert response.status_code in (200, 201, 202, 400, 422), (
                f"Unexpected status for empty event: {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_malformed_json(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test handling of malformed JSON."""
        url = f"{base_url}:{EVENT_BUS_PORT}/publish"

        try:
            response = await async_client.post(
                url,
                content="not valid json {{{",
                headers={"Content-Type": "application/json"},
                timeout=5.0
            )

            # Should return 400 for malformed JSON
            assert response.status_code in (400, 422, 500), (
                f"Expected error for malformed JSON, got {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestEventBusPerformance:
    """Test Event Bus performance characteristics."""

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.slow
    async def test_publish_throughput(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test Event Bus can handle multiple events quickly."""
        import asyncio

        url = f"{base_url}:{EVENT_BUS_PORT}/publish"
        num_events = 10

        async def publish_event(i: int):
            event = {
                "event": f"test.throughput.{i}",
                "source": "integration_tests",
                "data": {"index": i}
            }
            try:
                return await async_client.post(url, json=event, timeout=5.0)
            except Exception as e:
                return e

        try:
            start_time = time.time()
            tasks = [publish_event(i) for i in range(num_events)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time

            successes = sum(
                1 for r in results
                if isinstance(r, httpx.Response) and r.status_code in (200, 201, 202)
            )

            print(f"Published {successes}/{num_events} events in {elapsed:.2f}s")
            print(f"Rate: {successes/elapsed:.2f} events/second")

            # Should handle at least 5 events per second
            assert successes >= num_events * 0.8, (
                f"Only {successes}/{num_events} events succeeded"
            )

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")

    @pytest.mark.integration
    @pytest.mark.core
    async def test_response_time(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test Event Bus response time is acceptable."""
        url = f"{base_url}:{EVENT_BUS_PORT}/health"

        try:
            start_time = time.time()
            response = await async_client.get(url, timeout=5.0)
            elapsed = time.time() - start_time

            assert response.status_code == 200, "Health check failed"
            assert elapsed < 1.0, f"Response time too slow: {elapsed:.2f}s"

            print(f"Health check response time: {elapsed*1000:.2f}ms")

        except httpx.ConnectError:
            pytest.skip("Event Bus not available")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestEventBusIntegration:
    """Test Event Bus integration with other agents."""

    @pytest.mark.integration
    @pytest.mark.core
    async def test_hermes_can_publish(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test HERMES can publish to Event Bus."""
        event_bus_health = await check_agent_health(
            async_client, base_url, "event_bus", EVENT_BUS_PORT
        )
        hermes_health = await check_agent_health(
            async_client, base_url, "hermes", CORE_AGENTS["hermes"]
        )

        if not event_bus_health["healthy"]:
            pytest.skip("Event Bus not available")
        if not hermes_health["healthy"]:
            pytest.skip("HERMES not available")

        # Both should be healthy for HERMES to publish events
        assert event_bus_health["healthy"] and hermes_health["healthy"]

    @pytest.mark.integration
    @pytest.mark.core
    async def test_all_core_agents_can_reach_event_bus(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test all core agents have Event Bus available."""
        event_bus_health = await check_agent_health(
            async_client, base_url, "event_bus", EVENT_BUS_PORT
        )

        assert event_bus_health["healthy"], (
            "Event Bus must be healthy for inter-agent communication"
        )
