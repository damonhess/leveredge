"""
ARIA Chat Load Tests

Simulates users having conversations with ARIA (via ATLAS orchestration).
Tests the full conversation flow including:
- Intent classification
- Agent routing
- Response generation
- Conversation context management
"""

import random
import uuid
import json
from locust import HttpUser, task, between, tag

# Sample conversation starters for realistic testing
SAMPLE_QUERIES = [
    # Research queries (route to SCHOLAR)
    "What are the latest trends in AI automation?",
    "Research competitors in the workflow automation space",
    "Find market data on low-code platforms",

    # File/workflow operations (route to HEPHAESTUS)
    "Create a new workflow for email processing",
    "List all my active workflows",
    "What workflows ran yesterday?",

    # Scheduling (route to CHRONOS)
    "Schedule a backup for tonight at 2 AM",
    "What jobs are scheduled for this week?",
    "Cancel the morning report job",

    # Monitoring (route to ARGUS/ALOY)
    "Show me system health status",
    "What errors occurred in the last hour?",
    "Generate an audit report for today",

    # Storage (route to HADES)
    "When was the last backup?",
    "List available restore points",
    "How much storage is being used?",

    # Creative requests (route to MUSE)
    "Write a blog post about automation",
    "Create social media content for product launch",
    "Design a thumbnail for my video",

    # General assistant queries
    "What can you help me with?",
    "Summarize what happened today",
    "Help me optimize my workflows",
]

# Follow-up queries for multi-turn conversations
FOLLOWUP_QUERIES = [
    "Tell me more about that",
    "Can you give me specific numbers?",
    "What would you recommend?",
    "How does that compare to last week?",
    "Show me the details",
    "What's the next step?",
    "Can you export this?",
]


class AriaChatUser(HttpUser):
    """
    Simulates realistic user conversations with ARIA.

    Behavior:
    - Starts new conversations
    - Follows up with related queries
    - Maintains session context
    - Realistic think time between messages
    """

    wait_time = between(3, 10)  # Human-like typing/reading time
    weight = 3  # Higher weight for common user behavior

    def on_start(self):
        """Initialize user session."""
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        self.turn_count = 0

    @task(5)
    @tag('chat', 'new-conversation')
    def start_new_conversation(self):
        """Start a new conversation with ARIA."""
        query = random.choice(SAMPLE_QUERIES)
        self.session_id = str(uuid.uuid4())  # New session
        self.conversation_history = []
        self.turn_count = 0

        payload = {
            "input": {
                "query": query,
                "session_id": self.session_id,
                "context": {}
            }
        }

        with self.client.post(
            "http://localhost:8007/execute",
            json=payload,
            name="/execute [new-chat]",
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.conversation_history.append({
                        "query": query,
                        "response": data.get("response", ""),
                        "intent_id": data.get("intent_id", "")
                    })
                    self.turn_count = 1
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 503:
                response.failure("ATLAS overloaded")
            else:
                response.failure(f"Chat failed: {response.status_code}")

    @task(3)
    @tag('chat', 'followup')
    def continue_conversation(self):
        """Continue an existing conversation with follow-up."""
        if self.turn_count == 0:
            # No active conversation, start one
            self.start_new_conversation()
            return

        query = random.choice(FOLLOWUP_QUERIES)

        payload = {
            "input": {
                "query": query,
                "session_id": self.session_id,
                "context": {
                    "previous_turns": self.conversation_history[-3:],  # Last 3 turns
                    "turn_number": self.turn_count + 1
                }
            }
        }

        with self.client.post(
            "http://localhost:8007/execute",
            json=payload,
            name="/execute [followup]",
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.conversation_history.append({
                        "query": query,
                        "response": data.get("response", "")
                    })
                    self.turn_count += 1

                    # Reset conversation after ~5 turns (realistic)
                    if self.turn_count >= 5:
                        self.turn_count = 0
                        self.conversation_history = []

                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON in followup")
            else:
                response.failure(f"Followup failed: {response.status_code}")

    @task(2)
    @tag('chat', 'research')
    def research_query(self):
        """Send research-specific query (routes to SCHOLAR)."""
        research_queries = [
            "Research the enterprise automation market size",
            "Find recent news about workflow automation",
            "What are the top 5 workflow tools in 2026?",
            "Analyze competitor pricing strategies",
        ]

        payload = {
            "chain_name": "research",
            "input": {
                "topic": random.choice(research_queries),
                "depth": random.choice(["quick", "standard"]),
                "session_id": self.session_id
            }
        }

        with self.client.post(
            "http://localhost:8007/execute",
            json=payload,
            name="/execute [research]",
            catch_response=True,
            timeout=120  # Research takes longer
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 504:
                response.failure("Research timeout - may need longer timeout")
            else:
                response.failure(f"Research failed: {response.status_code}")

    @task(1)
    @tag('chat', 'workflow')
    def workflow_action(self):
        """Request workflow-related action (routes to HEPHAESTUS)."""
        actions = [
            {"action": "list_workflows", "filter": "active"},
            {"action": "get_workflow_status", "workflow_id": "test-workflow"},
            {"action": "list_executions", "limit": 10},
        ]

        action = random.choice(actions)

        payload = {
            "chain_name": "workflow_management",
            "input": action
        }

        with self.client.post(
            "http://localhost:8007/execute",
            json=payload,
            name="/execute [workflow]",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Workflow action failed: {response.status_code}")


class AriaBurstUser(HttpUser):
    """
    Simulates burst traffic patterns for ARIA.

    Use for testing how the system handles sudden spikes in chat traffic.
    """

    wait_time = between(0.5, 1.5)  # Faster than normal

    @task
    @tag('chat', 'burst')
    def burst_query(self):
        """Send rapid queries to test burst handling."""
        query = random.choice(SAMPLE_QUERIES)

        payload = {
            "input": {
                "query": query,
                "session_id": str(uuid.uuid4()),
                "burst_test": True
            }
        }

        with self.client.post(
            "http://localhost:8007/execute",
            json=payload,
            name="/execute [burst]",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited - expected under burst")
            elif response.status_code == 503:
                response.failure("Service overloaded")
            else:
                response.failure(f"Burst query failed: {response.status_code}")
