#!/usr/bin/env python3
"""
ERATO - Media Producer Agent
Port: 8033

Creative powerhouse of LeverEdge. AI image generation, video production, audio synthesis.
Interfaces with external APIs for high-quality media generation.

CAPABILITIES:
- AI image generation (DALL-E 3)
- Image post-processing (Pillow)
- Video assembly and editing (FFmpeg)
- Avatar video generation (Synthesia, HeyGen)
- Voice generation (ElevenLabs)
- Audio processing
- Thumbnail creation
- Stock footage sourcing (Pexels, Pixabay)

EXTERNAL APIS (via AEGIS):
- OpenAI (DALL-E 3)
- ElevenLabs (voice)
- Synthesia (avatars)
- HeyGen (avatars)
- Pexels (free stock)
- Pixabay (free stock)
"""

import os
import sys
import json
import uuid
import httpx
import asyncio
import subprocess
import tempfile
import shutil
from datetime import datetime, date
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from enum import Enum

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

# Image processing
try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[ERATO] Warning: Pillow not available, image processing limited")

# OpenAI for DALL-E
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[ERATO] Warning: OpenAI SDK not available")

app = FastAPI(
    title="ERATO",
    description="Media Producer Agent - Image, Video, and Audio Generation",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# API Keys (managed by AEGIS)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
SYNTHESIA_API_KEY = os.getenv("SYNTHESIA_API_KEY")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# Internal services
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Agent endpoints
AGENT_ENDPOINTS = {
    "AEGIS": "http://aegis:8012",
    "HERMES": "http://hermes:8014",
    "HEPHAESTUS": "http://hephaestus:8011",
    "EVENT_BUS": EVENT_BUS_URL
}

# Media storage paths
MEDIA_BASE_PATH = Path(os.getenv("MEDIA_PATH", "/opt/leveredge/media"))
MEDIA_BASE_PATH.mkdir(parents=True, exist_ok=True)
(MEDIA_BASE_PATH / "images").mkdir(exist_ok=True)
(MEDIA_BASE_PATH / "videos").mkdir(exist_ok=True)
(MEDIA_BASE_PATH / "audio").mkdir(exist_ok=True)
(MEDIA_BASE_PATH / "thumbnails").mkdir(exist_ok=True)

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize cost tracker
cost_tracker = CostTracker("ERATO")

# Initialize OpenAI client if available
openai_client = None
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# =============================================================================
# PRICING / COST TRACKING
# =============================================================================

MEDIA_COSTS = {
    # DALL-E 3 pricing
    "dalle3_standard_1024": 0.040,
    "dalle3_standard_1792": 0.080,
    "dalle3_hd_1024": 0.080,
    "dalle3_hd_1792": 0.120,
    # ElevenLabs pricing (per 1K characters)
    "elevenlabs_standard": 0.30,
    "elevenlabs_professional": 0.50,
    # Synthesia pricing (per minute)
    "synthesia_personal": 1.50,
    "synthesia_studio": 2.50,
    # HeyGen pricing (per minute)
    "heygen_creator": 1.00,
    "heygen_business": 2.00,
    # Stock footage (estimates)
    "pexels": 0.00,  # Free
    "pixabay": 0.00,  # Free
}

# =============================================================================
# ENUMS & MODELS
# =============================================================================

class VideoStyle(str, Enum):
    AVATAR = "avatar"
    MOTION_GRAPHICS = "motion_graphics"
    SLIDESHOW = "slideshow"
    STOCK_FOOTAGE = "stock_footage"

class ImageSize(str, Enum):
    SMALL = "1024x1024"
    WIDE = "1792x1024"
    TALL = "1024x1792"

class ImageQuality(str, Enum):
    STANDARD = "standard"
    HD = "hd"

class AvatarProvider(str, Enum):
    SYNTHESIA = "synthesia"
    HEYGEN = "heygen"

class VoiceProvider(str, Enum):
    ELEVENLABS = "elevenlabs"

class StockType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"

class ImageOperation(str, Enum):
    RESIZE = "resize"
    CROP = "crop"
    BLUR = "blur"
    SHARPEN = "sharpen"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    GRAYSCALE = "grayscale"
    WATERMARK = "watermark"
    OVERLAY_TEXT = "overlay_text"

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

# Image Models
class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., description="The prompt for image generation")
    style: Optional[str] = Field(None, description="Style modifier for the image")
    size: ImageSize = Field(ImageSize.SMALL, description="Image dimensions")
    n: int = Field(1, ge=1, le=4, description="Number of images to generate")
    quality: ImageQuality = Field(ImageQuality.STANDARD, description="Image quality")
    brand_colors: Optional[List[str]] = Field(None, description="Brand colors to incorporate")

