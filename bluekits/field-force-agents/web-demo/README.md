# Real-time Voice Conversation App

A real-time voice conversation application using OpenAI's GPT-4 Realtime API with a React TypeScript frontend and Node.js TypeScript backend.

## Features

- 🎤 Real-time voice conversation with AI assistant
- 🗣️ Natural speech recognition with Whisper transcription
- 🔊 Real-time audio playback of AI responses
- 📝 Live conversation transcripts
- 🎯 Auto-detect conversation end phrases ("I am done", "goodbye", etc.)
- 🎨 Modern dark theme UI with smooth animations
- 📊 Final transcript collection and display

## Tech Stack

### Backend
- Node.js with TypeScript
- Express for HTTP server
- WebSocket (`ws` library) for real-time communication
- OpenAI Realtime API integration
- dotenv for environment variables

### Frontend
- React 18 with TypeScript
- Vite as build tool
- Web Audio API for audio capture and playback
- WebSocket for real-time communication
- Vanilla CSS with modern animations

## Project Structure

```
project/
├── backend/
│   ├── src/
│   │   └── index.ts          # WebSocket server and OpenAI integration
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env.example
│   └── .gitignore
└── frontend/
    ├── src/
    │   ├── App.tsx            # Main app component
    │   ├── main.tsx           # React entry point
    │   ├── index.css          # Styles
    │   └── hooks/
    │       └── useRealtimeConversation.ts  # Audio handling & WebSocket hook
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── .gitignore
```

## Prerequisites

- Node.js 18+ and npm
- OpenAI API key with access to the Realtime API
- Modern web browser with microphone access

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file from the example:
```bash
cp .env.example .env
```

4. Add your OpenAI API key and configuration to `.env`:
```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-realtime-preview-2024-12-17
PORT=3001
```

5. Start the development server:
```bash
npm run dev
```

The backend server will start on `http://localhost:3001`.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will start on `http://localhost:5173`.

## Usage

1. Open your browser and navigate to `http://localhost:5173`
2. Click the large circular microphone button to start the conversation
3. Allow microphone access when prompted
4. The AI will greet you and start a conversation
5. Speak naturally - your speech will be transcribed in real-time
6. When you're done, say "I am done" or "goodbye"
7. The AI will ask for confirmation: "Are you sure you want to end our conversation?"
8. Respond with "yes" or similar affirmative phrase to confirm
9. The AI will say goodbye and the conversation will automatically end
10. View all your transcripts after the conversation ends

## How It Works

### Audio Processing

1. **Capture**: Microphone audio is captured at 24kHz sample rate using Web Audio API
2. **Encoding**: Audio is converted from Float32 to PCM16 format and encoded to base64
3. **Transmission**: Base64 audio chunks are sent to backend via WebSocket
4. **OpenAI Processing**: Backend forwards audio to OpenAI Realtime API with server-side VAD (Voice Activity Detection)
5. **Response**: OpenAI returns audio responses and transcripts
6. **Playback**: Frontend decodes base64 PCM16 back to Float32 and plays using AudioContext

### WebSocket Message Types

#### Client → Backend
- `start_conversation`: Initialize OpenAI connection
- `audio_data`: Send audio chunks
- `stop_conversation`: End conversation and get final transcripts

#### Backend → Client
- `audio_delta`: AI audio chunks
- `agent_transcript_delta`: Streaming AI transcript
- `agent_transcript_done`: Complete AI transcript
- `user_transcript`: User speech transcription
- `user_speaking_started/stopped`: Voice activity detection
- `final_transcripts`: All user transcripts at conversation end
- `end_phrase_detected`: End phrase detected in user speech
- `conversation_ended`: Conversation automatically ended after confirmation
- `error`: Error messages

## Configuration

### OpenAI Session Configuration

The backend configures the OpenAI session with:

- **Modalities**: Text and audio
- **Voice**: Alloy (configurable in `backend/src/index.ts`)
- **Audio Format**: PCM16 at 24kHz
- **Transcription**: Whisper-1 model
- **Turn Detection**: Server-side VAD with 500ms silence duration
- **Instructions**: Custom prompt for AI behavior

### End Phrases and Confirmation

The app uses a two-step confirmation process:

1. **End Phrases** - These trigger the confirmation request:
   - "I am done"
   - "I'm done"
   - "goodbye"
   - "bye"
   - "that's all"
   - "thats all"

2. **Confirmation Phrases** - These confirm ending after the AI asks:
   - "yes"
   - "yeah"
   - "yep"
   - "sure"
   - "ok" / "okay"
   - "alright"
   - "definitely"

When an end phrase is detected, the AI asks for confirmation. Once confirmed with a "yes" or similar phrase, the AI says goodbye and the conversation automatically ends after 3 seconds, showing all transcripts.

You can modify these phrases in [backend/src/index.ts](backend/src/index.ts).

## Production Build

### Backend
```bash
cd backend
npm run build
npm start
```

### Frontend
```bash
cd frontend
npm run build
npm run preview
```

## Environment Variables

### Backend (.env)
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: OpenAI Realtime model to use (default: `gpt-4o-realtime-preview-2024-12-17`)
- `PORT`: Server port (default: 3001)

## Troubleshooting

### Microphone Not Working
- Ensure you've granted microphone permissions in your browser
- Check browser console for errors
- Try using HTTPS in production (required by some browsers)

### WebSocket Connection Failed
- Verify backend server is running on port 3001
- Check firewall settings
- Ensure OPENAI_API_KEY is set correctly

### No Audio Playback
- Check browser's audio settings
- Ensure audio isn't muted
- Try refreshing the page

### OpenAI API Errors
- Verify your API key has Realtime API access
- Check OpenAI API status
- Review backend console logs for detailed error messages

## Browser Compatibility

- Chrome 89+
- Firefox 88+
- Safari 14.1+
- Edge 89+

Requires WebSocket, Web Audio API, and MediaDevices getUserMedia support.

## License

MIT

## Credits

Built with OpenAI's GPT-4 Realtime API and modern web technologies.
