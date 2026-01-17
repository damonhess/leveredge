"""
Health Check Load Tests

Tests health endpoints across all agents in the Leveredge fleet.
Simulates monitoring systems checking agent availability.
"""

import random
from locust import HttpUser, task, between, tag

# Agent fleet with ports
AGENTS = {
    # Core Infrastructure
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
    "event-bus": 8099,

    # Security Fleet
    "cerberus": 8020,
    "port-manager": 8021,

    # Creative Fleet
    "muse": 8030,
    "calliope": 8031,
    "thalia": 8032,
    "erato": 8033,
    "clio": 8034,
}


class HealthCheckUser(HttpUser):
    """
    Simulates monitoring systems checking agent health.

    Behavior:
    - Randomly selects agents to check
    - Expects fast responses (< 500ms)
    - High frequency, low payload
    """

    wait_time = between(0.5, 2)  # Quick polling

    def on_start(self):
        """Track which agents are available."""
        self.available_agents = list(AGENTS.keys())
        self.failed_agents = set()

    @task(10)
    @tag('health', 'core')
    def check_random_core_agent(self):
        """Check health of a random core agent."""
        core_agents = [
            "atlas", "hades", "chronos", "hephaestus",
            "aegis", "athena", "hermes", "event-bus"
        ]
        agent = random.choice(core_agents)
        port = AGENTS[agent]

        with self.client.get(
            f"http://localhost:{port}/health",
            name=f"/health [{agent}]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.failure(f"{agent} service unavailable")
            else:
                response.failure(f"{agent} returned {response.status_code}")

    @task(5)
    @tag('health', 'support')
    def check_support_agents(self):
        """Check health of support agents (monitoring, audit)."""
        support_agents = ["aloy", "argus", "chiron", "scholar", "sentinel"]
        agent = random.choice(support_agents)
        port = AGENTS[agent]

        with self.client.get(
            f"http://localhost:{port}/health",
            name=f"/health [{agent}]",
            catch_response=True,
            timeout=5
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"{agent} health check failed")

    @task(3)
    @tag('health', 'creative')
    def check_creative_fleet(self):
        """Check health of creative fleet agents."""
        creative_agents = ["muse", "calliope", "thalia", "erato", "clio"]
        agent = random.choice(creative_agents)
        port = AGENTS[agent]

        with self.client.get(
            f"http://localhost:{port}/health",
            name=f"/health [{agent}]",
            catch_response=True,
            timeout=5
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                # Creative fleet may not always be running
                response.failure(f"{agent} not responding")

    @task(2)
    @tag('health', 'security')
    def check_security_agents(self):
        """Check health of security agents."""
        security_agents = ["cerberus", "port-manager"]
        agent = random.choice(security_agents)
        port = AGENTS[agent]

        with self.client.get(
            f"http://localhost:{port}/health",
            name=f"/health [{agent}]",
            catch_response=True,
            timeout=5
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"{agent} security check failed")

    @task(1)
    @tag('health', 'batch')
    def check_all_agents_batch(self):
        """Batch check all agents (less frequent)."""
        results = {"healthy": 0, "unhealthy": 0, "errors": []}

        for agent, port in AGENTS.items():
            try:
                with self.client.get(
                    f"http://localhost:{port}/health",
                    name="/health [batch-all]",
                    catch_response=True,
                    timeout=3
                ) as response:
                    if response.status_code == 200:
                        results["healthy"] += 1
                        response.success()
                    else:
                        results["unhealthy"] += 1
                        results["errors"].append(agent)
                        response.failure(f"batch check: {agent} failed")
            except Exception as e:
                results["unhealthy"] += 1
                results["errors"].append(f"{agent}: {str(e)}")


class HealthCheckStressUser(HttpUser):
    """
    High-frequency health check stress test.

    Use for testing how agents handle rapid polling.
    """

    wait_time = between(0.1, 0.3)  # Very fast polling

    @task
    @tag('stress', 'health')
    def rapid_health_check(self):
        """Rapid-fire health checks to event-bus (most critical)."""
        with self.client.get(
            "http://localhost:8099/health",
            name="/health [event-bus-stress]",
            catch_response=True,
            timeout=2
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("event-bus overloaded")
