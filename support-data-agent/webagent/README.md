# Snowflake AI Chat Widget

Modern chat widget with AI-powered support for the Snowflake AI Data Cloud.

## Prerequisites

- Docker & Docker Compose
- Node.js 18+

## Quick Start

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
- **Glean Proxy** - MCP server for internal knowledge (ports 8001, 8090)

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
```

### Running with Troubleshooting Services

If you're also running the troubleshooting agent (which uses the same glean-proxy), start only the web-support-agent:

```bash
# Start only web-support-agent (skip glean-proxy to avoid port conflicts)
docker compose up -d web-support-agent
```

This reuses troubleshooting's glean-proxy service.

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
