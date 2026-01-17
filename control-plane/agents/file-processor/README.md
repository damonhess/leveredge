# FILE-PROCESSOR Agent

**Port:** 8050

File Processing Agent for LeverEdge - handles PDF, image, audio, and video processing with integrated cost tracking.

## Capabilities

| File Type | Features | Dependencies |
|-----------|----------|--------------|
| **PDF** | Text extraction with page citations, table extraction | pdfplumber |
| **Image** | OCR text extraction, dimension analysis | pytesseract, tesseract-ocr |
| **Audio** | Transcription via Whisper API | OPENAI_API_KEY, ffmpeg |
| **Video** | Audio extraction, transcription, key frame extraction with OCR | OPENAI_API_KEY, ffmpeg, tesseract-ocr |

## Prerequisites

### System Dependencies

```bash
# Ubuntu/Debian
apt-get update && apt-get install -y tesseract-ocr ffmpeg

# macOS
brew install tesseract ffmpeg

# Alpine Linux
apk add tesseract-ocr ffmpeg
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

```bash
# Required for audio/video transcription
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Event bus URL for cost tracking
export EVENT_BUS_URL="http://localhost:8099"
```

## Quick Start

```bash
# Start the agent
python file_processor.py

# Or with uvicorn
uvicorn file_processor:app --host 0.0.0.0 --port 8050
```

## API Endpoints

### GET /health

Health check with dependency status.

```bash
curl http://localhost:8050/health
```

Response:
```json
{
  "status": "healthy",
  "agent": "FILE-PROCESSOR",
  "port": 8050,
  "version": "1.0.0",
  "capabilities": ["pdf", "image", "audio", "video"],
  "dependencies": {
    "ffmpeg": true,
    "tesseract": true,
    "whisper_api": true
  },
  "timestamp": "2026-01-17T10:30:00.000000"
}
```

### GET /supported-formats

List all supported file types and extensions.

```bash
curl http://localhost:8050/supported-formats
```

### POST /process/pdf

Extract text from PDF with page citations.

```bash
curl -X POST http://localhost:8050/process/pdf \
  -F "file=@document.pdf"
```

Response:
```json
{
  "success": true,
  "filename": "document.pdf",
  "total_pages": 10,
  "pages": [
    {
      "page_number": 1,
      "text": "Page content...",
      "word_count": 250,
      "table_count": 0,
      "citation": "[Page 1]"
    }
  ],
  "full_text": "[Page 1]\nPage content...\n\n[Page 2]\n...",
  "word_count": 2500,
  "processing_time_seconds": 1.234,
  "cost": 0.01
}
```

### POST /process/image

OCR text extraction from images.

```bash
curl -X POST http://localhost:8050/process/image \
  -F "file=@screenshot.png" \
  -F "include_description=true"
```

Response:
```json
{
  "success": true,
  "filename": "screenshot.png",
  "dimensions": {"width": 1920, "height": 1080},
  "ocr_text": "Extracted text from image...",
  "word_count": 45,
  "description": "Image: 1920x1080 pixels",
  "processing_time_seconds": 0.567,
  "cost": 0.002
}
```

### POST /process/audio

Transcribe audio files using Whisper API.

```bash
curl -X POST http://localhost:8050/process/audio \
  -F "file=@recording.mp3"
```

Response:
```json
{
  "success": true,
  "filename": "recording.mp3",
  "duration_seconds": 180.5,
  "transcript": "Full transcription of the audio...",
  "word_count": 450,
  "language": "en",
  "processing_time_seconds": 12.345,
  "cost": 0.018
}
```

### POST /process/video

Process video: extract audio, transcribe, and capture key frames.

```bash
curl -X POST http://localhost:8050/process/video \
  -F "file=@video.mp4" \
  -F "extract_frames=true" \
  -F "frame_interval=30" \
  -F "max_frames=10"
```

Parameters:
- `extract_frames` (bool, default: true): Whether to extract key frames
- `frame_interval` (int, default: 30): Seconds between frame captures
- `max_frames` (int, default: 10): Maximum frames to extract

Response:
```json
{
  "success": true,
  "filename": "video.mp4",
  "duration_seconds": 300.0,
  "transcript": "Full video transcription...",
  "word_count": 800,
  "key_frames": [
    {
      "frame_index": 0,
      "timestamp_seconds": 0,
      "timestamp_formatted": "00:00",
      "dimensions": {"width": 1920, "height": 1080},
      "ocr_text": "Text visible in frame"
    }
  ],
  "frame_count": 10,
  "processing_time_seconds": 45.678,
  "cost": 0.045
}
```

## Cost Tracking

All processing operations are logged to the event bus at `http://localhost:8099/publish`.

Cost estimates per unit:
| Operation | Cost | Unit |
|-----------|------|------|
| PDF page | $0.001 | per page |
| Image OCR | $0.002 | per image |
| Audio transcription | $0.006 | per minute |
| Video processing | $0.008 | per minute |
| Frame extraction | $0.0005 | per frame |

Event payload example:
```json
{
  "event_type": "file_processing",
  "source": "FILE-PROCESSOR",
  "data": {
    "agent": "FILE-PROCESSOR",
    "endpoint": "/process/pdf",
    "file_type": "pdf",
    "file_size_bytes": 1048576,
    "processing_units": 10,
    "unit_type": "pages",
    "cost": 0.01,
    "duration_seconds": 1.234,
    "metadata": {"filename": "document.pdf", "word_count": 2500},
    "timestamp": "2026-01-17T10:30:00.000000"
  }
}
```

## Supported File Formats

### PDF
- Extensions: `.pdf`
- MIME types: `application/pdf`

### Images
- Extensions: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`
- MIME types: `image/png`, `image/jpeg`, `image/gif`, `image/bmp`, `image/tiff`, `image/webp`

### Audio
- Extensions: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.webm`
- MIME types: `audio/mpeg`, `audio/wav`, `audio/mp4`, `audio/flac`, `audio/ogg`, `audio/webm`

### Video
- Extensions: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.flv`
- MIME types: `video/mp4`, `video/avi`, `video/quicktime`, `video/x-matroska`, `video/webm`, `video/x-flv`

## Docker Deployment

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY file_processor.py .

ENV OPENAI_API_KEY=""
ENV EVENT_BUS_URL="http://event-bus:8099"

EXPOSE 8050

CMD ["python", "file_processor.py"]
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description",
  "agent": "FILE-PROCESSOR"
}
```

Common HTTP status codes:
- `400`: Invalid file type
- `500`: Processing error
- `503`: Missing dependency (tesseract, ffmpeg, or OPENAI_API_KEY)
- `504`: Processing timeout

## Integration Example

```python
import httpx

async def process_document(file_path: str):
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                "http://localhost:8050/process/pdf",
                files={"file": (file_path, f, "application/pdf")},
                timeout=60.0
            )

        result = response.json()
        print(f"Extracted {result['word_count']} words from {result['total_pages']} pages")
        print(f"Cost: ${result['cost']:.4f}")

        return result["full_text"]
```

## License

Internal LeverEdge agent - all rights reserved.
