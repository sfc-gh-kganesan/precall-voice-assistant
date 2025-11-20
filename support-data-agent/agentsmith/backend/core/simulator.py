"""Simulation engine for orchestrating agent testing."""

import asyncio
import logging
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

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Engine for running agent simulations."""

    def __init__(
        self,
        agent_client: AgentClientProtocol,
        stop_conditions: Optional[List[StopCondition]] = None,
        metrics_calculator: Optional[MetricsCalculatorProtocol] = None,
        concurrency: int = 1,
        max_turns: int = 20,
        conversation_timeout_seconds: int = 600,
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
            conversation_timeout_seconds: Maximum time per conversation in seconds (default: 600)
            user_simulator: Optional user simulator for multi-turn conversations
            on_conversation_complete: Optional callback when a conversation completes
            on_conversation_start: Optional callback when a conversation starts
            on_message_added: Optional callback when a message is added
        """
        self.agent_client = agent_client
        self.max_turns = max_turns
        self.conversation_timeout_seconds = conversation_timeout_seconds
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
        # Check if this is an analysis scenario (loaded from Snowflake)
        # vs a synthetic simulation scenario
        if scenario.metadata.get("source") == "snowflake_agent_traces":
            # Analysis mode: replay existing messages from Snowflake
            return await self._analyze_existing_conversation(scenario)
        else:
            # Simulation mode: generate new conversation with agent
            return await self._simulate_new_conversation(scenario)

    async def _analyze_existing_conversation(
        self, scenario: Scenario
    ) -> SimulationResult:
        """Analyze an existing conversation loaded from Snowflake.

        Args:
            scenario: Scenario with messages in metadata

        Returns:
            Simulation result with existing messages and calculated metrics
        """
        conversation_id = scenario.metadata.get("conversation_id", str(uuid.uuid4()))
        messages_data = scenario.metadata.get("messages", [])

        # Convert metadata messages to ConversationMessage objects
        messages: List[ConversationMessage] = []
        for msg_data in messages_data:
            # Handle both user/assistant messages
            # Each AGENT_TRACES row has both input_text and output_text
            # We need to create two messages per row
            if msg_data.get("role") == "user" and msg_data.get("content"):
                messages.append(
                    ConversationMessage(
                        role="user",
                        content=msg_data["content"],
                        timestamp=msg_data.get("timestamp"),
                        latency_ms=msg_data.get("latency_ms"),
                        token_count=msg_data.get("token_count"),
                    )
                )
            if msg_data.get("role") == "assistant" and msg_data.get("content"):
                messages.append(
                    ConversationMessage(
                        role="assistant",
                        content=msg_data["content"],
                        timestamp=msg_data.get("timestamp"),
                        latency_ms=msg_data.get("latency_ms"),
                        token_count=msg_data.get("token_count"),
                    )
                )

        if not messages:
            logger.warning(
                f"No messages found in scenario metadata for {conversation_id}"
            )
            # Return empty result
            return SimulationResult(
                conversation_id=conversation_id,
                success=False,
                messages=[],
                stop_reason=StopReason.ERROR,
                duration_ms=0.0,
                metrics={},
            )

        # Get timestamps
        started_at_str = scenario.metadata.get("session_start")
        completed_at_str = scenario.metadata.get("session_end")

        if started_at_str and completed_at_str:
            from datetime import datetime

            started_at = datetime.fromisoformat(started_at_str)
            completed_at = datetime.fromisoformat(completed_at_str)
            duration_ms = (completed_at - started_at).total_seconds() * 1000
        else:
            duration_ms = 0.0

        # Call conversation start callback
        if self.on_conversation_start:
            try:
                await self.on_conversation_start(scenario)
            except Exception as e:
                logger.error(
                    f"Error in conversation start callback: {e}", exc_info=True
                )

        # Call message added callback for each message
        if self.on_message_added:
            for message in messages:
                try:
                    await self.on_message_added(scenario, message)
                except Exception as e:
                    logger.error(f"Error in message added callback: {e}", exc_info=True)

        # Determine success based on errors in metadata
        has_errors = scenario.metadata.get("has_errors", False)
        success = not has_errors

        # Calculate metrics if calculator is available
        metrics = {}
        if self.metrics_calculator:
            context = ConversationContext(
                conversation_id=conversation_id,
                messages=messages,
                started_at=started_at_str or datetime.utcnow().isoformat(),
                turn_count=len(messages),
            )
            try:
                metrics = self.metrics_calculator.calculate_metrics(
                    context=context,
                    success=success,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                logger.warning(f"Failed to calculate metrics: {e}")
                metrics = {}

        # Create result
        result = SimulationResult(
            conversation_id=conversation_id,
            success=success,
            messages=messages,
            stop_reason=StopReason.CUSTOM_CONDITION,  # Already completed
            duration_ms=duration_ms,
            metrics=metrics,
        )

        # Call conversation complete callback
        if self.on_conversation_complete:
            try:
                await self.on_conversation_complete(scenario, result)
            except Exception as e:
                logger.error(
                    f"Error in conversation complete callback: {e}", exc_info=True
                )

        return result

    async def _simulate_new_conversation(self, scenario: Scenario) -> SimulationResult:
        """Simulate a new conversation with the agent (original behavior).

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
            # DEBUG: Log scenario state before creating initial message
            logger.info(
                f"[RUN_SIM START] scenario (id={id(scenario)}): persona={scenario.persona.name}, initial_query={scenario.initial_query[:80]}..."
            )

            initial_message = ConversationMessage(
                role="user",
                content=scenario.initial_query,
                timestamp=datetime.utcnow().isoformat(),
            )

            # DEBUG: Log what was actually stored in the message
            logger.info(
                f"[INITIAL_MSG] Created message with content={initial_message.content[:80]}..."
            )

            messages.append(initial_message)
            context.messages.append(initial_message)
            context.turn_count += 1  # Count all messages (user + assistant)

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

                # Hard guardrail: enforce conversation timeout
                elapsed_seconds = (datetime.utcnow() - started_at).total_seconds()
                if elapsed_seconds > self.conversation_timeout_seconds:
                    logger.warning(
                        f"Conversation {conversation_id} exceeded timeout "
                        f"({elapsed_seconds:.1f}s > {self.conversation_timeout_seconds}s)"
                    )
                    stop_reason = StopReason.TIMEOUT
                    success = False
                    break

                # Check stop conditions before sending
                # Note: LLM judge only evaluates assistant messages, so it won't trigger here
                # This check primarily serves MaxTurns, Timeout, and other conditions
                should_stop, reason = self._check_stop_conditions(
                    context, messages[-1] if messages else initial_message
                )
                if should_stop:
                    stop_reason = reason
                    # LLM_JUDGE is also a success reason
                    success = reason in [
                        StopReason.AGENT_SIGNAL,
                        StopReason.CUSTOM_CONDITION,
                        StopReason.LLM_JUDGE,
                    ]
                    # Require minimum turns for success (avoid premature success)
                    # turn_count now counts all messages: user(1) + assistant(2) + user(3) = 3 messages minimum
                    if success and context.turn_count < 3:
                        success = False
                        logger.warning(
                            f"Conversation stopped after only {context.turn_count} message(s), "
                            f"marking as unsuccessful despite stop reason: {reason}"
                        )
                    break

                # Send message to agent (agent_api.py handles retries internally)
                try:
                    response = await self.agent_client.send_message(
                        message=messages[-1].content,
                        conversation_id=conversation_id,
                        context=messages,
                    )
                except Exception as e:
                    # Agent API failed after all its internal retries
                    logger.error(
                        f"Agent API call failed for conversation {conversation_id}: {e}",
                        exc_info=True,
                    )
                    stop_reason = StopReason.ERROR
                    success = False
                    break

                # Record agent response
                agent_message = ConversationMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                    timestamp=datetime.utcnow().isoformat(),
                )
                messages.append(agent_message)
                context.messages.append(agent_message)
                context.turn_count += 1  # Count all messages (user + assistant)

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
                # LLM judge evaluates here (after assistant messages)
                should_stop, reason = self._check_stop_conditions(
                    context, agent_message
                )
                if should_stop:
                    stop_reason = reason
                    # LLM_JUDGE is also a success reason
                    success = reason in [
                        StopReason.AGENT_SIGNAL,
                        StopReason.CUSTOM_CONDITION,
                        StopReason.LLM_JUDGE,
                    ]
                    # Require minimum turns for success (avoid premature success)
                    # turn_count now counts all messages: user(1) + assistant(2) = 2 messages minimum
                    if success and context.turn_count < 2:
                        success = False
                        logger.warning(
                            f"Conversation stopped after only {context.turn_count} message(s), "
                            f"marking as unsuccessful despite stop reason: {reason}"
                        )
                    break

                # Generate next user message if user simulator is available
                if self.user_simulator:
                    try:
                        # DEBUG: Log what we're passing to user simulator
                        logger.info("=== USER SIMULATOR CALL DEBUG ===")
                        logger.info(f"Conversation ID: {conversation_id}")
                        logger.info(f"Turn count: {context.turn_count}")
                        logger.info(f"Persona name: {scenario.persona.name}")
                        logger.info(f"Persona goal: {scenario.persona.goal}")
                        logger.info(f"Initial query: {scenario.initial_query[:100]}...")
                        logger.info(
                            f"Knowledge base keys: {list(scenario.knowledge_base.keys()) if scenario.knowledge_base else 'None'}"
                        )
                        logger.info(f"Conversation history length: {len(messages)}")
                        logger.info(
                            f"Last 3 message roles: {[(m.role, m.content[:50] + '...') for m in messages[-3:]]}"
                        )
                        logger.info(
                            f"Agent's last message (first 150 chars): {response.content[:150]}..."
                        )

                        next_user_message = await self.user_simulator.generate_response(
                            persona=scenario.persona,
                            conversation_history=messages,
                            agent_last_message=response.content,
                            knowledge_base=scenario.knowledge_base,  # Pass knowledge_base!
                        )

                        logger.info(
                            f"Generated user message (first 150 chars): {next_user_message[:150]}..."
                        )
                        logger.info(
                            f"Generated message is JSON?: {next_user_message.strip().startswith('{')}"
                        )
                        logger.info("=== END USER SIMULATOR DEBUG ===")

                        # Add user's follow-up message
                        user_follow_up = ConversationMessage(
                            role="user",
                            content=next_user_message,
                            timestamp=datetime.utcnow().isoformat(),
                        )
                        messages.append(user_follow_up)
                        context.messages.append(user_follow_up)
                        context.turn_count += 1  # Count all messages (user + assistant)

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

        # Semantic evaluation fallback for max_turns conversations
        # If conversation hit max_turns but wasn't evaluated semantically, check now
        if stop_reason == StopReason.MAX_TURNS and not success and messages:
            # Try to evaluate semantically using LLM judge
            from backend.core.llm_judge import LLMStopCondition
            import os

            cortex_key = os.getenv("SNOWFLAKE_CORTEX_API_KEY")
            cortex_url = os.getenv("SNOWFLAKE_CORTEX_BASE_URL")

            if cortex_key and cortex_url:
                try:
                    logger.info(
                        "Conversation reached max_turns, attempting semantic evaluation"
                    )
                    llm_judge = LLMStopCondition(
                        api_key=cortex_key,
                        base_url=cortex_url,
                        model="claude-4-sonnet",
                        confidence_threshold=0.75,
                        max_retries=2,
                    )

                    # Evaluate the final conversation state
                    should_stop, eval_reason = llm_judge.should_stop(
                        context, messages[-1]
                    )

                    if should_stop and eval_reason == StopReason.LLM_JUDGE:
                        # Conversation actually succeeded semantically
                        success = True
                        stop_reason = StopReason.LLM_JUDGE
                        logger.info(
                            "Semantic evaluation: conversation succeeded despite reaching max_turns"
                        )
                    else:
                        logger.info(
                            "Semantic evaluation: conversation did not meet success criteria"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to perform semantic evaluation fallback: {e}",
                        exc_info=True,
                    )

        # Calculate duration
        duration_ms = (datetime.utcnow() - started_at).total_seconds() * 1000

        # Calculate metrics
        metrics = {}
        if self.metrics_calculator:
            metrics = self.metrics_calculator.calculate_metrics(context, messages)

        # DEBUG: Log scenario state at end of run_simulation
        logger.info(
            f"[RUN_SIM END] scenario (id={id(scenario)}): persona={scenario.persona.name}, initial_query={scenario.initial_query[:80]}..."
        )

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
