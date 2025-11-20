"""Agent client for communicating with target agent endpoint."""

from typing import Optional, List, Dict, Any
import httpx
from backend.core.interfaces import AgentResponse, ConversationMessage


class AgentClient:
    """Client for communicating with the agent under test via REST API."""

    def __init__(
        self,
        endpoint: str,
        auth_type: str = "none",
        auth_credentials: Optional[Dict[str, str]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ):
        self.endpoint = endpoint
        self.auth_type = auth_type
        self.auth_credentials = auth_credentials or {}
        self.custom_headers = custom_headers or {}
        self.timeout = timeout

    async def send_message(
        self,
        message: str,
        conversation_id: str,
        context: Optional[List[ConversationMessage]] = None,
    ) -> AgentResponse:
        """Send a message to the agent and get response."""
        headers = self._build_headers()
        payload = self._build_payload(message, conversation_id, context)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.endpoint,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            return AgentResponse(
                content=data.get("content", ""),
                tool_calls=data.get("tool_calls"),
                completion_signal=data.get("completion_signal"),
                metadata=data.get("metadata", {}),
            )

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        headers.update(self.custom_headers)

        if self.auth_type == "bearer":
            token = self.auth_credentials.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        elif self.auth_type == "api_key":
            key = self.auth_credentials.get("key", "")
            headers["X-API-Key"] = key
        elif self.auth_type == "basic":
            # Basic auth would need username and password
            import base64

            username = self.auth_credentials.get("username", "")
            password = self.auth_credentials.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    def _build_payload(
        self,
        message: str,
        conversation_id: str,
        context: Optional[List[ConversationMessage]] = None,
    ) -> Dict[str, Any]:
        """Build request payload."""
        payload = {
            "message": message,
            "conversation_id": conversation_id,
        }

        if context:
            payload["context"] = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": msg.tool_calls,
                }
                for msg in context
            ]

        return payload
