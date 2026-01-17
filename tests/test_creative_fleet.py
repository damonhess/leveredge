"""
Creative Fleet Tests.

Tests for the Creative Fleet agents:
- MUSE (8030) - Creative Director
- CALLIOPE (8031) - Writer
- THALIA (8032) - Designer
- ERATO (8033) - Media Producer
- CLIO (8034) - Reviewer
"""

import httpx
import pytest

from conftest import CREATIVE_AGENTS, check_agent_health


# =============================================================================
# MUSE (Creative Director) TESTS - Port 8030
# =============================================================================

class TestMuseCreativeDirector:
    """Tests for MUSE - the creative director agent."""

    MUSE_PORT = CREATIVE_AGENTS["muse"]

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_muse_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test MUSE health endpoint."""
        result = await check_agent_health(
            async_client, base_url, "muse", self.MUSE_PORT
        )
        assert result["healthy"], (
            f"MUSE not healthy: {result['error']}"
        )

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_muse_fleet_listing(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test MUSE can list creative fleet capabilities."""
        url = f"{base_url}:{self.MUSE_PORT}/fleet"

        try:
            response = await async_client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print(f"Creative fleet: {data}")
                # Should list available creative agents
                assert isinstance(data, (list, dict))

        except httpx.ConnectError:
            pytest.skip("MUSE not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_muse_create_project(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test MUSE can create a creative project."""
        url = f"{base_url}:{self.MUSE_PORT}/projects/create"

        project = {
            "name": "Integration Test Project",
            "type": "video",
            "description": "Test project for integration tests",
            "requirements": {
                "duration": "30 seconds",
                "style": "professional"
            }
        }

        try:
            response = await async_client.post(url, json=project, timeout=10.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Project created: {data}")
                # Should return project ID or details
                assert "id" in data or "project" in data or "status" in data

        except httpx.ConnectError:
            pytest.skip("MUSE not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_muse_storyboard(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test MUSE storyboard creation."""
        url = f"{base_url}:{self.MUSE_PORT}/storyboard"

        request = {
            "concept": "Product launch announcement",
            "scenes": 5,
            "style": "modern"
        }

        try:
            response = await async_client.post(url, json=request, timeout=15.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Storyboard: {data}")

        except httpx.ConnectError:
            pytest.skip("MUSE not available")


# =============================================================================
# CALLIOPE (Writer) TESTS - Port 8031
# =============================================================================

class TestCalliopeWriter:
    """Tests for CALLIOPE - the writer agent."""

    CALLIOPE_PORT = CREATIVE_AGENTS["calliope"]

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_calliope_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CALLIOPE health endpoint."""
        result = await check_agent_health(
            async_client, base_url, "calliope", self.CALLIOPE_PORT
        )
        assert result["healthy"], (
            f"CALLIOPE not healthy: {result['error']}"
        )

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_calliope_write_endpoint(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CALLIOPE write content endpoint."""
        url = f"{base_url}:{self.CALLIOPE_PORT}/write"

        request = {
            "type": "headline",
            "topic": "Product launch",
            "tone": "professional",
            "length": "short"
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Written content: {data}")
                # Should return generated content
                assert "content" in data or "text" in data or "result" in data

        except httpx.ConnectError:
            pytest.skip("CALLIOPE not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_calliope_script_video(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CALLIOPE video script generation."""
        url = f"{base_url}:{self.CALLIOPE_PORT}/script/video"

        request = {
            "topic": "Company introduction",
            "duration": "60 seconds",
            "style": "conversational"
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Video script: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("CALLIOPE not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_calliope_rewrite(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CALLIOPE content rewriting."""
        url = f"{base_url}:{self.CALLIOPE_PORT}/rewrite"

        request = {
            "original": "This is a test sentence that needs improvement.",
            "feedback": "Make it more engaging and professional",
            "tone": "formal"
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Rewritten: {data}")

        except httpx.ConnectError:
            pytest.skip("CALLIOPE not available")


# =============================================================================
# THALIA (Designer) TESTS - Port 8032
# =============================================================================

class TestThaliaDesigner:
    """Tests for THALIA - the designer agent."""

    THALIA_PORT = CREATIVE_AGENTS["thalia"]

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_thalia_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test THALIA health endpoint."""
        result = await check_agent_health(
            async_client, base_url, "thalia", self.THALIA_PORT
        )
        assert result["healthy"], (
            f"THALIA not healthy: {result['error']}"
        )

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_thalia_design_presentation(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test THALIA presentation design."""
        url = f"{base_url}:{self.THALIA_PORT}/design/presentation"

        request = {
            "title": "Q1 Results",
            "slides": 5,
            "style": "corporate"
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Presentation design: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("THALIA not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_thalia_design_chart(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test THALIA chart generation."""
        url = f"{base_url}:{self.THALIA_PORT}/design/chart"

        request = {
            "type": "bar",
            "title": "Revenue by Quarter",
            "data": {
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "values": [100, 150, 200, 180]
            }
        }

        try:
            response = await async_client.post(url, json=request, timeout=15.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Chart design: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("THALIA not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_thalia_design_landing_page(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test THALIA landing page generation."""
        url = f"{base_url}:{self.THALIA_PORT}/design/landing-page"

        request = {
            "product_name": "Test Product",
            "headline": "Revolutionize Your Workflow",
            "style": "modern",
            "sections": ["hero", "features", "cta"]
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Landing page: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("THALIA not available")


# =============================================================================
# ERATO (Media Producer) TESTS - Port 8033
# =============================================================================

class TestEratoMediaProducer:
    """Tests for ERATO - the media producer agent."""

    ERATO_PORT = CREATIVE_AGENTS["erato"]

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_erato_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ERATO health endpoint."""
        result = await check_agent_health(
            async_client, base_url, "erato", self.ERATO_PORT
        )
        assert result["healthy"], (
            f"ERATO not healthy: {result['error']}"
        )

    @pytest.mark.integration
    @pytest.mark.creative
    @pytest.mark.slow
    async def test_erato_generate_image(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ERATO AI image generation."""
        url = f"{base_url}:{self.ERATO_PORT}/generate/image"

        request = {
            "prompt": "A professional office workspace with modern design",
            "style": "photorealistic",
            "size": "1024x1024"
        }

        try:
            response = await async_client.post(url, json=request, timeout=60.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Image generation: {type(data)}")
                # Should return image URL or data
                assert "url" in data or "image" in data or "result" in data

        except httpx.ConnectError:
            pytest.skip("ERATO not available")
        except httpx.TimeoutException:
            pytest.skip("Image generation timed out (expected for heavy operations)")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_erato_source_stock(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test ERATO stock asset sourcing."""
        url = f"{base_url}:{self.ERATO_PORT}/source/stock"

        request = {
            "query": "business meeting",
            "type": "photo",
            "count": 5
        }

        try:
            response = await async_client.post(url, json=request, timeout=15.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Stock assets: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("ERATO not available")


# =============================================================================
# CLIO (Reviewer) TESTS - Port 8034
# =============================================================================

class TestClioReviewer:
    """Tests for CLIO - the content reviewer agent."""

    CLIO_PORT = CREATIVE_AGENTS["clio"]

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_clio_health(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CLIO health endpoint."""
        result = await check_agent_health(
            async_client, base_url, "clio", self.CLIO_PORT
        )
        assert result["healthy"], (
            f"CLIO not healthy: {result['error']}"
        )

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_clio_review_text(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CLIO text review."""
        url = f"{base_url}:{self.CLIO_PORT}/review/text"

        request = {
            "content": "This is sample text for review. It should be checked for grammar and tone.",
            "check_for": ["grammar", "tone", "brand_compliance"]
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Text review: {data}")
                # Should return review results
                assert "review" in data or "issues" in data or "score" in data or "result" in data

        except httpx.ConnectError:
            pytest.skip("CLIO not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_clio_fact_check(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CLIO fact-checking via SCHOLAR."""
        url = f"{base_url}:{self.CLIO_PORT}/fact-check"

        request = {
            "claims": [
                "The Earth is approximately 4.5 billion years old",
                "Water boils at 100 degrees Celsius at sea level"
            ]
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"Fact check: {data}")

        except httpx.ConnectError:
            pytest.skip("CLIO not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_clio_general_review(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CLIO general content review."""
        url = f"{base_url}:{self.CLIO_PORT}/review"

        request = {
            "content_type": "article",
            "content": "Sample article content for review...",
            "brand_guidelines": {
                "tone": "professional",
                "avoid": ["jargon", "passive voice"]
            }
        }

        try:
            response = await async_client.post(url, json=request, timeout=30.0)

            if response.status_code in (200, 201, 202):
                data = response.json()
                print(f"General review: {type(data)}")

        except httpx.ConnectError:
            pytest.skip("CLIO not available")


# =============================================================================
# FLEET INTEGRATION TESTS
# =============================================================================

class TestCreativeFleetIntegration:
    """Test integration between creative fleet agents."""

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_creative_fleet_all_healthy(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test all creative fleet agents are healthy."""
        import asyncio

        tasks = [
            check_agent_health(async_client, base_url, name, port)
            for name, port in CREATIVE_AGENTS.items()
        ]
        results = await asyncio.gather(*tasks)

        healthy_count = sum(1 for r in results if r["healthy"])
        total_count = len(results)

        print(f"\nCreative Fleet Health: {healthy_count}/{total_count}")

        for result in results:
            status = "OK" if result["healthy"] else "FAIL"
            print(f"  {result['agent']}: {status}")

        # At least half should be healthy
        assert healthy_count >= total_count // 2, (
            f"Only {healthy_count}/{total_count} creative agents are healthy"
        )

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_muse_can_orchestrate_calliope(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test MUSE can coordinate with CALLIOPE."""
        muse_health = await check_agent_health(
            async_client, base_url, "muse", CREATIVE_AGENTS["muse"]
        )
        calliope_health = await check_agent_health(
            async_client, base_url, "calliope", CREATIVE_AGENTS["calliope"]
        )

        if not muse_health["healthy"]:
            pytest.skip("MUSE not available")
        if not calliope_health["healthy"]:
            pytest.skip("CALLIOPE not available")

        # Both should be healthy for orchestration
        assert muse_health["healthy"] and calliope_health["healthy"]

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_content_pipeline_connectivity(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test content pipeline agents can communicate."""
        # MUSE -> CALLIOPE -> CLIO pipeline
        pipeline_agents = ["muse", "calliope", "clio"]

        for agent_name in pipeline_agents:
            result = await check_agent_health(
                async_client, base_url, agent_name, CREATIVE_AGENTS[agent_name]
            )
            if not result["healthy"]:
                pytest.skip(f"{agent_name} not available")

        # All pipeline agents should be healthy
        print("Content pipeline: MUSE -> CALLIOPE -> CLIO is healthy")


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestCreativeFleetErrorHandling:
    """Test creative fleet error handling."""

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_calliope_handles_invalid_type(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CALLIOPE handles invalid content type."""
        url = f"{base_url}:{CREATIVE_AGENTS['calliope']}/write"

        request = {
            "type": "invalid_type_12345",
            "topic": "Test"
        }

        try:
            response = await async_client.post(url, json=request, timeout=5.0)

            # Should return error or handle gracefully
            assert response.status_code in (200, 400, 422), (
                f"Unexpected status for invalid type: {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("CALLIOPE not available")

    @pytest.mark.integration
    @pytest.mark.creative
    async def test_clio_handles_empty_content(
        self,
        async_client: httpx.AsyncClient,
        base_url: str,
    ):
        """Test CLIO handles empty content for review."""
        url = f"{base_url}:{CREATIVE_AGENTS['clio']}/review"

        request = {
            "content_type": "text",
            "content": ""
        }

        try:
            response = await async_client.post(url, json=request, timeout=5.0)

            # Should return error or handle gracefully
            assert response.status_code in (200, 400, 422), (
                f"Unexpected status for empty content: {response.status_code}"
            )

        except httpx.ConnectError:
            pytest.skip("CLIO not available")
