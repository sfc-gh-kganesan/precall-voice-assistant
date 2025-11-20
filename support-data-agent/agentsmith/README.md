# AgentSmith - Chatbot Performance Analysis Platform

AgentSmith is a comprehensive platform for analyzing real chatbot conversations to identify performance issues, find trends in customer issues, and recommend optimizations to improve agent design.

## Overview

AgentSmith helps support engineers, IT engineers, and product managers:
- **Analyze real conversations** from production chatbot deployments
- **Identify trends** in customer issues and pain points
- **Find design gaps** in prompts, tools, and knowledge bases
- **Get AI-powered recommendations** with specific code changes
- **Track improvements** over time with analysis history

## Project Structure

```
agentsim/
├── backend/              # FastAPI backend
│   ├── api/             # API routes and schemas
│   ├── core/            # Core simulation engine
│   ├── models/          # Database models
│   └── services/        # Business logic
├── frontend/            # Next.js frontend
│   ├── src/
│   │   ├── app/        # Next.js pages
│   │   ├── components/ # React components
│   │   └── lib/        # API client & types
│   └── package.json
├── tests/               # Backend tests
└── pyproject.toml
```

## Features

### Backend
- ✅ FastAPI REST API
- ✅ Multi-turn conversation simulation
- ✅ Live progress tracking with incremental storage
- ✅ Custom persona support
- ✅ Snowflake Cortex integration
- ✅ Comprehensive metrics tracking
- ✅ 49% test coverage (25/26 tests passing)

### Frontend (In Progress)
- ✅ Next.js 14 with App Router
- ✅ TypeScript & Tailwind CSS
- ✅ API client configured
- ✅ Project management pages
- 🚧 Simulation configuration
- 🚧 Live monitoring
- 🚧 Results dashboard
- 🚧 Insights & recommendations

## Quick Start

### Backend

1. Install dependencies:
```bash
uv sync
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the server:
```bash
python -m backend.main
# Or with uvicorn directly:
uvicorn backend.main:app --reload --port 8080
```

Backend will be available at http://localhost:8080

### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start dev server:
```bash
npm run dev
```

Frontend will be available at http://localhost:3000

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Key API Endpoints

### Projects
- `POST /api/projects/` - Create project
- `GET /api/projects/` - List projects
- `GET /api/projects/{id}` - Get project
- `DELETE /api/projects/{id}` - Delete project

### Simulations
- `POST /api/simulations/` - Create & start simulation
- `GET /api/simulations/{id}` - Get simulation status
- `GET /api/simulations/{id}/results` - Get results
- `GET /api/simulations/{id}/conversations` - Get all conversations

### Conversations
- `GET /api/conversations/{id}` - Get conversation details

## Testing

### Backend Tests
```bash
pytest tests/ -v --cov=backend
```

Current coverage: 49% (25/26 passing)

### E2E Tests
```bash
# Test with mock agent
python test_e2e.py

# Test with Snowflake Cortex
python test_cortex_e2e.py
```

## Development

### Adding New Features

1. Backend changes go in `backend/`
2. Frontend changes go in `frontend/src/`
3. Add tests in `tests/`

### Database

SQLite database (`agentsim.db`) is created automatically.

To reset:
```bash
rm agentsim.db
```

## Architecture

### Backend
- **Framework**: FastAPI
- **Database**: SQLAlchemy + SQLite
- **Async**: asyncio for concurrent simulations
- **LLM Integration**: OpenAI/Anthropic/Snowflake Cortex

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **State**: React Query (TanStack Query)
- **Forms**: React Hook Form + Zod

## Configuration

### Agent Configuration
Configure your agent in the Projects section:
- Agent endpoint URL
- Authentication (none/bearer/api_key/basic)
- Business context
- Custom headers (optional)

### Simulation Configuration
- Number of simulations
- Concurrency level
- Max turns per conversation
- Timeout settings
- Stop conditions
- Custom personas

## Monitoring

Live progress tracking shows:
- Overall simulation status
- Individual conversation progress
- Turn-by-turn Q&A updates
- Success/failure indicators

## Metrics

Tracked metrics include:
- Success rate
- Average turns to completion
- Average duration
- Efficiency scores
- Tool usage statistics
- Custom metrics

## Insights

Get actionable recommendations:
- Common failure patterns
- Performance by persona type
- Areas for improvement
- Timeout optimization
- Multi-turn success rates

## Contributing

1. Create a feature branch
2. Make changes
3. Add tests
4. Submit PR

## License

MIT
