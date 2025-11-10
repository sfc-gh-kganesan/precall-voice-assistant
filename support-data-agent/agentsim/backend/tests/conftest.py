"""Pytest configuration and shared fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from backend.models.base import Base
from typing import Generator


@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_llm_response():
    """Mock LLM API responses to avoid costs during testing."""
    return {
        "openai": {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a mocked response.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
        "anthropic": {
            "id": "msg_test123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "This is a mocked response."}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
    }


@pytest.fixture
def sample_project_config():
    """Sample project configuration for testing."""
    return {
        "name": "Test Customer Support Agent",
        "description": "Testing customer support agent with Slack, Jira, and usage data tools",
        "business_context": "Customer support agent that helps resolve technical issues",
        "agent_endpoint": "http://localhost:8000/api/chat",
        "auth_type": "bearer",
        "auth_token": "test_token_123",
    }


@pytest.fixture
def sample_simulation_config():
    """Sample simulation configuration for testing."""
    return {
        "num_simulations": 10,
        "concurrency": 1,
        "max_turns": 20,
        "timeout_seconds": 300,
        "stop_conditions": ["max_turns", "agent_signal"],
        "metrics": ["efficiency", "quality", "tool_usage"],
    }


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing scenario generation."""
    return [
        {
            "role": "user",
            "content": "I'm having trouble logging into the app",
            "timestamp": "2024-01-01T10:00:00Z",
        },
        {
            "role": "assistant",
            "content": "I can help you with that. Let me check your account status.",
            "timestamp": "2024-01-01T10:00:05Z",
            "tool_calls": [{"tool": "check_user_status", "args": {"user_id": "12345"}}],
        },
        {
            "role": "assistant",
            "content": "I've found the issue. Your account was temporarily locked due to multiple failed login attempts. I've unlocked it for you.",
            "timestamp": "2024-01-01T10:00:15Z",
        },
        {
            "role": "user",
            "content": "Thank you! I can log in now.",
            "timestamp": "2024-01-01T10:00:30Z",
        },
    ]
