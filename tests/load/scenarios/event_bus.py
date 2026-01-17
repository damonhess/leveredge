"""
Event Bus Load Tests

Tests the Event Bus throughput and reliability under various conditions.
The Event Bus is critical infrastructure - all agent communication flows through it.
"""

import random
import uuid
import json
from datetime import datetime
from locust import HttpUser, task, between, tag

# Event types that flow through the bus
EVENT_TYPES = [
    # Workflow events
    "workflow.created",
    "workflow.updated",
    "workflow.deleted",
    "workflow.executed",
    "workflow.failed",

    # Agent communication
    "agent.request",
    "agent.response",
    "agent.error",
    "agent.health",

    # System events
    "system.alert",
    "system.metric",
    "system.backup",

    # User events
    "user.action",
    "user.approval_required",
    "user.notification",
]

# Source agents for events
SOURCE_AGENTS = [
    "ATLAS", "HEPHAESTUS", "AEGIS", "HERMES", "CHRONOS",
    "HADES", "ATHENA", "ALOY", "ARGUS", "SCHOLAR",
    "MUSE", "CALLIOPE", "THALIA", "SENTINEL"
]


def generate_event_payload(event_type: str = None) -> dict:
    """Generate a realistic event payload."""
    if not event_type:
        event_type = random.choice(EVENT_TYPES)

    source = random.choice(SOURCE_AGENTS)

    return {
        "source_agent": source,
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_id": str(uuid.uuid4()),
        "action": event_type.split(".")[1] if "." in event_type else event_type,
        "target": random.choice(SOURCE_AGENTS),
        "details": {
            "test_id": str(uuid.uuid4())[:8],
            "message": f"Load test event from {source}",
            "metrics": {
                "latency_ms": random.randint(10, 500),
                "queue_depth": random.randint(0, 100)
            }
        },
        "priority": random.choice(["low", "normal", "high"]),
    }


class EventBusUser(HttpUser):
    """
    Simulates normal agent communication through Event Bus.

    Behavior:
    - Publishes events at realistic rates
    - Queries for events
    - Acknowledges events
    - Monitors pending events
    """

    wait_time = between(0.5, 2)
    weight = 2

    def on_start(self):
        """Initialize tracking."""
        self.published_events = []
        self.pending_acknowledgments = []

    @task(10)
    @tag('event-bus', 'publish')
    def publish_event(self):
        """Publish a new event to the bus."""
        payload = generate_event_payload()

        with self.client.post(
            "http://localhost:8099/events",
            json=payload,
            name="/events [publish]",
            catch_response=True,
            timeout=10
        ) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    event_id = data.get("event_id")
                    if event_id:
                        self.published_events.append(event_id)
                        # Keep only last 50 events
                        if len(self.published_events) > 50:
                            self.published_events = self.published_events[-50:]
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Publish failed: {response.status_code}")

    @task(5)
    @tag('event-bus', 'query')
    def query_recent_events(self):
        """Query recent events from the bus."""
        params = {
            "limit": random.choice([10, 20, 50]),
            "source_agent": random.choice(SOURCE_AGENTS + [None]),
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        with self.client.get(
            "http://localhost:8099/events",
            params=params,
            name="/events [query]",
            catch_response=True,
            timeout=15
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    events = data.get("events", [])
                    # Track events that need acknowledgment
                    for event in events[:5]:  # Sample some for ack
                        if event.get("status") == "pending":
                            self.pending_acknowledgments.append(event.get("id"))
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in query")
            else:
                response.failure(f"Query failed: {response.status_code}")

    @task(3)
    @tag('event-bus', 'acknowledge')
    def acknowledge_event(self):
        """Acknowledge a pending event."""
        if not self.pending_acknowledgments:
            # No events to ack, just query instead
            return

        event_id = self.pending_acknowledgments.pop(0)

        with self.client.post(
            f"http://localhost:8099/events/{event_id}/acknowledge",
            json={"acknowledged_by": "load_test"},
            name="/events/{id}/acknowledge",
            catch_response=True,
            timeout=10
        ) as response:
            if response.status_code in [200, 404]:  # 404 is OK if event was already processed
                response.success()
            else:
                response.failure(f"Ack failed: {response.status_code}")

    @task(2)
    @tag('event-bus', 'health')
    def check_event_bus_health(self):
        """Check Event Bus health status."""
        with self.client.get(
            "http://localhost:8099/health",
            name="/health [event-bus]",
            catch_response=True,
            timeout=5
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Event bus unhealthy")

    @task(2)
    @tag('event-bus', 'agent-events')
    def query_agent_events(self):
        """Query events for a specific agent."""
        agent = random.choice(SOURCE_AGENTS).lower()

        with self.client.get(
            f"http://localhost:8099/agents/{agent}/events",
            params={"limit": 20},
            name="/agents/{agent}/events",
            catch_response=True,
            timeout=15
        ) as response:
            if response.status_code in [200, 404]:  # 404 OK if agent has no events
                response.success()
            else:
                response.failure(f"Agent events failed: {response.status_code}")

    @task(1)
    @tag('event-bus', 'pending')
    def query_pending_human(self):
        """Query events pending human approval."""
        with self.client.get(
            "http://localhost:8099/events/pending/human",
            name="/events/pending/human",
            catch_response=True,
            timeout=15
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Pending query failed: {response.status_code}")


class EventBusThroughputUser(HttpUser):
    """
    High-throughput Event Bus stress test.

    Use for testing maximum event throughput capacity.
    """

    wait_time = between(0.05, 0.2)  # Very fast

    @task
    @tag('event-bus', 'throughput')
    def rapid_publish(self):
        """Rapid-fire event publishing for throughput testing."""
        payload = generate_event_payload()

        with self.client.post(
            "http://localhost:8099/events",
            json=payload,
            name="/events [throughput]",
            catch_response=True,
            timeout=5
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited - expected under stress")
            else:
                response.failure(f"Throughput publish failed: {response.status_code}")


class EventBusBurstUser(HttpUser):
    """
    Burst pattern event publishing.

    Simulates sudden spikes of events (e.g., batch job completion).
    """

    wait_time = between(0.01, 0.05)  # Extreme burst

    def on_start(self):
        """Generate burst ID."""
        self.burst_id = str(uuid.uuid4())[:8]

    @task
    @tag('event-bus', 'burst')
    def burst_events(self):
        """Burst publish events."""
        payload = generate_event_payload("workflow.executed")
        payload["details"]["burst_id"] = self.burst_id
        payload["details"]["burst_sequence"] = random.randint(1, 1000)

        with self.client.post(
            "http://localhost:8099/events",
            json=payload,
            name="/events [burst]",
            catch_response=True,
            timeout=3
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                # Rate limiting under burst is expected
                response.failure("Burst rate limited")
            elif response.status_code == 503:
                response.failure("Event bus overloaded")
            else:
                response.failure(f"Burst failed: {response.status_code}")
