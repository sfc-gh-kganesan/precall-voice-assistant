"""Unit tests for metrics calculator."""

import pytest
from datetime import datetime, timedelta
from backend.core.interfaces import ConversationContext, ConversationMessage
from backend.core.evaluator import MetricsCalculator


@pytest.mark.unit
class TestMetricsCalculator:
    """Tests for MetricsCalculator."""

    def test_calculate_turns_to_completion(self):
        """Test calculating number of turns to completion."""
        calculator = MetricsCalculator()

        messages = [
            ConversationMessage(role="user", content="Message 1"),
            ConversationMessage(role="assistant", content="Response 1"),
            ConversationMessage(role="user", content="Message 2"),
            ConversationMessage(role="assistant", content="Response 2"),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=4,
        )

        metrics = calculator.calculate_metrics(context, messages)
        assert metrics["turns_to_completion"] == 4

    def test_calculate_total_duration(self):
        """Test calculating total conversation duration."""
        calculator = MetricsCalculator()

        started_at = datetime.utcnow() - timedelta(seconds=120)  # 2 minutes ago
        completed_at = datetime.utcnow()

        messages = [
            ConversationMessage(
                role="user", content="Message", timestamp=started_at.isoformat()
            ),
            ConversationMessage(
                role="assistant", content="Response", timestamp=completed_at.isoformat()
            ),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=started_at.isoformat(),
            turn_count=2,
        )

        metrics = calculator.calculate_metrics(context, messages)
        # Duration should be approximately 120000ms (2 minutes)
        assert 119000 <= metrics["total_duration_ms"] <= 121000

    def test_calculate_average_latency(self):
        """Test calculating average latency per turn."""
        calculator = MetricsCalculator()

        messages = [
            ConversationMessage(role="user", content="M1", latency_ms=100),
            ConversationMessage(role="assistant", content="R1", latency_ms=1500),
            ConversationMessage(role="user", content="M2", latency_ms=50),
            ConversationMessage(role="assistant", content="R2", latency_ms=1200),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=4,
        )

        metrics = calculator.calculate_metrics(context, messages)
        # Average = (100 + 1500 + 50 + 1200) / 4 = 712.5
        assert metrics["average_latency_ms"] == 712.5

    def test_calculate_token_usage(self):
        """Test calculating total token usage."""
        calculator = MetricsCalculator()

        messages = [
            ConversationMessage(role="user", content="M1", token_count=10),
            ConversationMessage(role="assistant", content="R1", token_count=50),
            ConversationMessage(role="user", content="M2", token_count=15),
            ConversationMessage(role="assistant", content="R2", token_count=40),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=4,
        )

        metrics = calculator.calculate_metrics(context, messages)
        assert metrics["total_tokens"] == 115

    def test_calculate_tool_usage_count(self):
        """Test calculating tool usage frequency."""
        calculator = MetricsCalculator()

        messages = [
            ConversationMessage(role="user", content="M1"),
            ConversationMessage(
                role="assistant",
                content="R1",
                tool_calls=[{"tool": "slack_search", "args": {}}],
            ),
            ConversationMessage(role="user", content="M2"),
            ConversationMessage(
                role="assistant",
                content="R2",
                tool_calls=[
                    {"tool": "jira_search", "args": {}},
                    {"tool": "slack_search", "args": {}},
                ],
            ),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=4,
        )

        metrics = calculator.calculate_metrics(context, messages)
        assert metrics["total_tool_calls"] == 3
        assert metrics["tool_usage"]["slack_search"] == 2
        assert metrics["tool_usage"]["jira_search"] == 1

    def test_calculate_metrics_empty_conversation(self):
        """Test metrics calculation for empty conversation."""
        calculator = MetricsCalculator()

        messages = []
        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=0,
        )

        metrics = calculator.calculate_metrics(context, messages)
        assert metrics["turns_to_completion"] == 0
        assert metrics["total_tokens"] == 0
        assert metrics["total_tool_calls"] == 0

    def test_calculate_metrics_no_latency_data(self):
        """Test metrics when latency data is missing."""
        calculator = MetricsCalculator()

        messages = [
            ConversationMessage(role="user", content="M1"),  # No latency
            ConversationMessage(role="assistant", content="R1", latency_ms=1000),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=2,
        )

        metrics = calculator.calculate_metrics(context, messages)
        # Should only average messages with latency data
        assert metrics["average_latency_ms"] == 1000

    def test_calculate_efficiency_score(self):
        """Test calculating efficiency score (turns vs time)."""
        calculator = MetricsCalculator()

        started_at = datetime.utcnow() - timedelta(seconds=60)  # 1 minute
        messages = [
            ConversationMessage(
                role="user", content="M1", timestamp=started_at.isoformat()
            ),
            ConversationMessage(role="assistant", content="R1"),
            ConversationMessage(role="user", content="M2"),
            ConversationMessage(
                role="assistant", content="R2", timestamp=datetime.utcnow().isoformat()
            ),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=started_at.isoformat(),
            turn_count=4,
        )

        metrics = calculator.calculate_metrics(context, messages)
        # Efficiency could be turns per minute
        assert "efficiency_score" in metrics
        assert metrics["efficiency_score"] > 0

    def test_calculate_cost_metrics(self):
        """Test calculating cost metrics based on token usage."""
        calculator = MetricsCalculator(cost_per_1k_tokens=0.002)

        messages = [
            ConversationMessage(role="user", content="M1", token_count=100),
            ConversationMessage(role="assistant", content="R1", token_count=500),
        ]

        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=2,
        )

        metrics = calculator.calculate_metrics(context, messages)
        # 600 tokens * $0.002 / 1000 = $0.0012
        assert abs(metrics["estimated_cost"] - 0.0012) < 0.0001