class ImageGenerateResponse(BaseModel):
    images: List[str]
    generation_id: str
    prompt_used: str
    cost: float
    timestamp: str

class ImageOperationSpec(BaseModel):
    operation: ImageOperation
    params: Dict[str, Any] = {}

class ImageProcessRequest(BaseModel):
    image_path: str
    operations: List[ImageOperationSpec]

class ImageProcessResponse(BaseModel):
    processed_path: str
    operations_applied: List[str]
    original_size: tuple
    final_size: tuple

# Video Models
class VoiceConfig(BaseModel):
    voice_id: str
    provider: VoiceProvider = VoiceProvider.ELEVENLABS
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-20.0, le=20.0)

class AvatarConfig(BaseModel):
    avatar_id: str
    provider: AvatarProvider = AvatarProvider.SYNTHESIA
    background: Optional[str] = "office"
    custom_background_url: Optional[str] = None

class MusicConfig(BaseModel):
    source: str  # "stock", "url", "path"
    query: Optional[str] = None
    url: Optional[str] = None
    path: Optional[str] = None
    volume: float = Field(0.3, ge=0.0, le=1.0)

class VideoGenerateRequest(BaseModel):
    script: str
    style: VideoStyle
    duration_target: Optional[float] = None
    voice_config: Optional[VoiceConfig] = None
    avatar_config: Optional[AvatarConfig] = None
    music: Optional[MusicConfig] = None

class CostBreakdown(BaseModel):
    voice: float = 0.0
    avatar: float = 0.0
    stock: float = 0.0
    processing: float = 0.0
    total: float = 0.0

class VideoGenerateResponse(BaseModel):
    video_path: str
    thumbnail_path: str
    duration: float
    render_time: float
    cost_breakdown: CostBreakdown

class AvatarGenerateRequest(BaseModel):
    script: str
    avatar_id: str
    provider: AvatarProvider = AvatarProvider.SYNTHESIA
    background: Optional[str] = "office"
    custom_background_url: Optional[str] = None

class AvatarGenerateResponse(BaseModel):
    video_path: str
    duration: float
    render_time: float
    cost: float

class VoiceoverGenerateRequest(BaseModel):
    text: str
    voice_id: str
    provider: VoiceProvider = VoiceProvider.ELEVENLABS
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-20.0, le=20.0)

class VoiceoverGenerateResponse(BaseModel):
    audio_path: str
    duration: float
    characters_used: int
    cost: float

class SceneSpec(BaseModel):
    type: Literal["image", "video", "text"]
    source: str  # path or text content
    duration: Optional[float] = 3.0
    transition: Optional[str] = "fade"
    text_overlay: Optional[str] = None
    voiceover_path: Optional[str] = None

class VideoAssembleRequest(BaseModel):
    scenes: List[SceneSpec]
    output_format: str = "mp4"
    resolution: str = "1920x1080"
    background_music: Optional[MusicConfig] = None

class VideoAssembleResponse(BaseModel):
    video_path: str
    duration: float
    file_size: int
    scenes_count: int

class StockSourceRequest(BaseModel):
    query: str
    type: StockType = StockType.PHOTO
    count: int = Field(10, ge=1, le=50)
    orientation: Optional[Literal["landscape", "portrait", "square"]] = None

class StockAsset(BaseModel):
    id: str
    url: str
    preview_url: str
    source: str
    photographer: Optional[str] = None
    duration: Optional[float] = None
    width: int
    height: int

class StockSourceResponse(BaseModel):
    assets: List[StockAsset]
    source: str
    query: str
    total_results: int

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_to_launch": days_to_launch,
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch"
    }

# =============================================================================
# EVENT BUS COMMUNICATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "ERATO",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[ERATO] Event bus notification failed: {e}")

async def log_media_cost(
    operation: str,
    cost: float,
    details: dict = None
):
    """Log media generation cost"""
    try:
        await cost_tracker.log_usage(
            endpoint=operation,
            model="media_generation",
            input_tokens=0,
            output_tokens=0,
            other_features={"media_cost": cost},
            metadata=details or {}
        )
    except Exception as e:
        print(f"[ERATO] Cost logging failed: {e}")

# =============================================================================
# IMAGE GENERATION (DALL-E 3)
# =============================================================================

