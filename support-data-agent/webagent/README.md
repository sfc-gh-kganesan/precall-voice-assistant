# Snowflake AI Chat Widget

Modern chat widget with AI-powered support for the Snowflake AI Data Cloud.

## Prerequisites

- Docker & Docker Compose
- Node.js 18+

## Docker Setup

This project uses shared Docker resources with AgentSmith:

- **Shared Network** (`aura-shared-network`) - Allows webagent and agentsmith to communicate
- **Shared Volume** (`aura-glean-tokens`) - Stores Glean OAuth tokens across services
- **Shared Services** - glean-proxy and github-proxy run in webagent, consumed by agentsmith

**Create the shared resources** (one-time setup):

```bash
docker network create aura-shared-network
docker volume create aura-glean-tokens
```

These resources only need to be created once and will persist across container restarts.

## Quick Start

**Note:** Make sure you've completed the [Docker Setup](#docker-setup) first (one-time setup).

**1. Start the backend:**
```bash
docker compose up -d
```

**2. Build the chat widget:**
```bash
cd chat-widget
npm install
npm run build
```

**3. Open the demo:**

Navigate to: **http://localhost:8004/demos/snowflake.html**

That's it! The chat widget should appear in the bottom-right corner.

## Features

- 💬 Real-time streaming responses
- 🎤 Voice support (OpenAI Realtime API) - see [docs/VOICE.md](docs/VOICE.md)
- 📚 Snowflake documentation search
- 🔍 Internal knowledge search (Glean)
- 📱 Mobile responsive
- 🎨 Markdown formatting

---

## Architecture

```
┌─────────────────────────┐
│   Chat Widget (React)   │
│   Port 8004 (nginx)     │
└──────────┬──────────────┘
           │ HTTP/SSE
           ↓
┌─────────────────────────┐
│  Backend Agent (FastAPI)│
│  Port 8003              │
│  - PydanticAI           │
│  - Cortex Search        │
│  - Glean Integration    │
└──────────┬──────────────┘
           │
      ┌────┴────┐
      ↓         ↓
┌──────────┐ ┌──────────┐
│  Cortex  │ │  Glean   │
│  Search  │ │  Proxy   │
└──────────┘ │ 8001/8090│
             └──────────┘
```

**Key Components:**
- **Chat Widget** - TypeScript/React with Vite
- **Backend API** - FastAPI + PydanticAI agent (port 8003)
- **Demo Server** - Nginx serving static HTML (port 8004)
- **Glean Proxy** - MCP server for internal knowledge (ports 8001, 8090) - **shared with AgentSmith**
- **GitHub Proxy** - MCP server for GitHub integration (port 8005) - **shared with AgentSmith**

## Development

**Watch backend logs:**
```bash
docker compose logs -f web-support-agent
```

**Develop widget with hot reload:**
```bash
cd chat-widget
npm run dev  # Starts dev server on http://localhost:5173
```

**Rebuild widget after changes:**
```bash
cd chat-widget
npm run build
```

**Check service status:**
```bash
docker compose ps
```

**Check API health:**
```bash
curl http://localhost:8003/health
```

## Configuration

### Environment Variables

Create `.env` file in the webagent directory:

```bash
# Snowflake Cortex Configuration (required)
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_PASSWORD=your_password

# Cortex Search Service
CORTEX_SEARCH_SERVICE=cke_snowflake_docs_service
CORTEX_SEARCH_DATABASE=snowflake_docs_cke
CORTEX_SEARCH_SCHEMA=shared

# OpenAI API Key (optional, for voice features)
OPENAI_API_KEY=sk-your-key-here

# Conversation History Limit
CONVERSATION_HISTORY_LIMIT=10

# Glean Configuration (optional)
# Controls whether webagent uses Glean for internal knowledge search
# Set to 'false' to disable Glean access (webagent will only use Snowflake docs)
# Set to 'true' to enable Glean search (requires glean-proxy service)
# Note: When false, glean-proxy still starts for AgentSmith to use
GLEAN_ENABLED=false
```

**About GLEAN_ENABLED:**
- When `false` (default): The webagent only uses Cortex Search for Snowflake documentation. The glean-proxy service still starts to provide Glean access to AgentSmith.
- When `true`: The webagent can also search internal Glean knowledge in addition to Snowflake docs.

### Running with AgentSmith

This webagent project hosts shared services (glean-proxy and github-proxy) that AgentSmith connects to via the `aura-shared-network`.

**Startup order:**

1. **Create shared resources** (if not already created):
   ```bash
   docker network create aura-shared-network
   docker volume create aura-glean-tokens
   ```

2. **Start webagent** (hosts the shared services):
   ```bash
   cd /path/to/webagent
   docker compose up -d
   ```

3. **Start agentsmith** (connects to shared services):
   ```bash
   cd /path/to/agentsmith
   docker compose up -d
   ```

AgentSmith will automatically connect to the glean-proxy (port 8001) and github-proxy (port 8005) running in webagent.

## Troubleshooting

### Widget Not Appearing

1. Check widget build files exist:
   ```bash
   ls chat-widget/dist/
   ```
2. Rebuild if needed: `cd chat-widget && npm run build`
3. Hard refresh browser: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows/Linux)

### Backend Not Responding

1. Check if backend is running:
   ```bash
   curl http://localhost:8003/health
   ```
2. View logs:
   ```bash
   docker compose logs -f web-support-agent
   ```
3. Verify environment variables in `.env`

### Port Conflicts (8001 or 8090)

**Error:** "port is already allocated"

**Cause:** Another glean-proxy is running (probably from troubleshooting)

**Solution:**
```bash
# Start only web-support-agent (reuse existing glean-proxy)
docker compose up -d web-support-agent
```

### Streaming Not Working

1. Check browser console for errors (F12)
2. Verify backend supports streaming:
   ```bash
   curl -X POST http://localhost:8003/query \
     -H "Content-Type: application/json" \
     -d '{"message": "test", "conversation_id": "test", "stream": true}'
   ```

### Voice Not Working

See [docs/VOICE.md](docs/VOICE.md) for voice-specific troubleshooting.

## Documentation

- [Voice Features Guide](docs/VOICE.md) - Voice chat setup and features

## Support

For issues:
1. Check logs: `docker compose logs -f`
2. Verify `.env` configuration
3. Check service health: `curl http://localhost:8003/health`
4. Review troubleshooting section above
