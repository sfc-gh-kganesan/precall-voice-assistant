"""Unit tests for stop conditions."""

import pytest
from datetime import datetime, timedelta
from backend.core.interfaces import (
    ConversationContext,
    ConversationMessage,
    StopReason,
)
from backend.core.stop_conditions import (
    MaxTurnsCondition,
    TimeoutCondition,
    AgentSignalCondition,
    CustomFunctionCondition,
    CombinedStopCondition,
)


@pytest.mark.unit
class TestMaxTurnsCondition:
    """Tests for MaxTurnsCondition."""

    def test_not_reached_max_turns(self):
        """Test condition when max turns not reached."""
        condition = MaxTurnsCondition(max_turns=10)
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=5,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is False
        assert reason is None

    def test_reached_max_turns(self):
        """Test condition when max turns reached."""
        condition = MaxTurnsCondition(max_turns=10)
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=10,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.MAX_TURNS

    def test_exceeded_max_turns(self):
        """Test condition when max turns exceeded."""
        condition = MaxTurnsCondition(max_turns=10)
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=15,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.MAX_TURNS


@pytest.mark.unit
class TestTimeoutCondition:
    """Tests for TimeoutCondition."""

    def test_not_timed_out(self):
        """Test condition when timeout not reached."""
        condition = TimeoutCondition(timeout_seconds=300)  # 5 minutes
        started_at = datetime.utcnow() - timedelta(seconds=60)  # Started 1 minute ago
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=started_at.isoformat(),
            turn_count=5,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is False
        assert reason is None

    def test_timed_out(self):
        """Test condition when timeout reached."""
        condition = TimeoutCondition(timeout_seconds=300)  # 5 minutes
        started_at = datetime.utcnow() - timedelta(
            seconds=350
        )  # Started 5.5 minutes ago
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=started_at.isoformat(),
            turn_count=5,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.TIMEOUT


@pytest.mark.unit
class TestAgentSignalCondition:
    """Tests for AgentSignalCondition."""

    def test_no_signal(self):
        """Test when agent doesn't send completion signal."""
        condition = AgentSignalCondition(completion_signals=["RESOLVED", "COMPLETED"])
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=3,
        )
        last_message = ConversationMessage(
            role="assistant",
            content="Let me help you with that.",
        )

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is False
        assert reason is None

    def test_signal_in_content(self):
        """Test when completion signal is in message content."""
        condition = AgentSignalCondition(completion_signals=["RESOLVED", "COMPLETED"])
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=3,
        )
        last_message = ConversationMessage(
            role="assistant",
            content="Your issue has been RESOLVED.",
        )

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.AGENT_SIGNAL

    def test_signal_case_insensitive(self):
        """Test that signal matching is case-insensitive."""
        condition = AgentSignalCondition(completion_signals=["RESOLVED"])
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=3,
        )
        last_message = ConversationMessage(
            role="assistant",
            content="Issue resolved successfully!",
        )

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.AGENT_SIGNAL

    def test_multiple_signals(self):
        """Test with multiple possible completion signals."""
        condition = AgentSignalCondition(
            completion_signals=["RESOLVED", "COMPLETED", "DONE"]
        )
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=3,
        )
        last_message = ConversationMessage(
            role="assistant",
            content="All DONE!",
        )

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.AGENT_SIGNAL


@pytest.mark.unit
class TestCustomFunctionCondition:
    """Tests for CustomFunctionCondition."""

    def test_custom_function_returns_false(self):
        """Test custom function that returns False."""

        def always_continue(context, last_message):
            return False

        condition = CustomFunctionCondition(func=always_continue)
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=5,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is False
        assert reason is None

    def test_custom_function_returns_true(self):
        """Test custom function that returns True."""

        def stop_on_thank_you(context, last_message):
            return "thank you" in last_message.content.lower()

        condition = CustomFunctionCondition(func=stop_on_thank_you)
        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=3,
        )
        last_message = ConversationMessage(
            role="user",
            content="Thank you for your help!",
        )

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.CUSTOM_CONDITION

    def test_custom_function_with_complex_logic(self):
        """Test custom function with complex stopping logic."""

        def stop_if_repeated_errors(context, last_message):
            # Stop if last 3 messages all contain "error"
            recent_messages = (
                context.messages[-3:]
                if len(context.messages) >= 3
                else context.messages
            )
            error_count = sum(
                1 for msg in recent_messages if "error" in msg.content.lower()
            )
            return error_count >= 3

        condition = CustomFunctionCondition(func=stop_if_repeated_errors)

        # Create context with 3 error messages
        messages = [
            ConversationMessage(role="assistant", content="Error occurred"),
            ConversationMessage(role="user", content="Still getting an error"),
            ConversationMessage(role="assistant", content="Another error happened"),
        ]
        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            started_at=datetime.utcnow().isoformat(),
            turn_count=3,
        )
        last_message = messages[-1]

        should_stop, reason = condition.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.CUSTOM_CONDITION


@pytest.mark.unit
class TestCombinedStopCondition:
    """Tests for CombinedStopCondition."""

    def test_no_conditions_met(self):
        """Test when none of the conditions are met."""
        conditions = [
            MaxTurnsCondition(max_turns=10),
            TimeoutCondition(timeout_seconds=300),
        ]
        combined = CombinedStopCondition(conditions=conditions)

        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=5,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = combined.should_stop(context, last_message)
        assert should_stop is False
        assert reason is None

    def test_one_condition_met(self):
        """Test when one of the conditions is met."""
        conditions = [
            MaxTurnsCondition(max_turns=10),
            AgentSignalCondition(completion_signals=["RESOLVED"]),
        ]
        combined = CombinedStopCondition(conditions=conditions)

        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=5,
        )
        last_message = ConversationMessage(
            role="assistant",
            content="Issue RESOLVED",
        )

        should_stop, reason = combined.should_stop(context, last_message)
        assert should_stop is True
        assert reason == StopReason.AGENT_SIGNAL

    def test_multiple_conditions_met_returns_first(self):
        """Test that when multiple conditions are met, the first one is returned."""
        started_at = datetime.utcnow() - timedelta(seconds=400)  # Timed out
        conditions = [
            MaxTurnsCondition(max_turns=10),
            TimeoutCondition(timeout_seconds=300),
        ]
        combined = CombinedStopCondition(conditions=conditions)

        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=started_at.isoformat(),
            turn_count=10,  # Also at max turns
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = combined.should_stop(context, last_message)
        assert should_stop is True
        # Should return the first condition that matched (MaxTurns comes first)
        assert reason == StopReason.MAX_TURNS

    def test_empty_conditions_list(self):
        """Test with no conditions (should never stop)."""
        combined = CombinedStopCondition(conditions=[])

        context = ConversationContext(
            conversation_id="conv_123",
            messages=[],
            started_at=datetime.utcnow().isoformat(),
            turn_count=100,
        )
        last_message = ConversationMessage(role="assistant", content="Response")

        should_stop, reason = combined.should_stop(context, last_message)
        assert should_stop is False
        assert reason is None
