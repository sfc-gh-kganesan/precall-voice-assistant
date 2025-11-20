# AgentSmith Frontend

React Next.js frontend for the AgentSmith chatbot performance analysis platform.

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Architecture

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **State Management**: React Query (TanStack Query)
- **API Client**: Axios
- **Forms**: React Hook Form + Zod

## Project Structure

```
frontend/
├── src/
│   ├── app/           # Next.js pages (App Router)
│   ├── components/    # React components
│   └── lib/           # Utilities, API client, types
├── public/            # Static assets
└── package.json
```

## Features

- ✅ Project management
- ✅ Analysis configuration
- ✅ Live monitoring
- ✅ Results visualization
- ✅ Insights and recommendations

## Backend Integration

The frontend connects to the backend API at `http://localhost:8082`. Make sure the backend is running:

```bash
cd ..
uvicorn backend.main:app --reload --port 8082
```
