# Voice Assistant Test Client

A React-based browser client for testing the voice assistant locally without needing Twilio.

## Features

- 🎤 **Browser-based voice input** - Uses your computer's microphone
- 🔊 **Real-time audio playback** - Hear Jarvis speak
- 📝 **Live transcript** - See the conversation in real-time
- 🔌 **Direct WebSocket connection** - Connects to the same backend as Twilio

## Quick Start

### 1. Start the Backend Server

In the root directory:
```bash
npm install
npm run dev
```

This starts the backend on `http://localhost:3000`

### 2. Start the Test Client

In a new terminal, navigate to the test-client directory:
```bash
cd test-client
npm install
npm run dev
```

This starts the React app on `http://localhost:5173`

### 3. Open in Browser

Navigate to `http://localhost:5173`

### 4. Test the Voice Assistant

1. Click **"📞 Start Call with Jarvis"**
2. Allow microphone access when prompted
3. Wait for Jarvis to say "Go for Jarvis"
4. Start asking questions:
   - "What's the primary objective?"
   - "Tell me about the 21 untapped patients"
   - "How should I handle XOLAIR objections?"
   - "What resources should I bring?"
5. Click **"⏹️ End Call"** when finished

## How It Works

```
Browser Microphone
       ↓
   AudioProcessor (PCM16 24kHz)
       ↓
   WebSocket (/test-client)
       ↓
   OpenAI Realtime API
       ↓
   WebSocket Response
       ↓
   Browser Audio Playback
```

### Key Differences from Twilio

| Feature | Twilio | Test Client |
|---------|--------|-------------|
| Audio Format | mulaw 8kHz | PCM16 24kHz |
| Connection | Phone Call | WebSocket |
| Endpoint | `/media-stream` | `/test-client` |
| Conversion | mulaw ↔ PCM16 | None needed |

## Architecture

### Frontend (`src/`)

- **`VoiceClient.tsx`** - Main React component with UI and WebSocket logic
- **`audioProcessor.ts`** - Audio recording and playback utilities
- **`VoiceClient.css`** - Styling

### Backend Integration

The test client connects to a dedicated WebSocket endpoint (`/test-client`) on the backend server. The backend creates a `TestClientHandler` that:

1. Receives PCM16 24kHz audio from the browser
2. Forwards it to OpenAI Realtime API
3. Receives audio responses from OpenAI
4. Sends them back to the browser for playback

See [src/services/testClientHandler.ts](../src/services/testClientHandler.ts:1-133) for implementation.

## Development

### File Structure

```
test-client/
├── src/
│   ├── components/
│   │   ├── VoiceClient.tsx      # Main component
│   │   └── VoiceClient.css      # Styles
│   ├── utils/
│   │   └── audioProcessor.ts    # Audio utilities
│   ├── main.tsx                 # React entry point
│   └── index.css                # Global styles
├── index.html                   # HTML template
├── package.json                 # Dependencies
├── tsconfig.json                # TypeScript config
├── vite.config.ts               # Vite config
└── README.md                    # This file
```

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Troubleshooting

### "WebSocket connection failed"

- Ensure the backend server is running on port 3000
- Check that you're accessing the test client on `http://localhost:5173`

### "Microphone access denied"

- Grant microphone permissions in your browser
- Check browser settings to ensure microphone access is allowed

### "No audio from Jarvis"

- Check browser console for errors
- Verify OpenAI API key is configured in backend `.env`
- Ensure you have access to OpenAI Realtime API

### "Audio is choppy or delayed"

- Close other applications using your microphone
- Try using headphones to avoid feedback
- Check your internet connection

## Browser Compatibility

Tested on:
- Chrome 90+
- Edge 90+
- Safari 14+
- Firefox 88+

Requires:
- WebSocket support
- Web Audio API
- MediaDevices API (for microphone access)

## Tips for Best Results

1. **Use headphones** to avoid audio feedback
2. **Speak clearly** and wait for Jarvis to finish before speaking
3. **Check your microphone** levels in system settings
4. **Use a quiet environment** for better speech recognition
5. **Wait for "Go for Jarvis"** before asking questions

## Next Steps

- Customize the UI styling in `VoiceClient.css`
- Add more features (mute, volume control, etc.)
- Implement conversation history saving
- Add authentication for secure access

## Production Note

This test client is for **local development only**. For production, use the Twilio integration with actual phone calls. This client is not suitable for production deployment as it requires microphone access and direct WebSocket connections.
