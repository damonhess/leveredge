#!/usr/bin/env python3
"""
FILE-PROCESSOR - File Processing Agent
Port: 8050

Processes various file types with cost tracking integration:
- PDF text extraction with page citations
- Image OCR and description
- Audio transcription (Whisper API)
- Video processing (audio extraction, transcription, key frames)
"""

import os
import sys
import io
import json
import uuid
import tempfile
import subprocess
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import httpx
import aiofiles
import pdfplumber
import pytesseract
from PIL import Image
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FILE-PROCESSOR")

# =============================================================================
# CONFIGURATION
# =============================================================================

AGENT_NAME = "FILE-PROCESSOR"
AGENT_PORT = 8050
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Supported formats
SUPPORTED_FORMATS = {
    "pdf": {
        "extensions": [".pdf"],
        "mime_types": ["application/pdf"],
        "description": "PDF documents - text extraction with page citations"
    },
    "image": {
        "extensions": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"],
        "mime_types": ["image/png", "image/jpeg", "image/gif", "image/bmp", "image/tiff", "image/webp"],
        "description": "Images - OCR text extraction and description"
    },
    "audio": {
        "extensions": [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"],
        "mime_types": ["audio/mpeg", "audio/wav", "audio/mp4", "audio/flac", "audio/ogg", "audio/webm"],
        "description": "Audio files - transcription via Whisper API"
    },
    "video": {
        "extensions": [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"],
        "mime_types": ["video/mp4", "video/avi", "video/quicktime", "video/x-matroska", "video/webm", "video/x-flv"],
        "description": "Video files - audio extraction, transcription, key frame extraction"
    }
}

# Processing costs (estimates per unit)
PROCESSING_COSTS = {
    "pdf_page": 0.001,      # per page
    "image_ocr": 0.002,     # per image
    "audio_minute": 0.006,  # per minute (Whisper API pricing)
    "video_minute": 0.008,  # per minute (includes audio + frame extraction)
    "frame_extraction": 0.0005  # per frame
}


# =============================================================================
# COST TRACKING
# =============================================================================

class FileCostTracker:
    """Cost tracker for file processing operations"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    async def log_processing(
        self,
        endpoint: str,
        file_type: str,
        file_size_bytes: int,
        processing_units: float,
        unit_type: str,
        cost: float,
        duration_seconds: float,
        metadata: Dict[str, Any] = None
    ) -> dict:
        """Log file processing to event bus"""

        log_entry = {
            "agent": self.agent_name,
            "endpoint": endpoint,
            "file_type": file_type,
            "file_size_bytes": file_size_bytes,
            "processing_units": processing_units,
            "unit_type": unit_type,
            "cost": round(cost, 6),
            "duration_seconds": round(duration_seconds, 3),
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        await self._publish_to_event_bus(log_entry)
        return log_entry

    async def _publish_to_event_bus(self, entry: dict) -> None:
        """Publish cost event to event bus"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{EVENT_BUS_URL}/publish",
                    json={
                        "event_type": "file_processing",
                        "source": self.agent_name,
                        "data": entry
                    },
                    timeout=5.0
                )
                logger.info(f"Cost logged: {entry['file_type']} - ${entry['cost']:.6f}")
        except Exception as e:
            logger.warning(f"Event bus publish failed: {e}")


cost_tracker = FileCostTracker(AGENT_NAME)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class PDFResult(BaseModel):
    """Result from PDF processing"""
    success: bool
    filename: str
    total_pages: int
    pages: List[Dict[str, Any]]
    full_text: str
    word_count: int
    processing_time_seconds: float
    cost: float


class ImageResult(BaseModel):
    """Result from image processing"""
    success: bool
    filename: str
    dimensions: Dict[str, int]
    ocr_text: str
    word_count: int
    description: Optional[str]
    processing_time_seconds: float
    cost: float


class AudioResult(BaseModel):
    """Result from audio processing"""
    success: bool
    filename: str
    duration_seconds: float
    transcript: str
    word_count: int
    language: Optional[str]
    processing_time_seconds: float
    cost: float


class VideoResult(BaseModel):
    """Result from video processing"""
    success: bool
    filename: str
    duration_seconds: float
    transcript: str
    word_count: int
    key_frames: List[Dict[str, Any]]
    frame_count: int
    processing_time_seconds: float
    cost: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    agent: str
    port: int
    version: str
    capabilities: List[str]
    dependencies: Dict[str, bool]
    timestamp: str


class SupportedFormatsResponse(BaseModel):
    """Supported formats response"""
    formats: Dict[str, Dict[str, Any]]
    total_extensions: int


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def check_ffmpeg() -> bool:
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def check_tesseract() -> bool:
    """Check if tesseract is available"""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def get_file_extension(filename: str) -> str:
    """Get lowercase file extension"""
    return Path(filename).suffix.lower()


async def save_upload_to_temp(file: UploadFile) -> str:
    """Save uploaded file to temporary location"""
    suffix = get_file_extension(file.filename)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        return tmp.name


async def cleanup_temp_file(filepath: str) -> None:
    """Remove temporary file"""
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {filepath}: {e}")


# =============================================================================
# PDF PROCESSING
# =============================================================================

async def process_pdf(file_path: str, filename: str) -> PDFResult:
    """Extract text from PDF with page citations"""
    start_time = datetime.now()
    pages_data = []
    full_text_parts = []

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)

            for i, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                tables = page.extract_tables() or []

                page_data = {
                    "page_number": i,
                    "text": page_text,
                    "word_count": len(page_text.split()) if page_text else 0,
                    "table_count": len(tables),
                    "citation": f"[Page {i}]"
                }

                # Add table data if present
                if tables:
                    page_data["tables"] = [
                        {
                            "table_index": j,
                            "rows": len(table),
                            "columns": len(table[0]) if table else 0,
                            "data": table
                        }
                        for j, table in enumerate(tables)
                    ]

                pages_data.append(page_data)
                if page_text:
                    full_text_parts.append(f"[Page {i}]\n{page_text}")

        full_text = "\n\n".join(full_text_parts)
        word_count = len(full_text.split())
        duration = (datetime.now() - start_time).total_seconds()
        cost = total_pages * PROCESSING_COSTS["pdf_page"]

        # Log cost
        await cost_tracker.log_processing(
            endpoint="/process/pdf",
            file_type="pdf",
            file_size_bytes=os.path.getsize(file_path),
            processing_units=total_pages,
            unit_type="pages",
            cost=cost,
            duration_seconds=duration,
            metadata={"filename": filename, "word_count": word_count}
        )

        return PDFResult(
            success=True,
            filename=filename,
            total_pages=total_pages,
            pages=pages_data,
            full_text=full_text,
            word_count=word_count,
            processing_time_seconds=duration,
            cost=cost
        )

    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")


