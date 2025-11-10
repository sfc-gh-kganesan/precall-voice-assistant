"""Simulation engine for orchestrating agent testing."""

import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from backend.core.interfaces import (
    Scenario,
    SimulationResult,
    SimulationRunResult,
    ConversationContext,
    ConversationMessage,
    StopCondition,
    StopReason,
    AgentClientProtocol,
    MetricsCalculatorProtocol,
)

if TYPE_CHECKING:
    from backend.core.user_simulator import UserSimulator


class SimulationEngine:
    """Engine for running agent simulations."""

    def __init__(
        self,
        agent_client: AgentClientProtocol,
        stop_conditions: Optional[List[StopCondition]] = None,
        metrics_calculator: Optional[MetricsCalculatorProtocol] = None,
        concurrency: int = 1,
        max_turns: int = 20,
        user_simulator: Optional["UserSimulator"] = None,
        on_conversation_complete: Optional[callable] = None,
        on_conversation_start: Optional[callable] = None,
        on_message_added: Optional[callable] = None,
    ):
        """Initialize simulation engine.

        Args:
            agent_client: Client for communicating with agent
            stop_conditions: List of conditions to stop conversations
            metrics_calculator: Calculator for metrics
            concurrency: Number of simulations to run in parallel
            max_turns: Maximum number of turns as a hard guardrail (default: 20)
            user_simulator: Optional user simulator for multi-turn conversations
            on_conversation_complete: Optional callback when a conversation completes
            on_conversation_start: Optional callback when a conversation starts
            on_message_added: Optional callback when a message is added
        """
        self.agent_client = agent_client
        self.max_turns = max_turns
        self.stop_conditions = stop_conditions or []
        self.metrics_calculator = metrics_calculator
        self.concurrency = concurrency
        self.user_simulator = user_simulator
        self.on_conversation_complete = on_conversation_complete
        self.on_conversation_start = on_conversation_start
        self.on_message_added = on_message_added

    async def run_simulation(self, scenario: Scenario) -> SimulationResult:
        """Run a single simulation.

        Args:
            scenario: The test scenario to run

        Returns:
            Simulation result with messages and metrics
        """
        conversation_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        messages: List[ConversationMessage] = []
        success = False
        stop_reason = StopReason.MAX_TURNS  # Default

        # Create conversation context
        context = ConversationContext(
            conversation_id=conversation_id,
            messages=[],
            started_at=started_at.isoformat(),
            turn_count=0,
        )

        # Call conversation start callback
        if self.on_conversation_start:
            try:
                await self.on_conversation_start(scenario)
            except Exception as e:
                import logging

                logging.error(
                    f"Error in conversation start callback: {e}", exc_info=True
                )

        try:
            # Send initial query
            initial_message = ConversationMessage(
                role="user",
                content=scenario.initial_query,
                timestamp=datetime.utcnow().isoformat(),
            )
            messages.append(initial_message)
            context.messages.append(initial_message)
            context.turn_count += 1  # Count user messages only

            # Call message added callback for initial message
            if self.on_message_added:
                try:
                    await self.on_message_added(scenario, initial_message)
                except Exception as e:
                    import logging

                    logging.error(
                        f"Error in message added callback: {e}", exc_info=True
                    )

            # Conversation loop
            while True:
                # Hard guardrail: enforce max_turns
                if context.turn_count >= self.max_turns:
                    stop_reason = StopReason.MAX_TURNS
                    success = False
                    break

                # Check stop conditions before sending
                should_stop, reason = self._check_stop_conditions(
                    context, messages[-1] if messages else initial_message
                )
                if should_stop:
                    stop_reason = reason
                    success = reason in [
                        StopReason.AGENT_SIGNAL,
                        StopReason.CUSTOM_CONDITION,
                    ]
                    break

                # Send message to agent
                response = await self.agent_client.send_message(
                    message=messages[-1].content,
                    conversation_id=conversation_id,
                    context=messages,
                )

                # Record agent response
                agent_message = ConversationMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                    timestamp=datetime.utcnow().isoformat(),
                )
                messages.append(agent_message)
                context.messages.append(agent_message)
                # Don't increment turn_count for agent responses - only count user messages

                # Call message added callback for agent response
                if self.on_message_added:
                    try:
                        await self.on_message_added(scenario, agent_message)
                    except Exception as e:
                        import logging

                        logging.error(
                            f"Error in message added callback: {e}", exc_info=True
                        )

                # Check if agent signaled completion
                if response.completion_signal:
                    stop_reason = StopReason.AGENT_SIGNAL
                    success = True
                    break

                # Check stop conditions after agent response
                should_stop, reason = self._check_stop_conditions(
                    context, agent_message
                )
                if should_stop:
                    stop_reason = reason
                    success = reason in [
                        StopReason.AGENT_SIGNAL,
                        StopReason.CUSTOM_CONDITION,
                    ]
                    break

                # Generate next user message if user simulator is available
                if self.user_simulator:
                    try:
                        next_user_message = await self.user_simulator.generate_response(
                            persona=scenario.persona,
                            conversation_history=messages,
                            agent_last_message=response.content,
                            knowledge_base=scenario.knowledge_base,  # Pass knowledge_base!
                        )

                        # Add user's follow-up message
                        user_follow_up = ConversationMessage(
                            role="user",
                            content=next_user_message,
                            timestamp=datetime.utcnow().isoformat(),
                        )
                        messages.append(user_follow_up)
                        context.messages.append(user_follow_up)
                        context.turn_count += 1  # Count user messages only

                        # Call message added callback for user follow-up
                        if self.on_message_added:
                            try:
                                await self.on_message_added(scenario, user_follow_up)
                            except Exception as e:
                                import logging

                                logging.error(
                                    f"Error in message added callback: {e}",
                                    exc_info=True,
                                )

                        # Continue loop to get agent's response to the follow-up
                    except Exception as e:
                        # If user simulation fails, end the conversation
                        import logging

                        logging.error(
                            f"User simulator error in conversation: {e}", exc_info=True
                        )
                        stop_reason = StopReason.ERROR
                        success = False
                        break
                else:
                    # No user simulator - single turn mode, exit after first agent response
                    break

        except Exception as e:
            import logging

            logging.error(f"Simulation error: {e}", exc_info=True)
            stop_reason = StopReason.ERROR
            success = False

        # Calculate duration
        duration_ms = (datetime.utcnow() - started_at).total_seconds() * 1000

        # Calculate metrics
        metrics = {}
        if self.metrics_calculator:
            metrics = self.metrics_calculator.calculate_metrics(context, messages)

        return SimulationResult(
            conversation_id=conversation_id,
            scenario=scenario,
            messages=messages,
            success=success,
            stop_reason=stop_reason,
            metrics=metrics,
            duration_ms=duration_ms,
        )

    async def run_simulations(self, scenarios: List[Scenario]) -> SimulationRunResult:
        """Run multiple simulations.

        Args:
            scenarios: List of scenarios to simulate

        Returns:
            Aggregated results from all simulations
        """
        simulation_id = hash(datetime.utcnow().isoformat())
        started_at = datetime.utcnow().isoformat()

        # Run simulations with concurrency control
        semaphore = asyncio.Semaphore(self.concurrency)

        async def run_with_semaphore(scenario: Scenario) -> SimulationResult:
            async with semaphore:
                result = await self.run_simulation(scenario)
                # Call callback if provided
                if self.on_conversation_complete:
                    try:
                        await self.on_conversation_complete(scenario, result)
                    except Exception as e:
                        # Log but don't let callback errors break simulation
                        import logging

                        logging.error(
                            f"Error in conversation callback: {e}", exc_info=True
                        )
                return result

        results = await asyncio.gather(
            *[run_with_semaphore(scenario) for scenario in scenarios],
            return_exceptions=False,
        )

        completed_at = datetime.utcnow().isoformat()

        # Calculate aggregate metrics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        aggregate_metrics = self._calculate_aggregate_metrics(results)

        return SimulationRunResult(
            simulation_id=simulation_id,
            total_simulations=len(scenarios),
            successful=successful,
            failed=failed,
            results=results,
            aggregate_metrics=aggregate_metrics,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _check_stop_conditions(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Check all stop conditions.

        Args:
            context: Current conversation context
            last_message: Last message in conversation

        Returns:
            (should_stop, reason) tuple
        """
        for condition in self.stop_conditions:
            should_stop, reason = condition.should_stop(context, last_message)
            if should_stop:
                return True, reason
        return False, None

    def _calculate_aggregate_metrics(self, results: List[SimulationResult]) -> dict:
        """Calculate aggregate metrics across all simulations.

        Args:
            results: List of simulation results

        Returns:
            Dictionary of aggregate metrics
        """
        if not results:
            return {}

        # Success rate
        success_rate = sum(1 for r in results if r.success) / len(results)

        # Average turns to completion
        avg_turns = sum(r.metrics.get("turns_to_completion", 0) for r in results) / len(
            results
        )

        # Average duration
        avg_duration = sum(r.duration_ms for r in results) / len(results)

        # Total cost
        total_cost = sum(r.metrics.get("estimated_cost", 0) for r in results)

        # Total tokens
        total_tokens = sum(r.metrics.get("total_tokens", 0) for r in results)

        return {
            "success_rate": success_rate,
            "avg_turns_to_completion": avg_turns,
            "avg_duration_ms": avg_duration,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
        }
