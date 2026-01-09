import os
from openai import OpenAI
from backend.models import ChatRequest, ChatResponse

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def chat(request: ChatRequest) -> ChatResponse:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[m.model_dump() for m in request.messages],
    )
    return ChatResponse(
        reply=response.choices[0].message.content,
    )