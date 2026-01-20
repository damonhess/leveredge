"""
Context Retrieval System

Assembles optimal context from primary buffer and archived chunks
using semantic search and relevance scoring.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
import httpx

from .conversation import UnifiedConversation, Message
from .chunking import Chunk, ChunkingEngine
from .embeddings import EmbeddingService

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))


@dataclass
class RetrievalConfig:
    """Configuration for context retrieval."""
    default_budget_tokens: int = 8000  # Default token budget
    primary_buffer_weight: float = 1.0  # Always include primary buffer
    semantic_weight: float = 0.7  # Weight for semantic similarity
    recency_weight: float = 0.3  # Weight for recency score
    similarity_threshold: float = 0.7  # Minimum similarity to retrieve
    max_chunks_to_retrieve: int = 10  # Maximum chunks to consider
    recency_decay_hours: float = 24.0  # Hours for recency decay factor

    # Importance multipliers for special content
    importance_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "has_decision": 1.5,
        "has_commitment": 1.5,
        "has_insight": 1.3,
        "has_user_preference": 1.4,
    })


@dataclass
class RetrievalResult:
    """Result of context retrieval."""
    primary_messages: List[Message]
    retrieved_chunks: List[Chunk]
    total_tokens: int
    primary_tokens: int
    archive_tokens: int
    retrieval_scores: Dict[str, float]
    query_used: Optional[str] = None


class ContextAssembler:
    """
    Assembles optimal context from primary buffer and archive.

    The assembler:
    1. Always includes the primary buffer (most recent messages)
    2. Performs semantic search on archived chunks
    3. Applies recency boost to recent chunks
    4. Fills the token budget with most relevant context
    """

    def __init__(
        self,
        conversation: UnifiedConversation,
        config: Optional[RetrievalConfig] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.conversation = conversation
        self.config = config or RetrievalConfig()
        self.embedding_service = embedding_service or EmbeddingService()
        self.chunking_engine = ChunkingEngine(conversation)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get Supabase API headers."""
        return {
            "apikey": self.conversation.supabase_key,
            "Authorization": f"Bearer {self.conversation.supabase_key}",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close HTTP client and related services."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        await self.embedding_service.close()
        await self.chunking_engine.close()

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // 4

    def calculate_recency_score(self, chunk_created_at: datetime) -> float:
        """
        Calculate recency score with exponential decay.

        Score decays from 1.0 to ~0 over several days.
        """
        if not chunk_created_at:
            return 0.5  # Default for unknown time

        now = datetime.utcnow()
        if chunk_created_at.tzinfo:
            now = datetime.now(chunk_created_at.tzinfo)

        age = now - chunk_created_at
        age_hours = age.total_seconds() / 3600

        # Exponential decay: score = 1 / (1 + age_hours / decay_factor)
        return 1.0 / (1 + age_hours / self.config.recency_decay_hours)

    def calculate_combined_score(
        self,
        similarity: float,
        recency_score: float,
        importance_score: float = 1.0,
    ) -> float:
        """
        Calculate combined relevance score.

        Combines semantic similarity, recency, and importance.
        """
        weighted_similarity = similarity * self.config.semantic_weight
        weighted_recency = recency_score * self.config.recency_weight
        base_score = weighted_similarity + weighted_recency

        # Apply importance multiplier
        return base_score * importance_score

    async def semantic_search(
        self,
        query: str,
        top_k: int = None,
    ) -> List[Chunk]:
        """
        Search archived chunks by semantic similarity.

        Args:
            query: Search query
            top_k: Maximum results (defaults to config)

        Returns:
            List of Chunks with similarity scores
        """
        top_k = top_k or self.config.max_chunks_to_retrieve
        client = await self._get_client()

        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Format embedding for PostgreSQL
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

        # Use database function for semantic search
        response = await client.post(
            f"{self.conversation.supabase_url}/rest/v1/rpc/search_chunks_semantic",
            headers=self.headers,
            json={
                "p_user_id": self.conversation.user_id,
                "p_embedding": embedding_str,
                "p_limit": top_k,
                "p_threshold": self.config.similarity_threshold,
            },
        )

        if response.status_code == 200:
            data = response.json()
            chunks = []
            for row in data:
                chunk = Chunk(
                    id=UUID(row["chunk_id"]),
                    conversation_id=self.conversation.conversation_id,
                    content=row["content"],
                    summary=row.get("summary"),
                    token_count=row["token_count"],
                    message_count=0,  # Not returned by search
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")) if row.get("created_at") else None,
                )
                chunk.similarity = row["similarity"]
                chunk.recency_score = self.calculate_recency_score(chunk.created_at)
                chunk.combined_score = self.calculate_combined_score(
                    chunk.similarity,
                    chunk.recency_score,
                )
                chunks.append(chunk)

            # Sort by combined score
            chunks.sort(key=lambda c: c.combined_score or 0, reverse=True)
            return chunks
        else:
            # If semantic search fails, fall back to recent chunks
            return await self.get_recent_chunks(limit=top_k)

    async def get_recent_chunks(self, limit: int = 10) -> List[Chunk]:
        """Get most recent chunks (fallback when no query)."""
        chunks = await self.chunking_engine.get_chunks(limit=limit)
        for chunk in chunks:
            chunk.recency_score = self.calculate_recency_score(chunk.created_at)
            chunk.similarity = 0.8  # Default similarity for recent chunks
            chunk.combined_score = self.calculate_combined_score(
                chunk.similarity,
                chunk.recency_score,
            )
        return chunks

    async def get_context(
        self,
        query: Optional[str] = None,
        budget_tokens: int = None,
        include_primary: bool = True,
    ) -> RetrievalResult:
        """
        Assemble context for LLM consumption.

        Args:
            query: Optional query for semantic search
            budget_tokens: Token budget (defaults to config)
            include_primary: Whether to include primary buffer

        Returns:
            RetrievalResult with assembled context
        """
        budget = budget_tokens or self.config.default_budget_tokens
        remaining_budget = budget

        primary_messages = []
        primary_tokens = 0
        retrieved_chunks = []
        archive_tokens = 0
        retrieval_scores = {}

        # 1. Always include primary buffer if requested
        if include_primary:
            primary_messages = await self.conversation.get_primary_buffer()
            # Reverse to get chronological order
            primary_messages = list(reversed(primary_messages))

            primary_tokens = sum(
                m.token_count or self.estimate_tokens(m.content)
                for m in primary_messages
            )
            remaining_budget -= primary_tokens

        # 2. Search archive if we have budget and a query
        if remaining_budget > 100:
            if query:
                # Semantic search
                candidates = await self.semantic_search(query)
                retrieval_scores["search_method"] = "semantic"
            else:
                # Fall back to recent chunks
                candidates = await self.get_recent_chunks()
                retrieval_scores["search_method"] = "recency"

            # 3. Fill budget with best chunks
            for chunk in candidates:
                if chunk.token_count <= remaining_budget:
                    retrieved_chunks.append(chunk)
                    archive_tokens += chunk.token_count
                    remaining_budget -= chunk.token_count

                    # Track retrieval scores
                    retrieval_scores[str(chunk.id)] = {
                        "similarity": chunk.similarity,
                        "recency": chunk.recency_score,
                        "combined": chunk.combined_score,
                    }

                if remaining_budget < 100:
                    break

            # 4. Update retrieval counts for retrieved chunks
            await self._update_retrieval_counts([c.id for c in retrieved_chunks])

        return RetrievalResult(
            primary_messages=primary_messages,
            retrieved_chunks=retrieved_chunks,
            total_tokens=primary_tokens + archive_tokens,
            primary_tokens=primary_tokens,
            archive_tokens=archive_tokens,
            retrieval_scores=retrieval_scores,
            query_used=query,
        )

    async def _update_retrieval_counts(self, chunk_ids: List[UUID]) -> None:
        """Update retrieval counts for chunks."""
        if not chunk_ids:
            return

        client = await self._get_client()

        for chunk_id in chunk_ids:
            # Increment retrieval count
            await client.patch(
                f"{self.conversation.supabase_url}/rest/v1/aria_unified_chunks",
                headers=self.headers,
                params={"id": f"eq.{chunk_id}"},
                json={
                    "retrieval_count": "retrieval_count + 1",  # This won't work as-is
                    "last_retrieved_at": datetime.utcnow().isoformat(),
                },
            )

    def format_context_for_llm(
        self,
        result: RetrievalResult,
        include_metadata: bool = False,
    ) -> str:
        """
        Format retrieval result as context string for LLM.

        Args:
            result: RetrievalResult from get_context
            include_metadata: Whether to include retrieval metadata

        Returns:
            Formatted context string
        """
        parts = []

        # Add archived context first (older)
        if result.retrieved_chunks:
            parts.append("=== RELEVANT PAST CONTEXT ===\n")
            for chunk in reversed(result.retrieved_chunks):  # Chronological order
                if chunk.summary:
                    parts.append(f"[Summary from {chunk.created_at.date() if chunk.created_at else 'past'}]")
                    parts.append(chunk.summary)
                else:
                    parts.append(chunk.content)
                parts.append("")

        # Add primary buffer (recent)
        if result.primary_messages:
            parts.append("=== RECENT CONVERSATION ===\n")
            for msg in result.primary_messages:
                role_label = msg.role.upper()
                parts.append(f"[{role_label}]")
                parts.append(msg.content)
                parts.append("")

        # Add metadata if requested
        if include_metadata:
            parts.append(f"\n[Context: {result.total_tokens} tokens, {len(result.retrieved_chunks)} archive chunks]")

        return "\n".join(parts)

    def __repr__(self) -> str:
        return f"ContextAssembler(conversation={self.conversation.user_id})"
