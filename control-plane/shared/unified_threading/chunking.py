"""
Semantic Chunking Engine

Chunks conversation messages based on semantic boundaries,
token limits, and topic shifts.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
import httpx

from .conversation import Message, UnifiedConversation

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))


@dataclass
class ChunkConfig:
    """Configuration for chunking behavior."""
    target_tokens: int = 450  # Target tokens per chunk (400-512 optimal)
    max_tokens: int = 600     # Maximum tokens before forced chunk
    min_messages: int = 3     # Minimum messages per chunk
    max_messages: int = 10    # Maximum messages per chunk
    overlap_tokens: int = 50  # Overlap with previous chunk
    time_gap_hours: float = 4.0  # Force chunk after time gap


@dataclass
class Chunk:
    """A chunk of archived conversation."""
    id: UUID
    conversation_id: UUID
    content: str
    summary: Optional[str] = None
    token_count: int = 0
    message_count: int = 0
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None
    messages_start_at: Optional[datetime] = None
    messages_end_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    topics: List[str] = field(default_factory=list)
    importance_score: float = 1.0
    retrieval_count: int = 0
    is_compacted: bool = False

    # For retrieval scoring
    similarity: Optional[float] = None
    recency_score: Optional[float] = None
    combined_score: Optional[float] = None


class ChunkingEngine:
    """
    Engine for chunking conversation messages.

    Uses semantic boundaries, token limits, and topic shifts
    to create optimal chunks for retrieval.
    """

    def __init__(
        self,
        conversation: UnifiedConversation,
        config: Optional[ChunkConfig] = None,
    ):
        self.conversation = conversation
        self.config = config or ChunkConfig()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get Supabase API headers."""
        return {
            "apikey": self.conversation.supabase_key,
            "Authorization": f"Bearer {self.conversation.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple approximation: ~4 characters per token for English.
        For more accuracy, use tiktoken.
        """
        return len(text) // 4

    def should_chunk(self, messages: List[Message]) -> bool:
        """
        Determine if messages should be chunked.

        Triggers:
        1. Token threshold exceeded
        2. Message count exceeded
        3. Time gap detected
        """
        if len(messages) < self.config.min_messages:
            return False

        # Check token count
        total_tokens = sum(
            m.token_count or self.estimate_tokens(m.content)
            for m in messages
        )
        if total_tokens >= self.config.max_tokens:
            return True

        # Check message count
        if len(messages) >= self.config.max_messages:
            return True

        # Check time gap
        if len(messages) >= 2:
            sorted_msgs = sorted(messages, key=lambda m: m.created_at or datetime.min)
            for i in range(1, len(sorted_msgs)):
                if sorted_msgs[i].created_at and sorted_msgs[i-1].created_at:
                    gap = sorted_msgs[i].created_at - sorted_msgs[i-1].created_at
                    if gap > timedelta(hours=self.config.time_gap_hours):
                        return True

        return False

    def find_chunk_boundary(self, messages: List[Message]) -> int:
        """
        Find optimal boundary for chunking.

        Prefers to break at:
        1. Topic shifts (detected by content change)
        2. User message boundaries
        3. Time gaps

        Returns index of last message to include in chunk.
        """
        if len(messages) <= self.config.min_messages:
            return len(messages) - 1

        # Start with target token count
        running_tokens = 0
        boundary_idx = self.config.min_messages - 1

        for i, msg in enumerate(messages):
            msg_tokens = msg.token_count or self.estimate_tokens(msg.content)
            running_tokens += msg_tokens

            # Check if we've hit target
            if running_tokens >= self.config.target_tokens:
                # Prefer to end at a user message (natural boundary)
                if msg.role == "user" and i >= self.config.min_messages - 1:
                    boundary_idx = i
                    break
                # Or at least not in the middle of an assistant response
                elif i > 0 and messages[i-1].role == "user":
                    boundary_idx = i - 1
                    break
                else:
                    boundary_idx = i
                    break

            # Update boundary as we go
            if i >= self.config.min_messages - 1:
                boundary_idx = i

            # Don't exceed max
            if i >= self.config.max_messages - 1:
                break

        return boundary_idx

    def format_chunk_content(self, messages: List[Message]) -> str:
        """Format messages into chunk content."""
        lines = []
        for msg in messages:
            role_label = msg.role.upper()
            timestamp = msg.created_at.isoformat() if msg.created_at else "unknown"
            lines.append(f"[{role_label}] ({timestamp})")
            lines.append(msg.content)
            lines.append("")  # Blank line between messages
        return "\n".join(lines)

    async def create_chunk(
        self,
        messages: List[Message],
        summary: Optional[str] = None,
    ) -> Chunk:
        """
        Create a chunk from messages.

        Args:
            messages: Messages to include in chunk
            summary: Optional LLM-generated summary

        Returns:
            Created Chunk object
        """
        client = await self._get_client()

        # Format content
        content = self.format_chunk_content(messages)
        token_count = sum(
            m.token_count or self.estimate_tokens(m.content)
            for m in messages
        )

        # Get message IDs
        message_ids = [str(m.id) for m in messages]

        # Use database function to create chunk atomically
        response = await client.post(
            f"{self.conversation.supabase_url}/rest/v1/rpc/create_chunk_from_buffer",
            headers=self.headers,
            json={
                "p_conversation_id": str(self.conversation.conversation_id),
                "p_message_ids": message_ids,
                "p_content": content,
                "p_token_count": token_count,
                "p_summary": summary,
            },
        )

        if response.status_code == 200:
            chunk_id = UUID(response.json())
            return Chunk(
                id=chunk_id,
                conversation_id=self.conversation.conversation_id,
                content=content,
                summary=summary,
                token_count=token_count,
                message_count=len(messages),
                start_sequence=messages[0].sequence_num if messages else None,
                end_sequence=messages[-1].sequence_num if messages else None,
                messages_start_at=messages[0].created_at if messages else None,
                messages_end_at=messages[-1].created_at if messages else None,
                created_at=datetime.utcnow(),
            )
        else:
            raise Exception(f"Failed to create chunk: {response.text}")

    async def auto_chunk(self) -> Optional[Chunk]:
        """
        Automatically chunk oldest messages if needed.

        Returns:
            Created Chunk if chunking occurred, None otherwise
        """
        # Check if chunking is needed
        if not await self.conversation.needs_chunking(self.config.max_messages):
            return None

        # Get messages that can be chunked
        messages = await self.conversation.get_messages_for_chunking(
            self.config.max_messages + 5  # Get a few extra for boundary finding
        )

        if not self.should_chunk(messages):
            return None

        # Find optimal boundary
        boundary = self.find_chunk_boundary(messages)
        messages_to_chunk = messages[:boundary + 1]

        # Create the chunk
        chunk = await self.create_chunk(messages_to_chunk)

        return chunk

    async def get_chunks(
        self,
        limit: int = 50,
        include_compacted: bool = True,
    ) -> List[Chunk]:
        """
        Get all chunks for the conversation.

        Args:
            limit: Maximum chunks to return
            include_compacted: Include compacted chunks

        Returns:
            List of Chunks, most recent first
        """
        client = await self._get_client()

        params = {
            "select": "*",
            "conversation_id": f"eq.{self.conversation.conversation_id}",
            "order": "created_at.desc",
            "limit": limit,
        }

        if not include_compacted:
            params["is_compacted"] = "eq.false"

        response = await client.get(
            f"{self.conversation.supabase_url}/rest/v1/aria_unified_chunks",
            headers=self.headers,
            params=params,
        )

        if response.status_code == 200:
            data = response.json()
            return [
                Chunk(
                    id=UUID(row["id"]),
                    conversation_id=UUID(row["conversation_id"]),
                    content=row["content"],
                    summary=row.get("summary"),
                    token_count=row["token_count"],
                    message_count=row["message_count"],
                    start_sequence=row.get("start_sequence"),
                    end_sequence=row.get("end_sequence"),
                    messages_start_at=datetime.fromisoformat(row["messages_start_at"].replace("Z", "+00:00")) if row.get("messages_start_at") else None,
                    messages_end_at=datetime.fromisoformat(row["messages_end_at"].replace("Z", "+00:00")) if row.get("messages_end_at") else None,
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")) if row.get("created_at") else None,
                    topics=row.get("topics", []),
                    importance_score=row.get("importance_score", 1.0),
                    retrieval_count=row.get("retrieval_count", 0),
                    is_compacted=row.get("is_compacted", False),
                )
                for row in data
            ]
        else:
            raise Exception(f"Failed to get chunks: {response.text}")

    async def get_chunk_count(self) -> int:
        """Get total chunk count."""
        stats = await self.conversation.get_stats()
        return stats.total_chunks

    def __repr__(self) -> str:
        return f"ChunkingEngine(conversation={self.conversation.user_id})"
