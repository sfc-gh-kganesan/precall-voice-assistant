"""Unit tests for AgentClient."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import httpx
from backend.core.agent_client import AgentClient
from backend.core.interfaces import ConversationMessage, AgentResponse


@pytest.mark.unit
class TestAgentClient:
    """Tests for AgentClient."""

    def test_init_basic(self):
        """Test basic initialization."""
        client = AgentClient(endpoint="http://localhost:8000/api/chat")
        assert client.endpoint == "http://localhost:8000/api/chat"
        assert client.auth_type == "none"
        assert client.timeout == 30

    def test_init_with_bearer_auth(self):
        """Test initialization with bearer token authentication."""
        client = AgentClient(
            endpoint="http://localhost:8000/api/chat",
            auth_type="bearer",
            auth_credentials={"token": "secret_token"},
        )
        assert client.auth_type == "bearer"
        assert client.auth_credentials["token"] == "secret_token"

    def test_init_with_api_key(self):
        """Test initialization with API key authentication."""
        client = AgentClient(
            endpoint="http://localhost:8000/api/chat",
            auth_type="api_key",
            auth_credentials={"key": "my_api_key"},
            custom_headers={"X-Custom-Header": "value"},
        )
        assert client.auth_type == "api_key"
        assert client.auth_credentials["key"] == "my_api_key"
        assert client.custom_headers["X-Custom-Header"] == "value"

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message send."""
        client = AgentClient(endpoint="http://localhost:8000/api/chat")

        mock_response = {
            "content": "Hello! How can I help you?",
            "tool_calls": None,
            "metadata": {"model": "gpt-4"},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = Mock(
                status_code=200, json=lambda: mock_response
            )

            response = await client.send_message(
                message="Hi there",
                conversation_id="conv_123",
            )

            assert isinstance(response, AgentResponse)
            assert response.content == "Hello! How can I help you?"
            assert response.tool_calls is None
            assert response.metadata["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_send_message_with_context(self):
        """Test sending message with conversation context."""
        client = AgentClient(endpoint="http://localhost:8000/api/chat")

        context = [
            ConversationMessage(role="user", content="Previous message"),
            ConversationMessage(role="assistant", content="Previous response"),
        ]

        mock_response = {
            "content": "Based on our previous conversation...",
            "tool_calls": None,
            "metadata": {},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = Mock(
                status_code=200, json=lambda: mock_response
            )

            response = await client.send_message(
                message="Continue",
                conversation_id="conv_123",
                context=context,
            )

            assert isinstance(response, AgentResponse)
            # Verify context was sent in request
            call_args = mock_client.post.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_send_message_with_tool_calls(self):
        """Test receiving response with tool calls."""
        client = AgentClient(endpoint="http://localhost:8000/api/chat")

        mock_response = {
            "content": "Let me check that for you.",
            "tool_calls": [
                {
                    "tool": "check_user_status",
                    "args": {"user_id": "12345"},
                }
            ],
            "metadata": {},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = Mock(
                status_code=200, json=lambda: mock_response
            )

            response = await client.send_message(
                message="Check my account",
                conversation_id="conv_123",
            )

            assert response.tool_calls is not None
            assert len(response.tool_calls) == 1
            assert response.tool_calls[0]["tool"] == "check_user_status"

    @pytest.mark.asyncio
    async def test_send_message_timeout(self):
        """Test handling of request timeout."""
        client = AgentClient(endpoint="http://localhost:8000/api/chat", timeout=5)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await client.send_message(
                    message="Test",
                    conversation_id="conv_123",
                )

    @pytest.mark.asyncio
    async def test_send_message_http_error(self):
        """Test handling of HTTP errors."""
        client = AgentClient(endpoint="http://localhost:8000/api/chat")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = Mock(
                status_code=500,
                raise_for_status=Mock(
                    side_effect=httpx.HTTPStatusError(
                        "Server error", request=Mock(), response=Mock()
                    )
                ),
            )

            with pytest.raises(httpx.HTTPStatusError):
                await client.send_message(
                    message="Test",
                    conversation_id="conv_123",
                )

    @pytest.mark.asyncio
    async def test_send_message_with_completion_signal(self):
        """Test receiving completion signal from agent."""
        client = AgentClient(endpoint="http://localhost:8000/api/chat")

        mock_response = {
            "content": "All done! Your issue is resolved.",
            "completion_signal": "RESOLVED",
            "metadata": {},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = Mock(
                status_code=200, json=lambda: mock_response
            )

            response = await client.send_message(
                message="Thanks!",
                conversation_id="conv_123",
            )

            assert response.completion_signal == "RESOLVED"

    @pytest.mark.asyncio
    async def test_bearer_auth_headers(self):
        """Test that bearer token is added to request headers."""
        client = AgentClient(
            endpoint="http://localhost:8000/api/chat",
            auth_type="bearer",
            auth_credentials={"token": "my_bearer_token"},
        )

        mock_response = {"content": "Response", "metadata": {}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = Mock(
                status_code=200, json=lambda: mock_response
            )

            await client.send_message(
                message="Test",
                conversation_id="conv_123",
            )

            # Verify Authorization header was set
            call_args = mock_client.post.call_args
            assert call_args is not None
            headers = call_args.kwargs.get("headers", {})
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer my_bearer_token"
