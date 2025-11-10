"""Database models for agentsim."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from .base import Base


class AuthType(enum.Enum):
    """Authentication types for agent endpoints."""

    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class SimulationStatus(enum.Enum):
    """Status of a simulation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class Project(Base):
    """Project configuration for agent simulation."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_context: Mapped[str] = mapped_column(Text)

    # Agent configuration
    agent_endpoint: Mapped[str] = mapped_column(String(512))
    auth_type: Mapped[AuthType] = mapped_column(SQLEnum(AuthType))
    auth_credentials: Mapped[Dict[str, Any]] = mapped_column(
        JSON
    )  # Store tokens, keys, etc.
    custom_headers: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON, nullable=True
    )

    # Historical data
    conversation_examples: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    simulations: Mapped[List["Simulation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    personas: Mapped[List["PersonaTemplate"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class PersonaTemplate(Base):
    """Reusable persona template for a project."""

    __tablename__ = "persona_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))

    # Persona details
    name: Mapped[str] = mapped_column(String(255))
    goal: Mapped[str] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(String(50), default="professional")
    personality_traits: Mapped[List[str]] = mapped_column(JSON)
    technical_level: Mapped[str] = mapped_column(String(50), default="intermediate")
    edge_case: Mapped[bool] = mapped_column(default=False)

    # Default scenario for this persona
    default_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    complexity: Mapped[str] = mapped_column(String(50), default="simple")
    category: Mapped[str] = mapped_column(String(100), default="general")

    # Knowledge base for realistic responses
    knowledge_base: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="personas")


class Simulation(Base):
    """A simulation run with configuration and results."""

    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))

    # Configuration
    num_simulations: Mapped[int] = mapped_column(Integer)
    concurrency: Mapped[int] = mapped_column(Integer, default=1)
    max_turns: Mapped[int] = mapped_column(Integer, default=20)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    stop_conditions: Mapped[List[str]] = mapped_column(
        JSON
    )  # List of stop condition names
    metrics_config: Mapped[List[str]] = mapped_column(
        JSON
    )  # List of metrics to calculate
    custom_scenarios: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )  # Custom personas/scenarios

    # Status
    status: Mapped[SimulationStatus] = mapped_column(
        SQLEnum(SimulationStatus), default=SimulationStatus.PENDING
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="simulations")
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="simulation", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """A single conversation/simulation instance."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id"))

    # Scenario information
    persona: Mapped[Dict[str, Any]] = mapped_column(JSON)  # Generated persona details
    scenario: Mapped[Dict[str, Any]] = mapped_column(JSON)  # Test scenario details

    # Results
    success: Mapped[bool] = mapped_column(default=False)
    num_turns: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    stop_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    simulation: Mapped["Simulation"] = relationship(back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    metrics: Mapped[List["ConversationMetric"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    """A single message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))

    role: Mapped[str] = mapped_column(String(50))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )

    # Metrics for this turn
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class ConversationMetric(Base):
    """Calculated metrics for a conversation."""

    __tablename__ = "conversation_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))

    metric_name: Mapped[str] = mapped_column(String(255))
    metric_value: Mapped[float] = mapped_column(Float)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # Renamed from metadata

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="metrics")


class ImprovementSuggestion(Base):
    """Suggested improvements for an agent."""

    __tablename__ = "improvement_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id"))

    category: Mapped[str] = mapped_column(String(100))  # tool, prompt, logic, etc.
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(50))  # high, medium, low
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSON)  # Supporting data

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
