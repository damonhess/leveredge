"""
Creative Fleet Load Tests

Tests the Creative Fleet agents (MUSE, CALLIOPE, THALIA, ERATO, CLIO)
for content generation and asset management workloads.
"""

import random
import uuid
import json
from locust import HttpUser, task, between, tag

# Creative Fleet ports
CREATIVE_AGENTS = {
    "muse": 8030,       # Creative Director - orchestrates creative work
    "calliope": 8031,   # Content Writer - text generation
    "thalia": 8032,     # Visual Designer - image/design generation
    "erato": 8033,      # Video Producer - video generation
    "clio": 8034,       # Asset Manager - stores/retrieves assets
}

# Sample content requests
BLOG_TOPICS = [
    "The Future of AI Automation",
    "How to Scale Your Workflow",
    "Best Practices for n8n Workflows",
    "Enterprise Automation Trends",
    "Low-Code Revolution in 2026",
]

SOCIAL_TOPICS = [
    "New feature announcement",
    "Customer success story",
    "Industry insight",
    "Product tip of the day",
    "Team spotlight",
]

DESIGN_REQUESTS = [
    {"type": "thumbnail", "style": "modern", "text": "New Video"},
    {"type": "social_banner", "style": "professional", "platform": "linkedin"},
    {"type": "blog_header", "style": "minimalist", "theme": "technology"},
    {"type": "icon_set", "style": "flat", "count": 5},
]


class CreativeFleetUser(HttpUser):
    """
    Simulates content creation requests to the Creative Fleet.

    Behavior:
    - Requests content through MUSE (creative director)
    - Direct requests to individual agents
    - Asset storage and retrieval
    """

    wait_time = between(5, 15)  # Creative tasks are slower, users wait longer
    weight = 1  # Lower weight - creative tasks are less frequent

    @task(5)
    @tag('creative', 'muse', 'orchestration')
    def request_content_through_muse(self):
        """Request content creation through MUSE orchestration."""
        content_types = ["blog_post", "social_media", "email_campaign", "press_release"]
        content_type = random.choice(content_types)

        payload = {
            "content_type": content_type,
            "topic": random.choice(BLOG_TOPICS),
            "tone": random.choice(["professional", "casual", "technical"]),
            "target_audience": random.choice(["developers", "executives", "general"]),
            "session_id": str(uuid.uuid4()),
        }

        with self.client.post(
            f"http://localhost:{CREATIVE_AGENTS['muse']}/create",
            json=payload,
            name="/create [muse]",
            catch_response=True,
            timeout=120  # Creative tasks can take time
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.failure("MUSE overloaded")
            elif response.status_code == 504:
                response.failure("Creative timeout - task too long")
            else:
                response.failure(f"MUSE create failed: {response.status_code}")

    @task(4)
    @tag('creative', 'calliope', 'writing')
    def request_text_content(self):
        """Request text content from CALLIOPE."""
        content_types = [
            {"type": "blog_post", "word_count": 800, "topic": random.choice(BLOG_TOPICS)},
            {"type": "social_post", "platform": "twitter", "topic": random.choice(SOCIAL_TOPICS)},
            {"type": "email", "purpose": "newsletter", "topic": "Monthly Update"},
            {"type": "summary", "source_text": "Lorem ipsum " * 100, "length": "brief"},
        ]

        payload = random.choice(content_types)
        payload["session_id"] = str(uuid.uuid4())

        with self.client.post(
            f"http://localhost:{CREATIVE_AGENTS['calliope']}/write",
            json=payload,
            name="/write [calliope]",
            catch_response=True,
            timeout=90
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.failure("CALLIOPE overloaded")
            else:
                response.failure(f"CALLIOPE write failed: {response.status_code}")

    @task(3)
    @tag('creative', 'thalia', 'design')
    def request_visual_design(self):
        """Request visual design from THALIA."""
        design = random.choice(DESIGN_REQUESTS)
        payload = {
            **design,
            "session_id": str(uuid.uuid4()),
            "quality": random.choice(["draft", "standard", "high"]),
        }

        with self.client.post(
            f"http://localhost:{CREATIVE_AGENTS['thalia']}/design",
            json=payload,
            name="/design [thalia]",
            catch_response=True,
            timeout=120  # Image generation can be slow
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                response.failure("THALIA overloaded")
            elif response.status_code == 504:
                response.failure("Design timeout")
            else:
                response.failure(f"THALIA design failed: {response.status_code}")

    @task(2)
    @tag('creative', 'clio', 'assets')
    def manage_assets(self):
        """Store or retrieve assets from CLIO."""
        operations = [
            {"action": "list", "type": "image", "limit": 20},
            {"action": "list", "type": "document", "limit": 20},
            {"action": "search", "query": "automation", "type": "all"},
            {"action": "get_metadata", "asset_id": str(uuid.uuid4())[:8]},
        ]

        operation = random.choice(operations)

        with self.client.post(
            f"http://localhost:{CREATIVE_AGENTS['clio']}/assets",
            json=operation,
            name="/assets [clio]",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code in [200, 404]:  # 404 OK for non-existent assets
                response.success()
            else:
                response.failure(f"CLIO assets failed: {response.status_code}")

    @task(2)
    @tag('creative', 'health')
    def check_creative_fleet_health(self):
        """Check health of all creative agents."""
        for agent, port in CREATIVE_AGENTS.items():
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
                    response.failure(f"{agent} unhealthy")

    @task(1)
    @tag('creative', 'pipeline')
    def full_content_pipeline(self):
        """
        Test full content pipeline:
        1. Request blog post from MUSE
        2. Store result in CLIO
        """
        session_id = str(uuid.uuid4())

        # Step 1: Create content
        with self.client.post(
            f"http://localhost:{CREATIVE_AGENTS['muse']}/create",
            json={
                "content_type": "blog_post",
                "topic": random.choice(BLOG_TOPICS),
                "session_id": session_id,
            },
            name="/create [pipeline-create]",
            catch_response=True,
            timeout=120
        ) as response:
            if response.status_code != 200:
                response.failure("Pipeline create failed")
                return
            response.success()

        # Step 2: Store in asset manager
        with self.client.post(
            f"http://localhost:{CREATIVE_AGENTS['clio']}/assets",
            json={
                "action": "store",
                "type": "document",
                "content_type": "blog_post",
                "session_id": session_id,
                "metadata": {"pipeline_test": True}
            },
            name="/assets [pipeline-store]",
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure("Pipeline store failed")


class CreativeBatchUser(HttpUser):
    """
    Batch content generation user.

    Simulates batch operations like generating multiple social posts.
    """

    wait_time = between(10, 30)  # Batch jobs are infrequent

    @task
    @tag('creative', 'batch')
    def batch_social_content(self):
        """Request batch social media content."""
        platforms = ["twitter", "linkedin", "facebook"]
        batch_size = random.randint(3, 10)

        payload = {
            "batch_type": "social_media_campaign",
            "platforms": platforms,
            "count_per_platform": batch_size,
            "topic": random.choice(SOCIAL_TOPICS),
            "campaign_id": str(uuid.uuid4())[:8],
        }

        with self.client.post(
            f"http://localhost:{CREATIVE_AGENTS['muse']}/batch",
            json=payload,
            name="/batch [muse]",
            catch_response=True,
            timeout=300  # Batch jobs can take 5+ minutes
        ) as response:
            if response.status_code in [200, 202]:  # 202 for async batch
                response.success()
            elif response.status_code == 504:
                response.failure("Batch timeout - expected for large batches")
            else:
                response.failure(f"Batch failed: {response.status_code}")
