# Twilio OpenAI Pre-Call Voice Assistant

A voice assistant for pharmaceutical sales representatives that helps them prepare for doctor calls by discussing pre-call plan data. Built with Twilio Media Streams and OpenAI's Realtime API.

## Features

- **Voice-First Interface**: Call a phone number to interact with "Jarvis" via voice
- **Real-Time AI Responses**: Powered by OpenAI's GPT-4 Realtime API
- **Pre-Call Data Integration**: Loads comprehensive HCP (Healthcare Provider) data from JSON
- **Bidirectional Audio Streaming**: Twilio Media Streams with WebSocket
- **Production-Ready**: Deploy to Render with included configuration

## Architecture

```
Twilio Phone Call
       ↓
   Webhook (/voice/incoming)
       ↓
   Media Stream (WebSocket)
       ↓
   Audio Conversion (mulaw 8kHz ↔ PCM16 24kHz)
       ↓
   OpenAI Realtime API
       ↓
   Voice Response
```

## Prerequisites

- Node.js 18+
- Twilio account with a phone number
- OpenAI API key with access to Realtime API

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
```env
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
PORT=3000
NODE_ENV=development
LOG_LEVEL=info
```

### 3. Build the Project

```bash
npm run build
```

### 4. Deploy to Render (Recommended)

Skip local development and deploy directly to get your public webhook URL.

## Deployment to Render

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

### Step 2: Create Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Render will automatically detect `render.yaml`
5. Add environment variables in the Render dashboard:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
   - `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
6. Click **Create Web Service**

### Step 3: Get Your Public Webhook URL

After deployment completes, Render will provide your public URL:
```
https://precall-voice-assistant.onrender.com
```

Or with your custom name:
```
https://your-service-name.onrender.com
```

### Step 4: Configure Twilio Phone Number

1. Log into [Twilio Console](https://console.twilio.com/)
2. Go to **Phone Numbers** → **Manage** → **Active Numbers**
3. Select your phone number
4. Under "Voice Configuration":
   - **A CALL COMES IN**: Webhook
   - **URL**: `https://your-service-name.onrender.com/voice/incoming`
   - **HTTP**: POST
5. Click **Save**

### Step 5: Test Your Voice Assistant

Call your Twilio phone number. Jarvis will answer with "Go for Jarvis" and you can start asking questions about the pre-call plan.

## Project Structure

```
src/
├── config/
│   └── env.ts                 # Environment configuration
├── services/
│   ├── preCallPlanService.ts  # Load JSON & build system prompt
│   ├── openAIRealtimeClient.ts # OpenAI Realtime API client
│   └── twilioMediaStreamHandler.ts # Twilio WebSocket handler
├── types/
│   └── preCallPlan.ts         # TypeScript interfaces
├── utils/
│   ├── audioConverter.ts      # Audio format conversion
│   └── logger.ts              # Pino logger
└── index.ts                   # Express server & main entry
```

## Pre-Call Plan Data

The assistant reads from `pre-call-context.json` in the project root. This file contains:

- HCP information (name, specialty, segment)
- Executive summary (call history, fatigue risk)
- Prescribing trends (DUPIXENT, XOLAIR, ICS/LABA)
- Smart alerts (pull-through failures, persistence risks, opportunities)
- Recommended approach (6-step conversation guide)
- Objection handling
- Role play Q&A
- Strategic summary

## Usage

1. Call your Twilio phone number
2. Jarvis will answer with "Go for Jarvis"
3. Ask questions about the pre-call plan:
   - "What's the primary objective for this call?"
   - "Tell me about the 21 untapped patients"
   - "How should I handle the XOLAIR competitive threat?"
   - "What objections might Dr. Chavarria raise?"
   - "What resources should I bring?"

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /voice/incoming` - Twilio voice webhook (returns TwiML)
- `WS /media-stream` - WebSocket for Twilio Media Streams

## Development

### Local Testing with Browser Client

For local testing without Twilio, use the React test client:

1. Start the backend server:
   ```bash
   npm install
   npm run dev
   ```

2. In a new terminal, start the test client:
   ```bash
   cd test-client
   npm install
   npm run dev
   ```

3. Open browser to `http://localhost:5173`
4. Click "Start Call with Jarvis" and test voice interactions

See [test-client/README.md](test-client/README.md) for more details.

### Run Backend in Development Mode

```bash
npm run dev
```

This uses `ts-node-dev` for auto-reloading.

### Build TypeScript

```bash
npm run build
```

### Clean Build Directory

```bash
npm run clean
```

## Audio Conversion

The app handles conversion between:
- **Twilio**: mulaw encoding, 8kHz sample rate
- **OpenAI**: PCM16 encoding, 24kHz sample rate

Conversion pipeline:
1. Twilio → mulaw 8kHz → PCM16 8kHz → PCM16 24kHz → OpenAI
2. OpenAI → PCM16 24kHz → PCM16 8kHz → mulaw 8kHz → Twilio

## Logging

Uses Pino for structured logging with pretty printing in development.

Log levels: `trace`, `debug`, `info`, `warn`, `error`, `fatal`

Set via `LOG_LEVEL` environment variable.

## Troubleshooting

### "Missing required environment variables"
- Ensure `.env` file exists with all required variables
- Check that variables are not commented out

### "OpenAI WebSocket error"
- Verify `OPENAI_API_KEY` is valid
- Ensure you have access to the Realtime API (may require beta access)

### "Twilio WebSocket closed immediately"
- Check webhook URL is correct and accessible
- Verify SSL certificate is valid (Twilio requires HTTPS in production)
- Check Render logs for startup errors

### No audio or garbled audio
- Verify audio conversion is working correctly
- Check sample rate conversions (8kHz ↔ 24kHz)
- Review WebSocket message flow in logs

### Call connects but Jarvis doesn't respond
- Check OpenAI API key and quota
- Review system prompt in logs
- Verify pre-call-context.json is being loaded

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.
