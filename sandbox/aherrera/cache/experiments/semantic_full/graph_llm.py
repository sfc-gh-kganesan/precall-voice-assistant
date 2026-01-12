"""Full Cache LangGraph experiment with Cortex LLM.

Combines both semantic plan caching AND tool-level caching using Snowflake Cortex Search.
- Layer 1 (Plan Cache): Caches LLM planning decisions (tool calls)
- Layer 2 (Tool Cache): Caches individual tool execution results

This represents the maximum caching strategy.
"""
import logging
import json
from typing import Optional, Tuple, Literal
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, END
from opentelemetry import trace

from shared.cortex_models import CortexLLM
from shared.tools import MATH_TOOLS
from shared.utils import get_snowpark_session, application_name
from shared.cache_backends import PlanCacheWithSearch
from trulens.otel.semconv.trace import SpanAttributes
from trulens.core.otel.instrument import instrument

logger = logging.getLogger(application_name)
tracer = trace.get_tracer(__name__)

# Cache configuration
TOOL_CACHE_TABLE = "AI_FDE.CACHE_EXPERIMENTS.tool_cache"
TOOL_CACHE_SEARCH_SERVICE = "AI_FDE.CACHE_EXPERIMENTS.tool_cache_search"
PLAN_CACHE_TABLE = "AI_FDE.CACHE_EXPERIMENTS.plan_cache"
PLAN_CACHE_SEARCH_SERVICE = "AI_FDE.CACHE_EXPERIMENTS.plan_cache_search"


class FullCacheState(MessagesState):
    """State with multi-level cache tracking."""
    plan_cache_hit: bool = False  # True if plan was cached
    tool_cache_hits: dict = {}  # tool_name -> list of hit booleans
    cache_enabled: bool = True


