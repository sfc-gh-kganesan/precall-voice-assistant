"""Unit tests for SimulationEngine callbacks."""

import pytest
from unittest.mock import Mock, AsyncMock
from backend.core.simulator import SimulationEngine
from backend.core.interfaces import Persona, Scenario, AgentResponse


class TestSimulatorCallbacks:
    """Test suite for SimulationEngine callback functionality."""

    @pytest.mark.asyncio
    async def test_on_conversation_start_callback_called(self):
        """Test that on_conversation_start callback is invoked."""
        # Create mocks
        mock_agent_client = Mock()
        mock_agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Response", completion_signal="COMPLETED", tool_calls=None
            )
        )

        callback_called = {"called": False, "scenario": None}

        async def on_start(scenario):
            callback_called["called"] = True
            callback_called["scenario"] = scenario

        # Create engine with callback
        engine = SimulationEngine(
            agent_client=mock_agent_client,
            on_conversation_start=on_start,
        )

        # Create scenario
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

        # Run simulation
        await engine.run_simulation(scenario)

        # Verify callback was called
        assert callback_called["called"]
        assert callback_called["scenario"] == scenario

    @pytest.mark.asyncio
    async def test_on_message_added_callback_called(self):
        """Test that on_message_added callback is invoked for each message."""
        # Create mocks
        mock_agent_client = Mock()
        mock_agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Response", completion_signal="COMPLETED", tool_calls=None
            )
        )

        messages_added = []

        async def on_message(scenario, message):
            messages_added.append((scenario, message))

        # Create engine with callback
        engine = SimulationEngine(
            agent_client=mock_agent_client,
            on_message_added=on_message,
        )

        # Create scenario
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

        # Run simulation
        await engine.run_simulation(scenario)

        # Verify callback was called for each message (initial user + assistant)
        assert len(messages_added) == 2
        assert messages_added[0][1].role == "user"
        assert messages_added[1][1].role == "assistant"

    @pytest.mark.asyncio
    async def test_on_conversation_complete_callback_called(self):
        """Test that on_conversation_complete callback is invoked."""
        # Create mocks
        mock_agent_client = Mock()
        mock_agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Response", completion_signal="COMPLETED", tool_calls=None
            )
        )

        callback_called = {"called": False, "result": None}

        async def on_complete(scenario, result):
            callback_called["called"] = True
            callback_called["result"] = result

        # Create engine with callback
        engine = SimulationEngine(
            agent_client=mock_agent_client,
            on_conversation_complete=on_complete,
        )

        # Create scenario
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

        # Run simulation (use run_simulations since that's where the callback is called)
        await engine.run_simulations([scenario])

        # Verify callback was called
        assert callback_called["called"]
        assert callback_called["result"] is not None
        assert callback_called["result"].success is True

    @pytest.mark.asyncio
    async def test_callback_error_doesnt_break_simulation(self):
        """Test that errors in callbacks don't break the simulation."""
        # Create mocks
        mock_agent_client = Mock()
        mock_agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Response", completion_signal="COMPLETED", tool_calls=None
            )
        )

        async def failing_callback(scenario, *args):
            raise Exception("Callback error!")

        # Create engine with failing callback
        engine = SimulationEngine(
            agent_client=mock_agent_client,
            on_conversation_start=failing_callback,
            on_message_added=failing_callback,
        )

        # Create scenario
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

        # Run simulation - should not raise error
        result = await engine.run_simulation(scenario)

        # Verify simulation completed despite callback errors
        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_all_callbacks_work_together(self):
        """Test that all three callbacks work together correctly."""
        # Create mocks
        mock_agent_client = Mock()
        mock_agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Response", completion_signal="COMPLETED", tool_calls=None
            )
        )

        call_order = []

        async def on_start(scenario):
            call_order.append("start")

        async def on_message(scenario, message):
            call_order.append(f"message:{message.role}")

        async def on_complete(scenario, result):
            call_order.append("complete")

        # Create engine with all callbacks
        engine = SimulationEngine(
            agent_client=mock_agent_client,
            on_conversation_start=on_start,
            on_message_added=on_message,
            on_conversation_complete=on_complete,
        )

        # Create scenario
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

        # Run simulation (use run_simulations since that's where the callback is called)
        await engine.run_simulations([scenario])

        # Verify correct call order
        assert call_order[0] == "start"
        assert "message:user" in call_order
        assert "message:assistant" in call_order
        assert call_order[-1] == "complete"

    @pytest.mark.asyncio
    async def test_callbacks_with_user_simulator(self):
        """Test callbacks work correctly with user simulator."""
        # Create mocks
        mock_agent_client = Mock()
        # Agent doesn't signal completion so conversation continues
        mock_agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Response", completion_signal=None, tool_calls=None
            )
        )

        mock_user_simulator = Mock()
        # Return follow-ups until max_turns is reached
        mock_user_simulator.generate_response = AsyncMock(
            side_effect=["Follow-up 1", "Follow-up 2", "Follow-up 3"]
        )

        messages_added = []

        async def on_message(scenario, message):
            messages_added.append(message.role)

        # Create engine with callbacks and user simulator
        engine = SimulationEngine(
            agent_client=mock_agent_client,
            user_simulator=mock_user_simulator,
            max_turns=4,  # Allow 4 turns: initial user, assistant, follow-up user, assistant
            on_message_added=on_message,
        )

        # Create scenario
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

        # Run simulation
        await engine.run_simulation(scenario)

        # Verify messages were added (user, assistant, user follow-up, assistant)
        assert len(messages_added) >= 4  # At least 2 turns (initial + 1 follow-up)
        assert messages_added.count("user") >= 2  # Initial + at least 1 follow-up
        assert messages_added.count("assistant") >= 2  # At least 2 responses
