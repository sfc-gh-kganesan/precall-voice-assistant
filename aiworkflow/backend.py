from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
from datetime import datetime

app = FastAPI(title="AI Workflow Backend", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class FileItem(BaseModel):
    name: str
    type: str  # 'file' or 'folder'
    path: str
    children: List["FileItem"] = []


class FileContentRequest(BaseModel):
    path: str
    content: str


class FileRenameRequest(BaseModel):
    oldPath: str
    newName: str


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class GraphNode(BaseModel):
    id: str
    title: str
    description: str
    type: str  # 'start', 'process', 'decision', 'end'
    position: Dict[str, int]


class WorkflowGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[Dict[str, str]]


class WorkflowRenameRequest(BaseModel):
    workflowId: str
    newName: str


# Fake data
fake_workflows = {
    "default-workflow-id": {
        "id": "default-workflow-id",
        "name": "Untitled Workflow",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
}

fake_files = [
    {
        "name": "workflows",
        "type": "folder",
        "path": "workflows",
        "children": [
            {
                "name": "main.py",
                "type": "file",
                "path": "workflows/main.py",
                "children": [],
            },
            {
                "name": "utils.py",
                "type": "file",
                "path": "workflows/utils.py",
                "children": [],
            },
        ],
    },
    {
        "name": "config",
        "type": "folder",
        "path": "config",
        "children": [
            {
                "name": "settings.json",
                "type": "file",
                "path": "config/settings.json",
                "children": [],
            }
        ],
    },
    {"name": "README.md", "type": "file", "path": "README.md", "children": []},
]

fake_file_contents = {
    "workflows/main.py": '''from typing import Dict, Any
import asyncio
from workflows.utils import process_data

class WorkflowEngine:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
    
    async def execute_workflow(self, workflow_data: Dict[str, Any]):
        """Execute a workflow with the given data"""
        result = await process_data(workflow_data)
        return result
    
    def add_node(self, node_id: str, node_config: Dict[str, Any]):
        """Add a new node to the workflow"""
        self.nodes[node_id] = node_config
    
    def connect_nodes(self, from_node: str, to_node: str):
        """Connect two nodes in the workflow"""
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append(to_node)

# Example workflow
async def main():
    engine = WorkflowEngine()
    
    # Add some nodes
    engine.add_node("start", {"type": "input", "description": "Start node"})
    engine.add_node("process", {"type": "transform", "description": "Process data"})
    engine.add_node("end", {"type": "output", "description": "End node"})
    
    # Connect nodes
    engine.connect_nodes("start", "process")
    engine.connect_nodes("process", "end")
    
    # Execute workflow
    result = await engine.execute_workflow({"data": "test"})
    print(f"Workflow result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
''',
    "workflows/utils.py": '''from typing import Dict, Any
import json

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the input data"""
    processed = {
        "original": data,
        "processed_at": "2024-01-01T00:00:00Z",
        "status": "completed"
    }
    return processed

def validate_workflow(workflow_config: Dict[str, Any]) -> bool:
    """Validate workflow configuration"""
    required_fields = ["nodes", "edges"]
    return all(field in workflow_config for field in required_fields)

def serialize_workflow(workflow: Dict[str, Any]) -> str:
    """Serialize workflow to JSON string"""
    return json.dumps(workflow, indent=2)
''',
    "config/settings.json": """{
  "workflow": {
    "max_nodes": 100,
    "timeout": 300,
    "retry_attempts": 3
  },
  "ai": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "ui": {
    "theme": "dark",
    "font_size": 14,
    "auto_save": true
  }
}""",
    "README.md": """# AI Workflow

A system for vibe-coding agentic workflows.

## Features

- Visual workflow editor
- AI-powered code assistance
- Real-time collaboration
- Workflow execution engine

## Getting Started

1. Install dependencies
2. Run the development server
3. Start building your workflows!

## Examples

See the `workflows/` directory for example implementations.
""",
}

fake_workflow_graph = {
    "nodes": [
        {
            "id": "start",
            "title": "Start Node",
            "description": "Workflow entry point",
            "type": "start",
            "position": {"x": 100, "y": 50},
        },
        {
            "id": "process",
            "title": "Data Processing",
            "description": "Process input data",
            "type": "process",
            "position": {"x": 200, "y": 150},
        },
        {
            "id": "decision",
            "title": "Decision Point",
            "description": "Make routing decision",
            "type": "decision",
            "position": {"x": 300, "y": 250},
        },
        {
            "id": "end",
            "title": "End Node",
            "description": "Workflow completion",
            "type": "end",
            "position": {"x": 400, "y": 350},
        },
    ],
    "edges": [
        {"from": "start", "to": "process"},
        {"from": "process", "to": "decision"},
        {"from": "decision", "to": "end"},
    ],
}

# API Endpoints


@app.get("/")
async def root():
    return {"message": "AI Workflow Backend API", "version": "1.0.0"}


@app.get("/api/files", response_model=List[FileItem])
async def get_files():
    """Get list of files and folders"""
    return fake_files


@app.get("/api/files/content")
async def get_file_content(path: str):
    """Get content of a specific file"""
    if path in fake_file_contents:
        return {"content": fake_file_contents[path]}
    else:
        # Return default content for new files
        return {"content": "# New file\n\nStart coding here..."}


@app.post("/api/files")
async def create_file(request: Dict[str, str]):
    """Create a new file"""
    path = request.get("path", "")
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")

    # Add to fake files (simplified)
    fake_file_contents[path] = "# New file\n\nStart coding here..."
    return {"message": f"File {path} created successfully"}


@app.delete("/api/files")
async def delete_file(path: str):
    """Delete a file"""
    if path in fake_file_contents:
        del fake_file_contents[path]
        return {"message": f"File {path} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.put("/api/files/rename")
async def rename_file(request: FileRenameRequest):
    """Rename a file"""
    old_path = request.oldPath
    new_name = request.newName

    if old_path in fake_file_contents:
        # Create new path with new name
        path_parts = old_path.split("/")
        path_parts[-1] = new_name
        new_path = "/".join(path_parts)

        # Move content
        content = fake_file_contents[old_path]
        del fake_file_contents[old_path]
        fake_file_contents[new_path] = content

        return {"message": f"File renamed from {old_path} to {new_path}"}
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.put("/api/files/content")
async def write_file_content(request: FileContentRequest):
    """Write content to a file"""
    path = request.path
    content = request.content

    fake_file_contents[path] = content
    return {"message": f"Content written to {path}"}


@app.post("/api/chat", response_model=ChatResponse)
async def send_chat_message(request: ChatMessage):
    """Send a message to the AI chatbot"""
    message = request.message.lower()

    # Simple fake AI responses based on keywords
    if "workflow" in message:
        response = "I can help you build workflows! Try creating nodes and connecting them. What kind of workflow are you working on?"
    elif "error" in message or "bug" in message:
        response = "Let me help you debug that. Can you share the error message or describe what's not working?"
    elif "help" in message:
        response = "I'm here to help! I can assist with workflow design, debugging, code review, and best practices. What would you like to work on?"
    elif "python" in message:
        response = "Great choice! Python is perfect for workflows. I can help you with async/await patterns, data processing, and workflow orchestration."
    elif "node" in message:
        response = "Nodes are the building blocks of workflows. Each node can have inputs, outputs, and processing logic. What type of node do you need?"
    else:
        response = "That's interesting! Tell me more about what you're trying to accomplish. I can help with workflow design, implementation, or debugging."

    return ChatResponse(response=response)


@app.get("/api/workflow/graph", response_model=WorkflowGraph)
async def get_workflow_graph():
    """Get the current workflow graph"""
    return fake_workflow_graph


@app.put("/api/workflow/rename")
async def rename_workflow(request: WorkflowRenameRequest):
    """Rename a workflow"""
    workflow_id = request.workflowId
    new_name = request.newName

    if workflow_id in fake_workflows:
        fake_workflows[workflow_id]["name"] = new_name
        fake_workflows[workflow_id]["updated_at"] = datetime.now().isoformat()
        return {"message": f"Workflow renamed to '{new_name}' successfully"}
    else:
        raise HTTPException(status_code=404, detail="Workflow not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
