"""LangGraph workflow with tool-level semantic caching.

This experiment caches individual tool outputs using Cortex Search.
The LLM still generates plans, but tool execution may hit cache.
"""
import json
import logging
from typing import Literal, TypedDict, Optional, Tuple

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, END
from opentelemetry import trace

from shared.cortex_models import CortexLLM
from shared.tools import MATH_TOOLS
from shared.utils import get_snowpark_session, application_name
from trulens.otel.semconv.trace import SpanAttributes
from trulens.core.otel.instrument import instrument

logger = logging.getLogger(application_name)
tracer = trace.get_tracer(__name__)

# Tool cache configuration
TOOL_CACHE_TABLE = "AI_FDE.CACHE_EXPERIMENTS.tool_cache"
TOOL_CACHE_SEARCH_SERVICE = "AI_FDE.CACHE_EXPERIMENTS.tool_cache_search"
DEFAULT_SIMILARITY_THRESHOLD = 0.85


class ToolCacheState(MessagesState):
    """State with tool cache tracking."""
    tool_cache_hits: dict  # tool_name -> list of hit booleans
    cache_enabled: bool


class ToolCacheChecker:
    """Helper class to check and store tool cache results.

    Uses the shared tool_cache table with Cortex Search filtering.
    """

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        enabled: bool = True
    ):
        self.similarity_threshold = similarity_threshold
        self.enabled = enabled
        self.session = get_snowpark_session()

    def _serialize_tool_input(self, tool_input: dict) -> str:
        """Serialize tool input for caching.

        Creates a human-readable string that can be semantically matched.
        """
        # Convert to key=value format for better semantic matching
        # e.g., {"a": 5, "b": 3} -> "a=5 b=3"
        parts = [f"{k}={v}" for k, v in sorted(tool_input.items())]
        return " ".join(parts)

    def get_cached_result(
        self,
        tool_name: str,
        tool_input: dict
    ) -> Optional[Tuple[str, float]]:
        """Get cached tool output using Cortex Search with tool filter.

        Returns:
            Tuple of (cached_output, similarity_score) if found, None otherwise
        """
        if not self.enabled:
            return None

        input_text = self._serialize_tool_input(tool_input)

        # Build JSON query for Cortex Search with filter
        query_json = json.dumps({
            "query": input_text,  # Human-readable search string
            "columns": ["input_text", "output_text", "metadata", "timestamp"],
            "filter": {"@eq": {"tool_name": tool_name}},  # Filter by tool_name
            "limit": 5
        })

        # Escape JSON for SQL
        query_json_escaped = query_json.replace("'", "''")

        # Use Cortex Search SEARCH_PREVIEW function
        search_query = f"""
            SELECT PARSE_JSON(
                SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    '{TOOL_CACHE_SEARCH_SERVICE}',
                    '{query_json_escaped}'
                )
            )['results'] as results
        """

        try:
            result = self.session.sql(search_query).collect()

            if result and result[0]['RESULTS']:
                # SEARCH_PREVIEW returns results as an array
                results_array = json.loads(result[0]['RESULTS']) if isinstance(result[0]['RESULTS'], str) else result[0]['RESULTS']

                if results_array and len(results_array) > 0:
                    # Take first result (most similar)
                    cached_data = results_array[0]
                    output_text = cached_data.get('output_text', '')

                    logger.info(
                        f"Tool cache HIT for {tool_name}",
                        extra={
                            "tool_name": tool_name,
                            "input": input_text[:100]
                        }
                    )
                    return (output_text, 1.0)  # Cortex Search doesn't return similarity score
                else:
                    logger.info(
                        f"Tool cache MISS for {tool_name}",
                        extra={
                            "tool_name": tool_name,
                            "input": input_text[:100]
                        }
                    )
                    return None
            else:
                logger.info(
                    f"Tool cache MISS for {tool_name}",
                    extra={
                        "tool_name": tool_name,
                        "input": input_text[:100]
                    }
                )
                return None
        except Exception as e:
            logger.error(f"Error checking tool cache: {e}")
            return None

    def store_result(
        self,
        tool_name: str,
        tool_input: dict,
        tool_output: str,
        metadata: Optional[dict] = None
    ):
        """Store tool execution result in cache."""
        if not self.enabled:
            return

        input_text = self._serialize_tool_input(tool_input)
        metadata_json = json.dumps(metadata or {})

        # Escape single quotes for SQL
        tool_name_escaped = tool_name.replace("'", "''")
        input_text_escaped = input_text.replace("'", "''")
        tool_output_escaped = tool_output.replace("'", "''")
        metadata_json_escaped = metadata_json.replace("'", "''")

        # Use SELECT instead of VALUES when using PARSE_JSON
        insert_query = f"""
        INSERT INTO {TOOL_CACHE_TABLE} (
            tool_name,
            input_text,
            output_text,
            metadata
        )
        SELECT
            '{tool_name_escaped}',
            '{input_text_escaped}',
            '{tool_output_escaped}',
            PARSE_JSON('{metadata_json_escaped}')
        """

        try:
            self.session.sql(insert_query).collect()
            logger.info(
                f"Stored tool result in cache: {tool_name}",
                extra={"tool_name": tool_name, "input": input_text[:100]}
            )
        except Exception as e:
            logger.error(f"Error storing tool result: {e}")


