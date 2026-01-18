#!/usr/bin/env python3
"""
ATLAS Orchestration Engine Tests
"""

import asyncio
import httpx
import pytest

ATLAS_URL = "http://localhost:8007"


@pytest.mark.asyncio
async def test_health():
    """Test health endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ATLAS_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["agent"] == "ATLAS"
        assert data["port"] == 8007


@pytest.mark.asyncio
async def test_list_chains():
    """Test listing chains."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ATLAS_URL}/chains")
        assert response.status_code == 200
        data = response.json()
        assert "chains" in data
        assert "count" in data
        assert data["count"] > 0  # Should have chains from registry


@pytest.mark.asyncio
async def test_list_agents():
    """Test listing agents."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ATLAS_URL}/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "count" in data
        assert data["count"] > 0


@pytest.mark.asyncio
async def test_direct_call():
    """Test direct agent call."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{ATLAS_URL}/call",
            json={
                "agent": "chiron",
                "action": "hype",
                "params": {}
            }
        )
        # May fail if CHIRON is down, but should not 500
        assert response.status_code in [200, 502, 504]


@pytest.mark.asyncio
async def test_execute_chain():
    """Test chain execution."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{ATLAS_URL}/execute",
            json={
                "chain_name": "fear-to-action",
                "input": {
                    "situation": "Testing ATLAS orchestration",
                    "avoiding": "nothing"
                }
            }
        )
        # Chain may fail if agents are down, but structure should be correct
        assert response.status_code == 200
        data = response.json()
        assert "intent_id" in data
        assert "status" in data


@pytest.mark.asyncio
async def test_batch_execution():
    """Test batch execution."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Start batch
        response = await client.post(
            f"{ATLAS_URL}/execute-parallel",
            json={
                "tasks": [
                    {"chain_name": "fear-to-action", "input": {"situation": "Test 1"}},
                    {"chain_name": "fear-to-action", "input": {"situation": "Test 2"}}
                ],
                "concurrency": 2
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "batch_id" in data

        # Check status
        batch_id = data["batch_id"]
        response = await client.get(f"{ATLAS_URL}/batch/{batch_id}/status")
        assert response.status_code == 200


if __name__ == "__main__":
    asyncio.run(test_health())
    print("Health check passed")

    asyncio.run(test_list_chains())
    print("List chains passed")

    asyncio.run(test_list_agents())
    print("List agents passed")

    print("\nATLAS basic tests passed!")
