"""Plan Cache LangGraph experiment with Cortex LLM.

Integrates semantic plan caching using Snowflake Cortex Search Service.
Caches LLM planning decisions (tool calls) before tool execution.
"""
import logging
import json
from typing import Optional
from typing import TypedDict, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes

from shared.cortex_models import CortexLLM
from shared.tools import MATH_TOOLS
from shared.utils import application_name, tracer
from shared.cache_backends import PlanCacheWithSearch

logger = logging.getLogger(application_name)

SYSTEM_PROMPT = """You are a helpful AI assistant that can perform mathematical calculations.

You have access to the following tools:
{tools}

Use the tools to answer the user's question accurately."""


class PlanCacheState(MessagesState):
    """Extended state for plan cache graph with cache hit tracking."""
    cache_hit: bool = False


def get_model_with_tools(tools=None, tool_choice="auto"):
    """Get Cortex LLM model with tools bound."""
    cortex_llm = CortexLLM(model_name="claude-3-5-sonnet")
    model = cortex_llm.get_llm()

    if tools:
        return model.bind_tools(tools, tool_choice=tool_choice)
    else:
        return model


def create_graph(
    enable_cache: bool = True,
    similarity_threshold: float = 0.85
):
    """Create LangGraph workflow with semantic plan caching.

    Args:
        enable_cache: Whether to enable plan caching
        similarity_threshold: Minimum similarity score for cache hit (0.0-1.0)

    Returns:
        Compiled LangGraph workflow
    """
    model = get_model_with_tools(MATH_TOOLS)

    # Initialize plan cache with Cortex Search
    plan_cache: Optional[PlanCacheWithSearch] = None
    if enable_cache:
        plan_cache = PlanCacheWithSearch(
            table_name="AI_FDE.CACHE_EXPERIMENTS.plan_cache",
            search_service_name="AI_FDE.CACHE_EXPERIMENTS.plan_cache_search",
            similarity_threshold=similarity_threshold
        )
        logger.info(
            f"Plan cache enabled with similarity threshold={similarity_threshold}",
            extra={"cache_enabled": True, "similarity_threshold": similarity_threshold}
        )

    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def call_llm(state: PlanCacheState):
        """Invoke Cortex LLM with semantic plan caching.

        Checks cache first using semantic search. On cache hit, returns
        cached response without LLM invocation. On cache miss, invokes
        LLM and stores response in cache.
        """
        with tracer.start_as_current_span("llm.invoke") as span:
            query = state["messages"][-1].content
            tool_names = [tool.name for tool in MATH_TOOLS]

            span.set_attribute("llm.message_count", len(state["messages"]))
            span.set_attribute("cache.enabled", plan_cache is not None)

            # Check cache first using semantic search
            if plan_cache:
                with tracer.start_as_current_span("cache.get") as cache_span:
                    cached_plan = plan_cache.get(query, tool_names)

                    if cached_plan:
                        logger.info(
                            f"Plan cache HIT for query: '{query[:50]}...'",
                            extra={"cache_hit": True, "query": query}
                        )
                        cache_span.set_attribute("cache.hit", True)
                        span.set_attribute("cache.hit", True)

                        # Deserialize cached AIMessage
                        # The cached plan contains the serialized message data
                        cached_message_data = cached_plan.get("message")

                        if isinstance(cached_message_data, dict):
                            # Reconstruct AIMessage from cached data
                            cached_message = AIMessage(
                                content=cached_message_data.get("content", ""),
                                tool_calls=cached_message_data.get("tool_calls", []),
                                additional_kwargs=cached_message_data.get("additional_kwargs", {})
                            )
                        else:
                            # Fallback if cached data is already a message object
                            cached_message = cached_message_data

                        return {"messages": [cached_message], "cache_hit": True}

            # Cache miss - invoke LLM
            logger.info(
                f"Plan cache MISS for query: '{query[:50]}...'",
                extra={"cache_hit": False, "query": query}
            )
            if plan_cache:
                span.set_attribute("cache.hit", False)

            logger.info(f"Invoking Cortex LLM with {len(MATH_TOOLS)} tools")

            system_message = SYSTEM_PROMPT.format(tools=MATH_TOOLS)
            messages = [SystemMessage(content=system_message)] + state["messages"]

            response = model.invoke(messages)

            span.set_attribute("llm.response_type", type(response).__name__)

            # Cache the plan (serialize the response)
            if plan_cache:
                with tracer.start_as_current_span("cache.set") as cache_set_span:
                    # Serialize AIMessage to dict for storage
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

                    success = plan_cache.set(
                        query,
                        tool_names,
                        plan_data,
                        metadata=metadata
                    )

                    cache_set_span.set_attribute("cache.set_success", success)

            return {"messages": [response], "cache_hit": False}

    # Initialize graph with PlanCacheState for cache hit tracking
    workflow = StateGraph(PlanCacheState)

    workflow.add_node("llm", call_llm)
    if MATH_TOOLS:
        workflow.add_node("tools", ToolNode(MATH_TOOLS))
        workflow.add_edge("tools", "llm")
        workflow.add_conditional_edges("llm", tools_condition)

    workflow.set_entry_point("llm")

    # Compile graph
    graph = workflow.compile()

    return graph


if __name__ == "__main__":
    # Quick test
    print("=" * 80)
    print("Testing Plan Cache Graph")
    print("=" * 80)

    # Test with cache enabled
    graph = create_graph(enable_cache=True, similarity_threshold=0.85)

    test_query = "What is 15 multiplied by 4?"
    state = {"messages": [HumanMessage(content=test_query)]}

    print(f"\n1st run (cache miss expected):")
    logger.info(f"Testing plan cache graph with query: {test_query}")
    result = graph.invoke(state)

    if "messages" in result and len(result["messages"]) > 0:
        answer = result["messages"][-1].content
        logger.info(f"Answer: {answer}")
        print(f"Q: {test_query}")
        print(f"A: {answer}")
    else:
        logger.error("No response from model")
        print("Error: No response from model")

    # Test again with same query (should hit cache)
    print(f"\n2nd run (cache hit expected):")
    result2 = graph.invoke(state)

    if "messages" in result2 and len(result2["messages"]) > 0:
        answer2 = result2["messages"][-1].content
        print(f"Q: {test_query}")
        print(f"A: {answer2}")

    # Test with similar query
    similar_query = "Calculate 15 times 4"
    state_similar = {"messages": [HumanMessage(content=similar_query)]}

    print(f"\n3rd run with similar query (may hit cache with high similarity):")
    result3 = graph.invoke(state_similar)

    if "messages" in result3 and len(result3["messages"]) > 0:
        answer3 = result3["messages"][-1].content
        print(f"Q: {similar_query}")
        print(f"A: {answer3}")

    print("\n" + "=" * 80)
