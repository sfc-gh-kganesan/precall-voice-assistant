# Creating a Workflow Using CLI (Cortex)

If you prefer to create workflows using the command line instead of the web interface:

### Prerequisites
- Have the Cortex CLI (`cortex`) installed and configured

### Steps

1. **Navigate to your project folder**
   ```bash
   cd /Users/rho/code/aura/p67/example_workflows/[project_folder]
   ```

2. **Copy template files** (if creating a new project manually)

   Copy the following files from the template folder:
   ```bash
   # Copy Cortex commands
   mkdir -p .cortex/commands
   cp -r ../template/.cortex/commands/* .cortex/commands/

   # Copy configuration
   mkdir -p conf
   cp -r ../template/conf/* conf/

   # Copy documentation
   cp ../template/AGENTS.md .
   cp ../template/LEARN_WORKFLOW.md .
   ```

3. **Start Cortex CLI**
   ```bash
   cortex
   ```

4. **Create the workflow specification**

   In the Cortex prompt:
   ```
   /create-workflow
   ```
   - Follow the interactive dialog to define your workflow
   - This creates the `workflow_spec.json` file

5. **Generate TypeScript implementation code**

   In the Cortex prompt:
   ```
   /generate-workflow-code
   ```
   - Follow the dialog to generate TypeScript implementation files
   - This creates the `src/steps/` directory with node implementations

### What Gets Created

After following these steps, your project will have:
```
project_folder/
├── .cortex/
│   └── commands/          # AI agent commands
├── conf/
│   └── workflow_graph_schema.json
├── src/
│   └── steps/            # TypeScript node implementations
├── workflow_spec.json    # Workflow definition
├── AGENTS.md             # Documentation
└── LEARN_WORKFLOW.md     # Workflow guide
```

# Creating a Workflow Using Workflow Editor UI

You can use the workflow editor UI to create the initial workflow graph.  But you need to go back to CLI mode to generate the code using
- cortex
- /generate-workflow-code

After the code is generated, you can go back to workflow editor UI to edit the code.

## Prerequisites

- Python 3.x installed
- `uv` package manager installed
- Git installed
- A web browser (Chrome, Firefox, Safari, or Edge)

## Setup Steps

### 0. Clone the Cortex Repository

If you haven't already, clone the cortex repository which contains the Coco Web Interface Server:

```bash
cd /Users/rho/code
git clone <cortex-repository-url> cortex
```


### 1. Start the Workflow Server

The workflow server handles file operations and serves the HTML interface.

```bash
cd /Users/rho/code/aura/p67/example_workflows
python3 workflow_server.py
```

**Expected Output:**
```
Starting workflow browser server...
Serving files from: /Users/rho/code/aura/p67/example_workflows
Server running at: http://localhost:8000

Open the workflow browser at:
  http://localhost:8000/workflow_browser.html

Press Ctrl+C to stop the server
```

### 2. Start the Coco Web Interface Server

The Coco server provides AI agent capabilities for workflow creation and editing.

**Open a new terminal window** and run:

```bash
cd /Users/rho/code/aura/p67/example_workflows
uv run python /Users/rho/code/cortex/cortexagent/codingagent/snova/web_api/fast_server.py
```

**Expected Output:**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8765 (Press CTRL+C to quit)
```

### 3. Open the Workflow Editor

Open your web browser and navigate to:

```
http://localhost:8000/workflow_editor.html
```

## What You Can Do

### Project Management
- **View Projects**: Browse existing workflow projects in the left panel
- **Add New Project**: Click the "**+ Add**" button to create a new project from template
- **Switch Projects**: Click on any project folder to load its workflow

### Workflow Editing
- **View Diagram**: Interactive Mermaid.js diagram in the center panel
- **Zoom & Pan**: Use zoom controls or mouse wheel to zoom, drag to pan
- **Edit Nodes**: Click on nodes to view/edit properties
- **Add Nodes**: Right-click on empty space to add new nodes
- **Connect Nodes**: Right-click on a node → "Connect" → click destination node
- **Delete Nodes/Edges**: Right-click on nodes or edges to delete

### AI Agent Chat
- **Ask Questions**: Use the chat panel on the right to ask the agent questions
- **Get Help**: Ask for help with workflow design, node configuration, etc.
- **Modify Workflow**: Request changes via natural language


## Troubleshooting

### Cortex Repository Not Found
If you get an error about the cortex repository path:
```bash
# Verify the cortex repository exists
ls /Users/rho/code/cortex/cortexagent/codingagent/snova/web_api/fast_server.py
```

If the file doesn't exist, you need to clone the cortex repository (see Step 0).

### Port Already in Use
If port 8000 or 8765 is already in use:

1. **Find the process:**
   ```bash
   lsof -i :8000
   lsof -i :8765
   ```

2. **Kill the process:**
   ```bash
   kill -9 <PID>
   ```

### Can't Connect to Agent
- Ensure both servers are running
- Check that port 8765 is accessible
- Look for error messages in the Coco server terminal
- Verify the cortex repository is properly set up

### Workflow Not Loading
- Ensure the project has a `workflow_spec.json` file
- Check the browser console for errors (F12)
- Verify the workflow server is serving files correctly

## Stopping the Servers

Press `Ctrl+C` in each terminal window to stop the servers gracefully.

## Tips

1. **Zoom Persistence**: The zoom level is preserved when switching between projects
2. **Auto-Save**: Click "Save Workflow" button to persist changes
3. **New Session**: Use "New Session" button in chat panel to reset the AI agent context
4. **Template Projects**: Use the template project as a reference for creating new workflows

## Example Workflow

Try this simple workflow creation:

1. Click "**+ Add**" and create a project called "demo"
2. Open the new "demo" project
3. In the chat, type: "Create a simple workflow with start, action, and end nodes"
4. The agent will help you create the workflow structure
5. Click nodes to customize their properties
6. Save your changes

---

**Happy workflow building!** 🚀

