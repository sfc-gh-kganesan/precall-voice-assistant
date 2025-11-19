# Voice Features Guide

Voice support using OpenAI Realtime API with backend agent integration.

## Overview

The chat widget supports voice input using OpenAI's Realtime API. Voice queries have full access to backend agent tools including:
- Snowflake documentation search (Cortex)
- Internal knowledge search (Glean)
- All capabilities available via text chat

## Setup

**1. Add OpenAI API Key**

Add to your `.env` file:
```bash
OPENAI_API_KEY=sk-your-openai-api-key-here
```

**2. Restart Backend**
```bash
docker compose restart web-support-agent
```

**3. Verify Voice is Available**
```bash
curl http://localhost:8003/api/v1/voice/available
# Should return: {"available": true}
```

If voice is available, a microphone button will appear in the chat widget.

## Usage

### Hold-to-Talk

1. **Open chat widget** (click blue bubble)
2. **Hold down** the microphone button (white circle, left of send button)
3. **Speak** your question
4. **Release** the button when done
5. Watch:
   - Status shows "Processing..."
   - Your speech appears as text message
   - Agent streams response in chat

### Visual Indicators

| State | Appearance | Meaning |
|-------|-----------|---------|
| **Idle** | White circle, blue mic icon | Ready to record |
| **Recording** | Red pulsing circle | Currently recording audio |
| **Processing** | Blue status text | Transcribing your speech |
| **Hidden** | Not visible | OpenAI key not configured |

## How It Works

```
User speaks
    ↓
Browser captures microphone audio
    ↓
Connects to OpenAI Realtime API (WebSocket)
    ↓
Audio streamed to OpenAI for real-time transcription
    ↓
Transcript sent to backend agent
    ↓
Agent uses tools (Glean, Cortex Search, etc.)
    ↓
Response appears in chat
```

**Key Features:**
- **Real-time transcription** - Your speech converted to text instantly
- **Backend integration** - Voice queries use same agent as text
- **Conversation history** - Voice and text share the same conversation context
- **Ephemeral tokens** - Secure authentication (API key stays on server)

## Architecture

```
┌──────────────────────┐
│   Chat Widget        │
│   (Hold mic button)  │
└──────────┬───────────┘
           │
           │ WebSocket
           ↓
┌──────────────────────┐
│  OpenAI Realtime API │
│  (Speech-to-text)    │
└──────────┬───────────┘
           │ Transcript
           ↓
┌──────────────────────┐
│  Backend Agent       │
│  Port 8003           │
│  - Glean Search      │
│  - Cortex Search     │
└──────────────────────┘
```

## Configuration

### Changing Voice

Edit `VoiceService.ts` (line ~110):

```typescript
voice: 'alloy',  // Options: alloy, echo, shimmer, nova, fable, onyx
```

### Customizing Voice Instructions

The voice agent receives the same system prompt as the text agent. To customize:

Edit `/webagent/backend/external_agent.py` - `EXTERNAL_SYSTEM_PROMPT` variable.

### Audio Settings

The voice service uses:
- **Sample rate:** 24kHz PCM16
- **Turn detection:** Disabled (manual push-to-talk)
- **Input format:** Raw PCM audio
- **Connection:** WebSocket to OpenAI Realtime API

## Troubleshooting

### Mic Button Not Appearing

**Cause:** OpenAI API key not configured

**Fix:**
1. Add `OPENAI_API_KEY` to `.env`
2. Restart: `docker compose restart web-support-agent`
3. Check: `curl http://localhost:8003/api/v1/voice/available`

### "Voice error: Failed to get voice token"

**Cause:** Invalid API key or network issue

**Check logs:**
```bash
docker compose logs web-support-agent | grep -i voice
```

**Verify API key:**
```bash
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

### Microphone Permission Denied

**Cause:** Browser blocked microphone access

**Fix:**
1. Click camera/mic icon in browser address bar
2. Allow microphone access
3. Reload page

**Note:** HTTPS may be required for microphone on some browsers

### Voice Works But No Transcription

**Debug steps:**
1. Open browser console (F12)
2. Look for `[VoiceService]` log messages
3. Should see:
   - "WebSocket connected"
   - "Starting recording..."
   - "User transcript: ..."

### Conversation History Not Shared

Voice and text use the same `conversation_id` generated on page load.

**Verify:**
```bash
curl http://localhost:8003/conversations
```

Both voice and text messages should appear in the same conversation.

### Error: "Cancellation failed: no active response"

This error has been fixed in the latest version. If you still see it:
1. Ensure you're using the latest code
2. Rebuild widget: `cd chat-widget && npm run build`
3. Hard refresh: Cmd+Shift+R

## Cost Considerations

### OpenAI Realtime API Pricing

- **Input audio:** $0.06 / minute
- **Output audio:** $0.24 / minute (if playing audio)
- **Text input/output:** Standard GPT-4 pricing

**Note:** Current implementation only sends audio input (no audio output), so costs are lower.

### Example Costs

| Usage | Estimated Cost |
|-------|---------------|
| 100 voice messages (avg 30s) | ~$3 + agent response costs |
| 1000 text messages | ~$10-20 (depending on length) |

## Browser Compatibility

| Browser | Support |
|---------|---------|
| **Chrome/Edge** | ✅ Full support |
| **Firefox** | ✅ Full support |
| **Safari** | ✅ Full support (may require HTTPS for mic) |
| **Mobile (iOS/Android)** | ✅ Works with touchstart/touchend |

## Security

- **Ephemeral Tokens:** Backend generates short-lived tokens for each session
- **No API Key in Browser:** OpenAI key never leaves the server
- **CORS:** Currently set to `*` (restrict in production)
- **Microphone Permissions:** Browser requires explicit user permission

## Production Checklist

- [ ] Set `OPENAI_API_KEY` in production environment
- [ ] Restrict CORS to specific domains
- [ ] Enable HTTPS (required for mic on many browsers)
- [ ] Add rate limiting for token generation
- [ ] Monitor OpenAI API usage and costs
- [ ] Test on all target browsers
- [ ] Add error tracking (Sentry, DataDog)

## Known Limitations

1. **No audio output:** Agent responds with text only (no voice playback)
2. **English optimized:** May work with other languages but not tested
3. **Push-to-talk only:** No continuous listening mode
4. **Single speaker:** Doesn't support multi-speaker detection

## Future Enhancements

Potential improvements:
- Audio playback (agent speaks responses)
- Continuous mode toggle
- Visual audio waveform
- Multi-language support
- Voice commands ("clear chat", "start over")

## Support

For voice-specific issues:
1. Check OpenAI API key is valid
2. Verify microphone permissions in browser
3. Check browser console for errors
4. Review backend logs: `docker compose logs -f web-support-agent`
5. Test text chat first (simpler to debug)