# Initialize tool cache checker
tool_cache_checker = ToolCacheChecker()


SYSTEM_PROMPT = """You are a helpful math assistant with access to calculator tools.

Available tools:
{tools}

When the user asks a math question:
1. Use the appropriate tool(s) to perform calculations
2. Return the final answer clearly

Be concise and accurate."""


@instrument(span_type=SpanAttributes.SpanType.GENERATION)
def call_llm(state: ToolCacheState):
    """Invoke Cortex LLM to get response or tool call."""
    with tracer.start_as_current_span("llm.invoke") as span:
        span.set_attribute("llm.message_count", len(state["messages"]))
        logger.info(f"Invoking Cortex LLM with {len(MATH_TOOLS)} tools")

        # Create model with tools
        cortex_llm = CortexLLM(model_name="claude-3-5-sonnet")
        model = cortex_llm.get_llm()
        if MATH_TOOLS:
            model = model.bind_tools(MATH_TOOLS)

        system_message = SYSTEM_PROMPT.format(tools=MATH_TOOLS)
        messages = [SystemMessage(content=system_message)] + state["messages"]

        response = model.invoke(messages)

        span.set_attribute("llm.response_type", type(response).__name__)
        return {"messages": [response]}


@instrument(span_type=SpanAttributes.SpanType.TOOL)
def call_tools_with_cache(state: ToolCacheState):
    """Execute tools with caching layer.

    For each tool call:
    1. Check cache using Cortex Search with tool_name filter
    2. If cache hit, return cached result
    3. If cache miss, execute tool and store result
    """
    with tracer.start_as_current_span("tools.cached_execution") as span:
        # Get the last AI message which contains tool calls
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])

        if not tool_calls:
            logger.warning("No tool calls found in last message")
            return {"messages": []}

        span.set_attribute("tool.call_count", len(tool_calls))

        # Create tool lookup
        tools_by_name = {tool.name: tool for tool in MATH_TOOLS}

        tool_messages = []
        cache_hits = state.get("tool_cache_hits", {})

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["args"]
            tool_call_id = tool_call["id"]

            logger.info(
                f"Processing tool call: {tool_name}",
                extra={"tool_name": tool_name, "input": tool_input}
            )

            # Check cache first
            cached_result = tool_cache_checker.get_cached_result(tool_name, tool_input)

            if cached_result:
                # Cache hit - use cached result
                output_text, similarity = cached_result
                tool_message = ToolMessage(
                    content=output_text,
                    tool_call_id=tool_call_id,
                    name=tool_name
                )

                # Track cache hit
                if tool_name not in cache_hits:
                    cache_hits[tool_name] = []
                cache_hits[tool_name].append(True)

                span.add_event(
                    "tool.cache_hit",
                    attributes={
                        "tool.name": tool_name,
                        "cache.similarity": similarity
                    }
                )
            else:
                # Cache miss - execute tool
                if tool_name not in tools_by_name:
                    logger.error(f"Tool not found: {tool_name}")
                    continue

                tool = tools_by_name[tool_name]

                try:
                    result = tool.invoke(tool_input)
                    output_text = str(result)

                    # Store in cache for future use
                    tool_cache_checker.store_result(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_output=output_text,
                        metadata={"tool_call_id": tool_call_id}
                    )

                    tool_message = ToolMessage(
                        content=output_text,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )

                    # Track cache miss
                    if tool_name not in cache_hits:
                        cache_hits[tool_name] = []
                    cache_hits[tool_name].append(False)

                    span.add_event(
                        "tool.cache_miss",
                        attributes={"tool.name": tool_name}
                    )

                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    tool_message = ToolMessage(
                        content=f"Error: {str(e)}",
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )

            tool_messages.append(tool_message)

        return {"messages": tool_messages, "tool_cache_hits": cache_hits}


def tools_condition(state: ToolCacheState) -> Literal["tools", "__end__"]:
    """Route to tools if the last message has tool calls."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"


def create_tool_cache_graph(
    cache_enabled: bool = True,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
):
    """Create LangGraph workflow with tool caching.

    Args:
        cache_enabled: Whether to enable tool caching
        similarity_threshold: Minimum similarity score for cache hits
    """
    # Update global cache checker config
    tool_cache_checker.enabled = cache_enabled
    tool_cache_checker.similarity_threshold = similarity_threshold

    logger.info(
        "Creating tool cache graph",
        extra={
            "cache_enabled": cache_enabled,
            "similarity_threshold": similarity_threshold
        }
    )

    # Build graph
    workflow = StateGraph(ToolCacheState)

    workflow.add_node("llm", call_llm)
    workflow.add_node("tools", call_tools_with_cache)

    workflow.set_entry_point("llm")
    workflow.add_conditional_edges("llm", tools_condition)
    workflow.add_edge("tools", "llm")

    graph = workflow.compile()

    return graph
