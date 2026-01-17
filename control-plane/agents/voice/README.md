# VOICE - Voice Interface for ARIA

**Port: 8051**

Voice Interface agent providing speech-to-text and text-to-speech capabilities for ARIA interactions. Enables voice conversations through Telegram voice notes or web interfaces.

## Features

- **Speech-to-Text (STT)**: Transcribe audio using OpenAI Whisper API
- **Text-to-Speech (TTS)**: Synthesize speech using OpenAI TTS API
- **Voice Chat**: Full voice-to-voice conversation flow through ARIA
- **Multi-format Support**: wav, mp3, m4a, ogg, webm, flac, mpeg, mpga

## Endpoints

### Health Check
```
GET /health
```
Returns service status, configuration state, and supported formats.

### Transcribe Audio
```
POST /voice/transcribe
Content-Type: multipart/form-data

Parameters:
- audio: Audio file (required)

Response:
{
  "text": "transcribed text",
  "duration_seconds": 5.2,
  "language": "en"
}
```

### Synthesize Speech
```
POST /voice/synthesize
Content-Type: application/json

{
  "text": "Text to convert to speech",
  "voice": "nova",      // alloy, echo, fable, onyx, nova, shimmer
  "model": "tts-1",     // tts-1 or tts-1-hd
  "response_format": "mp3"  // mp3, opus, aac, flac
}

Response: Audio file binary
```

### Voice Chat (Audio Response)
```
POST /voice/chat
Content-Type: multipart/form-data

Parameters:
- audio: Audio file with user's message (required)
- user_id: User identifier (default: "voice_user")
- voice: TTS voice for response (default: "nova")
- response_format: Audio format (default: "mp3")

Response: Audio file binary with headers:
- X-Conversation-Id: Unique conversation ID
- X-Input-Text: Transcribed input (truncated)
- X-Aria-Response-Length: Response text length
```

### Voice Chat (JSON Response)
```
POST /voice/chat/json
Content-Type: multipart/form-data

Parameters: Same as /voice/chat

Response:
{
  "conversation_id": "abc12345",
  "input_text": "transcribed user message",
  "aria_response": "ARIA's response text",
  "audio_base64": "base64-encoded audio",
  "audio_format": "mp3",
  "transcription_language": "en",
  "transcription_duration": 3.5
}
```

## Voice Options

| Voice | Description |
|-------|-------------|
| alloy | Neutral, balanced |
| echo | Warm, conversational |
| fable | Expressive, storytelling |
| onyx | Deep, authoritative |
| nova | Friendly, natural (default) |
| shimmer | Clear, optimistic |

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `ARIA_WEBHOOK_URL` | ARIA webhook endpoint | `http://localhost:5680/webhook/aria-router` |
| `EVENT_BUS_URL` | Event bus for logging | `http://event-bus:8099` |
| `VOICE_TEMP_DIR` | Temp file directory | `/tmp/voice-cache` |

## Usage Examples

### Transcribe a voice note
```bash
curl -X POST http://localhost:8051/voice/transcribe \
  -F "audio=@message.mp3"
```

### Generate speech
```bash
curl -X POST http://localhost:8051/voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is ARIA speaking", "voice": "nova"}' \
  --output response.mp3
```

### Full voice conversation
```bash
curl -X POST http://localhost:8051/voice/chat \
  -F "audio=@question.mp3" \
  -F "user_id=damon" \
  -F "voice=nova" \
  --output answer.mp3
```

### Voice conversation with JSON (for web apps)
```bash
curl -X POST http://localhost:8051/voice/chat/json \
  -F "audio=@question.mp3" \
  -F "user_id=damon"
```

## Integration with Telegram

VOICE is designed to process voice notes forwarded from Telegram via HERMES or other handlers:

1. Telegram bot receives voice message
2. Audio file is forwarded to `/voice/chat`
3. Response audio is sent back to user

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key-here"
export ARIA_WEBHOOK_URL="http://localhost:5680/webhook/aria-router"

# Run the service
python voice.py
```

## Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY voice.py .
EXPOSE 8051
CMD ["python", "voice.py"]
```

## Architecture

```
[Telegram/Web] -> [VOICE /voice/chat]
                       |
                       v
            [1. Whisper STT] -> Transcribe audio
                       |
                       v
            [2. ARIA Webhook] -> Process with AI
                       |
                       v
            [3. OpenAI TTS] -> Synthesize response
                       |
                       v
            [Audio Response] -> Return to user
```

## Event Bus Integration

VOICE logs all operations to the event bus:

- `transcription_request` - Audio received for transcription
- `transcription_complete` - Transcription finished
- `synthesis_request` - Text-to-speech requested
- `synthesis_complete` - Audio generated
- `voice_chat_start` - Voice conversation initiated
- `voice_chat_transcribed` - User message transcribed
- `voice_chat_aria_response` - ARIA response received
- `voice_chat_complete` - Response audio generated

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid input (empty audio, unsupported format) |
| 503 | OpenAI client not configured |
| 500 | Transcription or synthesis failed |

## Performance Notes

- **Whisper** model handles up to 25MB audio files
- **TTS** response time is typically 1-3 seconds
- Consider caching common responses for faster delivery
- Use `tts-1` for speed, `tts-1-hd` for quality
