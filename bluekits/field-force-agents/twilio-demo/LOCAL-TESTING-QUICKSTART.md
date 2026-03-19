# Local Testing Quick Start

Test the voice assistant in your browser without Twilio - 5 minutes setup!

## One-Command Setup

```bash
./start-local-test.sh
```

This starts both the backend and test client automatically.

## Manual Setup (Alternative)

### Step 1: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add:
```env
OPENAI_API_KEY=sk-your-key-here
TWILIO_ACCOUNT_SID=ACxxxxxxxx  # Can use dummy values for local testing
TWILIO_AUTH_TOKEN=xxxxxxxx     # Can use dummy values for local testing
```

### Step 2: Start Backend

**Terminal 1:**
```bash
npm install
npm run dev
```

You should see:
```
Server started on port 3000
Environment: development
```

### Step 3: Start Test Client

**Terminal 2:**
```bash
cd test-client
npm install
npm run dev
```

You should see:
```
VITE v5.0.8  ready in XXX ms

➜  Local:   http://localhost:5173/
```

### Step 4: Open Browser

Navigate to: **http://localhost:5173**

## Using the Test Client

### 1. Start the Call

Click the **"📞 Start Call with Jarvis"** button

### 2. Allow Microphone

When prompted, click **"Allow"** to grant microphone access

### 3. Wait for Jarvis

You should see:
- 🟢 Connected status
- "Go for Jarvis" in the transcript
- Recording indicator

### 4. Ask Questions

Try these:

> "What's the primary objective for this call?"

> "Tell me about the 21 untapped patients"

> "How should I handle the XOLAIR competitive threat?"

> "What objections might Dr. Chavarria raise?"

> "What resources should I bring?"

### 5. End the Call

Click **"⏹️ End Call"** when finished

## What You Should See

### Transcript Example

```
[10:30:15] 🟢 Connected to Jarvis
[10:30:15] 🎤 Recording started - speak now
[10:30:16] ✅ Session created
[10:30:17] 🤖 Jarvis: Go for Jarvis
[10:30:20] 👤 You: What's the primary objective?
[10:30:22] 🤖 Jarvis: The primary objective is to address the 21 OCS-dependent asthma patients who aren't on DUPIXENT...
```

## Troubleshooting

### Backend Won't Start

**Error: "Port 3000 already in use"**
```bash
# Kill the process using port 3000
lsof -ti:3000 | xargs kill -9

# Try again
npm run dev
```

**Error: "Missing environment variables"**
```bash
# Make sure .env exists
ls -la .env

# Copy example if needed
cp .env.example .env

# Edit and add your OpenAI API key
```

### Test Client Won't Start

**Error: "Cannot find module"**
```bash
# Reinstall dependencies
cd test-client
rm -rf node_modules
npm install
npm run dev
```

### Connection Issues

**"WebSocket connection failed"**
1. Verify backend is running (check Terminal 1)
2. Make sure you see "Server started on port 3000"
3. Refresh the browser page

### Audio Issues

**"Microphone access denied"**
1. Check browser permissions
2. Click the lock icon in address bar
3. Allow microphone access
4. Refresh the page

**"No audio from Jarvis"**
1. Check system audio is not muted
2. Verify OpenAI API key is valid
3. Check browser console for errors (F12 → Console)

**"Audio is choppy"**
1. Close other apps using microphone
2. Use headphones to avoid feedback
3. Check internet connection

### OpenAI Issues

**"OpenAI connection error"**
1. Verify your OpenAI API key is correct
2. Check you have credits in your OpenAI account
3. Ensure you have access to Realtime API (may need to request beta access)

## System Requirements

### Minimum Requirements

- **Node.js**: 18.0.0 or higher
- **npm**: 8.0.0 or higher
- **Browser**: Chrome 90+, Safari 14+, Firefox 88+, or Edge 90+
- **Microphone**: Any working microphone
- **Internet**: Broadband connection

### Recommended Setup

- **Headphones**: To avoid audio feedback
- **Quiet environment**: For better speech recognition
- **Good microphone**: For clearer audio input

## Architecture Overview

```
┌─────────────────┐
│  Your Browser   │
│  localhost:5173 │
└────────┬────────┘
         │ WebSocket
         ↓
┌─────────────────┐
│  Backend Server │
│  localhost:3000 │
│                 │
│  /test-client   │← WebSocket endpoint
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  OpenAI         │
│  Realtime API   │
│                 │
│  gpt-4o-realtime│
└─────────────────┘
```

## Files You'll Need

```
twilio-openai-pre-call-app/
├── .env                        ← Your API keys
├── pre-call-context.json       ← Pre-call plan data
├── start-local-test.sh         ← Quick start script
│
├── src/                        ← Backend
│   └── ...
│
└── test-client/                ← React app
    ├── src/
    │   ├── components/VoiceClient.tsx
    │   └── utils/audioProcessor.ts
    └── ...
```

## What's Different from Production?

| Feature | Local Testing | Production (Twilio) |
|---------|--------------|---------------------|
| Interface | Browser + Microphone | Phone call |
| Connection | WebSocket direct | Twilio Media Stream |
| Audio | PCM16 24kHz | mulaw 8kHz |
| Endpoint | `/test-client` | `/media-stream` |
| Access | localhost:5173 | Call phone number |

## Next Steps

Once local testing works:

1. ✅ Test all conversation flows
2. ✅ Verify data accuracy
3. ✅ Deploy to Render
4. ✅ Configure Twilio webhook
5. ✅ Test with real phone calls

## Need More Help?

- **Full documentation**: [README.md](README.md)
- **Test client details**: [test-client/README.md](test-client/README.md)
- **Comprehensive testing**: [TESTING.md](TESTING.md)
- **Deployment**: [QUICKSTART.md](QUICKSTART.md)

## Quick Commands Reference

```bash
# Start everything (automated)
./start-local-test.sh

# Start backend only
npm run dev

# Start test client only
cd test-client && npm run dev

# Check backend health
curl http://localhost:3000/health

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Rebuild backend
npm run build

# Clean and reinstall
rm -rf node_modules && npm install
```

Happy testing! 🎉
