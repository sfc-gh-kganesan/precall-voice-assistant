"""Core interfaces and protocols for agentsim."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from enum import Enum
from pydantic import BaseModel


class StopReason(Enum):
    """Reasons for stopping a conversation."""

    MAX_TURNS = "max_turns"
    TIMEOUT = "timeout"
    AGENT_SIGNAL = "agent_signal"
    CUSTOM_CONDITION = "custom_condition"
    LLM_EVALUATION = "llm_evaluation"
    ERROR = "error"


class ConversationMessage(BaseModel):
    """A message in a conversation."""

    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None
    latency_ms: Optional[float] = None
    token_count: Optional[int] = None


class ConversationContext(BaseModel):
    """Context for an ongoing conversation."""

    conversation_id: str
    messages: List[ConversationMessage]
    started_at: str
    turn_count: int = 0
    metadata: Dict[str, Any] = {}


class Persona(BaseModel):
    """A generated persona for testing."""

    name: str
    goal: str
    tone: str
    personality_traits: List[str]
    technical_level: str  # beginner, intermediate, expert
    edge_case: bool = False
    knowledge_base: Optional[Dict[str, Any]] = (
        None  # Real data the persona can reference
    )


class Scenario(BaseModel):
    """A test scenario for simulation."""

    persona: Persona
    initial_query: str
    expected_outcome: Optional[str] = None
    complexity: str  # simple, moderate, complex
    category: str  # e.g., login_issue, data_query, bug_report
    knowledge_base: Optional[Dict[str, Any]] = (
        None  # Forwarded from persona for easy access
    )


class StopCondition(ABC):
    """Abstract base class for stop conditions."""

    @abstractmethod
    def should_stop(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Check if conversation should stop.

        Returns:
            (should_stop, reason) tuple
        """
        pass


class AgentResponse(BaseModel):
    """Response from the agent under test."""

    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    completion_signal: Optional[str] = None  # Agent can signal completion
    metadata: Dict[str, Any] = {}


class AgentClientProtocol(Protocol):
    """Protocol for agent communication."""

    async def send_message(
        self,
        message: str,
        conversation_id: str,
        context: Optional[List[ConversationMessage]] = None,
    ) -> AgentResponse:
        """Send a message to the agent and get response."""
        ...


class ScenarioGeneratorProtocol(Protocol):
    """Protocol for generating test scenarios."""

    async def generate_scenarios(
        self,
        business_context: str,
        num_scenarios: int,
        historical_conversations: Optional[List[Dict[str, Any]]] = None,
        edge_case_ratio: float = 0.2,
    ) -> List[Scenario]:
        """Generate test scenarios based on context."""
        ...


class MetricsCalculatorProtocol(Protocol):
    """Protocol for calculating conversation metrics."""

    def calculate_metrics(
        self,
        conversation: ConversationContext,
        messages: List[ConversationMessage],
    ) -> Dict[str, float]:
        """Calculate metrics for a completed conversation."""
        ...


class SimulationResult(BaseModel):
    """Result of a single simulation."""

    conversation_id: str
    scenario: Scenario
    messages: List[ConversationMessage]
    success: bool
    stop_reason: StopReason
    metrics: Dict[str, Any]  # Changed from float to Any to support nested dicts
    duration_ms: float


class SimulationRunResult(BaseModel):
    """Results of a complete simulation run."""

    simulation_id: int
    total_simulations: int
    successful: int
    failed: int
    results: List[SimulationResult]
    aggregate_metrics: Dict[str, float]
    started_at: str
    completed_at: str