# =============================================================================
# IMAGE PROCESSING
# =============================================================================

async def process_image(file_path: str, filename: str, include_description: bool = False) -> ImageResult:
    """OCR and optionally describe image"""
    start_time = datetime.now()

    try:
        # Open and process image
        with Image.open(file_path) as img:
            dimensions = {"width": img.width, "height": img.height}

            # Perform OCR
            ocr_text = pytesseract.image_to_string(img)
            word_count = len(ocr_text.split()) if ocr_text else 0

        # Description placeholder (could integrate with vision model)
        description = None
        if include_description:
            # Basic description from image properties
            description = f"Image: {dimensions['width']}x{dimensions['height']} pixels"

        duration = (datetime.now() - start_time).total_seconds()
        cost = PROCESSING_COSTS["image_ocr"]

        # Log cost
        await cost_tracker.log_processing(
            endpoint="/process/image",
            file_type="image",
            file_size_bytes=os.path.getsize(file_path),
            processing_units=1,
            unit_type="images",
            cost=cost,
            duration_seconds=duration,
            metadata={"filename": filename, "dimensions": dimensions, "ocr_words": word_count}
        )

        return ImageResult(
            success=True,
            filename=filename,
            dimensions=dimensions,
            ocr_text=ocr_text.strip(),
            word_count=word_count,
            description=description,
            processing_time_seconds=duration,
            cost=cost
        )

    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


# =============================================================================
# AUDIO PROCESSING
# =============================================================================

