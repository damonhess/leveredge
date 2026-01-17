#!/usr/bin/env python3
"""
VOICE - Voice Interface for ARIA
Port: 8051

Provides voice-to-text and text-to-voice capabilities for ARIA interactions.
Supports voice notes from Telegram/web interfaces.
"""

import os
import io
import uuid
import httpx
import aiofiles
import tempfile
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from openai import AsyncOpenAI

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ARIA_WEBHOOK_URL = os.getenv("ARIA_WEBHOOK_URL", "http://localhost:5680/webhook/aria-router")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
TEMP_DIR = Path(os.getenv("VOICE_TEMP_DIR", "/tmp/voice-cache"))

# Supported audio formats
SUPPORTED_FORMATS = {"wav", "mp3", "m4a", "ogg", "webm", "flac", "mpeg", "mpga"}

# TTS voices available
TTS_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
DEFAULT_VOICE = "nova"
DEFAULT_TTS_MODEL = "tts-1"
DEFAULT_STT_MODEL = "whisper-1"

# Ensure temp directory exists
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Initialize OpenAI client
openai_client: Optional[AsyncOpenAI] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global openai_client

    if OPENAI_API_KEY:
        openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI client initialized")
    else:
        print("WARNING: OPENAI_API_KEY not set - voice features will be unavailable")

    yield

    # Cleanup temp files on shutdown
    for temp_file in TEMP_DIR.glob("*"):
        try:
            temp_file.unlink()
        except Exception:
            pass


app = FastAPI(
    title="VOICE",
    description="Voice Interface for ARIA - Speech-to-Text and Text-to-Speech",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class SynthesizeRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    model: str = DEFAULT_TTS_MODEL
    response_format: str = "mp3"


class TranscriptionResponse(BaseModel):
    text: str
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


class ChatResponse(BaseModel):
    input_text: str
    aria_response: str
    audio_url: Optional[str] = None
    conversation_id: Optional[str] = None


# Helper Functions
async def log_to_event_bus(action: str, target: str = "", details: dict = None):
    """Log events to the event bus."""
    if details is None:
        details = {}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "VOICE",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")


def get_file_extension(filename: str) -> str:
    """Extract and validate file extension."""
    if not filename:
        return ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext


async def transcribe_audio(audio_data: bytes, filename: str) -> dict:
    """Transcribe audio using OpenAI Whisper API."""
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not configured")

    ext = get_file_extension(filename)
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {ext}. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Create a file-like object for the API
    audio_file = io.BytesIO(audio_data)
    audio_file.name = filename

    try:
        response = await openai_client.audio.transcriptions.create(
            model=DEFAULT_STT_MODEL,
            file=audio_file,
            response_format="verbose_json"
        )

        return {
            "text": response.text,
            "duration_seconds": getattr(response, "duration", None),
            "language": getattr(response, "language", None)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


async def synthesize_speech(text: str, voice: str = DEFAULT_VOICE,
                           model: str = DEFAULT_TTS_MODEL,
                           response_format: str = "mp3") -> bytes:
    """Synthesize speech using OpenAI TTS API."""
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not configured")

    if voice not in TTS_VOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voice: {voice}. Available: {', '.join(TTS_VOICES)}"
        )

    try:
        response = await openai_client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format=response_format
        )

        # Read the streaming response into bytes
        audio_data = response.content
        return audio_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


async def send_to_aria(text: str, user_id: str = "voice_user") -> dict:
    """Send text to ARIA workflow and get response."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ARIA_WEBHOOK_URL,
                json={
                    "message": text,
                    "user_id": user_id,
                    "source": "voice",
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=60.0  # ARIA may take time to process
            )

            if response.status_code == 200:
                data = response.json()
                # Handle different response structures
                if isinstance(data, dict):
                    return {
                        "response": data.get("response", data.get("message", str(data))),
                        "conversation_id": data.get("conversation_id")
                    }
                return {"response": str(data), "conversation_id": None}
            else:
                return {
                    "response": f"ARIA returned status {response.status_code}",
                    "conversation_id": None
                }
    except httpx.TimeoutException:
        return {"response": "ARIA request timed out. Please try again.", "conversation_id": None}
    except Exception as e:
        return {"response": f"Failed to reach ARIA: {str(e)}", "conversation_id": None}


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint."""
    openai_configured = bool(OPENAI_API_KEY and openai_client)

    return {
        "status": "healthy",
        "agent": "VOICE",
        "port": 8051,
        "openai_configured": openai_configured,
        "aria_webhook": ARIA_WEBHOOK_URL,
        "supported_formats": list(SUPPORTED_FORMATS),
        "available_voices": list(TTS_VOICES),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/voice/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    audio: UploadFile = File(..., description="Audio file to transcribe")
):
    """
    Transcribe audio to text using OpenAI Whisper.

    Supported formats: wav, mp3, m4a, ogg, webm, flac, mpeg, mpga
    """
    # Read audio data
    audio_data = await audio.read()

    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Log the transcription request
    await log_to_event_bus(
        "transcription_request",
        details={
            "filename": audio.filename,
            "size_bytes": len(audio_data)
        }
    )

    # Transcribe
    result = await transcribe_audio(audio_data, audio.filename or "audio.mp3")

    await log_to_event_bus(
        "transcription_complete",
        details={
            "text_length": len(result["text"]),
            "duration": result.get("duration_seconds"),
            "language": result.get("language")
        }
    )

    return TranscriptionResponse(**result)


