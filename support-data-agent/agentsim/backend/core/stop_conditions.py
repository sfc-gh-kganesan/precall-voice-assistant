"""Stop condition implementations for controlling simulation termination."""

from typing import Optional, Callable, List
from datetime import datetime
from backend.core.interfaces import (
    StopCondition,
    ConversationContext,
    ConversationMessage,
    StopReason,
)


class MaxTurnsCondition(StopCondition):
    """Stop conversation after maximum number of turns."""

    def __init__(self, max_turns: int):
        self.max_turns = max_turns

    def should_stop(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Check if conversation has reached max turns."""
        if context.turn_count >= self.max_turns:
            return True, StopReason.MAX_TURNS
        return False, None


class TimeoutCondition(StopCondition):
    """Stop conversation after timeout duration."""

    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds

    def should_stop(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Check if conversation has timed out."""
        started_at = datetime.fromisoformat(context.started_at)
        elapsed = (datetime.utcnow() - started_at).total_seconds()

        if elapsed >= self.timeout_seconds:
            return True, StopReason.TIMEOUT
        return False, None


class AgentSignalCondition(StopCondition):
    """Stop conversation when agent sends completion signal."""

    def __init__(self, completion_signals: List[str]):
        self.completion_signals = [signal.lower() for signal in completion_signals]

    def should_stop(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Check if agent sent a completion signal."""
        content_lower = last_message.content.lower()

        for signal in self.completion_signals:
            if signal in content_lower:
                return True, StopReason.AGENT_SIGNAL

        return False, None


class CustomFunctionCondition(StopCondition):
    """Stop conversation based on custom function logic."""

    def __init__(
        self, func: Callable[[ConversationContext, ConversationMessage], bool]
    ):
        self.func = func

    def should_stop(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Check if custom function indicates stop."""
        if self.func(context, last_message):
            return True, StopReason.CUSTOM_CONDITION
        return False, None


class CombinedStopCondition(StopCondition):
    """Combine multiple stop conditions with OR logic."""

    def __init__(self, conditions: List[StopCondition]):
        self.conditions = conditions

    def should_stop(
        self, context: ConversationContext, last_message: ConversationMessage
    ) -> tuple[bool, Optional[StopReason]]:
        """Check if any condition indicates stop."""
        for condition in self.conditions:
            should_stop, reason = condition.should_stop(context, last_message)
            if should_stop:
                return True, reason

        return False, None