async def get_audio_duration(file_path: str) -> float:
    """Get audio duration using ffprobe"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


async def transcribe_audio_whisper(file_path: str) -> Dict[str, Any]:
    """Transcribe audio using OpenAI Whisper API"""
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY not configured for audio transcription"
        )

    try:
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as audio_file:
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    files={"file": (Path(file_path).name, audio_file, "audio/mpeg")},
                    data={"model": "whisper-1", "response_format": "verbose_json"},
                    timeout=300.0
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Whisper API error: {response.text}"
                )

            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Audio transcription timed out")
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")


async def process_audio(file_path: str, filename: str) -> AudioResult:
    """Transcribe audio file"""
    start_time = datetime.now()

    try:
        # Get duration
        duration_seconds = await get_audio_duration(file_path)
        duration_minutes = duration_seconds / 60.0

        # Transcribe
        whisper_result = await transcribe_audio_whisper(file_path)
        transcript = whisper_result.get("text", "")
        language = whisper_result.get("language")
        word_count = len(transcript.split()) if transcript else 0

        processing_duration = (datetime.now() - start_time).total_seconds()
        cost = duration_minutes * PROCESSING_COSTS["audio_minute"]

        # Log cost
        await cost_tracker.log_processing(
            endpoint="/process/audio",
            file_type="audio",
            file_size_bytes=os.path.getsize(file_path),
            processing_units=duration_minutes,
            unit_type="minutes",
            cost=cost,
            duration_seconds=processing_duration,
            metadata={"filename": filename, "language": language, "audio_duration": duration_seconds}
        )

        return AudioResult(
            success=True,
            filename=filename,
            duration_seconds=duration_seconds,
            transcript=transcript,
            word_count=word_count,
            language=language,
            processing_time_seconds=processing_duration,
            cost=cost
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")


# =============================================================================
# VIDEO PROCESSING
# =============================================================================

async def extract_audio_from_video(video_path: str) -> str:
    """Extract audio track from video using ffmpeg"""
    audio_path = video_path + ".audio.mp3"

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", video_path,
                "-vn", "-acodec", "libmp3lame", "-q:a", "4",
                audio_path
            ],
            capture_output=True,
            timeout=600
        )

        if result.returncode != 0:
            raise Exception(f"ffmpeg audio extraction failed: {result.stderr.decode()}")

        return audio_path

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Audio extraction timed out")
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {str(e)}")


async def extract_key_frames(video_path: str, interval_seconds: int = 30, max_frames: int = 10) -> List[Dict[str, Any]]:
    """Extract key frames from video at regular intervals"""
    frames = []
    temp_dir = tempfile.mkdtemp()

    try:
        # Get video duration
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        duration = float(result.stdout.strip())

        # Calculate frame timestamps
        timestamps = []
        current = 0
        while current < duration and len(timestamps) < max_frames:
            timestamps.append(current)
            current += interval_seconds

        # Extract frames
        for i, ts in enumerate(timestamps):
            frame_path = os.path.join(temp_dir, f"frame_{i:04d}.jpg")

            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", str(ts),
                    "-i", video_path,
                    "-vframes", "1", "-q:v", "2",
                    frame_path
                ],
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0 and os.path.exists(frame_path):
                # Get frame dimensions
                with Image.open(frame_path) as img:
                    dimensions = {"width": img.width, "height": img.height}

                    # OCR on frame
                    ocr_text = pytesseract.image_to_string(img).strip()

                frames.append({
                    "frame_index": i,
                    "timestamp_seconds": ts,
                    "timestamp_formatted": f"{int(ts // 60):02d}:{int(ts % 60):02d}",
                    "dimensions": dimensions,
                    "ocr_text": ocr_text if ocr_text else None
                })

                # Cleanup frame file
                os.unlink(frame_path)

    except Exception as e:
        logger.warning(f"Frame extraction error: {e}")
    finally:
        # Cleanup temp directory
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass

    return frames


async def get_video_duration(file_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


async def process_video(
    file_path: str,
    filename: str,
    extract_frames: bool = True,
    frame_interval: int = 30,
    max_frames: int = 10
) -> VideoResult:
    """Process video: extract audio, transcribe, get key frames"""
    start_time = datetime.now()
    audio_path = None

    try:
        # Get video duration
        duration_seconds = await get_video_duration(file_path)
        duration_minutes = duration_seconds / 60.0

        # Extract audio
        audio_path = await extract_audio_from_video(file_path)

        # Transcribe audio
        whisper_result = await transcribe_audio_whisper(audio_path)
        transcript = whisper_result.get("text", "")
        word_count = len(transcript.split()) if transcript else 0

        # Extract key frames
        key_frames = []
        if extract_frames:
            key_frames = await extract_key_frames(
                file_path,
                interval_seconds=frame_interval,
                max_frames=max_frames
            )

        processing_duration = (datetime.now() - start_time).total_seconds()

        # Calculate cost
        cost = duration_minutes * PROCESSING_COSTS["video_minute"]
        cost += len(key_frames) * PROCESSING_COSTS["frame_extraction"]

        # Log cost
        await cost_tracker.log_processing(
            endpoint="/process/video",
            file_type="video",
            file_size_bytes=os.path.getsize(file_path),
            processing_units=duration_minutes,
            unit_type="minutes",
            cost=cost,
            duration_seconds=processing_duration,
            metadata={
                "filename": filename,
                "video_duration": duration_seconds,
                "frames_extracted": len(key_frames)
            }
        )

        return VideoResult(
            success=True,
            filename=filename,
            duration_seconds=duration_seconds,
            transcript=transcript,
            word_count=word_count,
            key_frames=key_frames,
            frame_count=len(key_frames),
            processing_time_seconds=processing_duration,
            cost=cost
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")
    finally:
        # Cleanup extracted audio
        if audio_path:
            await cleanup_temp_file(audio_path)


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info(f"Starting {AGENT_NAME} on port {AGENT_PORT}")
    logger.info(f"FFmpeg available: {check_ffmpeg()}")
    logger.info(f"Tesseract available: {check_tesseract()}")
    logger.info(f"Whisper API configured: {bool(OPENAI_API_KEY)}")
    yield
    logger.info(f"Shutting down {AGENT_NAME}")


app = FastAPI(
    title="FILE-PROCESSOR",
    description="File Processing Agent - PDF, Image, Audio, Video processing with cost tracking",
    version="1.0.0",
    lifespan=lifespan
)


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        agent=AGENT_NAME,
        port=AGENT_PORT,
        version="1.0.0",
        capabilities=["pdf", "image", "audio", "video"],
        dependencies={
            "ffmpeg": check_ffmpeg(),
            "tesseract": check_tesseract(),
            "whisper_api": bool(OPENAI_API_KEY)
        },
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """List all supported file formats"""
    total_extensions = sum(
        len(fmt["extensions"]) for fmt in SUPPORTED_FORMATS.values()
    )
    return SupportedFormatsResponse(
        formats=SUPPORTED_FORMATS,
        total_extensions=total_extensions
    )


@app.post("/process/pdf", response_model=PDFResult)
async def process_pdf_endpoint(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Extract text from PDF with page citations.

    Returns text content organized by page with citation markers.
    Also extracts tables if present.
    """
    # Validate file type
    extension = get_file_extension(file.filename)
    if extension not in SUPPORTED_FORMATS["pdf"]["extensions"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected PDF, got: {extension}"
        )

    temp_path = await save_upload_to_temp(file)

    try:
        result = await process_pdf(temp_path, file.filename)
        return result
    finally:
        if background_tasks:
            background_tasks.add_task(cleanup_temp_file, temp_path)
        else:
            await cleanup_temp_file(temp_path)


