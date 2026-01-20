"""
Embedding Service

Generates and manages vector embeddings for semantic search.
"""

import os
from typing import Optional, List
from uuid import UUID
import httpx

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIMENSION = 1536


class EmbeddingService:
    """
    Service for generating and storing embeddings.

    Uses OpenAI's text-embedding-ada-002 model for generating
    vector embeddings of conversation chunks.
    """

    def __init__(
        self,
        openai_api_key: str = None,
        supabase_url: str = None,
        supabase_key: str = None,
        model: str = EMBEDDING_MODEL,
    ):
        self.openai_api_key = openai_api_key or OPENAI_API_KEY
        self.supabase_url = supabase_url or SUPABASE_URL
        self.supabase_key = supabase_key or SUPABASE_KEY
        self.model = model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI API.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        client = await self._get_client()

        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": text,
                "model": self.model,
            },
        )

        if response.status_code == 200:
            data = response.json()
            return data["data"][0]["embedding"]
        else:
            raise Exception(f"Failed to generate embedding: {response.text}")

    async def store_embedding(
        self,
        chunk_id: UUID,
        embedding: List[float],
    ) -> UUID:
        """
        Store embedding in database.

        Args:
            chunk_id: ID of the chunk this embedding belongs to
            embedding: The embedding vector

        Returns:
            ID of the stored embedding
        """
        client = await self._get_client()

        # Format embedding as PostgreSQL array string
        embedding_str = f"[{','.join(str(x) for x in embedding)}]"

        response = await client.post(
            f"{self.supabase_url}/rest/v1/aria_unified_embeddings",
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={
                "chunk_id": str(chunk_id),
                "embedding": embedding_str,
                "model": self.model,
            },
        )

        if response.status_code in (200, 201):
            data = response.json()
            return UUID(data[0]["id"]) if isinstance(data, list) else UUID(data["id"])
        else:
            raise Exception(f"Failed to store embedding: {response.text}")

    async def embed_and_store(self, chunk_id: UUID, text: str) -> UUID:
        """
        Generate embedding for text and store it.

        Args:
            chunk_id: ID of the chunk to embed
            text: Text content to embed

        Returns:
            ID of the stored embedding
        """
        # Truncate text if too long (ada-002 has 8191 token limit)
        max_chars = 30000  # ~7500 tokens
        if len(text) > max_chars:
            text = text[:max_chars]

        embedding = await self.generate_embedding(text)
        return await self.store_embedding(chunk_id, embedding)

    async def get_embedding(self, chunk_id: UUID) -> Optional[List[float]]:
        """
        Get stored embedding for a chunk.

        Args:
            chunk_id: ID of the chunk

        Returns:
            Embedding vector or None if not found
        """
        client = await self._get_client()

        response = await client.get(
            f"{self.supabase_url}/rest/v1/aria_unified_embeddings",
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
            },
            params={
                "select": "embedding",
                "chunk_id": f"eq.{chunk_id}",
            },
        )

        if response.status_code == 200:
            data = response.json()
            if data:
                # Parse embedding from PostgreSQL array format
                embedding_str = data[0]["embedding"]
                if isinstance(embedding_str, str):
                    # Parse "[1,2,3]" format
                    return [float(x) for x in embedding_str.strip("[]").split(",")]
                elif isinstance(embedding_str, list):
                    return embedding_str
            return None
        else:
            return None

    async def delete_embedding(self, chunk_id: UUID) -> bool:
        """
        Delete embedding for a chunk.

        Args:
            chunk_id: ID of the chunk

        Returns:
            True if deleted successfully
        """
        client = await self._get_client()

        response = await client.delete(
            f"{self.supabase_url}/rest/v1/aria_unified_embeddings",
            headers={
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
            },
            params={
                "chunk_id": f"eq.{chunk_id}",
            },
        )

        return response.status_code in (200, 204)

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (-1 to 1, higher is more similar)
        """
        if len(a) != len(b):
            raise ValueError("Vectors must have same dimension")

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def __repr__(self) -> str:
        return f"EmbeddingService(model={self.model})"
