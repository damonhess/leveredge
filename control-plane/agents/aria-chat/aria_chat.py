#!/usr/bin/env python3
"""
ARIA Chat Service - DEV Environment

Simple chat endpoint that connects ARIA frontend to OpenAI.
Port: 8113
"""

import os
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ARIA-CHAT")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ARIA mode system prompts
MODE_PROMPTS = {
    "DEFAULT": "You are ARIA, a helpful and balanced AI personal assistant. Be friendly, clear, and efficient.",
    "COACH": "You are ARIA in COACH mode. Be motivational, supportive, and help the user achieve their goals. Celebrate progress and encourage action.",
    "HYPE": "You are ARIA in HYPE mode! Be ENERGETIC, enthusiastic, and celebrate EVERYTHING! Use exclamation marks! Get the user PUMPED! 🔥💪",
    "COMFORT": "You are ARIA in COMFORT mode. Be calm, gentle, and reassuring. Provide emotional support and understanding. Use a warm, nurturing tone.",
    "FOCUS": "You are ARIA in FOCUS mode. Be direct, concise, and cut through distractions. No fluff. Get to the point. Help the user stay on track.",
    "DRILL": "You are ARIA in DRILL mode. Be challenging and demanding. Push the user harder. No excuses. High standards. Tough love.",
    "STRATEGY": "You are ARIA in STRATEGY mode. Be analytical, thoughtful, and methodical. Help with planning, consider trade-offs, and think long-term.",
}

app = FastAPI(
    title="ARIA Chat Service",
    description="Chat endpoint for ARIA personal assistant",
    version="1.0.0"
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


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    mode: str = "DEFAULT"
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    mode: str
    model: str
    usage: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    openai_configured: bool


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check"""
    return HealthResponse(
        status="healthy",
        service="ARIA Chat",
        version="1.0.0",
        openai_configured=bool(OPENAI_API_KEY)
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message and return AI response"""

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    # Get system prompt for mode
    system_prompt = MODE_PROMPTS.get(request.mode, MODE_PROMPTS["DEFAULT"])

    # Build messages for OpenAI
    openai_messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Add conversation history (last 20 messages max)
    for msg in request.messages[-20:]:
        openai_messages.append({
            "role": msg.role,
            "content": msg.content
        })

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": openai_messages,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
                timeout=60.0
            )

            if response.status_code != 200:
                logger.error(f"OpenAI error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=502, detail="AI service error")

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage")

            logger.info(f"Chat response generated for mode={request.mode}, tokens={usage}")

            return ChatResponse(
                content=content,
                mode=request.mode,
                model=OPENAI_MODEL,
                usage=usage
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI service timeout")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8113"))
    logger.info(f"Starting ARIA Chat on port {port}")

    uvicorn.run(
        "aria_chat:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
