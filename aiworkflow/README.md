# AI Workflow

A system for vibe-coding agentic workflows with a VSCode-like interface.

## Features

- **VSCode-like UI**: Title bar, file browser, code editor, graph visualization, and AI chat
- **Monaco Editor**: Full-featured code editor with syntax highlighting
- **Resizable Panes**: Drag-to-resize all panes like VSCode (sidebar, editor, graph, chat)
- **File Management**: Create, rename, delete, and edit files
- **Workflow Visualization**: Visual representation of workflow nodes and connections
- **AI Chat Interface**: Interactive AI assistant for workflow development
- **Light/Dark Themes**: Toggle between light and dark themes with persistent preferences
- **Python Backend**: FastAPI backend with fake data for development

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+

### Setup

1. **Create and activate a Python virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install backend dependencies:**

   ```bash
   pip install --upgrade pip
   pip install --only-binary=all -r requirements.txt
   ```

3. **Install frontend dependencies:**

   ```bash
   npm install
   ```

4. **Start the backend server:**

   ```bash
   source venv/bin/activate  # Make sure virtual env is activated
   python backend.py
   ```

   The backend will run on http://localhost:8000

5. **Start the frontend development server (in a new terminal):**

   ```bash
   npm run dev
   ```

   The frontend will run on http://localhost:3000 (or 3001 if 3000 is busy)

6. **Open your browser** and navigate to http://localhost:3000

## Project Structure

```
aiworkflow/
├── src/                    # Frontend source code
│   ├── components/         # React components
│   ├── services/           # API services
│   ├── App.tsx            # Main app component
│   └── main.tsx           # Entry point
├── backend.py             # Python FastAPI backend
├── requirements.txt       # Python dependencies
├── package.json          # Node.js dependencies
└── vite.config.ts        # Vite configuration
```

## API Endpoints

The backend provides the following endpoints:

- `GET /api/files` - List files and folders
- `GET /api/files/content?path=<path>` - Get file content
- `POST /api/files` - Create new file
- `DELETE /api/files?path=<path>` - Delete file
- `PUT /api/files/rename` - Rename file
- `PUT /api/files/content` - Write file content
- `POST /api/chat` - Send message to AI chatbot
- `GET /api/workflow/graph` - Get workflow graph

## Development

The frontend uses Vite for fast development with hot reloading. The backend uses FastAPI with automatic API documentation available at http://localhost:8000/docs.

## Next Steps

This is a foundation for building a full AI workflow system. Future enhancements could include:

- Real file system integration
- Actual AI model integration
- Workflow execution engine
- Real-time collaboration
- Plugin system
- Workflow templates
