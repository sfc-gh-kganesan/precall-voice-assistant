from fastapi import APIRouter

from ..schemas.chat import ChatMessageRequest, ChatMessageResponse

router = APIRouter()


@router.post("/messages", response_model=ChatMessageResponse)
async def send_message(payload: ChatMessageRequest):
    return ChatMessageResponse(
        response="I can help you analyze support metrics. Try asking about top issues, "
        "resolution rates, or specific products.",
        suggestedQueries=[
            "What are the top issues?",
            "Show me product metrics",
            "What's the average case life?",
        ],
    )