@app.post("/voice/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Convert text to speech using OpenAI TTS.

    Available voices: alloy, echo, fable, onyx, nova, shimmer
    Response formats: mp3, opus, aac, flac
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Log the synthesis request
    await log_to_event_bus(
        "synthesis_request",
        details={
            "text_length": len(request.text),
            "voice": request.voice,
            "format": request.response_format
        }
    )

    # Synthesize speech
    audio_data = await synthesize_speech(
        text=request.text,
        voice=request.voice,
        model=request.model,
        response_format=request.response_format
    )

    await log_to_event_bus(
        "synthesis_complete",
        details={
            "audio_size_bytes": len(audio_data),
            "voice": request.voice
        }
    )

    # Determine content type
    content_types = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac"
    }
    content_type = content_types.get(request.response_format, "audio/mpeg")

    return Response(
        content=audio_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="speech.{request.response_format}"'
        }
    )


@app.post("/voice/chat")
async def voice_chat(
    audio: UploadFile = File(..., description="Audio file with user's message"),
    user_id: str = Form(default="voice_user", description="User identifier"),
    voice: str = Form(default=DEFAULT_VOICE, description="TTS voice for response"),
    response_format: str = Form(default="mp3", description="Audio format for response")
):
    """
    Full voice conversation flow:
    1. Transcribe incoming audio
    2. Send text to ARIA webhook
    3. Get ARIA response
    4. Synthesize response to audio
    5. Return audio file

    This endpoint combines transcription, ARIA processing, and synthesis
    into a single voice-to-voice interaction.
    """
    conversation_id = str(uuid.uuid4())[:8]

    # Read audio data
    audio_data = await audio.read()

    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    await log_to_event_bus(
        "voice_chat_start",
        details={
            "conversation_id": conversation_id,
            "user_id": user_id,
            "audio_size": len(audio_data)
        }
    )

    # Step 1: Transcribe incoming audio
    try:
        transcription = await transcribe_audio(audio_data, audio.filename or "audio.mp3")
        input_text = transcription["text"]
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    if not input_text.strip():
        raise HTTPException(status_code=400, detail="Could not transcribe any speech from audio")

    await log_to_event_bus(
        "voice_chat_transcribed",
        details={
            "conversation_id": conversation_id,
            "input_text": input_text[:100]  # Truncate for logging
        }
    )

    # Step 2 & 3: Send to ARIA and get response
    aria_result = await send_to_aria(input_text, user_id)
    aria_response = aria_result["response"]

    await log_to_event_bus(
        "voice_chat_aria_response",
        details={
            "conversation_id": conversation_id,
            "response_length": len(aria_response)
        }
    )

    # Step 4: Synthesize response to audio
    try:
        response_audio = await synthesize_speech(
            text=aria_response,
            voice=voice,
            response_format=response_format
        )
    except HTTPException as e:
        # If synthesis fails, return text response
        return {
            "conversation_id": conversation_id,
            "input_text": input_text,
            "aria_response": aria_response,
            "audio_url": None,
            "error": f"Speech synthesis failed: {e.detail}"
        }

    await log_to_event_bus(
        "voice_chat_complete",
        details={
            "conversation_id": conversation_id,
            "response_audio_size": len(response_audio)
        }
    )

    # Step 5: Return audio response
    content_types = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac"
    }
    content_type = content_types.get(response_format, "audio/mpeg")

    return Response(
        content=response_audio,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="response_{conversation_id}.{response_format}"',
            "X-Conversation-Id": conversation_id,
            "X-Input-Text": input_text[:200],  # Truncated input in header
            "X-Aria-Response-Length": str(len(aria_response))
        }
    )


@app.post("/voice/chat/json")
async def voice_chat_json(
    audio: UploadFile = File(..., description="Audio file with user's message"),
    user_id: str = Form(default="voice_user", description="User identifier"),
    voice: str = Form(default=DEFAULT_VOICE, description="TTS voice for response"),
    response_format: str = Form(default="mp3", description="Audio format for response")
):
    """
    Full voice conversation flow with JSON response.

    Same as /voice/chat but returns JSON with base64-encoded audio
    instead of raw audio file. Useful for web clients that need
    both text and audio.
    """
    import base64

    conversation_id = str(uuid.uuid4())[:8]

    # Read audio data
    audio_data = await audio.read()

    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Step 1: Transcribe
    transcription = await transcribe_audio(audio_data, audio.filename or "audio.mp3")
    input_text = transcription["text"]

    if not input_text.strip():
        raise HTTPException(status_code=400, detail="Could not transcribe any speech from audio")

    # Step 2 & 3: Send to ARIA
    aria_result = await send_to_aria(input_text, user_id)
    aria_response = aria_result["response"]

    # Step 4: Synthesize
    try:
        response_audio = await synthesize_speech(
            text=aria_response,
            voice=voice,
            response_format=response_format
        )
        audio_base64 = base64.b64encode(response_audio).decode("utf-8")
    except Exception as e:
        audio_base64 = None

    return {
        "conversation_id": conversation_id,
        "input_text": input_text,
        "aria_response": aria_response,
        "audio_base64": audio_base64,
        "audio_format": response_format if audio_base64 else None,
        "transcription_language": transcription.get("language"),
        "transcription_duration": transcription.get("duration_seconds")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8051)
