"""Pydantic schemas for API requests and responses."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime


# Project schemas
class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str
    description: Optional[str] = None
    business_context: str
    agent_endpoint: Optional[str] = None  # Optional for analysis-only projects
    auth_type: str = "none"  # none, bearer, api_key, basic
    auth_credentials: Dict[str, str] = {}
    custom_headers: Optional[Dict[str, str]] = None
    conversation_examples: Optional[List[Dict[str, Any]]] = None
    # Snowflake data source
    source_database: Optional[str] = None
    source_schema: Optional[str] = None
    source_table: Optional[str] = None
    # GitHub configuration
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    target_path: Optional[str] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: int
    name: str
    description: Optional[str]
    business_context: str
    agent_endpoint: Optional[str]  # Optional
    auth_type: str
    source_database: Optional[str]
    source_schema: Optional[str]
    source_table: Optional[str]
    github_owner: Optional[str]
    github_repo: Optional[str]
    target_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Simulation schemas
class SimulationCreate(BaseModel):
    """Schema for creating a simulation (conversation analysis)."""

    project_id: int

    # Conversation selection (for analysis mode)
    num_simulations: int  # Maps to conversation_limit (max conversations to analyze)
    date_from: Optional[datetime] = None  # Start date (default: 7 days ago)
    date_to: Optional[datetime] = None  # End date (default: now)

    # Optional filters
    conversation_ids: Optional[List[str]] = None  # Specific Snowflake conversation IDs
    triggered_by: Optional[str] = None  # Filter: 'voice' or 'text'
    include_errors_only: bool = False  # Only analyze conversations with errors

    # Analysis configuration
    concurrency: int = 1
    max_turns: int = 20
    timeout_seconds: int = 300
    conversation_timeout_seconds: int = 600  # Max time per conversation (10 minutes)
    stop_conditions: List[str] = ["llm_judge", "max_turns"]
    metrics_config: List[str] = ["efficiency", "quality", "tool_usage"]

    # Legacy fields (kept for backwards compatibility)
    edge_case_ratio: float = 0.2  # Not used in analysis mode
    custom_scenarios: Optional[List[Dict[str, Any]]] = None  # Not used in analysis mode


class SimulationResponse(BaseModel):
    """Schema for simulation response."""

    id: int
    project_id: int
    num_simulations: int
    status: str
    conversation_timeout_seconds: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SimulationResultsResponse(BaseModel):
    """Schema for simulation results."""

    id: int
    project_id: int
    num_simulations: int
    status: str
    successful: int
    failed: int
    aggregate_metrics: Dict[str, Any]


# Message schemas
class MessageResponse(BaseModel):
    """Schema for message response."""

    id: int
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]]
    latency_ms: Optional[float]
    token_count: Optional[int]
    timestamp: datetime

    class Config:
        from_attributes = True


# Conversation schemas
class ConversationSummaryResponse(BaseModel):
    """Schema for conversation summary in list view."""

    id: str  # UUID
    simulation_id: int
    persona: Dict[str, Any]  # Include persona for progress tracking
    success: bool
    num_turns: int
    total_duration_ms: float
    stop_reason: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Schema for full conversation details."""

    id: str  # UUID
    simulation_id: int
    persona: Dict[str, Any]
    scenario: Dict[str, Any]
    success: bool
    num_turns: int
    total_duration_ms: float
    stop_reason: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


# Persona Template schemas
class PersonaTemplateCreate(BaseModel):
    """Schema for creating a persona template."""

    name: str
    goal: str
    tone: str = "professional"
    personality_traits: List[str] = []
    technical_level: str = "intermediate"
    edge_case: bool = False
    default_query: Optional[str] = None
    expected_outcome: Optional[str] = None
    complexity: str = "simple"
    category: str = "general"
    knowledge_base: Optional[Dict[str, Any]] = None


class PersonaTemplateResponse(BaseModel):
    """Schema for persona template response."""

    id: int
    project_id: int
    name: str
    goal: str
    tone: str
    personality_traits: List[str]
    technical_level: str
    edge_case: bool
    default_query: Optional[str]
    expected_outcome: Optional[str]
    complexity: str
    category: str
    knowledge_base: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# Improvement Suggestion schemas
class ImprovementSuggestionResponse(BaseModel):
    """Schema for AI-generated improvement suggestion response."""

    id: int
    simulation_id: int
    category: str
    title: str
    description: str
    priority: str
    evidence: Dict[str, Any]
    code_recommendation: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CombinedInsightsResponse(BaseModel):
    """Schema for combined rule-based and AI insights."""

    rule_based: List[Dict[str, Any]]  # From frontend calculations
    ai_generated: List[ImprovementSuggestionResponse]


class CreateGithubIssueRequest(BaseModel):
    """Schema for GitHub issue creation with optional custom content."""

    title: Optional[str] = None
    body: Optional[str] = None
