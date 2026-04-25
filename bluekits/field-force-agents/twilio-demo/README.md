# Pre-Call Voice Assistant

A browser-based voice assistant powered by OpenAI's Realtime API that helps pharmaceutical sales representatives prepare for doctor calls. Ask "Jarvis" questions about the pre-call plan and get real-time voice responses.

## Architecture

```
┌─────────────────────┐
│  Browser (React)    │
│  Microphone + Audio │
└──────────┬──────────┘
           │ WebSocket (PCM16 24kHz)
           ▼
┌─────────────────────┐
│  Express Server     │
│  (Node.js)          │
│  - Static files     │
│  - /test-client WS  │
└──────────┬──────────┘
           │ WebSocket
           ▼
┌─────────────────────┐
│  OpenAI Realtime    │
│  API (gpt-4o)       │
└─────────────────────┘
```

A single container serves both the React UI and the WebSocket backend on port 3000.

## Prerequisites

- Node.js 18+
- Docker (with `buildx` for cross-platform builds)
- OpenAI API key with access to the Realtime API
- Snowflake CLI (`snow`) for SPCS deployment

## Quick Start (Local)

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-key-here
```

### 2. Install dependencies

```bash
npm install
cd test-client && npm install && cd ..
```

### 3. Start the backend

```bash
npm run dev
```

You should see: `Server started on port 3000`

### 4. Start the React client

In a second terminal:

```bash
cd test-client
npm run dev
```

You should see: `Local: http://localhost:5173/`

### 5. Open in browser

Navigate to **http://localhost:5173**, click **"Start Call with Jarvis"**, allow microphone access, and start talking.

## Docker

### Build

```bash
# For local testing (native architecture)
docker build -t precall-voice-assistant .

# For SPCS / cloud deployment (must be amd64)
docker buildx build --platform linux/amd64 -t precall-voice-assistant:latest --load .
```

### Run locally

```bash
docker run --rm -p 8080:3000 \
  -e OPENAI_API_KEY=sk-your-key-here \
  precall-voice-assistant
```

Open **http://localhost:8080** in your browser.

## Deploy to Snowflake SPCS

### Step 1: Set up Snowflake connection

Add a connection to `~/.snowflake/connections.toml`:

```toml
[mlp]
account = "your-account"
user = "your-user"
database = "your-database"
schema = "your-schema"
warehouse = "your-warehouse"
password = "..."
role = "your-role"
```

Verify the connection:

```bash
snow connection test -c mlp
```

### Step 2: Create the database and schema (if needed)

```sql
CREATE DATABASE IF NOT EXISTS AURA;
CREATE SCHEMA IF NOT EXISTS AURA.VOICE;
```

### Step 3: Create an image repository

```sql
CREATE IMAGE REPOSITORY IF NOT EXISTS AURA.VOICE.IMAGES;
```

### Step 4: Build and push the Docker image

```bash
# Login to Snowflake registry
docker login <account>.registry.snowflakecomputing.com/aura/voice/images \
  -u <username> -p <password>

# Build for amd64 (required for SPCS)
docker buildx build --platform linux/amd64 \
  -t <account>.registry.snowflakecomputing.com/aura/voice/images/precall-voice-assistant:latest \
  --load .

# Push
docker push <account>.registry.snowflakecomputing.com/aura/voice/images/precall-voice-assistant:latest
```

### Step 5: Create a Snowflake secret for the OpenAI API key

```sql
CREATE SECRET IF NOT EXISTS AURA.VOICE.OPENAI_KEY
  TYPE = GENERIC_STRING
  SECRET_STRING = 'sk-your-openai-key-here';
```

### Step 6: Create an external access integration

If you don't already have one that allows outbound traffic:

```sql
CREATE OR REPLACE NETWORK RULE ALLOW_ALL_RULE
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('0.0.0.0:443', '0.0.0.0:80');

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION ALLOW_ALL_EAI
  ALLOWED_NETWORK_RULES = (ALLOW_ALL_RULE)
  ENABLED = TRUE;
```

### Step 7: Create a compute pool