async def generate_dalle3_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    style: Optional[str] = None,
    brand_colors: Optional[List[str]] = None,
    n: int = 1
) -> tuple[List[str], float]:
    """Generate images using DALL-E 3"""
    if not openai_client:
        raise HTTPException(status_code=503, detail="OpenAI client not configured")

    # Build enhanced prompt
    enhanced_prompt = prompt
    if style:
        enhanced_prompt = f"{style} style: {enhanced_prompt}"
    if brand_colors:
        color_str = ", ".join(brand_colors)
        enhanced_prompt = f"{enhanced_prompt}. Use these brand colors: {color_str}"

    # Calculate cost
    cost_key = f"dalle3_{quality}_{size.split('x')[0]}"
    unit_cost = MEDIA_COSTS.get(cost_key, MEDIA_COSTS["dalle3_standard_1024"])

    images = []
    total_cost = 0.0

    # DALL-E 3 only supports n=1, so we loop
    for _ in range(n):
        try:
            response = await openai_client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality=quality,
                n=1
            )

            # Download and save image
            image_url = response.data[0].url
            image_id = str(uuid.uuid4())[:8]
            image_filename = f"{image_id}.png"
            image_path = MEDIA_BASE_PATH / "images" / image_filename

            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url, timeout=60.0)
                with open(image_path, "wb") as f:
                    f.write(img_response.content)

            images.append(str(image_path))
            total_cost += unit_cost

        except Exception as e:
            print(f"[ERATO] DALL-E generation error: {e}")
            raise HTTPException(status_code=500, detail=f"Image generation failed: {e}")

    return images, total_cost

# =============================================================================
# IMAGE PROCESSING (Pillow)
# =============================================================================

def process_image_operations(
    image_path: str,
    operations: List[ImageOperationSpec]
) -> tuple[str, List[str], tuple, tuple]:
    """Apply operations to an image using Pillow"""
    if not PIL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Image processing not available")

    img = Image.open(image_path)
    original_size = img.size
    applied_ops = []

    for op_spec in operations:
        op = op_spec.operation
        params = op_spec.params

        if op == ImageOperation.RESIZE:
            width = params.get("width", img.width)
            height = params.get("height", img.height)
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            applied_ops.append(f"resize({width}x{height})")

        elif op == ImageOperation.CROP:
            left = params.get("left", 0)
            top = params.get("top", 0)
            right = params.get("right", img.width)
            bottom = params.get("bottom", img.height)
            img = img.crop((left, top, right, bottom))
            applied_ops.append(f"crop({left},{top},{right},{bottom})")

        elif op == ImageOperation.BLUR:
            radius = params.get("radius", 2)
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))
            applied_ops.append(f"blur({radius})")

        elif op == ImageOperation.SHARPEN:
            factor = params.get("factor", 1.5)
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(factor)
            applied_ops.append(f"sharpen({factor})")

        elif op == ImageOperation.BRIGHTNESS:
            factor = params.get("factor", 1.0)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(factor)
            applied_ops.append(f"brightness({factor})")

        elif op == ImageOperation.CONTRAST:
            factor = params.get("factor", 1.0)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(factor)
            applied_ops.append(f"contrast({factor})")

        elif op == ImageOperation.GRAYSCALE:
            img = img.convert("L").convert("RGB")
            applied_ops.append("grayscale")

        elif op == ImageOperation.WATERMARK:
            text = params.get("text", "LeverEdge")
            position = params.get("position", "bottom-right")
            opacity = params.get("opacity", 0.5)
            # Simple text watermark
            draw = ImageDraw.Draw(img)
            # Calculate position
            text_bbox = draw.textbbox((0, 0), text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            if position == "bottom-right":
                x = img.width - text_width - 10
                y = img.height - text_height - 10
            elif position == "bottom-left":
                x = 10
                y = img.height - text_height - 10
            elif position == "top-right":
                x = img.width - text_width - 10
                y = 10
            else:  # top-left
                x = 10
                y = 10

            # Draw with semi-transparency (simplified)
            draw.text((x, y), text, fill=(255, 255, 255, int(255 * opacity)))
            applied_ops.append(f"watermark({text})")

        elif op == ImageOperation.OVERLAY_TEXT:
            text = params.get("text", "")
            position = params.get("position", "center")
            font_size = params.get("font_size", 24)
            color = params.get("color", "white")
            draw = ImageDraw.Draw(img)
            # Use default font (customize as needed)
            text_bbox = draw.textbbox((0, 0), text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            if position == "center":
                x = (img.width - text_width) // 2
                y = (img.height - text_height) // 2
            else:
                x, y = 10, 10

            draw.text((x, y), text, fill=color)
            applied_ops.append(f"overlay_text({text[:20]}...)")

    # Save processed image
    output_id = str(uuid.uuid4())[:8]
    output_path = MEDIA_BASE_PATH / "images" / f"processed_{output_id}.png"
    img.save(output_path, "PNG")

    return str(output_path), applied_ops, original_size, img.size

# =============================================================================
# VOICE GENERATION (ElevenLabs)
# =============================================================================

async def generate_elevenlabs_voice(
    text: str,
    voice_id: str,
    speed: float = 1.0,
    pitch: float = 0.0
) -> tuple[str, float, int, float]:
    """Generate voiceover using ElevenLabs API"""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=503, detail="ElevenLabs API key not configured")

    char_count = len(text)
    cost = (char_count / 1000) * MEDIA_COSTS["elevenlabs_standard"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True
                    }
                },
                timeout=120.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ElevenLabs API error: {response.text}"
                )

            # Save audio file
            audio_id = str(uuid.uuid4())[:8]
            audio_path = MEDIA_BASE_PATH / "audio" / f"voice_{audio_id}.mp3"

            with open(audio_path, "wb") as f:
                f.write(response.content)

            # Estimate duration (roughly 150 words per minute)
            word_count = len(text.split())
            duration = (word_count / 150) * 60 / speed

            return str(audio_path), duration, char_count, cost

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"ElevenLabs API request failed: {e}")

