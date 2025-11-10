"""Unit tests for UserSimulator."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from backend.core.user_simulator import UserSimulator
from backend.core.interfaces import Persona, ConversationMessage


class TestUserSimulator:
    """Test suite for UserSimulator class."""

    def test_init_with_snowflake_provider(self):
        """Test initialization with Snowflake provider."""
        simulator = UserSimulator(
            provider="snowflake",
            api_key="test_key",
            model="claude-4-sonnet",
            base_url="https://test.snowflakecomputing.com/api/v2/cortex/v1",
        )

        assert simulator.provider == "snowflake"
        assert simulator.api_key == "test_key"
        assert simulator.model == "claude-4-sonnet"
        assert (
            simulator.base_url == "https://test.snowflakecomputing.com/api/v2/cortex/v1"
        )
        assert simulator._client is None  # Lazy loaded

    def test_init_with_openai_provider(self):
        """Test initialization with OpenAI provider."""
        simulator = UserSimulator(
            provider="openai",
            api_key="test_key",
            model="gpt-4o-mini",
        )

        assert simulator.provider == "openai"
        assert simulator.model == "gpt-4o-mini"
        assert simulator.base_url is None

    def test_init_with_anthropic_provider(self):
        """Test initialization with Anthropic provider."""
        simulator = UserSimulator(
            provider="anthropic",
            api_key="test_key",
            model="claude-3-5-sonnet-20241022",
        )

        assert simulator.provider == "anthropic"
        assert simulator.model == "claude-3-5-sonnet-20241022"

    @pytest.mark.asyncio
    @patch("openai.OpenAI")
    async def test_generate_response_snowflake(self, mock_openai_class):
        """Test generating response with Snowflake provider."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="This is a follow-up question"))
        ]
        mock_client.chat.completions.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        # Create simulator
        simulator = UserSimulator(
            provider="snowflake",
            api_key="test_key",
            model="claude-4-sonnet",
            base_url="https://test.snowflakecomputing.com/api/v2/cortex/v1",
        )

        # Create test data
        persona = Persona(
            name="Test User",
            goal="Get information",
            tone="professional",
            personality_traits=["curious"],
            technical_level="intermediate",
            edge_case=False,
        )

        conversation_history = [
            ConversationMessage(
                role="user",
                content="What is the status?",
                timestamp="2024-01-01T00:00:00",
            ),
            ConversationMessage(
                role="assistant",
                content="The status is good.",
                timestamp="2024-01-01T00:00:01",
            ),
        ]

        # Generate response
        response = await simulator.generate_response(
            persona=persona,
            conversation_history=conversation_history,
            agent_last_message="The status is good.",
        )

        # Verify
        assert response == "This is a follow-up question"
        mock_client.chat.completions.create.assert_called_once()

        # Verify Snowflake uses max_completion_tokens
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_completion_tokens" in call_kwargs
        assert "max_tokens" not in call_kwargs

    @pytest.mark.asyncio
    @patch("openai.OpenAI")
    async def test_generate_response_openai(self, mock_openai_class):
        """Test generating response with OpenAI provider."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Follow-up question"))]
        mock_client.chat.completions.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        # Create simulator
        simulator = UserSimulator(
            provider="openai",
            api_key="test_key",
            model="gpt-4o-mini",
        )

        # Create test data
        persona = Persona(
            name="Test User",
            goal="Get information",
            tone="professional",
            personality_traits=["curious"],
            technical_level="intermediate",
            edge_case=False,
        )

        conversation_history = []

        # Generate response
        response = await simulator.generate_response(
            persona=persona,
            conversation_history=conversation_history,
            agent_last_message="Hello",
        )

        # Verify
        assert response == "Follow-up question"

        # Verify OpenAI uses max_tokens
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "max_tokens" in call_kwargs
        assert "max_completion_tokens" not in call_kwargs

    @pytest.mark.asyncio
    @patch("anthropic.Anthropic")
    async def test_generate_response_anthropic(self, mock_anthropic_class):
        """Test generating response with Anthropic provider."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Anthropic follow-up")]
        # Use AsyncMock to properly handle async call
        mock_client.messages = Mock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        # Create simulator
        simulator = UserSimulator(
            provider="anthropic",
            api_key="test_key",
            model="claude-3-5-sonnet-20241022",
        )

        # Create test data
        persona = Persona(
            name="Test User",
            goal="Get information",
            tone="professional",
            personality_traits=["curious"],
            technical_level="intermediate",
            edge_case=False,
        )

        conversation_history = []

        # Generate response
        response = await simulator.generate_response(
            persona=persona,
            conversation_history=conversation_history,
            agent_last_message="Hello",
        )

        # Verify
        assert response == "Anthropic follow-up"
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("openai.OpenAI")
    async def test_generate_response_with_persona_traits(self, mock_openai_class):
        """Test that persona traits are included in prompt."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Urgent response"))]
        mock_client.chat.completions.create = Mock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        # Create simulator
        simulator = UserSimulator(provider="openai", api_key="test_key")

        # Create persona with specific traits
        persona = Persona(
            name="Urgent User",
            goal="Get data quickly",
            tone="urgent",
            personality_traits=["impatient", "direct"],
            technical_level="expert",
            edge_case=False,
        )

        conversation_history = []

        # Generate response
        await simulator.generate_response(
            persona=persona,
            conversation_history=conversation_history,
            agent_last_message="Here's the data",
        )

        # Verify prompt includes persona traits
        call_args = mock_client.chat.completions.create.call_args[1]
        messages = call_args["messages"]
        system_prompt = messages[0]["content"]

        assert "urgent" in system_prompt.lower() or "impatient" in system_prompt.lower()
        assert "expert" in system_prompt.lower()

    @pytest.mark.asyncio
    @patch("openai.OpenAI")
    async def test_error_handling(self, mock_openai_class):
        """Test error handling when API fails - should return fallback."""
        # Setup mock to raise error
        mock_client = Mock()
        mock_client.chat.completions.create = Mock(side_effect=Exception("API Error"))
        mock_openai_class.return_value = mock_client

        # Create simulator
        simulator = UserSimulator(provider="openai", api_key="test_key")

        # Create test data
        persona = Persona(
            name="Test User",
            goal="Get information",
            tone="professional",
            personality_traits=["curious"],
            technical_level="intermediate",
            edge_case=False,
        )

        # Generate response - should not raise error, should return fallback
        response = await simulator.generate_response(
            persona=persona,
            conversation_history=[],
            agent_last_message="Hello",
        )

        # Verify it returned a fallback response instead of raising
        assert response is not None
        assert len(response) > 0
