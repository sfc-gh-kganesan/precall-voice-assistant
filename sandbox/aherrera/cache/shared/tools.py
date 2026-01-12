"""Common tools for agent experiments.

Includes math operations, data query tools, Q&A tools, and multi-step reasoning tools.
All tools include tracing and logging for observability.
"""
import logging
import time
from langchain_core.tools import tool

from shared.utils import application_name, tracer

logger = logging.getLogger(application_name)

# Math operations (from jsummer example)

@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.multiply") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Multiplying {a} and {b}", extra={"a": a, "b": b})

        # Simulate production tool latency
        time.sleep(7)

        result = a * b
        span.set_attribute("tool.output", result)
        return result


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.add") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Adding {a} and {b}", extra={"a": a, "b": b})

        # Simulate production tool latency
        time.sleep(7)

        result = a + b
        span.set_attribute("tool.output", result)
        return result


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` by `b`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.divide") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Dividing {a} by {b}", extra={"a": a, "b": b})
        if b == 0:
            span.set_attribute("tool.error", "Division by zero")
            logger.error("Division by zero")
            raise ValueError("Cannot divide by zero")

        # Simulate production tool latency
        time.sleep(7)

        result = a / b
        span.set_attribute("tool.output", result)
        return result


@tool
def subtract(a: int, b: int) -> int:
    """Subtract `b` from `a`.

    Args:
        a: First int
        b: Second int
    """
    with tracer.start_as_current_span("tool.subtract") as span:
        span.set_attribute("tool.input.a", a)
        span.set_attribute("tool.input.b", b)
        logger.info(f"Subtracting {b} from {a}", extra={"a": a, "b": b})

        # Simulate production tool latency
        time.sleep(7)

        result = a - b
        span.set_attribute("tool.output", result)
        return result


# Data analysis tools (placeholder for Cortex Analyst integration)

@tool
def query_database(query: str) -> str:
    """Execute a database query and return results.

    This tool will be integrated with Cortex Analyst for text-to-SQL.

    Args:
        query: Natural language query to execute
    """
    with tracer.start_as_current_span("tool.query_database") as span:
        span.set_attribute("tool.input.query", query)
        logger.info(f"Querying database: {query}")
        # Placeholder - will integrate with Cortex Analyst
        result = f"Query result for: {query}"
        span.set_attribute("tool.output", result)
        return result


# Q&A tools (placeholder for knowledge retrieval)

@tool
def search_knowledge(question: str) -> str:
    """Search knowledge base for information.

    Args:
        question: Question to search for
    """
    with tracer.start_as_current_span("tool.search_knowledge") as span:
        span.set_attribute("tool.input.question", question)
        logger.info(f"Searching knowledge: {question}")
        # Placeholder - will integrate with knowledge source or Cortex Search
        result = f"Answer for: {question}"
        span.set_attribute("tool.output", result)
        return result


# Multi-step reasoning helper

@tool
def calculate_average(numbers: list[int]) -> float:
    """Calculate the average of a list of numbers.

    Args:
        numbers: List of integers to average
    """
    with tracer.start_as_current_span("tool.calculate_average") as span:
        span.set_attribute("tool.input.count", len(numbers))
        logger.info(f"Calculating average of {len(numbers)} numbers")
        if not numbers:
            raise ValueError("Cannot calculate average of empty list")

        # Simulate production tool latency
        time.sleep(7)

        result = sum(numbers) / len(numbers)
        span.set_attribute("tool.output", result)
        return result


# All available tools
MATH_TOOLS = [multiply, add, divide, subtract, calculate_average]
DATA_TOOLS = [query_database]
QA_TOOLS = [search_knowledge]
ALL_TOOLS = MATH_TOOLS + DATA_TOOLS + QA_TOOLS
