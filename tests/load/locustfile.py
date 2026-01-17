"""
Leveredge Load Testing - Main Locust File

This is the main entry point for Locust load testing.
It combines all scenarios and provides configurable test profiles.

Usage:
    # Web UI mode
    locust -f locustfile.py --host http://localhost

    # Headless mode with config
    locust -f locustfile.py --config configs/medium.conf

    # Run specific user class
    locust -f locustfile.py --class-picker

    # Run tagged tests only
    locust -f locustfile.py --tags health

Available User Classes:
    - HealthCheckUser: Agent health monitoring
    - AriaChatUser: Conversation load testing
    - EventBusUser: Event throughput testing
    - CreativeFleetUser: Creative content generation

Tags:
    - health: Health check endpoints
    - chat: ARIA conversation tests
    - event-bus: Event Bus throughput
    - creative: Creative Fleet tests
    - core: Core infrastructure tests
    - stress: High-load stress tests
    - burst: Burst traffic patterns
"""

import os
import logging
from datetime import datetime

from locust import HttpUser, task, between, tag, events
from locust.env import Environment

# Import all scenario users
from scenarios.health_checks import HealthCheckUser, HealthCheckStressUser
from scenarios.aria_chat import AriaChatUser, AriaBurstUser
from scenarios.event_bus import EventBusUser, EventBusThroughputUser, EventBusBurstUser
from scenarios.creative_fleet import CreativeFleetUser, CreativeBatchUser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('leveredge-load-test')


# ============================================================================
# Combined User Classes for Different Test Profiles
# ============================================================================

class MixedWorkloadUser(HttpUser):
    """
    Mixed workload simulating realistic production traffic.

    Combines health checks, chat, and event bus in realistic proportions.
    """

    wait_time = between(1, 5)
    weight = 5  # Most common user type

    def on_start(self):
        """Initialize session data."""
        self.session_start = datetime.now()
        logger.info(f"Mixed workload user started at {self.session_start}")

    @task(3)
    @tag('health', 'mixed')
    def health_check(self):
        """Periodic health check (30% of traffic)."""
        agents = [
            ("atlas", 8007),
            ("event-bus", 8099),
            ("hephaestus", 8011),
        ]
        agent, port = agents[hash(str(datetime.now())) % len(agents)]

        with self.client.get(
            f"http://localhost:{port}/health",
            name=f"/health [{agent}]",
            catch_response=True,
            timeout=5
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"{agent} unhealthy")

    @task(5)
    @tag('chat', 'mixed')
    def chat_query(self):
        """Chat query (50% of traffic)."""
        import uuid
        import random

        queries = [
            "What is the system status?",
            "Show me recent workflows",
            "Generate a summary report",
            "What happened today?",
        ]

        payload = {
            "input": {
                "query": random.choice(queries),
                "session_id": str(uuid.uuid4())
            }
        }

        with self.client.post(
            "http://localhost:8007/execute",
            json=payload,
            name="/execute [mixed-chat]",
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Chat failed: {response.status_code}")

    @task(2)
    @tag('event-bus', 'mixed')
    def event_publish(self):
        """Event publish (20% of traffic)."""
        import uuid

        payload = {
            "source_agent": "LOAD_TEST",
            "action": "test_event",
            "details": {"test_id": str(uuid.uuid4())[:8]}
        }

        with self.client.post(
            "http://localhost:8099/events",
            json=payload,
            name="/events [mixed-publish]",
            catch_response=True,
            timeout=10
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Event publish failed: {response.status_code}")


class APIOnlyUser(HttpUser):
    """
    API-only load testing (no LLM calls).

    Tests infrastructure endpoints without triggering expensive LLM operations.
    """

    wait_time = between(0.5, 2)
    weight = 3

    @task(5)
    @tag('api', 'health')
    def health_checks(self):
        """Health endpoint tests."""
        ports = [8007, 8099, 8011, 8012, 8013, 8014]
        port = ports[hash(str(datetime.now())) % len(ports)]

        with self.client.get(
            f"http://localhost:{port}/health",
            name="/health [api-only]",
            catch_response=True,
            timeout=5
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Health check failed")

    @task(3)
    @tag('api', 'query')
    def query_endpoints(self):
        """Query various list endpoints."""
        endpoints = [
            ("http://localhost:8007/chains", "GET"),
            ("http://localhost:8007/batches", "GET"),
            ("http://localhost:8099/events?limit=10", "GET"),
        ]
        url, method = endpoints[hash(str(datetime.now())) % len(endpoints)]

        with self.client.get(
            url,
            name="/query [api-only]",
            catch_response=True,
            timeout=15
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure("Query failed")

    @task(2)
    @tag('api', 'event-bus')
    def event_operations(self):
        """Event bus operations without LLM."""
        import uuid

        payload = {
            "source_agent": "API_TEST",
            "action": "api_test",
            "details": {"timestamp": datetime.now().isoformat()}
        }

        with self.client.post(
            "http://localhost:8099/events",
            json=payload,
            name="/events [api-only]",
            catch_response=True,
            timeout=10
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure("Event post failed")


# ============================================================================
# Event Hooks for Metrics and Reporting
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs):
    """Called when test starts."""
    logger.info("=" * 60)
    logger.info("LEVEREDGE LOAD TEST STARTING")
    logger.info(f"Start time: {datetime.now().isoformat()}")
    logger.info(f"Host: {environment.host}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs):
    """Called when test stops."""
    logger.info("=" * 60)
    logger.info("LEVEREDGE LOAD TEST COMPLETED")
    logger.info(f"End time: {datetime.now().isoformat()}")

    # Log summary statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Failures: {stats.total.num_failures}")
    logger.info(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")

    if stats.total.num_requests > 0:
        logger.info(f"Avg response time: {stats.total.avg_response_time:.2f}ms")
        logger.info(f"P50 response time: {stats.total.get_response_time_percentile(0.5):.2f}ms")
        logger.info(f"P95 response time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        logger.info(f"P99 response time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
        logger.info(f"RPS: {stats.total.total_rps:.2f}")

    logger.info("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Called on each request - for detailed logging."""
    # Only log failures or slow requests (> 5s)
    if exception or response_time > 5000:
        if exception:
            logger.warning(f"FAILED: {name} - {exception}")
        else:
            logger.warning(f"SLOW: {name} - {response_time:.2f}ms")


# ============================================================================
# Export all user classes for Locust discovery
# ============================================================================

# Primary test classes (shown in Locust UI)
__all__ = [
    # Combined/Mixed workloads
    'MixedWorkloadUser',
    'APIOnlyUser',

    # Health checks
    'HealthCheckUser',
    'HealthCheckStressUser',

    # ARIA Chat
    'AriaChatUser',
    'AriaBurstUser',

    # Event Bus
    'EventBusUser',
    'EventBusThroughputUser',
    'EventBusBurstUser',

    # Creative Fleet
    'CreativeFleetUser',
    'CreativeBatchUser',
]