```sql
CREATE COMPUTE POOL IF NOT EXISTS VOICE_ASSISTANT_POOL
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = CPU_X64_XS
  AUTO_RESUME = TRUE
  AUTO_SUSPEND_SECS = 1800;
```

### Step 8: Deploy the service

```sql
CREATE SERVICE AURA.VOICE.PRECALL_VOICE_ASSISTANT
  IN COMPUTE POOL VOICE_ASSISTANT_POOL
  FROM SPECIFICATION $$
spec:
  containers:
    - name: voice-assistant
      image: /aura/voice/images/precall-voice-assistant:latest
      env:
        NODE_ENV: production
        PORT: "3000"
      secrets:
        - snowflakeSecret: aura.voice.openai_key
          secretKeyRef: secret_string
          envVarName: OPENAI_API_KEY
  endpoints:
    - name: voice-ui
      port: 3000
      public: true
$$
EXTERNAL_ACCESS_INTEGRATIONS = (ALLOW_ALL_EAI)
MIN_INSTANCES = 1
MAX_INSTANCES = 1;
```

### Step 9: Get the public URL

```sql
SHOW ENDPOINTS IN SERVICE AURA.VOICE.PRECALL_VOICE_ASSISTANT;
```

The `ingress_url` column contains your public URL (may take 1-2 minutes to provision).

### Step 10: Open and test

Navigate to `https://<your-ingress-url>` in your browser, click **"Start Call with Jarvis"**, and test the voice assistant.

## Managing the SPCS Service

```sql
-- Check service status
SELECT SYSTEM$GET_SERVICE_STATUS('AURA.VOICE.PRECALL_VOICE_ASSISTANT');

-- View container logs
CALL SYSTEM$GET_SERVICE_LOGS('AURA.VOICE.PRECALL_VOICE_ASSISTANT', '0', 'voice-assistant', 100);

-- Suspend (stop billing)
ALTER SERVICE AURA.VOICE.PRECALL_VOICE_ASSISTANT SUSPEND;

-- Resume
ALTER SERVICE AURA.VOICE.PRECALL_VOICE_ASSISTANT RESUME;

-- Redeploy after pushing a new image
ALTER SERVICE AURA.VOICE.PRECALL_VOICE_ASSISTANT SUSPEND;
ALTER SERVICE AURA.VOICE.PRECALL_VOICE_ASSISTANT RESUME;

-- Delete
DROP SERVICE AURA.VOICE.PRECALL_VOICE_ASSISTANT;
DROP COMPUTE POOL VOICE_ASSISTANT_POOL;
```

## Project Structure

```
├── src/
│   ├── config/env.ts                  # Environment configuration
│   ├── services/
│   │   ├── openAIRealtimeClient.ts    # OpenAI Realtime API WebSocket client
│   │   ├── testClientHandler.ts       # Browser ↔ OpenAI bridge
│   │   └── preCallPlanService.ts      # Load JSON & build system prompt
│   ├── types/preCallPlan.ts           # TypeScript interfaces
│   └── utils/logger.ts               # Pino logger
├── test-client/                       # React frontend (Vite)
│   └── src/
│       ├── components/VoiceClient.tsx  # Main voice UI component
│       └── utils/audioProcessor.ts    # Browser audio capture & playback
├── pre-call-context.json              # Pre-call plan data (HCP info)
├── Dockerfile                         # Multi-stage build
├── spcs-spec.yaml                     # SPCS service specification
├── .env.example                       # Environment template
└── package.json
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key with Realtime API access |
| `OPENAI_MODEL` | No | `gpt-4o-realtime-preview-2024-12-17` | OpenAI Realtime model |
| `PORT` | No | `3000` | Server port |
| `NODE_ENV` | No | `development` | `development` or `production` |
| `LOG_LEVEL` | No | `info` | Log level: trace, debug, info, warn, error |

## Usage Tips

- **Use headphones** to avoid audio feedback between speaker and microphone
- **Speak clearly** and wait for Jarvis to finish before speaking
- Try questions like:
  - "What's the primary objective for this call?"
  - "Tell me about the 21 untapped patients"
  - "How should I handle the XOLAIR competitive threat?"
  - "What objections might Dr. Chavarria raise?"
  - "What resources should I bring?"

## License

MIT
