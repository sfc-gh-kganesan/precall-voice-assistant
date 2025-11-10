from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message: str
    sessionId: str


class ChatMessageResponse(BaseModel):
    response: str
    suggestedQueries: list[str] | None = None
