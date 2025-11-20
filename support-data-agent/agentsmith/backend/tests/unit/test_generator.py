"""Unit tests for ScenarioGenerator."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from backend.core.generator import ScenarioGenerator
from backend.core.interfaces import Scenario


@pytest.mark.unit
class TestScenarioGenerator:
    """Tests for ScenarioGenerator."""

    def test_init_with_openai(self):
        """Test initialization with OpenAI provider."""
        generator = ScenarioGenerator(provider="openai", api_key="test_key")
        assert generator.provider == "openai"
        assert generator.api_key == "test_key"

    def test_init_with_anthropic(self):
        """Test initialization with Anthropic provider."""
        generator = ScenarioGenerator(provider="anthropic", api_key="test_key")
        assert generator.provider == "anthropic"
        assert generator.api_key == "test_key"

    @pytest.mark.asyncio
    async def test_generate_scenarios_basic(self, mock_llm_response):
        """Test basic scenario generation."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            generator = ScenarioGenerator(provider="openai", api_key="test_key")

            # Mock LLM response with scenario JSON
            mock_response = Mock()
            mock_response.choices = [
                Mock(
                    message=Mock(
                        content='{"personas": [{"name": "John", "goal": "Get help", "tone": "polite", "personality_traits": ["patient"], "technical_level": "beginner", "edge_case": false}], "scenarios": [{"initial_query": "I need help", "expected_outcome": "Issue resolved", "complexity": "simple", "category": "general"}]}'
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response

            scenarios = await generator.generate_scenarios(
                business_context="Customer support for a SaaS product",
                num_scenarios=1,
            )

            assert len(scenarios) == 1
            assert isinstance(scenarios[0], Scenario)
            assert scenarios[0].persona.name == "John"
            assert scenarios[0].initial_query == "I need help"

    @pytest.mark.asyncio
    async def test_generate_scenarios_with_edge_cases(self, mock_llm_response):
        """Test scenario generation with edge case ratio."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            generator = ScenarioGenerator(provider="openai", api_key="test_key")

            mock_response = Mock()
            mock_response.choices = [
                Mock(
                    message=Mock(
                        content='{"personas": [{"name": "Jane", "goal": "Test edge case", "tone": "frustrated", "personality_traits": ["impatient"], "technical_level": "expert", "edge_case": true}], "scenarios": [{"initial_query": "Edge case query", "expected_outcome": "Handled", "complexity": "complex", "category": "edge_case"}]}'
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response

            scenarios = await generator.generate_scenarios(
                business_context="Customer support",
                num_scenarios=1,
                edge_case_ratio=1.0,  # 100% edge cases
            )

            assert len(scenarios) == 1
            assert scenarios[0].persona.edge_case is True

    @pytest.mark.asyncio
    async def test_generate_scenarios_with_historical_data(self):
        """Test scenario generation learning from historical conversations."""
        generator = ScenarioGenerator(provider="openai", api_key="test_key")

        historical = [
            {
                "role": "user",
                "content": "I can't log in",
            },
            {
                "role": "assistant",
                "content": "Let me help you with that",
            },
        ]

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = Mock()
            mock_response.choices = [
                Mock(
                    message=Mock(
                        content='{"personas": [{"name": "User", "goal": "Login", "tone": "neutral", "personality_traits": ["direct"], "technical_level": "intermediate", "edge_case": false}], "scenarios": [{"initial_query": "Login issue", "expected_outcome": "Resolved", "complexity": "simple", "category": "authentication"}]}'
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response

            await generator.generate_scenarios(
                business_context="Customer support",
                num_scenarios=1,
                historical_conversations=[historical],
            )

            # Verify historical context was included in prompt
            call_args = mock_client.chat.completions.create.call_args
            assert call_args is not None
            messages = call_args.kwargs["messages"]
            prompt_text = str(messages)
            assert (
                "historical" in prompt_text.lower() or "example" in prompt_text.lower()
            )

    @pytest.mark.asyncio
    async def test_generate_multiple_scenarios(self):
        """Test generating multiple scenarios."""
        generator = ScenarioGenerator(provider="openai", api_key="test_key")

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = Mock()
            # Return multiple personas and scenarios
            mock_response.choices = [
                Mock(
                    message=Mock(
                        content='{"personas": [{"name": "User1", "goal": "Goal1", "tone": "polite", "personality_traits": ["patient"], "technical_level": "beginner", "edge_case": false}, {"name": "User2", "goal": "Goal2", "tone": "urgent", "personality_traits": ["impatient"], "technical_level": "expert", "edge_case": false}], "scenarios": [{"initial_query": "Query1", "expected_outcome": "Outcome1", "complexity": "simple", "category": "cat1"}, {"initial_query": "Query2", "expected_outcome": "Outcome2", "complexity": "moderate", "category": "cat2"}]}'
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response

            scenarios = await generator.generate_scenarios(
                business_context="Customer support",
                num_scenarios=2,
            )

            assert len(scenarios) == 2
            assert scenarios[0].persona.name == "User1"
            assert scenarios[1].persona.name == "User2"

    @pytest.mark.asyncio
    async def test_generate_scenarios_anthropic_provider(self):
        """Test scenario generation with Anthropic provider."""
        generator = ScenarioGenerator(provider="anthropic", api_key="test_key")

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_response = Mock()
            mock_response.content = [
                Mock(
                    text='{"personas": [{"name": "Alice", "goal": "Help", "tone": "friendly", "personality_traits": ["helpful"], "technical_level": "intermediate", "edge_case": false}], "scenarios": [{"initial_query": "Need help", "expected_outcome": "Resolved", "complexity": "simple", "category": "general"}]}'
                )
            ]
            mock_client.messages.create.return_value = mock_response

            scenarios = await generator.generate_scenarios(
                business_context="Customer support",
                num_scenarios=1,
            )

            assert len(scenarios) == 1
            assert scenarios[0].persona.name == "Alice"

    @pytest.mark.asyncio
    async def test_parse_llm_response_valid_json(self):
        """Test parsing valid JSON response from LLM."""
        generator = ScenarioGenerator(provider="openai", api_key="test_key")

        json_str = """
        {
            "personas": [{
                "name": "Test User",
                "goal": "Get support",
                "tone": "polite",
                "personality_traits": ["patient", "understanding"],
                "technical_level": "beginner",
                "edge_case": false
            }],
            "scenarios": [{
                "initial_query": "I have a question",
                "expected_outcome": "Question answered",
                "complexity": "simple",
                "category": "general_inquiry"
            }]
        }
        """

        scenarios = generator._parse_llm_response(json_str)
        assert len(scenarios) == 1
        assert scenarios[0].persona.name == "Test User"
        assert len(scenarios[0].persona.personality_traits) == 2

    def test_parse_llm_response_invalid_json(self):
        """Test handling of invalid JSON response."""
        generator = ScenarioGenerator(provider="openai", api_key="test_key")

        with pytest.raises(ValueError):
            generator._parse_llm_response("This is not valid JSON")

    def test_build_prompt_includes_context(self):
        """Test that prompt builder includes business context."""
        generator = ScenarioGenerator(provider="openai", api_key="test_key")

        prompt = generator._build_prompt(
            business_context="E-commerce support for electronics",
            num_scenarios=5,
            edge_case_ratio=0.2,
        )

        assert "E-commerce support for electronics" in prompt
        assert "5" in prompt or "five" in prompt.lower()

    def test_build_prompt_with_historical_conversations(self):
        """Test prompt building with historical conversations."""
        generator = ScenarioGenerator(provider="openai", api_key="test_key")

        historical = [
            {
                "role": "user",
                "content": "My order is delayed",
            }
        ]

        prompt = generator._build_prompt(
            business_context="E-commerce",
            num_scenarios=1,
            historical_conversations=[historical],
        )

        assert "My order is delayed" in prompt

    @pytest.mark.asyncio
    async def test_generate_scenarios_with_retry(self):
        """Test retry logic on LLM failures."""
        generator = ScenarioGenerator(
            provider="openai", api_key="test_key", max_retries=2
        )

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            # First call fails, second succeeds
            mock_client.chat.completions.create.side_effect = [
                Exception("API Error"),
                Mock(
                    choices=[
                        Mock(
                            message=Mock(
                                content='{"personas": [{"name": "User", "goal": "Goal", "tone": "neutral", "personality_traits": ["direct"], "technical_level": "beginner", "edge_case": false}], "scenarios": [{"initial_query": "Query", "expected_outcome": "Outcome", "complexity": "simple", "category": "test"}]}'
                            )
                        )
                    ]
                ),
            ]

            scenarios = await generator.generate_scenarios(
                business_context="Test",
                num_scenarios=1,
            )

            assert len(scenarios) == 1
            assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_scenarios_max_retries_exceeded(self):
        """Test behavior when max retries exceeded."""
        generator = ScenarioGenerator(
            provider="openai", api_key="test_key", max_retries=2
        )

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            # All calls fail
            mock_client.chat.completions.create.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                await generator.generate_scenarios(
                    business_context="Test",
                    num_scenarios=1,
                )