# =============================================================================
# AVATAR VIDEO GENERATION
# =============================================================================

async def generate_synthesia_avatar(
    script: str,
    avatar_id: str,
    background: str = "office",
    custom_background_url: Optional[str] = None
) -> tuple[str, float, float, float]:
    """Generate avatar video using Synthesia API"""
    if not SYNTHESIA_API_KEY:
        raise HTTPException(status_code=503, detail="Synthesia API key not configured")

    start_time = datetime.now()

    try:
        async with httpx.AsyncClient() as client:
            # Create video request
            payload = {
                "test": True,  # Set to False for production
                "input": [
                    {
                        "avatar": avatar_id,
                        "background": custom_background_url or background,
                        "scriptText": script
                    }
                ],
                "title": f"LeverEdge Video {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }

            response = await client.post(
                "https://api.synthesia.io/v2/videos",
                headers={
                    "Authorization": SYNTHESIA_API_KEY,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )

            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Synthesia API error: {response.text}"
                )

            video_data = response.json()
            video_id = video_data.get("id")

            # Poll for completion (simplified - in production use webhooks)
            video_url = None
            for _ in range(60):  # Max 5 minutes polling
                await asyncio.sleep(5)
                status_response = await client.get(
                    f"https://api.synthesia.io/v2/videos/{video_id}",
                    headers={"Authorization": SYNTHESIA_API_KEY},
                    timeout=30.0
                )
                status_data = status_response.json()
                if status_data.get("status") == "complete":
                    video_url = status_data.get("download")
                    break

            if not video_url:
                raise HTTPException(status_code=408, detail="Video generation timed out")

            # Download video
            video_response = await client.get(video_url, timeout=300.0)
            video_filename = f"avatar_{uuid.uuid4().hex[:8]}.mp4"
            video_path = MEDIA_BASE_PATH / "videos" / video_filename

            with open(video_path, "wb") as f:
                f.write(video_response.content)

            # Estimate duration from script (roughly 150 wpm)
            word_count = len(script.split())
            duration = (word_count / 150) * 60

            # Calculate cost
            cost = (duration / 60) * MEDIA_COSTS["synthesia_personal"]

            render_time = (datetime.now() - start_time).total_seconds()

            return str(video_path), duration, render_time, cost

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Synthesia API request failed: {e}")

async def generate_heygen_avatar(
    script: str,
    avatar_id: str,
    background: str = "office",
    custom_background_url: Optional[str] = None
) -> tuple[str, float, float, float]:
    """Generate avatar video using HeyGen API"""
    if not HEYGEN_API_KEY:
        raise HTTPException(status_code=503, detail="HeyGen API key not configured")

    start_time = datetime.now()

    try:
        async with httpx.AsyncClient() as client:
            # Create video request
            payload = {
                "video_inputs": [
                    {
                        "character": {
                            "type": "avatar",
                            "avatar_id": avatar_id
                        },
                        "voice": {
                            "type": "text",
                            "input_text": script
                        },
                        "background": {
                            "type": "color" if not custom_background_url else "image",
                            "value": custom_background_url or "#ffffff"
                        }
                    }
                ],
                "dimension": {
                    "width": 1920,
                    "height": 1080
                }
            }

            response = await client.post(
                "https://api.heygen.com/v2/video/generate",
                headers={
                    "X-Api-Key": HEYGEN_API_KEY,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )

            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"HeyGen API error: {response.text}"
                )

            video_data = response.json()
            video_id = video_data.get("data", {}).get("video_id")

            # Poll for completion
            video_url = None
            for _ in range(60):
                await asyncio.sleep(5)
                status_response = await client.get(
                    f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
                    headers={"X-Api-Key": HEYGEN_API_KEY},
                    timeout=30.0
                )
                status_data = status_response.json()
                if status_data.get("data", {}).get("status") == "completed":
                    video_url = status_data.get("data", {}).get("video_url")
                    break

            if not video_url:
                raise HTTPException(status_code=408, detail="Video generation timed out")

            # Download video
            video_response = await client.get(video_url, timeout=300.0)
            video_filename = f"heygen_{uuid.uuid4().hex[:8]}.mp4"
            video_path = MEDIA_BASE_PATH / "videos" / video_filename

            with open(video_path, "wb") as f:
                f.write(video_response.content)

            # Estimate duration
            word_count = len(script.split())
            duration = (word_count / 150) * 60

            # Calculate cost
            cost = (duration / 60) * MEDIA_COSTS["heygen_creator"]

            render_time = (datetime.now() - start_time).total_seconds()

            return str(video_path), duration, render_time, cost

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"HeyGen API request failed: {e}")

