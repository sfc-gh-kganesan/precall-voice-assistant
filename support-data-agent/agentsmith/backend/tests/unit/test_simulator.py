"""Unit tests for SimulationEngine."""

import pytest
from unittest.mock import AsyncMock, Mock
from backend.core.simulator import SimulationEngine
from backend.core.interfaces import (
    Scenario,
    Persona,
    AgentResponse,
    StopReason,
    SimulationResult,
)
from backend.core.stop_conditions import MaxTurnsCondition
from backend.core.agent_client import AgentClient
from backend.core.evaluator import MetricsCalculator


@pytest.mark.unit
class TestSimulationEngine:
    """Tests for SimulationEngine."""

    def test_init_basic(self):
        """Test basic initialization."""
        agent_client = Mock(spec=AgentClient)
        engine = SimulationEngine(agent_client=agent_client)
        assert engine.agent_client == agent_client
        assert engine.concurrency == 1  # Default

    def test_init_with_concurrency(self):
        """Test initialization with custom concurrency."""
        agent_client = Mock(spec=AgentClient)
        engine = SimulationEngine(agent_client=agent_client, concurrency=5)
        assert engine.concurrency == 5

    @pytest.mark.asyncio
    async def test_run_single_simulation(self):
        """Test running a single simulation."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Hello! How can I help you?",
                completion_signal="RESOLVED",
            )
        )

        engine = SimulationEngine(
            agent_client=agent_client,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenario = Scenario(
            persona=Persona(
                name="Test User",
                goal="Get help",
                tone="polite",
                personality_traits=["patient"],
                technical_level="beginner",
                edge_case=False,
            ),
            initial_query="I need help",
            complexity="simple",
            category="general",
        )

        result = await engine.run_simulation(scenario)

        assert isinstance(result, SimulationResult)
        assert result.success is True
        assert len(result.messages) > 0
        assert result.messages[0].content == "I need help"

    @pytest.mark.asyncio
    async def test_run_simulation_with_stop_condition(self):
        """Test simulation stops when condition is met."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(content="Response")
        )

        # Stop after 2 turns
        engine = SimulationEngine(
            agent_client=agent_client,
            stop_conditions=[MaxTurnsCondition(max_turns=2)],
            metrics_calculator=MetricsCalculator(),
        )

        scenario = Scenario(
            persona=Persona(
                name="User",
                goal="Test",
                tone="neutral",
                personality_traits=[],
                technical_level="beginner",
                edge_case=False,
            ),
            initial_query="Test query",
            complexity="simple",
            category="test",
        )

        result = await engine.run_simulation(scenario)

        assert result.stop_reason == StopReason.MAX_TURNS
        assert len(result.messages) == 2  # Initial query + 1 response

    @pytest.mark.asyncio
    async def test_run_simulation_tracks_metrics(self):
        """Test that metrics are calculated for simulation."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Done",
                completion_signal="RESOLVED",
            )
        )

        engine = SimulationEngine(
            agent_client=agent_client,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenario = Scenario(
            persona=Persona(
                name="User",
                goal="Test",
                tone="neutral",
                personality_traits=[],
                technical_level="beginner",
                edge_case=False,
            ),
            initial_query="Query",
            complexity="simple",
            category="test",
        )

        result = await engine.run_simulation(scenario)

        assert "turns_to_completion" in result.metrics
        assert result.metrics["turns_to_completion"] >= 1

    @pytest.mark.asyncio
    async def test_run_simulation_handles_agent_errors(self):
        """Test handling of agent API errors."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(side_effect=Exception("API Error"))

        engine = SimulationEngine(
            agent_client=agent_client,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenario = Scenario(
            persona=Persona(
                name="User",
                goal="Test",
                tone="neutral",
                personality_traits=[],
                technical_level="beginner",
                edge_case=False,
            ),
            initial_query="Query",
            complexity="simple",
            category="test",
        )

        result = await engine.run_simulation(scenario)

        assert result.success is False
        assert result.stop_reason == StopReason.ERROR

    @pytest.mark.asyncio
    async def test_run_multiple_simulations_sequential(self):
        """Test running multiple simulations sequentially."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(content="Done", completion_signal="RESOLVED")
        )

        engine = SimulationEngine(
            agent_client=agent_client,
            concurrency=1,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenarios = [
            Scenario(
                persona=Persona(
                    name=f"User{i}",
                    goal="Test",
                    tone="neutral",
                    personality_traits=[],
                    technical_level="beginner",
                    edge_case=False,
                ),
                initial_query=f"Query {i}",
                complexity="simple",
                category="test",
            )
            for i in range(3)
        ]

        run_result = await engine.run_simulations(scenarios)

        assert run_result.total_simulations == 3
        assert len(run_result.results) == 3
        assert run_result.successful == 3
        assert run_result.failed == 0

    @pytest.mark.asyncio
    async def test_run_multiple_simulations_with_failures(self):
        """Test aggregating results with some failures."""
        agent_client = Mock(spec=AgentClient)

        # First two succeed, third fails
        responses = [
            AgentResponse(content="Done", completion_signal="RESOLVED"),
            AgentResponse(content="Done", completion_signal="RESOLVED"),
        ]
        call_count = [0]

        async def mock_send(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                return responses[call_count[0] - 1]
            raise Exception("API Error")

        agent_client.send_message = mock_send

        engine = SimulationEngine(
            agent_client=agent_client,
            concurrency=1,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenarios = [
            Scenario(
                persona=Persona(
                    name=f"User{i}",
                    goal="Test",
                    tone="neutral",
                    personality_traits=[],
                    technical_level="beginner",
                    edge_case=False,
                ),
                initial_query=f"Query {i}",
                complexity="simple",
                category="test",
            )
            for i in range(3)
        ]

        run_result = await engine.run_simulations(scenarios)

        assert run_result.total_simulations == 3
        assert run_result.successful == 2
        assert run_result.failed == 1

    @pytest.mark.asyncio
    async def test_run_simulations_calculates_aggregate_metrics(self):
        """Test calculation of aggregate metrics across simulations."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(content="Done", completion_signal="RESOLVED")
        )

        engine = SimulationEngine(
            agent_client=agent_client,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenarios = [
            Scenario(
                persona=Persona(
                    name=f"User{i}",
                    goal="Test",
                    tone="neutral",
                    personality_traits=[],
                    technical_level="beginner",
                    edge_case=False,
                ),
                initial_query=f"Query {i}",
                complexity="simple",
                category="test",
            )
            for i in range(3)
        ]

        run_result = await engine.run_simulations(scenarios)

        assert "avg_turns_to_completion" in run_result.aggregate_metrics
        assert "success_rate" in run_result.aggregate_metrics
        assert run_result.aggregate_metrics["success_rate"] == 1.0  # All succeeded

    @pytest.mark.asyncio
    async def test_simulation_generates_conversation_id(self):
        """Test that each simulation gets a unique conversation ID."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(content="Done", completion_signal="RESOLVED")
        )

        engine = SimulationEngine(
            agent_client=agent_client,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenario = Scenario(
            persona=Persona(
                name="User",
                goal="Test",
                tone="neutral",
                personality_traits=[],
                technical_level="beginner",
                edge_case=False,
            ),
            initial_query="Query",
            complexity="simple",
            category="test",
        )

        result1 = await engine.run_simulation(scenario)
        result2 = await engine.run_simulation(scenario)

        assert result1.conversation_id != result2.conversation_id

    @pytest.mark.asyncio
    async def test_simulation_tracks_tool_calls(self):
        """Test that tool calls are tracked in messages."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(
                content="Checking...",
                tool_calls=[{"tool": "search", "args": {"query": "test"}}],
                completion_signal="RESOLVED",
            )
        )

        engine = SimulationEngine(
            agent_client=agent_client,
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenario = Scenario(
            persona=Persona(
                name="User",
                goal="Test",
                tone="neutral",
                personality_traits=[],
                technical_level="beginner",
                edge_case=False,
            ),
            initial_query="Query",
            complexity="simple",
            category="test",
        )

        result = await engine.run_simulation(scenario)

        # Check that assistant message has tool calls
        assistant_messages = [m for m in result.messages if m.role == "assistant"]
        assert len(assistant_messages) > 0
        assert assistant_messages[0].tool_calls is not None
        assert len(assistant_messages[0].tool_calls) == 1

    @pytest.mark.asyncio
    async def test_concurrent_simulations(self):
        """Test running simulations with concurrency > 1."""
        agent_client = Mock(spec=AgentClient)
        agent_client.send_message = AsyncMock(
            return_value=AgentResponse(content="Done", completion_signal="RESOLVED")
        )

        engine = SimulationEngine(
            agent_client=agent_client,
            concurrency=3,  # Run 3 at a time
            stop_conditions=[MaxTurnsCondition(max_turns=10)],
            metrics_calculator=MetricsCalculator(),
        )

        scenarios = [
            Scenario(
                persona=Persona(
                    name=f"User{i}",
                    goal="Test",
                    tone="neutral",
                    personality_traits=[],
                    technical_level="beginner",
                    edge_case=False,
                ),
                initial_query=f"Query {i}",
                complexity="simple",
                category="test",
            )
            for i in range(5)
        ]

        run_result = await engine.run_simulations(scenarios)

        assert run_result.total_simulations == 5
        assert run_result.successful == 5
