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
from backend.core.generator import ScenarioGenerator
from backend.core.stop_conditions import (
    MaxTurnsCondition,
    TimeoutCondition,
    AgentSignalCondition,
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
            agent_client = self._create_agent_client(project)
            stop_conditions = self._create_stop_conditions(simulation)
            metrics_calculator = MetricsCalculator(
                cost_per_1k_tokens=0.001
            )  # Default cost
            scenario_generator = self._create_scenario_generator(project)
            user_simulator = self._create_user_simulator()  # Add user simulator

            # Generate scenarios - use custom if provided, otherwise generate
            if simulation.custom_scenarios:
                base_scenarios = self._parse_custom_scenarios(
                    simulation.custom_scenarios
                )
                logger.info(f"Using {len(base_scenarios)} custom personas...")

                # Distribute scenarios across num_simulations (round-robin)
                scenarios = []
                for i in range(simulation.num_simulations):
                    scenario_index = i % len(base_scenarios)
                    scenarios.append(base_scenarios[scenario_index])

                logger.info(
                    f"Created {len(scenarios)} scenarios from {len(base_scenarios)} personas (round-robin distribution)"
                )
            else:
                logger.info(f"Generating {simulation.num_simulations} scenarios...")
                scenarios = await self._generate_scenarios(
                    scenario_generator,
                    simulation.num_simulations,
                    project.business_context,
                )
            logger.info(f"Loaded {len(scenarios)} scenarios")

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
            engine = SimulationEngine(
                agent_client=agent_client,
                stop_conditions=stop_conditions,
                metrics_calculator=metrics_calculator,
                concurrency=simulation.concurrency,
                max_turns=simulation.max_turns,
                user_simulator=user_simulator,  # Pass user simulator
                on_conversation_complete=on_conversation_complete,  # Pass callback
                on_conversation_start=on_conversation_start,  # Pass start callback
                on_message_added=on_message_added,  # Pass message callback
            )

            # Run simulations with concurrency control
            logger.info(
                f"Running {len(scenarios)} simulations with concurrency={simulation.concurrency}..."
            )
            await engine.run_simulations(scenarios=scenarios)
            logger.info("Simulations completed, all conversations stored incrementally")

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
        conditions = []

        for condition_name in simulation.stop_conditions:
            if condition_name == "max_turns":
                conditions.append(MaxTurnsCondition(max_turns=simulation.max_turns))
            elif condition_name == "timeout":
                conditions.append(
                    TimeoutCondition(timeout_seconds=simulation.timeout_seconds)
                )
            elif condition_name == "agent_signal":
                # Look for common completion signals
                conditions.append(
                    AgentSignalCondition(
                        completion_signals=["RESOLVED", "COMPLETED", "DONE"]
                    )
                )

        if len(conditions) > 1:
            return [CombinedStopCondition(conditions)]
        return conditions

    def _create_scenario_generator(
        self, project: Project
    ) -> Optional[ScenarioGenerator]:
        """Create a scenario generator if LLM config is available."""
        # For now, we'll use OpenAI if API key is in environment
        # In production, this should be configurable per project
        import os

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OPENAI_API_KEY found, will use fallback scenarios")
            return None

        return ScenarioGenerator(
            provider="openai",
            api_key=api_key,
            model="gpt-4o-mini",
        )

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

    async def _generate_scenarios(
        self,
        generator: Optional[ScenarioGenerator],
        num_scenarios: int,
        business_context: str,
    ) -> List[Scenario]:
        """Generate test scenarios."""
        if generator:
            try:
                scenarios = await generator.generate_scenarios(
                    business_context=business_context,
                    num_scenarios=num_scenarios,
                )
                return scenarios
            except Exception as e:
                logger.warning(
                    f"Failed to generate scenarios with LLM: {e}, using fallback"
                )

        # Fallback: create simple test scenarios
        return self._create_fallback_scenarios(num_scenarios)

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
    ) -> int:
        """Create conversation record at start."""
        from datetime import datetime

        conversation = Conversation(
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
        return conversation.id

    async def _add_message(self, conversation_id: int, message):
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

        # Update num_turns if this is a user message
        if message.role == "user":
            conversation = (
                self.db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if conversation:
                conversation.num_turns += 1
                self.db.commit()

    async def _complete_conversation(
        self, conversation_id: int, result: SimulationResult
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

        # Store metrics
        for metric_name, metric_value in result.metrics.items():
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

        # Calculate num_turns from messages
        num_turns = len([m for m in result.messages if m.role == "user"])

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
            api_key = os.getenv("SNOWFLAKE_CORTEX_API_KEY")
            base_url = os.getenv("SNOWFLAKE_CORTEX_BASE_URL")
            model = os.getenv("SNOWFLAKE_CORTEX_MODEL", "snowflake-arctic")

            if not api_key or not base_url:
                logger.warning(
                    "Snowflake Cortex not configured, skipping AI insights generation. "
                    "Set SNOWFLAKE_CORTEX_API_KEY and SNOWFLAKE_CORTEX_BASE_URL to enable."
                )
                return

            logger.info(f"Generating AI insights for simulation {simulation_id} in background")
            judge = InsightsJudge(api_key=api_key, base_url=base_url, model=model)
            insights = await judge.generate_insights(simulation_id, self.db)

            logger.info(f"Successfully generated {len(insights)} AI insights for simulation {simulation_id}")

        except Exception as e:
            logger.error(
                f"Failed to generate AI insights for simulation {simulation_id}: {e}",
                exc_info=True,
            )
            # Do not raise - this is a background task, should not fail the simulation

