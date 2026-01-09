# Agent OS UI (Sandbox)

This is an **experimental, sandbox UI** for interacting with the Agent OS
MetaOrchestrator ("Brain").

## Purpose
- Provide a lightweight UI shell for:
  - Chat-based interaction with the Brain
  - Inspecting available agents
- Intended for **local development and learning only**

## Non-goals
- Production UI
- Authentication
- Workflow execution
- Persistence or memory
- Multi-user support

## Structure
- Brain: chat-based interface (LLM-backed)
- Agents: read-only registry view
- Workflows / Runs: placeholders for future exploration

## Running locally

```bash
npm install
npm run dev