class ToolCacheChecker:
    """Helper class to check and store tool cache results."""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        enabled: bool = True
    ):
        self.similarity_threshold = similarity_threshold
        self.enabled = enabled
        self.session = get_snowpark_session()

    def _serialize_tool_input(self, tool_input: dict) -> str:
        """Serialize tool input for caching - human readable format."""
        parts = [f"{k}={v}" for k, v in sorted(tool_input.items())]
        return " ".join(parts)

    def get_cached_result(
        self,
        tool_name: str,
        tool_input: dict
    ) -> Optional[Tuple[str, float]]:
        """Get cached tool output using Cortex Search with tool filter."""
        if not self.enabled:
            return None

        input_text = self._serialize_tool_input(tool_input)

        # Build JSON query for Cortex Search with filter
        query_json = json.dumps({
            "query": input_text,
            "columns": ["input_text", "output_text", "metadata", "timestamp"],
            "filter": {"@eq": {"tool_name": tool_name}},
            "limit": 5
        })

        query_json_escaped = query_json.replace("'", "''")

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
                results_array = json.loads(result[0]['RESULTS']) if isinstance(result[0]['RESULTS'], str) else result[0]['RESULTS']

                if results_array and len(results_array) > 0:
                    cached_data = results_array[0]
                    output_text = cached_data.get('output_text', '')

                    logger.info(
                        f"Tool cache HIT for {tool_name}",
                        extra={"tool_name": tool_name, "input": input_text[:100]}
                    )
                    return (output_text, 1.0)
                else:
                    logger.info(
                        f"Tool cache MISS for {tool_name}",
                        extra={"tool_name": tool_name, "input": input_text[:100]}
                    )
                    return None
            else:
                logger.info(
                    f"Tool cache MISS for {tool_name}",
                    extra={"tool_name": tool_name, "input": input_text[:100]}
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


def create_full_cache_graph(
    enable_plan_cache: bool = True,
    enable_tool_cache: bool = True,
    similarity_threshold: float = 0.85
):
    """Create LangGraph workflow with both plan and tool caching.

    Args:
        enable_plan_cache: Whether to enable plan caching
        enable_tool_cache: Whether to enable tool caching
        similarity_threshold: Minimum similarity for cache hits (0.0-1.0)
    """
    # Initialize plan cache
    plan_cache: Optional[PlanCacheWithSearch] = None
    if enable_plan_cache:
        plan_cache = PlanCacheWithSearch(
            table_name=PLAN_CACHE_TABLE,
            search_service_name=PLAN_CACHE_SEARCH_SERVICE,
            similarity_threshold=similarity_threshold
        )
        logger.info(
            f"Plan cache enabled with threshold={similarity_threshold}",
            extra={"plan_cache_enabled": True}
        )

    # Configure tool cache
    tool_cache_checker.enabled = enable_tool_cache
    tool_cache_checker.similarity_threshold = similarity_threshold
    if enable_tool_cache:
        logger.info(
            f"Tool cache enabled with threshold={similarity_threshold}",
            extra={"tool_cache_enabled": True}
        )

    logger.info(
        "Creating full cache graph",
        extra={
            "plan_cache": enable_plan_cache,
            "tool_cache": enable_tool_cache,
            "similarity_threshold": similarity_threshold
        }
    )

    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def call_llm(state: FullCacheState):
        """Invoke Cortex LLM with plan caching."""
        with tracer.start_as_current_span("llm.invoke") as span:
            span.set_attribute("llm.message_count", len(state["messages"]))
            logger.info(f"Invoking Cortex LLM with {len(MATH_TOOLS)} tools")

            # Check if this is first LLM call (no tool messages yet) or subsequent call (after tools)
            from langchain_core.messages import ToolMessage
            is_first_call = not any(isinstance(msg, ToolMessage) for msg in state["messages"])

            # Check plan cache first (only on first call)
            cache_hit = False
            if plan_cache and enable_plan_cache and is_first_call:
                # Get current query
                last_message = state["messages"][-1]
                if isinstance(last_message, HumanMessage):
                    query = last_message.content
                    tool_names = [tool.name for tool in MATH_TOOLS]

                    cached_plan = plan_cache.get(
                        query=query,
                        tools=tool_names,
                        conversation_history=None
                    )

                    if cached_plan:
                        cache_hit = True
                        span.set_attribute("plan_cache.hit", True)
                        logger.info(
                            f"Plan cache HIT for query: '{query[:50]}...'",
                            extra={"cache_hit": True}
                        )

                        # Reconstruct AIMessage from cached plan
                        cached_message_data = cached_plan.get("message")

                        if isinstance(cached_message_data, dict):
                            # Reconstruct AIMessage from cached data
                            cached_response = AIMessage(
                                content=cached_message_data.get("content", ""),
                                tool_calls=cached_message_data.get("tool_calls", []),
                                additional_kwargs=cached_message_data.get("additional_kwargs", {})
                            )
                        else:
                            # Fallback if cached data is already a message object
                            cached_response = cached_message_data

                        return {
                            "messages": [cached_response],
                            "plan_cache_hit": True
                        }
                    else:
                        logger.info(
                            f"Plan cache MISS for query: '{query[:50]}...'",
                            extra={"cache_hit": False}
                        )

            # Cache miss - invoke LLM
            cortex_llm = CortexLLM(model_name="claude-3-5-sonnet")
            model = cortex_llm.get_llm()
            if MATH_TOOLS:
                model = model.bind_tools(MATH_TOOLS)

            system_message = SYSTEM_PROMPT.format(tools=MATH_TOOLS)
            messages = [SystemMessage(content=system_message)] + state["messages"]

            response = model.invoke(messages)

            # Cache the plan if enabled
            if plan_cache and enable_plan_cache and not cache_hit:
                if isinstance(state["messages"][-1], HumanMessage):
                    query = state["messages"][-1].content
                    tool_names = [tool.name for tool in MATH_TOOLS]

                    # Serialize response for caching (match plan_cache format)
                    message_data = {
                        "content": response.content,
                        "tool_calls": response.tool_calls if hasattr(response, 'tool_calls') else [],
                        "additional_kwargs": response.additional_kwargs if hasattr(response, 'additional_kwargs') else {}
                    }

                    plan_data = {
                        "message": message_data,
                        "tool_calls": response.tool_calls if hasattr(response, 'tool_calls') else []
                    }

                    metadata = {
                        "model": "claude-3-5-sonnet",
                        "has_tool_calls": len(response.tool_calls) > 0 if hasattr(response, 'tool_calls') else False
                    }

                    plan_cache.set(
                        query=query,
                        tools=tool_names,
                        plan_response=plan_data,
                        conversation_history=None,
                        metadata=metadata
                    )

            span.set_attribute("llm.response_type", type(response).__name__)
            span.set_attribute("plan_cache.hit", cache_hit)

            # Only update plan_cache_hit on first call to avoid overwriting
            result = {"messages": [response]}
            if is_first_call:
                result["plan_cache_hit"] = cache_hit

            return result

    @instrument(span_type=SpanAttributes.SpanType.TOOL)
    def call_tools_with_cache(state: FullCacheState):
        """Execute tools with caching layer."""
        with tracer.start_as_current_span("tools.cached_execution") as span:
            last_message = state["messages"][-1]
            tool_calls = getattr(last_message, "tool_calls", [])

            if not tool_calls:
                logger.warning("No tool calls found in last message")
                return {"messages": []}

            span.set_attribute("tool.call_count", len(tool_calls))

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

                # Check tool cache first
                cached_result = tool_cache_checker.get_cached_result(tool_name, tool_input)

                if cached_result:
                    # Cache hit
                    output_text, similarity = cached_result
                    tool_message = ToolMessage(
                        content=output_text,
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )

                    if tool_name not in cache_hits:
                        cache_hits[tool_name] = []
                    cache_hits[tool_name].append(True)

                    span.add_event(
                        "tool.cache_hit",
                        attributes={"tool.name": tool_name, "cache.similarity": similarity}
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

                        # Store in cache
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

                        if tool_name not in cache_hits:
                            cache_hits[tool_name] = []
                        cache_hits[tool_name].append(False)

                        span.add_event("tool.cache_miss", attributes={"tool.name": tool_name})

                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        tool_message = ToolMessage(
                            content=f"Error: {str(e)}",
                            tool_call_id=tool_call_id,
                            name=tool_name
                        )

                tool_messages.append(tool_message)

            return {"messages": tool_messages, "tool_cache_hits": cache_hits}

    def tools_condition(state: FullCacheState) -> Literal["tools", "__end__"]:
        """Route to tools if the last message has tool calls."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "__end__"

    # Build graph
    workflow = StateGraph(FullCacheState)

    workflow.add_node("llm", call_llm)
    workflow.add_node("tools", call_tools_with_cache)

    workflow.set_entry_point("llm")
    workflow.add_conditional_edges("llm", tools_condition)
    workflow.add_edge("tools", "llm")

    graph = workflow.compile()

    return graph
