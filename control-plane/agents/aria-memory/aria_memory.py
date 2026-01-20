#!/usr/bin/env python3
"""
ARIA Memory Service - Unified Threading API

Provides API endpoints for ARIA's unified conversation threading system.
Handles message storage, semantic chunking, and context retrieval.

Port: 8114
Domain: ARIA_SANCTUM
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add shared modules to path
sys.path.insert(0, "/opt/leveredge/control-plane/shared")

from unified_threading import (
    UnifiedConversation,
    ContextAssembler,
    ChunkingEngine,
    RetrievalResult,
    EmbeddingService,
)
from unified_threading.chunking import ChunkConfig
from unified_threading.retrieval import RetrievalConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ARIA-MEMORY")

# Configuration
AGENT_NAME = "ARIA-MEMORY"
AGENT_PORT = int(os.getenv("ARIA_MEMORY_PORT", "8114"))
AGENT_DOMAIN = "ARIA_SANCTUM"

app = FastAPI(
    title="ARIA Memory Service",
    description="Unified conversation threading with semantic retrieval",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dev.aria.leveredgeai.com",
        "https://aria.leveredgeai.com",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===

class MessageRequest(BaseModel):
    """Request to add a message to conversation."""
    user_id: str
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    token_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Response after adding a message."""
    message_id: str
    conversation_id: str
    sequence_num: Optional[int] = None
    created_at: str


class ContextRequest(BaseModel):
    """Request for context retrieval."""
    user_id: str
    query: Optional[str] = None
    budget_tokens: int = 8000
    include_primary: bool = True


class ContextResponse(BaseModel):
    """Response with assembled context."""
    context: str
    total_tokens: int
    primary_tokens: int
    archive_tokens: int
    chunks_retrieved: int
    query_used: Optional[str] = None


class HistoryRequest(BaseModel):
    """Request for conversation history."""
    user_id: str
    limit: int = 50


class HistoryResponse(BaseModel):
    """Response with conversation history."""
    messages: List[Dict[str, Any]]
    total_count: int


class SearchRequest(BaseModel):
    """Request for history search."""
    user_id: str
    query: str
    limit: int = 10


class SearchResponse(BaseModel):
    """Response with search results."""
    results: List[Dict[str, Any]]
    query: str


class ChunkRequest(BaseModel):
    """Request to force chunking."""
    user_id: str


class ChunkResponse(BaseModel):
    """Response after chunking."""
    chunk_created: bool
    chunk_id: Optional[str] = None
    token_count: Optional[int] = None
    message_count: Optional[int] = None


class StatsResponse(BaseModel):
    """Conversation statistics."""
    conversation_id: str
    user_id: str
    total_messages: int
    total_chunks: int
    primary_buffer_size: int
    last_message_at: Optional[str] = None
    created_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    domain: str


# === Endpoints ===

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=AGENT_NAME,
        version="1.0.0",
        domain=AGENT_DOMAIN,
    )


