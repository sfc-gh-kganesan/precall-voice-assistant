from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import os
import glob

app = Flask(__name__)

def get_workflow_files():
    """Get all *.workflow.json files in the current directory"""
    base_dir = os.path.dirname(__file__)
    pattern = os.path.join(base_dir, '*.workflow.json')
    files = glob.glob(pattern)
    workflows = []
    for file_path in files:
        filename = os.path.basename(file_path)
        name = filename.replace('.workflow.json', '')
        workflows.append({
            "id": filename,
            "name": name,
            "filename": filename
        })
    return workflows

# Mock data for chat messages
chat_messages = [
    {
        "id": 1,
        "role": "assistant",
        "content": "Hi! I'm your AI assistant. I can help you configure and optimize your workflow nodes. Select a node to get started, or ask me anything about building data workflows.",
        "timestamp": datetime.now().strftime("%I:%M %p"),
    }
]


@app.route("/")
def index():
    workflows = get_workflow_files()
    return render_template(
        "index.html",
        workflows=workflows
    )


@app.route("/api/workflows", methods=["GET"])
def list_workflows():
    """List all workflow files"""
    workflows = get_workflow_files()
    return jsonify(workflows)


@app.route("/api/workflows/create", methods=["POST"])
def create_workflow():
    """Create a new workflow file"""
    data = request.json
    name = data.get("name", "untitled")
    
    base_dir = os.path.dirname(__file__)
    filename = f"{name}.workflow.json"
    filepath = os.path.join(base_dir, filename)
    
    counter = 1
    while os.path.exists(filepath):
        filename = f"{name}{counter}.workflow.json"
        filepath = os.path.join(base_dir, filename)
        counter += 1
    
    initial_data = {
        "nodes": [
            {
                "id": "start",
                "title": "Start",
                "description": "",
                "color": "#6b7280",
                "x": 100,
                "y": 100,
                "isStart": True
            }
        ],
        "edges": []
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(initial_data, f, indent=2)
        return jsonify({
            "success": True,
            "filename": filename,
            "name": filename.replace('.workflow.json', '')
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")

    # Add user message
    chat_messages.append(
        {
            "id": len(chat_messages) + 1,
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().strftime("%I:%M %p"),
        }
    )

    # Mock AI response
    ai_response = f"I received your message: '{user_message}'. I can help you with workflow configuration. Try asking me about specific nodes or data transformations!"

    chat_messages.append(
        {
            "id": len(chat_messages) + 1,
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().strftime("%I:%M %p"),
        }
    )

    return jsonify({"messages": chat_messages[-2:]})  # Return last 2 messages


@app.route("/api/chat/messages", methods=["GET"])
def get_chat_messages():
    return jsonify(chat_messages)


@app.route("/api/workflow/<filename>", methods=["GET"])
def get_workflow(filename):
    """Load workflow from specific file"""
    if not filename.endswith('.workflow.json'):
        filename = f"{filename}.workflow.json"
    
    workflow_path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(workflow_path, 'r') as f:
            workflow_data = json.load(f)
        return jsonify(workflow_data)
    except FileNotFoundError:
        return jsonify({"error": "Workflow file not found"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in workflow file"}), 400


@app.route("/api/workflow/<filename>", methods=["POST"])
def save_workflow(filename):
    """Save workflow to specific file"""
    if not filename.endswith('.workflow.json'):
        filename = f"{filename}.workflow.json"
    
    workflow_path = os.path.join(os.path.dirname(__file__), filename)
    try:
        workflow_data = request.json
        with open(workflow_path, 'w') as f:
            json.dump(workflow_data, f, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001, use_reloader=False)
