# Snowflake Customer 360 Suite

> Transform your customer support operations with AI-powered insights, automated troubleshooting, and comprehensive analytics built natively on Snowflake.

## Table of Contents

- [Why Customer 360?](#why-customer-360)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Demo Flow](#demo-flow)
- [Quick Start](#quick-start)
- [Component Documentation](#component-documentation)
- [Development](#development)
- [Deployment](#deployment)
- [Monitoring & Operations](#monitoring--operations)
- [Roadmap](#roadmap)
- [Support & Contributing](#support--contributing)

---

## Why Customer 360?

### The Problem

Customer Support is expected to be a **$70B industry by 2030**. Many enterprises already have support and customer data in Snowflake, but face limited options:

**Option 1: Build from Scratch**
- Expensive and time-consuming
- Fragmented tooling
- Difficult to maintain
- No enterprise context (product usage, sales data)

**Option 2: Off-the-Shelf Vendors**
- $100k+ annual costs
- Limited enterprise integration
- Siloed from your Snowflake data
- Generic insights without product context

### The Solution

**Snowflake's Customer 360 Suite** leverages your comprehensive sales, support, and product data to deliver value across your organization:

**For Your Customers:**
- AI-powered self-service support
- Instant answers to common questions
- Seamless escalation for complex cases
- 24/7 availability

**For Your Support Team:**
- AI diagnostic tools with enterprise intelligence
- Automated troubleshooting workflows
- Fast access to historical case context
- Best-in-class knowledge integration (Glean)

**For Your Product/Exec Team:**
- 360° insights on product performance
- Support trend analysis and forecasting
- Product area health metrics
- Data-driven decision making

**For Your Admin/AI Team:**
- Taxonomy and knowledge base management
- Agent performance testing (AgentSim)
- Custom workflow configuration
- Pre-deployment validation

---

## Architecture

```
support-data-agent/
│
├── troubleshooting/          # Support Engineer Tools
│   ├── FastAPI REST API      • Diagnostic data queries (18+ endpoints)
│   ├── MCP Servers           • DDA diagnostic tools + Glean integration
│   └── AI Agent              • Natural language troubleshooting interface
│
├── 360app/                   # Product/Executive Dashboard
│   ├── Frontend (Next.js)    • Analytics visualization
│   ├── Backend (FastAPI)     • Snowflake Cortex AI classification
│   └── Database              • Snowflake + Cortex AI
│
├── agentsim/                 # Agent Testing & Validation
│   ├── Frontend (Next.js)    • Test management interface
│   ├── Backend (FastAPI)     • Simulation engine
│   └── Database (SQLite)     • Test results & metrics
│
└── consumer/                 # Customer-Facing Portal (Planned)
    ├── Website Integration   • Chat widget
    ├── AI Support Bot        • Self-service answers
    └── Case Creation         • Salesforce integration
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15+, React 19, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+ |
| **Database** | Snowflake (primary), SQLite (AgentSim) |
| **AI/ML** | Snowflake Cortex, OpenAI, Anthropic Claude |
| **Integration** | Salesforce API, Glean MCP |
| **Deployment** | Docker, Docker Compose |

---

## Key Features

### Troubleshooting Service
- 18+ diagnostic query endpoints
- AI-powered troubleshooting agent
- MCP server architecture for tool composition
- Glean knowledge base integration
- Natural language query interface
- Environment-based data masking
- In-memory caching with 15-min TTL

### 360 Dashboard
- Snowflake Cortex AI case classification
- Product area performance tracking
- Resolution rate analytics
- Trend analysis and forecasting
- Custom business context
- Real-time metrics

### AgentSim Platform
- Multi-turn conversation simulation
- Custom persona support
- Live progress tracking
- Comprehensive metrics (success rate, avg turns, efficiency)
- Pre-deployment agent validation

---

## Demo Flow

The Customer 360 Suite demonstrates value across four stakeholder perspectives:

### 1. External Customers (Consumer Portal)
**Component:** `/consumer` (planned)
- Visit company website with integrated support chat
- Ask product questions → receive instant AI-powered answers
- Complex issues → automatic support case creation in Salesforce

### 2. Support Engineers (Troubleshooting Tools)
**Component:** `/troubleshooting`
- View newly created cases in Salesforce integration
- Chat with AI troubleshooting agent for diagnosis
- Access comprehensive diagnostic data from Snowflake
- Respond to customers with recommended solutions

### 3. Product Team & Executives (360 Dashboard)
**Component:** `/360app`
- Review product area performance metrics
- Drill into specific products with active cases
- View AI-generated insights and trends
- Track resolution rates and customer satisfaction

### 4. Admins & AI/IT Teams (Testing & Configuration)
**Component:** `/agentsim`
- Build and maintain knowledge taxonomies
- Test agent performance before deployment
- Configure custom workflows
- Monitor agent behavior with simulated scenarios

---

## Quick Start

### Prerequisites

- Python 3.11+ with `uv` installed ([installation guide](https://github.com/astral-sh/uv))
- Node.js 18+ and npm
- Snowflake account with Cortex AI access
- Docker & Docker Compose (for full suite)

### Environment Setup

1. **Clone the repository:**
```bash
cd /path/to/support-data-agent
```

2. **Configure Snowflake credentials:**
```bash
# For troubleshooting service
cd troubleshooting
cp .env.example .env
# Edit .env with your Snowflake credentials

# For 360app
cd ../360app
cp env.example .env
# Edit .env with your Snowflake credentials
```

3. **Install dependencies:**
```bash
# Troubleshooting (Python)
cd troubleshooting
uv sync

# 360app Frontend
cd ../360app/frontend
npm install

# AgentSim Frontend
cd ../../agentsim/frontend
npm install
```

### Launch Components

#### Option A: Full Suite with Docker

```bash
# Launch everything at once
docker compose up -d
```

Access points:
- 360 Dashboard: http://localhost:3000
- Troubleshooting API: http://localhost:8000
- AgentSim: http://localhost:3001

#### Option B: Individual Components

**Troubleshooting Service:**
```bash
cd troubleshooting
# Start REST API
uv run uvicorn app.main:app --reload --port 8000

# Or start AI Agent (separate terminal)
python start_services.py
uv run app/agent_cli.py
```
See [troubleshooting/README.md](troubleshooting/README.md) for full details.

**360 Dashboard:**
```bash
cd 360app

# Start backend
cd backend
uvicorn main:app --reload --port 8000

# Start frontend (separate terminal)
cd ../frontend
npm run dev
```
See [360app/README.md](360app/README.md) for full details.

**AgentSim Testing Platform:**
```bash
cd agentsim

# Start backend
uvicorn backend.main:app --reload --port 8002

# Start frontend (separate terminal)
cd frontend
npm run dev
```
See [agentsim/README.md](agentsim/README.md) for full details.

---

## Component Documentation

Each component has detailed documentation in its respective directory:

| Component | Purpose | Documentation |
|-----------|---------|---------------|
| **Troubleshooting** | Support engineer diagnostic tools & AI agent | [troubleshooting/README.md](troubleshooting/README.md) |
| **360app** | Executive dashboard with product insights | [360app/README.md](360app/README.md) |
| **AgentSim** | Agent testing & validation platform | [agentsim/README.md](agentsim/README.md) |
| **Consumer** | Customer-facing support portal | Coming soon |

---

## Development

### Project Structure

```
support-data-agent/
├── troubleshooting/
│   ├── app/
│   │   ├── api/v1/endpoints/    # REST API endpoints
│   │   ├── core/                # DB, cache, config
│   │   ├── services/            # Business logic
│   │   ├── mcp_server.py        # DDA MCP server
│   │   ├── glean_proxy.py       # Glean integration
│   │   └── agent_cli.py         # AI agent CLI
│   └── tests/
│
├── 360app/
│   ├── frontend/
│   │   └── app/                 # Next.js pages & components
│   └── backend/
│       ├── api/                 # FastAPI routes
│       └── services/            # Snowflake operations
│
├── agentsim/
│   ├── frontend/
│   │   └── src/                 # React components
│   └── backend/
│       ├── api/                 # FastAPI routes
│       ├── core/                # Simulation engine
│       └── models/              # Database models
│
└── docs/                        # Shared documentation
```

### Testing

```bash
# Troubleshooting service tests
cd troubleshooting
uv run pytest --cov=app

# AgentSim tests
cd agentsim
pytest tests/ -v --cov=backend
```

### Code Quality

```bash
# Format code
uv run black app/

# Lint
uv run flake8 app/

# Type checking
uv run mypy app/
```

---

## Deployment

### Docker Deployment

Each component includes Docker configuration:

```bash
# Build and run individual component
cd troubleshooting
docker build -t customer360-troubleshooting:latest .
docker run -p 8000:8000 --env-file .env customer360-troubleshooting:latest

# Or use Docker Compose for full suite
docker compose up -d
```

### Environment Configuration

See component-specific README files for detailed environment variable documentation:
- [troubleshooting/.env.example](troubleshooting/.env.example)
- [360app/env.example](360app/env.example)
- [agentsim/.env.example](agentsim/.env.example)

---

## Monitoring & Operations

### Health Checks

Each service exposes health endpoints:
- `/health` - Basic service health
- `/ready` - Dependency readiness check

### API Documentation

When services are running, access interactive API docs:
- Troubleshooting: http://localhost:8000/api/docs
- 360app Backend: http://localhost:8000/docs
- AgentSim: http://localhost:8002/docs

### Logging

All services use structured logging to stdout:
```
2024-01-15 10:30:45 - app.main - INFO - Starting service in local environment
```

---

## Roadmap

### MVP (Current)
- ✅ Troubleshooting FastAPI service with 18+ endpoints
- ✅ AI agent with MCP servers (DDA + Glean)
- ✅ 360 Dashboard with Cortex AI classification
- ✅ AgentSim testing platform
- ✅ Docker deployment
- ⏳ Consumer-facing support portal

### Phase 2 (Q1 2025) -- TO BE UPDATED
- OAuth2 + JWT authentication
- Redis distributed caching
- JIRA integration
- Salesforce bi-directional sync
- Enhanced metrics & monitoring
- Kubernetes deployment manifests

### Phase 3 (Q2 2025) -- TO BE UPDATED
- Advanced analytics & forecasting
- Custom workflow builder
- Multi-language support
- Mobile-responsive consumer portal
- Self-service taxonomy management

---

## Support & Contributing

### Getting Help

1. Check component-specific README files for detailed documentation
2. Review API documentation at `/api/docs` endpoints
3. Contact the Customer Experience Engineering team

### Contributing

See [CONTRIBUTING.md](360app/CONTRIBUTING.md) for development guidelines and best practices.

---

## License

Internal Snowflake project - not for external distribution.

---

## Contact

**Customer Experience Engineering Team**
Snowflake Computing, Inc.
