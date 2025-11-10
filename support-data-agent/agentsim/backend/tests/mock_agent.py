"""Simple mock agent for testing AgentSim."""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

app = FastAPI(title="Mock Customer Support Agent")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    context: Optional[List[Message]] = None


class ChatResponse(BaseModel):
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    completion_signal: Optional[str] = None
    metadata: Dict[str, Any] = {}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Mock chat endpoint that simulates a customer support agent."""

    # Count turns
    turn_count = len(request.context) if request.context else 0

    # Simulate different responses based on content
    query_lower = request.message.lower()

    if "login" in query_lower or "password" in query_lower:
        if turn_count == 0:
            return ChatResponse(
                content="I can help you with login issues. Let me check your account status.",
                tool_calls=[{"tool": "check_account_status", "args": {"user": "test"}}],
                metadata={"model": "mock-agent", "tokens": 25},
            )
        else:
            return ChatResponse(
                content="I've checked your account and reset your password. You should be able to login now.",
                completion_signal="RESOLVED",
                metadata={"model": "mock-agent", "tokens": 30},
            )

    elif "help" in query_lower or "support" in query_lower:
        return ChatResponse(
            content="I'm here to help! What specific issue are you experiencing?",
            metadata={"model": "mock-agent", "tokens": 20},
        )

    elif "thank" in query_lower:
        return ChatResponse(
            content="You're welcome! Is there anything else I can help you with?",
            completion_signal="RESOLVED",
            metadata={"model": "mock-agent", "tokens": 22},
        )

    else:
        # Default response after a few turns
        if turn_count >= 2:
            return ChatResponse(
                content="I've addressed your concern. Is there anything else I can assist you with?",
                completion_signal="RESOLVED",
                metadata={"model": "mock-agent", "tokens": 25},
            )
        else:
            return ChatResponse(
                content=f"I understand your question about '{request.message}'. Let me help you with that.",
                metadata={"model": "mock-agent", "tokens": 28},
            )


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "mock-customer-support"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
