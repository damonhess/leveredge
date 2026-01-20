"""
Unified Conversation Stream

One continuous conversation per user with automatic chunking
and primary buffer management.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
import asyncio
import httpx

# Database configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))


@dataclass
class Message:
    """A single message in the unified stream."""
    id: UUID
    role: str  # user, assistant, system
    content: str
    token_count: Optional[int] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    sequence_num: Optional[int] = None
    chunk_id: Optional[UUID] = None
    is_in_primary_buffer: bool = True


@dataclass
class ConversationStats:
    """Statistics for a unified conversation."""
    conversation_id: UUID
    user_id: str
    total_messages: int
    total_chunks: int
    primary_buffer_size: int
    last_message_at: Optional[datetime]
    created_at: datetime


class UnifiedConversation:
    """
    A unified conversation stream for a single user.

    All messages go into one continuous stream. The primary buffer
    holds the most recent messages (always included in context).
    Older messages are automatically chunked and stored for
    semantic retrieval.
    """

    def __init__(
        self,
        conversation_id: UUID,
        user_id: str,
        primary_buffer_size: int = 20,
        supabase_url: str = None,
        supabase_key: str = None,
    ):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.primary_buffer_size = primary_buffer_size
        self.supabase_url = supabase_url or SUPABASE_URL
        self.supabase_key = supabase_key or SUPABASE_KEY
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get Supabase API headers."""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @classmethod
    async def get_or_create(
        cls,
        user_id: str,
        primary_buffer_size: int = 20,
        supabase_url: str = None,
        supabase_key: str = None,
    ) -> "UnifiedConversation":
        """
        Get existing or create new unified conversation for a user.

        Args:
            user_id: Unique user identifier
            primary_buffer_size: Number of messages to keep in primary buffer
            supabase_url: Optional Supabase URL override
            supabase_key: Optional Supabase key override

        Returns:
            UnifiedConversation instance
        """
        url = supabase_url or SUPABASE_URL
        key = supabase_key or SUPABASE_KEY

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call the database function to get or create
            response = await client.post(
                f"{url}/rest/v1/rpc/get_or_create_unified_conversation",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={"p_user_id": user_id},
            )

            if response.status_code == 200:
                conversation_id = UUID(response.json())
                return cls(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    primary_buffer_size=primary_buffer_size,
                    supabase_url=url,
                    supabase_key=key,
                )
            else:
                raise Exception(f"Failed to get/create conversation: {response.text}")

    async def add_message(
        self,
        role: str,
        content: str,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Add a message to the unified stream.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            token_count: Optional token count
            metadata: Optional metadata (mode, tools_used, etc.)

        Returns:
            The created Message object
        """
        client = await self._get_client()

        # Use the database function for atomic operation
        response = await client.post(
            f"{self.supabase_url}/rest/v1/rpc/add_unified_message",
            headers=self.headers,
            json={
                "p_user_id": self.user_id,
                "p_role": role,
                "p_content": content,
                "p_token_count": token_count,
                "p_metadata": metadata or {},
            },
        )

        if response.status_code == 200:
            message_id = UUID(response.json())
            return Message(
                id=message_id,
                role=role,
                content=content,
                token_count=token_count,
                created_at=datetime.utcnow(),
                metadata=metadata or {},
                is_in_primary_buffer=True,
            )
        else:
            raise Exception(f"Failed to add message: {response.text}")

    async def get_primary_buffer(self, limit: Optional[int] = None) -> List[Message]:
        """
        Get messages in the primary buffer.

        Args:
            limit: Optional limit (defaults to primary_buffer_size)

        Returns:
            List of Messages, most recent first
        """
        client = await self._get_client()
        limit = limit or self.primary_buffer_size

        response = await client.post(
            f"{self.supabase_url}/rest/v1/rpc/get_primary_buffer",
            headers=self.headers,
            json={
                "p_user_id": self.user_id,
                "p_limit": limit,
            },
        )

        if response.status_code == 200:
            data = response.json()
            return [
                Message(
                    id=UUID(row["id"]),
                    role=row["role"],
                    content=row["content"],
                    token_count=row["token_count"],
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")) if row["created_at"] else None,
                    metadata=row.get("metadata", {}),
                    sequence_num=row["sequence_num"],
                    is_in_primary_buffer=True,
                )
                for row in data
            ]
        else:
            raise Exception(f"Failed to get primary buffer: {response.text}")

    async def get_message_count(self) -> int:
        """Get total message count in the conversation."""
        client = await self._get_client()

        response = await client.get(
            f"{self.supabase_url}/rest/v1/aria_unified_conversations",
            headers=self.headers,
            params={
                "select": "total_messages",
                "user_id": f"eq.{self.user_id}",
            },
        )

        if response.status_code == 200:
            data = response.json()
            return data[0]["total_messages"] if data else 0
        else:
            return 0

    async def get_stats(self) -> ConversationStats:
        """Get conversation statistics."""
        client = await self._get_client()

        response = await client.get(
            f"{self.supabase_url}/rest/v1/aria_unified_conversations",
            headers=self.headers,
            params={
                "select": "*",
                "user_id": f"eq.{self.user_id}",
            },
        )

        if response.status_code == 200:
            data = response.json()
            if data:
                row = data[0]
                return ConversationStats(
                    conversation_id=UUID(row["id"]),
                    user_id=row["user_id"],
                    total_messages=row["total_messages"],
                    total_chunks=row["total_chunks"],
                    primary_buffer_size=row.get("primary_buffer_size", 20),
                    last_message_at=datetime.fromisoformat(row["last_message_at"].replace("Z", "+00:00")) if row["last_message_at"] else None,
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                )
            else:
                raise Exception("Conversation not found")
        else:
            raise Exception(f"Failed to get stats: {response.text}")

    async def needs_chunking(self, threshold: int = None) -> bool:
        """
        Check if the primary buffer needs chunking.

        Args:
            threshold: Token or message threshold for chunking

        Returns:
            True if chunking is needed
        """
        threshold = threshold or (self.primary_buffer_size * 2)
        messages = await self.get_primary_buffer(limit=threshold + 1)
        return len(messages) > threshold

    async def get_messages_for_chunking(self, count: int) -> List[Message]:
        """
        Get oldest messages from primary buffer for chunking.

        Args:
            count: Number of messages to get

        Returns:
            List of messages to chunk (oldest first)
        """
        client = await self._get_client()

        # Get the oldest messages that are still in primary buffer
        response = await client.get(
            f"{self.supabase_url}/rest/v1/aria_unified_messages",
            headers=self.headers,
            params={
                "select": "*",
                "conversation_id": f"eq.{self.conversation_id}",
                "is_in_primary_buffer": "eq.true",
                "order": "sequence_num.asc",
                "limit": count,
            },
        )

        if response.status_code == 200:
            data = response.json()
            return [
                Message(
                    id=UUID(row["id"]),
                    role=row["role"],
                    content=row["content"],
                    token_count=row.get("token_count"),
                    created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")) if row["created_at"] else None,
                    metadata=row.get("metadata", {}),
                    sequence_num=row["sequence_num"],
                    is_in_primary_buffer=True,
                )
                for row in data
            ]
        else:
            raise Exception(f"Failed to get messages for chunking: {response.text}")

    async def search_history(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search conversation history by text.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching messages
        """
        client = await self._get_client()

        # Simple text search (can be enhanced with full-text search)
        response = await client.get(
            f"{self.supabase_url}/rest/v1/aria_unified_messages",
            headers=self.headers,
            params={
                "select": "*",
                "conversation_id": f"eq.{self.conversation_id}",
                "content": f"ilike.%{query}%",
                "order": "created_at.desc",
                "limit": limit,
            },
        )

        if response.status_code == 200:
            return response.json()
        else:
            return []

    def __repr__(self) -> str:
        return f"UnifiedConversation(user_id={self.user_id}, id={self.conversation_id})"