# =============================================================================
# STOCK FOOTAGE SOURCING
# =============================================================================

async def search_pexels(
    query: str,
    media_type: StockType,
    count: int = 10,
    orientation: Optional[str] = None
) -> List[StockAsset]:
    """Search Pexels for stock photos/videos"""
    if not PEXELS_API_KEY:
        raise HTTPException(status_code=503, detail="Pexels API key not configured")

    try:
        async with httpx.AsyncClient() as client:
            if media_type == StockType.PHOTO:
                url = "https://api.pexels.com/v1/search"
            else:
                url = "https://api.pexels.com/videos/search"

            params = {
                "query": query,
                "per_page": count
            }
            if orientation:
                params["orientation"] = orientation

            response = await client.get(
                url,
                headers={"Authorization": PEXELS_API_KEY},
                params=params,
                timeout=30.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Pexels API error: {response.text}"
                )

            data = response.json()
            assets = []

            if media_type == StockType.PHOTO:
                for photo in data.get("photos", []):
                    assets.append(StockAsset(
                        id=str(photo["id"]),
                        url=photo["src"]["original"],
                        preview_url=photo["src"]["medium"],
                        source="pexels",
                        photographer=photo.get("photographer"),
                        width=photo["width"],
                        height=photo["height"]
                    ))
            else:
                for video in data.get("videos", []):
                    # Get the best quality video file
                    video_files = video.get("video_files", [])
                    best_file = max(video_files, key=lambda x: x.get("width", 0)) if video_files else {}
                    assets.append(StockAsset(
                        id=str(video["id"]),
                        url=best_file.get("link", ""),
                        preview_url=video.get("image", ""),
                        source="pexels",
                        photographer=video.get("user", {}).get("name"),
                        duration=video.get("duration"),
                        width=best_file.get("width", 0),
                        height=best_file.get("height", 0)
                    ))

            return assets

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Pexels API request failed: {e}")

async def search_pixabay(
    query: str,
    media_type: StockType,
    count: int = 10,
    orientation: Optional[str] = None
) -> List[StockAsset]:
    """Search Pixabay for stock photos/videos"""
    if not PIXABAY_API_KEY:
        raise HTTPException(status_code=503, detail="Pixabay API key not configured")

    try:
        async with httpx.AsyncClient() as client:
            if media_type == StockType.PHOTO:
                url = "https://pixabay.com/api/"
            else:
                url = "https://pixabay.com/api/videos/"

            params = {
                "key": PIXABAY_API_KEY,
                "q": query,
                "per_page": count
            }
            if orientation:
                params["orientation"] = orientation

            response = await client.get(url, params=params, timeout=30.0)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Pixabay API error: {response.text}"
                )

            data = response.json()
            assets = []

            for hit in data.get("hits", []):
                if media_type == StockType.PHOTO:
                    assets.append(StockAsset(
                        id=str(hit["id"]),
                        url=hit["largeImageURL"],
                        preview_url=hit["previewURL"],
                        source="pixabay",
                        photographer=hit.get("user"),
                        width=hit["imageWidth"],
                        height=hit["imageHeight"]
                    ))
                else:
                    videos = hit.get("videos", {})
                    large = videos.get("large", {})
                    assets.append(StockAsset(
                        id=str(hit["id"]),
                        url=large.get("url", ""),
                        preview_url=hit.get("picture_id", ""),
                        source="pixabay",
                        photographer=hit.get("user"),
                        duration=hit.get("duration"),
                        width=large.get("width", 0),
                        height=large.get("height", 0)
                    ))

            return assets

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Pixabay API request failed: {e}")

# =============================================================================
# VIDEO ASSEMBLY (FFmpeg)
# =============================================================================

def check_ffmpeg_available() -> bool:
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

