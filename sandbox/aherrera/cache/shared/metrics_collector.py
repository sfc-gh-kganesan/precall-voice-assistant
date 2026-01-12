"""Performance metrics collector for caching experiments.

Tracks detailed metrics beyond TruLens correctness:
- Latency (ms)
- Token usage
- Cache hits/misses
- Tool calls
- Cost savings
"""
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from shared.utils import application_name

logger = logging.getLogger(application_name)


@dataclass
class InvocationMetrics:
    """Metrics for a single query invocation."""
    query_id: str
    query: str
    response: str
    latency_ms: float
    tokens_used: int
    cache_hit: bool = False
    tools_called: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/logging."""
        return asdict(self)


class PerformanceMetrics:
    """Collector for performance metrics across experiment runs."""

    def __init__(self, token_cost_per_1k: float = 0.003):
        """Initialize metrics collector.

        Args:
            token_cost_per_1k: Cost per 1000 tokens for cost calculations
        """
        self.invocations: List[InvocationMetrics] = []
        self.token_cost_per_1k = token_cost_per_1k
        logger.info("Initialized PerformanceMetrics collector", extra={
            "token_cost_per_1k": token_cost_per_1k
        })

    def record_invocation(
        self,
        query_id: str,
        query: str,
        response: str,
        latency_ms: float,
        tokens_used: int,
        cache_hit: bool = False,
        tools_called: Optional[List[str]] = None
    ):
        """Record metrics for a single invocation.

        Args:
            query_id: Unique identifier for the query
            query: The input query text
            response: The response text
            latency_ms: Latency in milliseconds
            tokens_used: Total tokens used (input + output)
            cache_hit: Whether this was a cache hit
            tools_called: List of tool names that were called
        """
        if tools_called is None:
            tools_called = []

        invocation = InvocationMetrics(
            query_id=query_id,
            query=query,
            response=response,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cache_hit=cache_hit,
            tools_called=tools_called
        )

        self.invocations.append(invocation)

        logger.debug(
            f"Recorded invocation metrics for query_id={query_id}",
            extra={
                "query_id": query_id,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "cache_hit": cache_hit,
                "tools_count": len(tools_called)
            }
        )

    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate metrics across all invocations.

        Returns:
            Dictionary containing aggregate metrics:
            - total_invocations
            - cache_hit_rate
            - avg_latency_ms, p50_latency_ms, p95_latency_ms, p99_latency_ms
            - total_tokens, avg_tokens_per_query
            - cache_hits, cache_misses
            - cost_estimate_usd
            - tool_usage_stats
        """
        if not self.invocations:
            return {
                "total_invocations": 0,
                "cache_hit_rate": 0.0,
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "total_tokens": 0,
                "avg_tokens_per_query": 0.0,
                "cache_hits": 0,
                "cache_misses": 0,
                "cost_estimate_usd": 0.0,
            }

        total = len(self.invocations)
        cache_hits = sum(1 for inv in self.invocations if inv.cache_hit)
        cache_misses = total - cache_hits

        # Latency stats
        latencies = sorted([inv.latency_ms for inv in self.invocations])
        avg_latency = sum(latencies) / len(latencies)
        p50_latency = latencies[int(len(latencies) * 0.50)]
        p95_latency = latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
        p99_latency = latencies[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0]

        # Token stats
        total_tokens = sum(inv.tokens_used for inv in self.invocations)
        avg_tokens = total_tokens / total if total > 0 else 0

        # Cost estimate
        cost_estimate = (total_tokens / 1000) * self.token_cost_per_1k

        # Tool usage stats
        tool_usage = {}
        for inv in self.invocations:
            for tool in inv.tools_called:
                tool_usage[tool] = tool_usage.get(tool, 0) + 1

        metrics = {
            "total_invocations": total,
            "cache_hit_rate": cache_hits / total if total > 0 else 0.0,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "avg_latency_ms": round(avg_latency, 2),
            "p50_latency_ms": round(p50_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "total_tokens": total_tokens,
            "avg_tokens_per_query": round(avg_tokens, 2),
            "cost_estimate_usd": round(cost_estimate, 4),
            "tool_usage": tool_usage,
        }

        logger.info("Calculated aggregate metrics", extra=metrics)
        return metrics

    def compare_with_baseline(
        self,
        baseline_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare current metrics with baseline metrics.

        Args:
            baseline_metrics: Aggregate metrics from baseline experiment

        Returns:
            Dictionary containing comparison metrics:
            - latency_reduction_pct
            - token_reduction_pct
            - cost_savings_usd
            - speedup_factor
        """
        current = self.get_aggregate_metrics()

        if not baseline_metrics or baseline_metrics.get("total_invocations", 0) == 0:
            logger.warning("No baseline metrics to compare against")
            return {}

        # Latency comparison
        baseline_latency = baseline_metrics.get("avg_latency_ms", 0)
        current_latency = current.get("avg_latency_ms", 0)
        latency_reduction = 0.0
        speedup_factor = 1.0

        if baseline_latency > 0:
            latency_reduction = (baseline_latency - current_latency) / baseline_latency
            speedup_factor = baseline_latency / current_latency if current_latency > 0 else 1.0

        # Token/cost comparison
        baseline_tokens = baseline_metrics.get("total_tokens", 0)
        current_tokens = current.get("total_tokens", 0)
        token_reduction = 0.0
        cost_savings = 0.0

        if baseline_tokens > 0:
            token_reduction = (baseline_tokens - current_tokens) / baseline_tokens
            tokens_saved = baseline_tokens - current_tokens
            cost_savings = (tokens_saved / 1000) * self.token_cost_per_1k

        comparison = {
            "latency_reduction_pct": round(latency_reduction * 100, 2),
            "token_reduction_pct": round(token_reduction * 100, 2),
            "cost_savings_usd": round(cost_savings, 4),
            "speedup_factor": round(speedup_factor, 2),
            "baseline_avg_latency_ms": baseline_latency,
            "current_avg_latency_ms": current_latency,
            "baseline_total_tokens": baseline_tokens,
            "current_total_tokens": current_tokens,
        }

        logger.info("Comparison with baseline", extra=comparison)
        return comparison

    def get_all_invocations(self) -> List[Dict[str, Any]]:
        """Get all recorded invocations as dictionaries."""
        return [inv.to_dict() for inv in self.invocations]

    def reset(self):
        """Reset all collected metrics."""
        self.invocations = []
        logger.info("Reset PerformanceMetrics collector")


# Context manager for timing invocations
class TimedInvocation:
    """Context manager to time graph invocations and record metrics."""

    def __init__(
        self,
        metrics_collector: PerformanceMetrics,
        query_id: str,
        query: str
    ):
        """Initialize timed invocation.

        Args:
            metrics_collector: PerformanceMetrics instance to record to
            query_id: Unique identifier for the query
            query: The input query text
        """
        self.metrics_collector = metrics_collector
        self.query_id = query_id
        self.query = query
        self.start_time = None
        self.response = None
        self.tokens_used = 0
        self.cache_hit = False
        self.tools_called = []

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metrics."""
        if self.start_time is not None:
            latency_ms = (time.time() - self.start_time) * 1000

            self.metrics_collector.record_invocation(
                query_id=self.query_id,
                query=self.query,
                response=self.response or "",
                latency_ms=latency_ms,
                tokens_used=self.tokens_used,
                cache_hit=self.cache_hit,
                tools_called=self.tools_called
            )

        return False  # Don't suppress exceptions

    def set_response(
        self,
        response: str,
        tokens_used: int = 0,
        cache_hit: bool = False,
        tools_called: Optional[List[str]] = None
    ):
        """Set response details for this invocation.

        Args:
            response: The response text
            tokens_used: Total tokens used
            cache_hit: Whether this was a cache hit
            tools_called: List of tool names that were called
        """
        self.response = response
        self.tokens_used = tokens_used
        self.cache_hit = cache_hit
        self.tools_called = tools_called or []
