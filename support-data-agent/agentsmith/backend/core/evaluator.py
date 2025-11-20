"""Metrics calculator for evaluating conversation performance."""

from typing import Dict, List
from datetime import datetime
from collections import defaultdict
from backend.core.interfaces import ConversationContext, ConversationMessage


class MetricsCalculator:
    """Calculate metrics for conversation evaluation."""

    def __init__(self, cost_per_1k_tokens: float = 0.0):
        """Initialize metrics calculator.

        Args:
            cost_per_1k_tokens: Cost per 1000 tokens for cost estimation
        """
        self.cost_per_1k_tokens = cost_per_1k_tokens

    def calculate_metrics(
        self,
        conversation: ConversationContext,
        messages: List[ConversationMessage],
    ) -> Dict[str, float]:
        """Calculate all metrics for a conversation.

        Args:
            conversation: The conversation context
            messages: List of messages in the conversation

        Returns:
            Dictionary of metric names to values
        """
        metrics = {}

        # Basic metrics
        metrics["turns_to_completion"] = len(messages)

        # Duration metrics
        if messages:
            metrics["total_duration_ms"] = self._calculate_duration(
                messages, conversation
            )
        else:
            metrics["total_duration_ms"] = 0

        # Latency metrics
        metrics["average_latency_ms"] = self._calculate_average_latency(messages)

        # Token usage metrics
        metrics["total_tokens"] = self._calculate_total_tokens(messages)

        # Tool usage metrics
        tool_metrics = self._calculate_tool_usage(messages)
        metrics["total_tool_calls"] = tool_metrics["total"]
        metrics["tool_usage"] = tool_metrics["breakdown"]

        # Efficiency score (turns per minute)
        if metrics["total_duration_ms"] > 0:
            duration_minutes = metrics["total_duration_ms"] / 60000
            metrics["efficiency_score"] = (
                len(messages) / duration_minutes if duration_minutes > 0 else 0
            )
        else:
            metrics["efficiency_score"] = 0

        # Cost estimation
        if self.cost_per_1k_tokens > 0:
            metrics["estimated_cost"] = (
                metrics["total_tokens"] / 1000
            ) * self.cost_per_1k_tokens
        else:
            metrics["estimated_cost"] = 0

        return metrics

    def _calculate_duration(
        self, messages: List[ConversationMessage], conversation: ConversationContext
    ) -> float:
        """Calculate total duration in milliseconds."""
        if not messages:
            return 0

        # Try to use message timestamps if available
        messages_with_timestamps = [m for m in messages if m.timestamp]
        if len(messages_with_timestamps) >= 2:
            start = datetime.fromisoformat(messages_with_timestamps[0].timestamp)
            end = datetime.fromisoformat(messages_with_timestamps[-1].timestamp)
            return (end - start).total_seconds() * 1000

        # Fall back to conversation start time
        started_at = datetime.fromisoformat(conversation.started_at)
        elapsed = (datetime.utcnow() - started_at).total_seconds()
        return elapsed * 1000

    def _calculate_average_latency(self, messages: List[ConversationMessage]) -> float:
        """Calculate average latency per message."""
        latencies = [m.latency_ms for m in messages if m.latency_ms is not None]
        if not latencies:
            return 0
        return sum(latencies) / len(latencies)

    def _calculate_total_tokens(self, messages: List[ConversationMessage]) -> int:
        """Calculate total token count."""
        return sum(m.token_count or 0 for m in messages)

    def _calculate_tool_usage(self, messages: List[ConversationMessage]) -> Dict:
        """Calculate tool usage statistics."""
        tool_counts = defaultdict(int)
        total_calls = 0

        for message in messages:
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get("tool", "unknown")
                    tool_counts[tool_name] += 1
                    total_calls += 1

        return {
            "total": total_calls,
            "breakdown": dict(tool_counts),
        }
