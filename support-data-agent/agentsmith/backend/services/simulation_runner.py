"""Service for running simulations in the background."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.models.models import (
    Simulation,
    Project,
    Conversation,
    Message,
    ConversationMetric,
    SimulationStatus,
)
from backend.core.simulator import SimulationEngine
from backend.core.agent_client import AgentClient
from backend.core.conversation_loader import (
    ConversationLoader,
)

from backend.core.stop_conditions import (
    MaxTurnsCondition,
    TimeoutCondition,
    CombinedStopCondition,
)
from backend.core.evaluator import MetricsCalculator
from backend.core.interfaces import Scenario, SimulationResult

logger = logging.getLogger(__name__)


class SimulationRunner:
    """Handles the execution of simulations."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def run_simulation(self, simulation_id: int):
        """Run a simulation in the background."""
        simulation = (
            self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        )
        if not simulation:
            logger.error(f"Simulation {simulation_id} not found")
            return

        logger.info(f"Starting simulation {simulation_id}")

        try:
            # Update status to running
            simulation.status = SimulationStatus.RUNNING
            simulation.started_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Simulation {simulation_id} marked as RUNNING")

            # Load project configuration
            project = simulation.project
            if not project:
                raise ValueError(f"Project {simulation.project_id} not found")

            logger.info(f"Initializing components for simulation {simulation_id}")

            # Initialize components
            # Note: agent_client is no longer needed for analysis (we're not calling the agent)
            # But keep it for backwards compatibility in case we want to re-run failed conversations
            agent_client = self._create_agent_client(project) if False else None
            stop_conditions = self._create_stop_conditions(simulation)
            metrics_calculator = MetricsCalculator(
                cost_per_1k_tokens=0.001
            )  # Default cost

            # NEW: Create conversation analyzer for quality evaluation
            conversation_analyzer = self._create_conversation_analyzer(simulation)

            # Create Snowflake session for loading conversations from AGENT_TRACES
            # Note: We use a separate Snowflake connection for querying conversation data,
            # while self.db (SQLite) is used for storing simulation metadata
            snowflake_session = next(get_snowflake_db())
            if snowflake_session is None:
                raise ValueError(
                    "Snowflake is not configured. Cannot load conversations from AGENT_TRACES. "
                    "Set SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ACCOUNT, "
                    "SNOWFLAKE_WAREHOUSE, and SNOWFLAKE_ROLE environment variables."
                )

            try:
                # NEW: Use conversation loader with Snowflake session
                conversation_loader = ConversationLoader(
                    snowflake_session, project=project
                )

                # Load real conversations from Snowflake AGENT_TRACES table
                logger.info(
                    f"Loading up to {simulation.num_simulations} conversations from Snowflake..."
                )
                logger.info(
                    f"Using table from project config: {project.source_database}.{project.source_schema}.{project.source_table if project.source_database else 'env vars'}"
                )

                # Use date range and filters from simulation config
                scenarios = await conversation_loader.load_conversations(
                    date_from=simulation.date_from,
                    date_to=simulation.date_to,
                    conversation_ids=simulation.conversation_ids,
                    triggered_by=simulation.triggered_by,
                    include_errors_only=simulation.include_errors_only,
                    limit=simulation.num_simulations,
                )
            finally:
                # Clean up Snowflake session after loading conversations
                if snowflake_session:
                    snowflake_session.close()
                    logger.info("Snowflake session closed after loading conversations")

            if not scenarios:
                raise ValueError(
                    "No conversations found to analyze. Check date range and filters."
                )

            logger.info(f"Loaded {len(scenarios)} real conversations for analysis")

            # Create conversation tracking dict for storing conversation IDs
            conversation_map = {}  # scenario -> conversation_id

            # Define callbacks for incremental storage
            async def on_conversation_start(scenario):
                """Create conversation record when it starts."""
                conversation_id = await self._start_conversation(simulation, scenario)
                conversation_map[id(scenario)] = conversation_id
                logger.info(
                    f"Started conversation (persona: {scenario.persona.name}, id: {conversation_id})"
                )
                return conversation_id

            async def on_message_added(scenario, message):
                """Store message immediately after it's added."""
                conversation_id = conversation_map.get(id(scenario))
                if conversation_id:
                    await self._add_message(conversation_id, message)

            async def on_conversation_complete(scenario, result):
                """Update conversation with final results after it completes."""
                conversation_id = conversation_map.get(id(scenario))
                if conversation_id:
                    await self._complete_conversation(conversation_id, result)
                    logger.info(
                        f"Completed conversation (persona: {scenario.persona.name})"
                    )

            # Create simulation engine
            # Note: For analysis mode, we don't need agent_client or user_simulator
            # The engine will process existing conversation data instead of simulating new ones
            engine = SimulationEngine(
                agent_client=agent_client,  # None for analysis mode
                stop_conditions=stop_conditions,
                metrics_calculator=metrics_calculator,
                conversation_analyzer=conversation_analyzer,  # NEW: For evaluating completed conversations
                concurrency=simulation.concurrency,
                max_turns=simulation.max_turns,
                conversation_timeout_seconds=simulation.conversation_timeout_seconds,
                user_simulator=None,  # Not needed for analysis
                on_conversation_complete=on_conversation_complete,
                on_conversation_start=on_conversation_start,
                on_message_added=on_message_added,
            )

            # Run analysis with concurrency control
            logger.info(
                f"Analyzing {len(scenarios)} conversations with concurrency={simulation.concurrency}..."
            )
            await engine.run_simulations(scenarios=scenarios)
            logger.info("Analysis completed, all conversations stored incrementally")

            # Mark as completed
            simulation.status = SimulationStatus.COMPLETED
            simulation.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Simulation {simulation_id} completed successfully")

            # Trigger AI insights generation in the background
            await self._generate_ai_insights_async(simulation_id)

        except Exception as e:
            logger.error(f"Simulation {simulation_id} failed: {e}", exc_info=True)
            simulation.status = SimulationStatus.FAILED
            simulation.error_message = str(e)
            simulation.completed_at = datetime.utcnow()
            self.db.commit()

    def _create_agent_client(self, project: Project) -> AgentClient:
        """Create an agent client from project configuration."""
        return AgentClient(
            endpoint=project.agent_endpoint,
            auth_type=project.auth_type.value,
            auth_credentials=project.auth_credentials,
            custom_headers=project.custom_headers,
            timeout=120.0,  # Increased to match simulation timeout for MCP tool calls (DDA + Glean)
        )

    def _create_stop_conditions(self, simulation: Simulation) -> List[Any]:
        """Create stop conditions from simulation configuration."""
        from backend.core.llm_judge import LLMStopCondition
        import os

        conditions = []

        for condition_name in simulation.stop_conditions:
            if condition_name == "max_turns":
                conditions.append(MaxTurnsCondition(max_turns=simulation.max_turns))
            elif condition_name == "timeout":
                conditions.append(
                    TimeoutCondition(timeout_seconds=simulation.timeout_seconds)
                )
            # elif condition_name == "agent_signal":
            #     # DISABLED: Text-based signal matching is too error-prone for support conversations
            #     # Agent responses naturally contain words like "RESOLVED", "COMPLETED", "DONE"
            #     # when discussing resolved tickets, completed tasks, etc.
            #     # Use llm_judge for intelligent completion detection instead.
            #     conditions.append(
            #         AgentSignalCondition(
            #             completion_signals=["RESOLVED", "COMPLETED", "DONE"]
            #         )
            #     )
            elif condition_name == "llm_judge":
                # Use same env var pattern as analyzer and insights
                api_key = os.getenv("SNOWFLAKE_PASSWORD")
                account = os.getenv("SNOWFLAKE_ACCOUNT")

                if api_key and account:
                    base_url = (
                        f"https://{account}.snowflakecomputing.com/api/v2/cortex/v1"
                    )
                    logger.info("Adding LLM-based stop condition with Snowflake Cortex")
                    conditions.append(
                        LLMStopCondition(
                            api_key=api_key,
                            base_url=base_url,
                            model="claude-4-sonnet",
                            confidence_threshold=0.75,  # Slightly more lenient than default
                            max_retries=2,
                        )
                    )
                else:
                    logger.warning(
                        "llm_judge requested but Snowflake Cortex not configured. "
                        "Set SNOWFLAKE_PASSWORD and SNOWFLAKE_ACCOUNT."
                    )

        if len(conditions) > 1:
            return [CombinedStopCondition(conditions)]
        return conditions

    def _create_user_simulator(self) -> Optional:
        """Create a user simulator if LLM config is available."""
        from backend.core.user_simulator import UserSimulator
        import os

        api_key = os.environ.get("SNOWFLAKE_PASSWORD")
        account = os.environ.get("SNOWFLAKE_ACCOUNT")

        if not api_key or not account:
            logger.warning(
                "No Snowflake credentials found, multi-turn conversations disabled"
            )
            return None

        base_url = f"https://{account}.snowflakecomputing.com/api/v2/cortex/v1"

        logger.info(
            "Initializing UserSimulator for multi-turn conversations with Snowflake Cortex"
        )
        return UserSimulator(
            provider="snowflake",
            api_key=api_key,
            model="claude-4-sonnet",
            base_url=base_url,
        )

    def _parse_custom_scenarios(self, custom_scenarios: List[Dict]) -> List[Scenario]:
        """Parse custom scenarios from API request."""
        from backend.core.interfaces import Persona, Scenario

        scenarios = []
        for scenario_dict in custom_scenarios:
            try:
                # Parse persona
                persona_dict = scenario_dict.get("persona", {})

                # Extract knowledge_base - can be at persona level or scenario level
                knowledge_base = persona_dict.get(
                    "knowledge_base"
                ) or scenario_dict.get("knowledge_base")

                persona = Persona(
                    name=persona_dict.get("name", "Custom User"),
                    goal=persona_dict.get("goal", "Complete task"),
                    tone=persona_dict.get("tone", "neutral"),
                    personality_traits=persona_dict.get(
                        "personality_traits", ["curious"]
                    ),
                    technical_level=persona_dict.get("technical_level", "intermediate"),
                    edge_case=persona_dict.get("edge_case", False),
                    knowledge_base=knowledge_base,
                )

                # Parse scenario
                scenario = Scenario(
                    persona=persona,
                    initial_query=scenario_dict.get("initial_query", "I need help"),
                    expected_outcome=scenario_dict.get(
                        "expected_outcome", "Issue resolved"
                    ),
                    complexity=scenario_dict.get("complexity", "simple"),
                    category=scenario_dict.get("category", "general"),
                    knowledge_base=knowledge_base,  # Store in scenario for easy access
                )
                scenarios.append(scenario)
            except Exception as e:
                logger.warning(f"Failed to parse custom scenario: {e}, skipping")
                continue

        if not scenarios:
            logger.warning("No valid custom scenarios provided, using fallback")
            return self._create_fallback_scenarios(1)

        return scenarios

    def _create_fallback_scenarios(self, num_scenarios: int) -> List[Scenario]:
        """Create simple fallback scenarios when LLM generation fails."""
        from backend.core.interfaces import Persona

        templates = [
            ("I need help with login issues", "Login", "polite", "login_issue"),
            (
                "I can't access my account",
                "Account Access",
                "frustrated",
                "account_access",
            ),
            (
                "How do I reset my password?",
                "Password Reset",
                "confused",
                "password_reset",
            ),
            (
                "I need technical support",
                "Technical Support",
                "professional",
                "technical_support",
            ),
            (
                "Can you help me with my subscription?",
                "Subscription",
                "curious",
                "subscription",
            ),
        ]

        scenarios = []
        for i in range(num_scenarios):
            template_idx = i % len(templates)
            initial_query, goal, tone, category = templates[template_idx]

            persona = Persona(
                name=f"Test User {i + 1}",
                goal=goal,
                tone=tone,
                personality_traits=["polite", "patient"],
                technical_level="intermediate",
                edge_case=False,
            )

            scenario = Scenario(
                persona=persona,
                initial_query=initial_query,
                expected_outcome=f"{goal} resolved successfully",
                complexity="simple",
                category=category,
            )
            scenarios.append(scenario)

        return scenarios

    async def _start_conversation(
        self,
        simulation: Simulation,
        scenario: Scenario,
    ) -> str:
        """Create conversation record at start."""
        from datetime import datetime
        import uuid

        conversation_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            simulation_id=simulation.id,
            persona=scenario.persona.model_dump(),
            scenario={
                "initial_query": scenario.initial_query,
                "expected_outcome": scenario.expected_outcome,
                "complexity": scenario.complexity,
                "category": scenario.category,
            },
            success=False,  # Will update on completion
            num_turns=0,  # Will update as messages are added
            total_duration_ms=0.0,  # Will update on completion
            stop_reason=None,  # Will update on completion
            started_at=datetime.utcnow(),
            completed_at=None,  # Will update on completion
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation_id

    async def _add_message(self, conversation_id: str, message):
        """Store a single message immediately."""
        from datetime import datetime

        # Convert timestamp string to datetime if it's a string
        timestamp = message.timestamp
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        db_message = Message(
            conversation_id=conversation_id,
            role=message.role,
            content=message.content,
            tool_calls=message.tool_calls,
            timestamp=timestamp,
        )
        self.db.add(db_message)
        self.db.commit()

        # Update num_turns for all messages (user + assistant)
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if conversation:
            conversation.num_turns += 1
            self.db.commit()

    async def _complete_conversation(
        self, conversation_id: str, result: SimulationResult
    ):
        """Update conversation with final results."""
        from datetime import datetime

        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not conversation:
            return

        # Update final fields
        conversation.success = result.success
        conversation.total_duration_ms = result.duration_ms
        conversation.stop_reason = (
            result.stop_reason.value
            if hasattr(result.stop_reason, "value")
            else str(result.stop_reason)
        )
        conversation.completed_at = datetime.utcnow()

        # Store evaluation results in scenario JSON if available
        # TODO: Once DB migration is done, store in dedicated columns
        if "evaluation" in result.metrics:
            eval_data = result.metrics["evaluation"]

            # Store evaluation in scenario metadata for now
            if not conversation.scenario:
                conversation.scenario = {}

            conversation.scenario["evaluation"] = {
                "quality_score": eval_data.get("quality_score"),
                "confidence": eval_data.get("confidence"),
                "ending_assessment": eval_data.get("ending_assessment"),
                "reasoning": eval_data.get("reasoning"),
                "knowledge_gap": eval_data.get("knowledge_gap"),
                "capability_gap": eval_data.get("capability_gap"),
            }

            logger.info(
                f"Stored evaluation for conversation {conversation_id}: "
                f"quality={eval_data.get('quality_score'):.2f}, "
                f"ending={eval_data.get('ending_assessment')}"
            )

        # Store metrics
        for metric_name, metric_value in result.metrics.items():
            # Skip 'evaluation' dict - already stored in scenario JSON
            if metric_name == "evaluation":
                continue

            if isinstance(metric_value, dict):
                for sub_name, sub_value in metric_value.items():
                    metric = ConversationMetric(
                        conversation_id=conversation.id,
                        metric_name=f"{metric_name}.{sub_name}",
                        metric_value=float(sub_value)
                        if isinstance(sub_value, (int, float))
                        else 0.0,
                        meta_data={"parent_metric": metric_name},
                    )
                    self.db.add(metric)
            elif isinstance(metric_value, (int, float)):
                metric = ConversationMetric(
                    conversation_id=conversation.id,
                    metric_name=metric_name,
                    metric_value=float(metric_value),
                )
                self.db.add(metric)

        self.db.commit()

    async def _store_conversation(
        self, simulation: Simulation, scenario: Scenario, result: SimulationResult
    ):
        """Store conversation results in the database."""
        from datetime import datetime

        # Calculate num_turns from messages (count all messages)
        num_turns = len(result.messages)

        # Get timestamps from messages
        started_at = (
            datetime.fromisoformat(result.messages[0].timestamp)
            if result.messages
            else datetime.utcnow()
        )
        completed_at = (
            datetime.fromisoformat(result.messages[-1].timestamp)
            if result.messages
            else datetime.utcnow()
        )

        # Create conversation record
        conversation = Conversation(
            simulation_id=simulation.id,
            persona=scenario.persona.model_dump(),  # Convert Pydantic model to dict
            scenario={
                "initial_query": scenario.initial_query,
                "expected_outcome": scenario.expected_outcome,
                "complexity": scenario.complexity,
                "category": scenario.category,
            },
            success=result.success,
            num_turns=num_turns,
            total_duration_ms=result.duration_ms,
            stop_reason=result.stop_reason.value
            if hasattr(result.stop_reason, "value")
            else str(result.stop_reason),
            started_at=started_at,
            completed_at=completed_at,
        )
        self.db.add(conversation)
        self.db.flush()  # Get the ID

        # Store messages
        for msg in result.messages:
            # Convert timestamp string to datetime if it's a string
            timestamp = msg.timestamp
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            elif timestamp is None:
                timestamp = datetime.utcnow()

            message = Message(
                conversation_id=conversation.id,
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                timestamp=timestamp,
            )
            self.db.add(message)

        # Store metrics
        for metric_name, metric_value in result.metrics.items():
            # Handle nested metrics (like tool_usage)
            if isinstance(metric_value, dict):
                for sub_name, sub_value in metric_value.items():
                    metric = ConversationMetric(
                        conversation_id=conversation.id,
                        metric_name=f"{metric_name}.{sub_name}",
                        metric_value=float(sub_value)
                        if isinstance(sub_value, (int, float))
                        else 0.0,
                        meta_data={"parent_metric": metric_name},
                    )
                    self.db.add(metric)
            elif isinstance(metric_value, (int, float)):
                metric = ConversationMetric(
                    conversation_id=conversation.id,
                    metric_name=metric_name,
                    metric_value=float(metric_value),
                )
                self.db.add(metric)

        self.db.commit()

    async def _generate_ai_insights_async(self, simulation_id: int):
        """Generate AI insights in the background after simulation completes."""
        import os
        from backend.core.insights_judge import InsightsJudge

        try:
            api_key = os.getenv("SNOWFLAKE_PASSWORD")
            account = os.getenv("SNOWFLAKE_ACCOUNT")
            model = os.getenv("SNOWFLAKE_CORTEX_MODEL", "claude-4-sonnet")

            if not api_key or not account:
                logger.warning(
                    "Snowflake Cortex not configured, skipping AI insights generation. "
                    "Set SNOWFLAKE_PASSWORD and SNOWFLAKE_ACCOUNT to enable."
                )
                return

            base_url = f"https://{account}.snowflakecomputing.com/api/v2/cortex/v1"

            logger.info(
                f"Generating AI insights for simulation {simulation_id} in background"
            )
            judge = InsightsJudge(api_key=api_key, base_url=base_url, model=model)
            insights = await judge.generate_insights(simulation_id, self.db)

            # Mark insights as generated on the simulation record
            simulation = (
                self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
            )
            if simulation:
                simulation.llm_insights_generated = True
                simulation.llm_insights_generated_at = datetime.utcnow()
                self.db.commit()
                logger.info(
                    f"Successfully generated {len(insights)} AI insights for simulation {simulation_id}, flag set"
                )

                # Generate code/knowledge recommendations for each insight
                logger.info(
                    f"Generating recommendations for {len(insights)} insights..."
                )
                from backend.api.routes.insights import (
                    _generate_recommendations_for_insights,
                )

                await _generate_recommendations_for_insights(
                    simulation, insights, self.db
                )
                logger.info(
                    f"Recommendation generation complete for simulation {simulation_id}"
                )
            else:
                logger.warning(
                    f"Simulation {simulation_id} not found when setting insights flag"
                )

        except Exception as e:
            logger.error(
                f"Failed to generate AI insights for simulation {simulation_id}: {e}",
                exc_info=True,
            )
            # Do not raise - this is a background task, should not fail the simulation
