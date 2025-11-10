"""Unit tests for SimulationRunner."""

import pytest
from unittest.mock import Mock, patch
from backend.services.simulation_runner import SimulationRunner
from backend.core.interfaces import (
    Persona,
    Scenario,
    SimulationResult,
    StopReason,
    ConversationMessage,
)


class TestSimulationRunner:
    """Test suite for SimulationRunner class."""

    def test_init(self):
        """Test initialization."""
        mock_db = Mock()
        runner = SimulationRunner(mock_db)
        assert runner.db == mock_db

    @pytest.mark.asyncio
    async def test_start_conversation(self):
        """Test _start_conversation creates conversation record."""
        # Setup mock DB
        mock_db = Mock()
        mock_conversation = Mock(id=1)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # Mock the conversation instance
        with patch(
            "backend.services.simulation_runner.Conversation",
            return_value=mock_conversation,
        ):
            runner = SimulationRunner(mock_db)

            # Create test data
            mock_simulation = Mock(id=1)
            persona = Persona(
                name="Test User",
                goal="Test goal",
                tone="professional",
                personality_traits=["curious"],
                technical_level="intermediate",
                edge_case=False,
            )
            scenario = Scenario(
                persona=persona,
                initial_query="Test query",
                expected_outcome="Test outcome",
                complexity="simple",
                category="test",
            )

            # Call method
            conversation_id = await runner._start_conversation(
                mock_simulation, scenario
            )

            # Verify
            assert conversation_id == 1
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message(self):
        """Test _add_message stores message and updates turn count."""
        # Setup mock DB
        mock_db = Mock()
        mock_conversation = Mock(id=1, num_turns=0)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.query = Mock(
            return_value=Mock(
                filter=Mock(
                    return_value=Mock(first=Mock(return_value=mock_conversation))
                )
            )
        )

        runner = SimulationRunner(mock_db)

        # Create test message
        message = ConversationMessage(
            role="user",
            content="Test message",
            timestamp="2024-01-01T00:00:00",
        )

        # Call method
        await runner._add_message(1, message)

        # Verify message was added
        assert mock_db.add.called
        assert mock_db.commit.call_count == 2  # Once for message, once for turn count

        # Verify turn count was updated for user message
        assert mock_conversation.num_turns == 1

    @pytest.mark.asyncio
    async def test_add_message_assistant_no_turn_increment(self):
        """Test _add_message doesn't increment turns for assistant messages."""
        # Setup mock DB
        mock_db = Mock()
        mock_conversation = Mock(id=1, num_turns=1)
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.query = Mock(
            return_value=Mock(
                filter=Mock(
                    return_value=Mock(first=Mock(return_value=mock_conversation))
                )
            )
        )

        runner = SimulationRunner(mock_db)

        # Create assistant message
        message = ConversationMessage(
            role="assistant",
            content="Response",
            timestamp="2024-01-01T00:00:01",
        )

        # Call method
        await runner._add_message(1, message)

        # Verify turn count wasn't changed
        assert mock_conversation.num_turns == 1
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_conversation(self):
        """Test _complete_conversation updates final fields."""
        # Setup mock DB
        mock_db = Mock()
        mock_conversation = Mock(id=1)
        mock_db.query = Mock(
            return_value=Mock(
                filter=Mock(
                    return_value=Mock(first=Mock(return_value=mock_conversation))
                )
            )
        )
        mock_db.add = Mock()
        mock_db.commit = Mock()

        runner = SimulationRunner(mock_db)

        # Create test persona and scenario
        persona = Persona(
            name="Test User",
            goal="Test",
            tone="professional",
            personality_traits=["curious"],
            technical_level="intermediate",
            edge_case=False,
        )
        scenario = Scenario(
            persona=persona,
            initial_query="Test query",
            expected_outcome="Test outcome",
            complexity="simple",
            category="test",
        )

        # Create test result
        result = SimulationResult(
            conversation_id="test-123",
            success=True,
            stop_reason=StopReason.AGENT_SIGNAL,
            scenario=scenario,
            messages=[],
            metrics={"efficiency_score": 5.0, "tool_usage": {"count": 2}},
            duration_ms=1000.0,
        )

        # Call method
        await runner._complete_conversation(1, result)

        # Verify conversation was updated
        assert mock_conversation.success
        assert mock_conversation.total_duration_ms == 1000.0
        assert mock_conversation.stop_reason == "agent_signal"  # lowercase in DB
        assert mock_conversation.completed_at is not None

        # Verify metrics were stored
        assert (
            mock_db.add.call_count >= 2
        )  # At least 2 metrics (efficiency_score and tool_usage.count)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_conversation_not_found(self):
        """Test _complete_conversation handles missing conversation."""
        # Setup mock DB with no conversation
        mock_db = Mock()
        mock_db.query = Mock(
            return_value=Mock(
                filter=Mock(return_value=Mock(first=Mock(return_value=None)))
            )
        )

        runner = SimulationRunner(mock_db)

        # Create test persona and scenario
        persona = Persona(
            name="Test User",
            goal="Test",
            tone="professional",
            personality_traits=["curious"],
            technical_level="intermediate",
            edge_case=False,
        )
        scenario = Scenario(
            persona=persona,
            initial_query="Test query",
            expected_outcome="Test outcome",
            complexity="simple",
            category="test",
        )

        # Create test result
        result = SimulationResult(
            conversation_id="test-123",
            success=True,
            stop_reason=StopReason.AGENT_SIGNAL,
            scenario=scenario,
            messages=[],
            metrics={},
            duration_ms=1000.0,
        )

        # Call method - should not raise error
        await runner._complete_conversation(999, result)

        # Verify nothing was committed
        assert not mock_db.commit.called

    @pytest.mark.asyncio
    async def test_store_conversation_legacy_method(self):
        """Test legacy _store_conversation method still works."""
        # Setup mock DB
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.flush = Mock()

        runner = SimulationRunner(mock_db)

        # Create test data
        mock_simulation = Mock(id=1)
        persona = Persona(
            name="Test User",
            goal="Test goal",
            tone="professional",
            personality_traits=["curious"],
            technical_level="intermediate",
            edge_case=False,
        )
        scenario = Scenario(
            persona=persona,
            initial_query="Test query",
            expected_outcome="Test outcome",
            complexity="simple",
            category="test",
        )
        result = SimulationResult(
            conversation_id="test-123",
            success=True,
            stop_reason=StopReason.AGENT_SIGNAL,
            scenario=scenario,
            messages=[
                ConversationMessage(
                    role="user", content="Q1", timestamp="2024-01-01T00:00:00"
                ),
                ConversationMessage(
                    role="assistant", content="A1", timestamp="2024-01-01T00:00:01"
                ),
            ],
            metrics={"efficiency_score": 5.0},
            duration_ms=1000.0,
        )

        # Call method
        await runner._store_conversation(mock_simulation, scenario, result)

        # Verify conversation and messages were added
        assert mock_db.add.call_count >= 3  # Conversation + 2 messages
        mock_db.commit.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_create_agent_client(self):
        """Test _create_agent_client creates client with correct config."""
        mock_db = Mock()
        runner = SimulationRunner(mock_db)

        # Create mock project
        from backend.models.models import AuthType

        mock_project = Mock(
            agent_endpoint="http://test.com/api",
            auth_type=AuthType.BEARER,
            auth_credentials={"token": "test_token"},
            custom_headers={"X-Custom": "value"},
        )

        # Create client
        client = runner._create_agent_client(mock_project)

        # Verify
        assert client.endpoint == "http://test.com/api"
        assert client.auth_type == "bearer"
        assert client.auth_credentials == {"token": "test_token"}
        assert client.custom_headers == {"X-Custom": "value"}
        assert client.timeout == 60.0  # Updated timeout

    def test_create_stop_conditions(self):
        """Test _create_stop_conditions creates correct conditions."""
        mock_db = Mock()
        runner = SimulationRunner(mock_db)

        # Create mock simulation
        mock_simulation = Mock(
            stop_conditions=["max_turns", "timeout", "agent_signal"],
            max_turns=20,
            timeout_seconds=300,
        )

        # Create conditions
        conditions = runner._create_stop_conditions(mock_simulation)

        # Verify - should be wrapped in CombinedStopCondition if multiple
        assert len(conditions) == 1
        # The combined condition contains the individual conditions

    def test_parse_custom_scenarios(self):
        """Test _parse_custom_scenarios parses scenarios correctly."""
        mock_db = Mock()
        runner = SimulationRunner(mock_db)

        # Create custom scenario data
        custom_scenarios = [
            {
                "persona": {
                    "name": "Test User",
                    "goal": "Get data",
                    "tone": "urgent",
                    "personality_traits": ["impatient"],
                    "technical_level": "expert",
                    "edge_case": False,
                },
                "initial_query": "I need data now!",
                "expected_outcome": "Receive data",
                "complexity": "simple",
                "category": "data_query",
            }
        ]

        # Parse scenarios
        scenarios = runner._parse_custom_scenarios(custom_scenarios)

        # Verify
        assert len(scenarios) == 1
        assert scenarios[0].persona.name == "Test User"
        assert scenarios[0].initial_query == "I need data now!"
        assert scenarios[0].persona.tone == "urgent"

    def test_parse_custom_scenarios_with_invalid_data(self):
        """Test _parse_custom_scenarios handles invalid data gracefully."""
        mock_db = Mock()
        runner = SimulationRunner(mock_db)

        # Create invalid scenario data
        custom_scenarios = [
            {"invalid": "data"},  # Missing required fields
        ]

        # Parse scenarios - should return fallback
        scenarios = runner._parse_custom_scenarios(custom_scenarios)

        # Verify fallback scenario was created with "Custom User" name
        assert len(scenarios) == 1
        assert scenarios[0].persona.name == "Custom User"

    def test_create_fallback_scenarios(self):
        """Test _create_fallback_scenarios creates valid scenarios."""
        mock_db = Mock()
        runner = SimulationRunner(mock_db)

        # Create fallback scenarios
        scenarios = runner._create_fallback_scenarios(3)

        # Verify
        assert len(scenarios) == 3
        for i, scenario in enumerate(scenarios):
            assert scenario.persona.name == f"Test User {i + 1}"
            assert scenario.initial_query is not None
            assert scenario.complexity == "simple"