@app.post("/process/image", response_model=ImageResult)
async def process_image_endpoint(
    file: UploadFile = File(...),
    include_description: bool = Form(default=False),
    background_tasks: BackgroundTasks = None
):
    """
    Perform OCR on image and optionally generate description.

    Returns extracted text and image metadata.
    """
    # Validate file type
    extension = get_file_extension(file.filename)
    if extension not in SUPPORTED_FORMATS["image"]["extensions"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected image, got: {extension}"
        )

    if not check_tesseract():
        raise HTTPException(
            status_code=503,
            detail="Tesseract OCR not available on this system"
        )

    temp_path = await save_upload_to_temp(file)

    try:
        result = await process_image(temp_path, file.filename, include_description)
        return result
    finally:
        if background_tasks:
            background_tasks.add_task(cleanup_temp_file, temp_path)
        else:
            await cleanup_temp_file(temp_path)


@app.post("/process/audio", response_model=AudioResult)
async def process_audio_endpoint(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Transcribe audio file using Whisper API.

    Returns full transcript with language detection.
    Requires OPENAI_API_KEY environment variable.
    """
    # Validate file type
    extension = get_file_extension(file.filename)
    if extension not in SUPPORTED_FORMATS["audio"]["extensions"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected audio, got: {extension}"
        )

    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY not configured for audio transcription"
        )

    temp_path = await save_upload_to_temp(file)

    try:
        result = await process_audio(temp_path, file.filename)
        return result
    finally:
        if background_tasks:
            background_tasks.add_task(cleanup_temp_file, temp_path)
        else:
            await cleanup_temp_file(temp_path)


@app.post("/process/video", response_model=VideoResult)
async def process_video_endpoint(
    file: UploadFile = File(...),
    extract_frames: bool = Form(default=True),
    frame_interval: int = Form(default=30),
    max_frames: int = Form(default=10),
    background_tasks: BackgroundTasks = None
):
    """
    Process video file: extract audio, transcribe, and get key frames.

    - Extracts audio track and transcribes using Whisper API
    - Optionally extracts key frames at specified intervals
    - Performs OCR on extracted frames

    Parameters:
    - extract_frames: Whether to extract key frames (default: True)
    - frame_interval: Seconds between frame captures (default: 30)
    - max_frames: Maximum number of frames to extract (default: 10)
    """
    # Validate file type
    extension = get_file_extension(file.filename)
    if extension not in SUPPORTED_FORMATS["video"]["extensions"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected video, got: {extension}"
        )

    if not check_ffmpeg():
        raise HTTPException(
            status_code=503,
            detail="FFmpeg not available on this system"
        )

    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY not configured for audio transcription"
        )

    temp_path = await save_upload_to_temp(file)

    try:
        result = await process_video(
            temp_path,
            file.filename,
            extract_frames=extract_frames,
            frame_interval=frame_interval,
            max_frames=max_frames
        )
        return result
    finally:
        if background_tasks:
            background_tasks.add_task(cleanup_temp_file, temp_path)
        else:
            await cleanup_temp_file(temp_path)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "agent": AGENT_NAME
        }
    )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
