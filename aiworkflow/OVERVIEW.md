# AI Workflow
AI Workflow is a system for vibe-coding agentic workflows. It fits nicely in
between the UI-only workflow systems like n8n and the code-only workflow
systems like Langraph.

This is structured as a web-app. The UI will be in Typescript with node. The backend will be Python.


## UI
The UI resembles VSCode:
- title bar at the top with the name of the workflow
- file browser on the left
- pane for code editor (we'll be using Microsoft's monaco editor)
- pane for visualizing the graph as constructed
- below the code pane there's a chat pane for the AI (like Cursor's).


## Backend
- Endpoint for file operations
	- list
	- rename
	- delete
	- create
	- reading file contents
	- writing file contents
- Endpoint for interacting with the AI chatbot
	- send message
	- stream results
- Endpoint for fetching workflow graph



