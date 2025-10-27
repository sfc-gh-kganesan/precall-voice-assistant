from typing import Annotated

from fastapi import APIRouter, Form
from fastapi.responses import StreamingResponse
from pydantic_ai import ModelMessagesTypeAdapter

from ..services.cortex_agent import stream_chat_response

router = APIRouter()


@router.post("/messages")
async def send_message(
    message: Annotated[str, Form()],
    message_history: Annotated[str | None, Form()] = None,
) -> StreamingResponse:
    """Send query to Cortex Analyst and stream response with conversation history.

    This endpoint streams newline-delimited JSON messages containing
    the user's message and the agent's streaming response. It maintains
    conversation context by accepting and returning message history.

    Parameters
    ----------
    message : str
        The user's chat message
    message_history : str | None
        JSON-serialized array of previous conversation messages (optional)

    Returns
    -------
    StreamingResponse
        Streaming response with role, timestamp, content, and final history update
    """
    # Parse and validate message history if provided
    history = []
    if message_history:
        try:
            history = ModelMessagesTypeAdapter.validate_json(message_history)
        except Exception as e:
            # Log error but continue with empty history rather than failing
            print(f"Warning: Failed to parse message history: {e}")

    return StreamingResponse(stream_chat_response(message, history), media_type="text/plain")