@app.post("/conversation/message", response_model=MessageResponse)
async def add_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    Add a message to the unified conversation stream.

    Automatically handles chunking in the background if needed.
    """
    try:
        # Get or create conversation
        conv = await UnifiedConversation.get_or_create(request.user_id)

        # Add message
        message = await conv.add_message(
            role=request.role,
            content=request.content,
            token_count=request.token_count,
            metadata=request.metadata,
        )

        # Schedule auto-chunking in background
        background_tasks.add_task(auto_chunk_if_needed, conv)

        await conv.close()

        return MessageResponse(
            message_id=str(message.id),
            conversation_id=str(conv.conversation_id),
            sequence_num=message.sequence_num,
            created_at=message.created_at.isoformat() if message.created_at else datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context/retrieve", response_model=ContextResponse)
async def retrieve_context(request: ContextRequest):
    """
    Retrieve assembled context for LLM consumption.

    Combines primary buffer with semantically relevant archived chunks.
    """
    try:
        # Get conversation
        conv = await UnifiedConversation.get_or_create(request.user_id)

        # Create assembler with config
        config = RetrievalConfig(default_budget_tokens=request.budget_tokens)
        assembler = ContextAssembler(conv, config=config)

        # Get context
        result = await assembler.get_context(
            query=request.query,
            budget_tokens=request.budget_tokens,
            include_primary=request.include_primary,
        )

        # Format for LLM
        context = assembler.format_context_for_llm(result, include_metadata=True)

        await assembler.close()
        await conv.close()

        return ContextResponse(
            context=context,
            total_tokens=result.total_tokens,
            primary_tokens=result.primary_tokens,
            archive_tokens=result.archive_tokens,
            chunks_retrieved=len(result.retrieved_chunks),
            query_used=result.query_used,
        )

    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/history", response_model=HistoryResponse)
async def get_history(user_id: str, limit: int = 50):
    """
    Get recent conversation history from primary buffer.
    """
    try:
        conv = await UnifiedConversation.get_or_create(user_id)

        messages = await conv.get_primary_buffer(limit=limit)

        # Convert to dict format
        message_dicts = [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "token_count": m.token_count,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "metadata": m.metadata,
                "sequence_num": m.sequence_num,
            }
            for m in reversed(messages)  # Chronological order
        ]

        total = await conv.get_message_count()
        await conv.close()

        return HistoryResponse(
            messages=message_dicts,
            total_count=total,
        )

    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/conversation/search", response_model=SearchResponse)
async def search_history(request: SearchRequest):
    """
    Search conversation history by text.
    """
    try:
        conv = await UnifiedConversation.get_or_create(request.user_id)

        results = await conv.search_history(
            query=request.query,
            limit=request.limit,
        )

        await conv.close()

        return SearchResponse(
            results=results,
            query=request.query,
        )

    except Exception as e:
        logger.error(f"Error searching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/context/force-chunk", response_model=ChunkResponse)
async def force_chunk(request: ChunkRequest):
    """
    Force chunking of oldest messages in primary buffer.

    Useful for manual archival or before context switches.
    """
    try:
        conv = await UnifiedConversation.get_or_create(request.user_id)
        engine = ChunkingEngine(conv)

        chunk = await engine.auto_chunk()

        await engine.close()
        await conv.close()

        if chunk:
            return ChunkResponse(
                chunk_created=True,
                chunk_id=str(chunk.id),
                token_count=chunk.token_count,
                message_count=chunk.message_count,
            )
        else:
            return ChunkResponse(chunk_created=False)

    except Exception as e:
        logger.error(f"Error forcing chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/context/stats", response_model=StatsResponse)
async def get_stats(user_id: str):
    """
    Get conversation statistics.
    """
    try:
        conv = await UnifiedConversation.get_or_create(user_id)
        stats = await conv.get_stats()

        await conv.close()

        return StatsResponse(
            conversation_id=str(stats.conversation_id),
            user_id=stats.user_id,
            total_messages=stats.total_messages,
            total_chunks=stats.total_chunks,
            primary_buffer_size=stats.primary_buffer_size,
            last_message_at=stats.last_message_at.isoformat() if stats.last_message_at else None,
            created_at=stats.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === Background Tasks ===

async def auto_chunk_if_needed(conv: UnifiedConversation):
    """Background task to check and perform auto-chunking."""
    try:
        engine = ChunkingEngine(conv)

        # Check if chunking needed (more than 2x buffer size)
        if await conv.needs_chunking(conv.primary_buffer_size * 2):
            chunk = await engine.auto_chunk()
            if chunk:
                logger.info(f"Auto-chunked {chunk.message_count} messages for user {conv.user_id}")

                # Generate embedding for the chunk
                embedding_service = EmbeddingService()
                try:
                    await embedding_service.embed_and_store(chunk.id, chunk.content)
                    logger.info(f"Generated embedding for chunk {chunk.id}")
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {e}")
                finally:
                    await embedding_service.close()

        await engine.close()

    except Exception as e:
        logger.error(f"Auto-chunk error: {e}")


# === Main ===

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {AGENT_NAME} on port {AGENT_PORT}")
    logger.info(f"Domain: {AGENT_DOMAIN}")

    uvicorn.run(
        "aria_memory:app",
        host="0.0.0.0",
        port=AGENT_PORT,
        reload=True,
    )
