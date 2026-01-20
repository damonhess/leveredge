"""
Unified Threading Module for ARIA

Provides a single continuous conversation stream with smart chunking
and semantic retrieval for context management.

Usage:
    from unified_threading import UnifiedConversation, ContextAssembler

    # Get or create conversation for user
    conv = await UnifiedConversation.get_or_create(user_id="damon")

    # Add message
    await conv.add_message("user", "What did we discuss about pricing?")

    # Get context for LLM
    assembler = ContextAssembler(conv)
    context = await assembler.get_context(
        query="pricing discussion",
        budget_tokens=8000
    )

    # Use context with LLM...
"""

from .conversation import UnifiedConversation
from .chunking import ChunkingEngine, Chunk
from .retrieval import ContextAssembler, RetrievalResult
from .embeddings import EmbeddingService

__all__ = [
    "UnifiedConversation",
    "ChunkingEngine",
    "Chunk",
    "ContextAssembler",
    "RetrievalResult",
    "EmbeddingService",
]

__version__ = "1.0.0"