async def assemble_video_with_ffmpeg(
    scenes: List[SceneSpec],
    output_format: str = "mp4",
    resolution: str = "1920x1080",
    background_music: Optional[MusicConfig] = None
) -> tuple[str, float, int]:
    """Assemble video from scenes using FFmpeg"""
    if not check_ffmpeg_available():
        raise HTTPException(status_code=503, detail="FFmpeg not available")

    width, height = map(int, resolution.split("x"))
    temp_dir = tempfile.mkdtemp()

    try:
        # Create concat file for FFmpeg
        concat_file_path = os.path.join(temp_dir, "concat.txt")
        intermediate_clips = []
        total_duration = 0.0

        for i, scene in enumerate(scenes):
            clip_path = os.path.join(temp_dir, f"clip_{i}.{output_format}")

            if scene.type == "image":
                # Convert image to video clip
                duration = scene.duration or 3.0
                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", scene.source,
                    "-c:v", "libx264",
                    "-t", str(duration),
                    "-pix_fmt", "yuv420p",
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    clip_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                total_duration += duration

            elif scene.type == "video":
                # Process video clip
                duration = scene.duration
                cmd = [
                    "ffmpeg", "-y",
                    "-i", scene.source,
                    "-c:v", "libx264",
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
                ]
                if duration:
                    cmd.extend(["-t", str(duration)])
                cmd.append(clip_path)
                subprocess.run(cmd, capture_output=True, check=True)

                # Get actual duration if not specified
                if not duration:
                    probe_result = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", scene.source],
                        capture_output=True, text=True
                    )
                    duration = float(probe_result.stdout.strip() or "0")
                total_duration += duration

            elif scene.type == "text":
                # Create text clip (black background with text)
                duration = scene.duration or 3.0
                text = scene.source.replace("'", "\\'")
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=black:s={width}x{height}:d={duration}",
                    "-vf", f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    clip_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                total_duration += duration

            # Add voiceover if specified
            if scene.voiceover_path:
                with_audio_path = os.path.join(temp_dir, f"clip_{i}_audio.{output_format}")
                cmd = [
                    "ffmpeg", "-y",
                    "-i", clip_path,
                    "-i", scene.voiceover_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-shortest",
                    with_audio_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                clip_path = with_audio_path

            intermediate_clips.append(clip_path)

            # Add to concat file
            with open(concat_file_path, "a") as f:
                f.write(f"file '{clip_path}'\n")

        # Concatenate all clips
        output_id = str(uuid.uuid4())[:8]
        output_path = MEDIA_BASE_PATH / "videos" / f"assembled_{output_id}.{output_format}"

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file_path,
            "-c", "copy",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        # Add background music if specified
        if background_music and background_music.path:
            with_music_path = MEDIA_BASE_PATH / "videos" / f"assembled_{output_id}_music.{output_format}"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(output_path),
                "-i", background_music.path,
                "-filter_complex",
                f"[1:a]volume={background_music.volume}[bg];[0:a][bg]amix=inputs=2:duration=first",
                "-c:v", "copy",
                str(with_music_path)
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                os.replace(with_music_path, output_path)

        # Get file size
        file_size = os.path.getsize(output_path)

        return str(output_path), total_duration, file_size

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

# =============================================================================
# THUMBNAIL GENERATION
# =============================================================================

async def create_thumbnail(
    video_path: str,
    timestamp: float = 0.5,
    size: tuple = (1280, 720)
) -> str:
    """Extract a frame from video as thumbnail"""
    if not check_ffmpeg_available():
        raise HTTPException(status_code=503, detail="FFmpeg not available")

    thumb_id = str(uuid.uuid4())[:8]
    thumb_path = MEDIA_BASE_PATH / "thumbnails" / f"thumb_{thumb_id}.jpg"

    # Get video duration first
    probe_result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    duration = float(probe_result.stdout.strip() or "1")

    # Calculate actual timestamp
    actual_timestamp = min(timestamp * duration, duration - 0.1)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(actual_timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-vf", f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=decrease,pad={size[0]}:{size[1]}:(ow-iw)/2:(oh-ih)/2",
        "-q:v", "2",
        str(thumb_path)
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Thumbnail generation failed: {result.stderr.decode()}")

    return str(thumb_path)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    time_ctx = get_time_context()

    # Check service availability
    services = {
        "openai_dalle": bool(openai_client),
        "elevenlabs": bool(ELEVENLABS_API_KEY),
        "synthesia": bool(SYNTHESIA_API_KEY),
        "heygen": bool(HEYGEN_API_KEY),
        "pexels": bool(PEXELS_API_KEY),
        "pixabay": bool(PIXABAY_API_KEY),
        "ffmpeg": check_ffmpeg_available(),
        "pillow": PIL_AVAILABLE
    }

    return {
        "status": "healthy",
        "agent": "ERATO",
        "role": "Media Producer",
        "version": "1.0.0",
        "port": 8033,
        "services": services,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "launch_status": time_ctx['launch_status'],
        "media_path": str(MEDIA_BASE_PATH)
    }

# -----------------------------------------------------------------------------
# IMAGE ENDPOINTS
# -----------------------------------------------------------------------------

@app.post("/generate/image", response_model=ImageGenerateResponse)
async def generate_image(request: ImageGenerateRequest, background_tasks: BackgroundTasks):
    """Generate images using DALL-E 3"""
    time_ctx = get_time_context()
    generation_id = str(uuid.uuid4())

    # Build enhanced prompt with style and brand colors
    images, cost = await generate_dalle3_image(
        prompt=request.prompt,
        size=request.size.value,
        quality=request.quality.value,
        style=request.style,
        brand_colors=request.brand_colors,
        n=request.n
    )

    # Log cost in background
    background_tasks.add_task(
        log_media_cost,
        "dalle3_image_generation",
        cost,
        {"prompt": request.prompt[:100], "n": request.n, "size": request.size.value}
    )

    # Notify event bus
    background_tasks.add_task(
        notify_event_bus,
        "image_generated",
        {"generation_id": generation_id, "count": len(images), "cost": cost}
    )

    return ImageGenerateResponse(
        images=images,
        generation_id=generation_id,
        prompt_used=request.prompt,
        cost=cost,
        timestamp=time_ctx['current_datetime']
    )

@app.post("/process/image", response_model=ImageProcessResponse)
async def process_image(request: ImageProcessRequest):
    """Apply post-processing operations to an image"""
    processed_path, applied_ops, original_size, final_size = process_image_operations(
        request.image_path,
        request.operations
    )

    return ImageProcessResponse(
        processed_path=processed_path,
        operations_applied=applied_ops,
        original_size=original_size,
        final_size=final_size
    )

# -----------------------------------------------------------------------------
# VIDEO ENDPOINTS
# -----------------------------------------------------------------------------

@app.post("/generate/video", response_model=VideoGenerateResponse)
async def generate_video(request: VideoGenerateRequest, background_tasks: BackgroundTasks):
    """Generate a complete video based on script and style"""
    start_time = datetime.now()
    cost_breakdown = CostBreakdown()

    scenes = []
    voiceover_path = None

    # Step 1: Generate voiceover if voice config provided
    if request.voice_config:
        audio_path, duration, chars, voice_cost = await generate_elevenlabs_voice(
            text=request.script,
            voice_id=request.voice_config.voice_id,
            speed=request.voice_config.speed,
            pitch=request.voice_config.pitch
        )
        voiceover_path = audio_path
        cost_breakdown.voice = voice_cost

    # Step 2: Handle different video styles
    if request.style == VideoStyle.AVATAR:
        # Generate avatar video
        if not request.avatar_config:
            raise HTTPException(status_code=400, detail="Avatar config required for avatar style")

        if request.avatar_config.provider == AvatarProvider.SYNTHESIA:
            video_path, duration, render_time, avatar_cost = await generate_synthesia_avatar(
                script=request.script,
                avatar_id=request.avatar_config.avatar_id,
                background=request.avatar_config.background,
                custom_background_url=request.avatar_config.custom_background_url
            )
        else:
            video_path, duration, render_time, avatar_cost = await generate_heygen_avatar(
                script=request.script,
                avatar_id=request.avatar_config.avatar_id,
                background=request.avatar_config.background,
                custom_background_url=request.avatar_config.custom_background_url
            )

        cost_breakdown.avatar = avatar_cost
        thumbnail_path = await create_thumbnail(video_path)

    elif request.style == VideoStyle.SLIDESHOW:
        # For slideshow, we need images - generate them from script keywords
        # This is a simplified implementation
        raise HTTPException(
            status_code=501,
            detail="Slideshow style requires image assets. Use /assemble/video with prepared scenes."
        )

    elif request.style == VideoStyle.MOTION_GRAPHICS:
        # Motion graphics require After Effects or similar
        raise HTTPException(
            status_code=501,
            detail="Motion graphics style not yet implemented. Use /assemble/video with prepared assets."
        )

    elif request.style == VideoStyle.STOCK_FOOTAGE:
        # Stock footage style requires pre-sourced footage
        raise HTTPException(
            status_code=501,
            detail="Stock footage style requires sourced assets. Use /source/stock then /assemble/video."
        )

    cost_breakdown.total = (
        cost_breakdown.voice +
        cost_breakdown.avatar +
        cost_breakdown.stock +
        cost_breakdown.processing
    )

    render_time = (datetime.now() - start_time).total_seconds()

    # Log cost in background
    background_tasks.add_task(
        log_media_cost,
        "video_generation",
        cost_breakdown.total,
        {"style": request.style.value, "duration": duration}
    )

    # Notify event bus
    background_tasks.add_task(
        notify_event_bus,
        "video_generated",
        {"style": request.style.value, "duration": duration, "cost": cost_breakdown.total}
    )

    return VideoGenerateResponse(
        video_path=video_path,
        thumbnail_path=thumbnail_path,
        duration=duration,
        render_time=render_time,
        cost_breakdown=cost_breakdown
    )

@app.post("/generate/avatar", response_model=AvatarGenerateResponse)
async def generate_avatar(request: AvatarGenerateRequest, background_tasks: BackgroundTasks):
    """Generate avatar video directly"""
    if request.provider == AvatarProvider.SYNTHESIA:
        video_path, duration, render_time, cost = await generate_synthesia_avatar(
            script=request.script,
            avatar_id=request.avatar_id,
            background=request.background,
            custom_background_url=request.custom_background_url
        )
    else:
        video_path, duration, render_time, cost = await generate_heygen_avatar(
            script=request.script,
            avatar_id=request.avatar_id,
            background=request.background,
            custom_background_url=request.custom_background_url
        )

    background_tasks.add_task(
        log_media_cost,
        f"avatar_generation_{request.provider.value}",
        cost,
        {"avatar_id": request.avatar_id, "duration": duration}
    )

    background_tasks.add_task(
        notify_event_bus,
        "avatar_generated",
        {"provider": request.provider.value, "duration": duration, "cost": cost}
    )

    return AvatarGenerateResponse(
        video_path=video_path,
        duration=duration,
        render_time=render_time,
        cost=cost
    )

@app.post("/generate/voiceover", response_model=VoiceoverGenerateResponse)
async def generate_voiceover(request: VoiceoverGenerateRequest, background_tasks: BackgroundTasks):
    """Generate voiceover audio"""
    audio_path, duration, characters_used, cost = await generate_elevenlabs_voice(
        text=request.text,
        voice_id=request.voice_id,
        speed=request.speed,
        pitch=request.pitch
    )

    background_tasks.add_task(
        log_media_cost,
        "voiceover_generation",
        cost,
        {"voice_id": request.voice_id, "characters": characters_used}
    )

    background_tasks.add_task(
        notify_event_bus,
        "voiceover_generated",
        {"duration": duration, "characters": characters_used, "cost": cost}
    )

    return VoiceoverGenerateResponse(
        audio_path=audio_path,
        duration=duration,
        characters_used=characters_used,
        cost=cost
    )

@app.post("/assemble/video", response_model=VideoAssembleResponse)
async def assemble_video(request: VideoAssembleRequest, background_tasks: BackgroundTasks):
    """Assemble video from multiple scenes"""
    video_path, duration, file_size = await assemble_video_with_ffmpeg(
        scenes=request.scenes,
        output_format=request.output_format,
        resolution=request.resolution,
        background_music=request.background_music
    )

    background_tasks.add_task(
        notify_event_bus,
        "video_assembled",
        {"scenes": len(request.scenes), "duration": duration, "size": file_size}
    )

    return VideoAssembleResponse(
        video_path=video_path,
        duration=duration,
        file_size=file_size,
        scenes_count=len(request.scenes)
    )

@app.post("/source/stock", response_model=StockSourceResponse)
async def source_stock(request: StockSourceRequest):
    """Search for stock photos/videos from Pexels and Pixabay"""
    # Search both sources
    pexels_results = []
    pixabay_results = []

    try:
        if PEXELS_API_KEY:
            pexels_results = await search_pexels(
                query=request.query,
                media_type=request.type,
                count=request.count // 2 + 1,
                orientation=request.orientation
            )
    except Exception as e:
        print(f"[ERATO] Pexels search error: {e}")

    try:
        if PIXABAY_API_KEY:
            pixabay_results = await search_pixabay(
                query=request.query,
                media_type=request.type,
                count=request.count // 2 + 1,
                orientation=request.orientation
            )
    except Exception as e:
        print(f"[ERATO] Pixabay search error: {e}")

    # Combine results
    all_assets = pexels_results + pixabay_results

    # Trim to requested count
    all_assets = all_assets[:request.count]

    source = "pexels+pixabay" if pexels_results and pixabay_results else (
        "pexels" if pexels_results else "pixabay"
    )

    return StockSourceResponse(
        assets=all_assets,
        source=source,
        query=request.query,
        total_results=len(all_assets)
    )

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8033)
