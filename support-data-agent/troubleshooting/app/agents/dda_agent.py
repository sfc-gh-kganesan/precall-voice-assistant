"""
PydanticAI Agent for DDA Service

An AI agent that uses the DDA Native MCP server tools to help support engineers
diagnose Snowflake customer issues. Uses Snowflake Cortex as the LLM provider.
"""

import asyncio
import logging
import os
from typing import List

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types import chat
from pydantic_ai import Agent, AgentRunResultEvent, ModelMessage, RunContext
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.history import keep_last_n_tokens
from app.services.cortex_search import CortexSearchClient

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

# Initialize Cortex Search client (global instance)
cortex_search_client = None
try:
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if snowflake_account and snowflake_password:
        cortex_search_client = CortexSearchClient(
            account=snowflake_account,
            password=snowflake_password,
            service_name=os.getenv(
                "CORTEX_SEARCH_SERVICE", "cke_snowflake_docs_service"
            ),
            database=os.getenv("CORTEX_SEARCH_DATABASE", "snowflake_docs_cke"),
            schema=os.getenv("CORTEX_SEARCH_SCHEMA", "shared"),
        )
        logger.info("✓ Cortex Search client initialized with Snowflake credentials")
    else:
        logger.warning(
            "SNOWFLAKE_ACCOUNT or SNOWFLAKE_PASSWORD not set, documentation search will be disabled"
        )
except Exception as e:
    logger.error(f"Failed to initialize Cortex Search client: {e}")
    cortex_search_client = None


class SnowflakeCortexModel(OpenAIChatModel):
    """Custom model that handles Snowflake Cortex API response quirks.

    Fixes two key issues:
    1. Empty fields in non-streaming responses (finish_reason, service_tier)
    2. Missing 'index' field in streaming tool call chunks (causes name concatenation)
    """

    def __init__(self, model_name: str, *, provider: OpenAIProvider):
        super().__init__(model_name, provider=provider)
        self._tool_call_index_map: dict[
            str, int
        ] = {}  # Maps tool_call_id -> synthetic index
        logger.info(
            "Initialized SnowflakeCortexModel with streaming fix for missing 'index' fields"
        )

    def _process_response(self, response):
        # Patch Snowflake's empty fields before validation
        response_dict = response.model_dump()

        # Fix empty finish_reason
        if "choices" in response_dict:
            for choice in response_dict["choices"]:
                if choice.get("finish_reason") == "":
                    choice["finish_reason"] = "stop"

        # Fix empty service_tier
        if response_dict.get("service_tier") == "":
            response_dict["service_tier"] = "default"

        # Re-create response with fixed data
        fixed_response = chat.ChatCompletion.model_validate(response_dict)

        # Let parent process the fixed response
        return super()._process_response(fixed_response)

    def _normalize_tool_call_chunk(self, chunk):
        """Inject synthetic index when missing from Cortex streaming chunks.

        Snowflake Cortex omits the 'index' field in streaming tool call chunks,
        causing pydantic-ai to store all parallel tool calls under dict key None,
        which concatenates their names. We inject a synthetic index based on
        tool_call_id to keep them separate.

        Args:
            chunk: Tool call chunk from streaming response

        Returns:
            Normalized chunk with synthetic index if needed
        """
        if chunk.index is None and hasattr(chunk, "id") and chunk.id:
            # Use cached mapping for stability across chunks of same tool call
            if chunk.id not in self._tool_call_index_map:
                self._tool_call_index_map[chunk.id] = len(self._tool_call_index_map)
                logger.debug(
                    f"Injected synthetic index {self._tool_call_index_map[chunk.id]} "
                    f"for tool_call_id={chunk.id} (missing from Cortex response)"
                )
            chunk.index = self._tool_call_index_map[chunk.id]
        return chunk

    async def _process_streamed_response(self, response, model_request_parameters):
        """Process streamed response and normalize chunks before pydantic-ai processes them."""
        self._tool_call_index_map.clear()  # Reset for each new request

        # Wrap the response to normalize chunks on-the-fly
        class NormalizedStream:
            def __init__(self, stream, normalizer):
                self._stream = stream
                self._normalizer = normalizer

            def __aiter__(self):
                return self

            async def __anext__(self):
                chunk = await self._stream.__anext__()
                # Normalize tool call chunks if present
                if hasattr(chunk, "choices"):
                    for choice in chunk.choices:
                        if (
                            hasattr(choice, "delta")
                            and hasattr(choice.delta, "tool_calls")
                            and choice.delta.tool_calls
                        ):
                            choice.delta.tool_calls = [
                                self._normalizer(tc) for tc in choice.delta.tool_calls
                            ]
                return chunk

        # Wrap the response stream
        normalized_response = NormalizedStream(
            response, self._normalize_tool_call_chunk
        )

        # Call parent with normalized stream
        return await super()._process_streamed_response(
            normalized_response, model_request_parameters
        )


# System prompt for the agent
SYSTEM_PROMPT = """You are a Snowflake Support Assistant. You help support engineers
investigate and troubleshoot customer issues using comprehensive diagnostic tools.

**Tool Selection Guide:**

Choose your tools based on the question type:

1. **Pure Documentation Questions** (syntax, features, general "how-to"):
   - Use ONLY: search_snowflake_documentation
   - When: User asks about SQL syntax, Snowflake features, configuration options, best practices
   - Examples: "CREATE TABLE syntax", "Time Travel retention period", "COPY INTO options"

2. **Customer-Specific Diagnostics** (cases, queries, errors, performance):
   - Use: DDA tools (primary) + documentation (for syntax clarification if needed)
   - When: Investigating actual customer issues with specific identifiers
   - Examples: "Analyze case 12345", "Why is query abc123 slow?", "User login failing for account X"

3. **Internal Knowledge/Context** (past incidents, procedures, expertise):
   - Use: Glean search + documentation (as needed)
   - When: Looking for past solutions, internal procedures, or employee expertise
   - Examples: "How did we solve X before?", "Standard procedure for Y", "Who handles Z?"

**Your Tools:**

**Snowflake Documentation Search:**
- Official Snowflake documentation for syntax, features, configurations, and best practices
- Always accurate and up-to-date
- Best for: SQL command reference, function documentation, feature explanations, configuration options
- Use when you need authoritative "how-to" information

**DDA Diagnostic Tools:**
- Deep, authoritative access to customer environments, logs, and diagnostic data
- Capabilities: Case analysis, query diagnostics, performance investigation, auth/RBAC analysis,
  warehouse metrics, account parameters, internal logs, Jira integration
- Best for: Customer-specific troubleshooting with actual case/query/account identifiers
- Use when investigating real customer issues that require environment-specific data

**Glean Knowledge Tools:**
- Internal Snowflake knowledge base, presentations, conversations, and code repositories
- Best for: Past incident solutions, internal procedures, employee expertise, tribal knowledge
- Use when you need internal context or historical approaches to similar problems

**Investigation Approach:**

1. **Classify the Question**:
   - Is it general documentation? → Documentation only
   - Is it a customer-specific issue? → DDA tools + documentation if needed
   - Need internal context? → Glean + documentation if needed

2. **Execute Efficiently**:
   - Don't use multiple tools when one will suffice
   - For syntax questions, documentation alone is sufficient
   - For customer diagnostics, start with DDA to get environment-specific data

3. **Analyze & Synthesize**:
   - Combine insights from your tool calls
   - Provide clear, actionable findings with supporting evidence
   - Cite your sources

Always be thorough but concise. Format technical details clearly. Choose the right tool for each question type.
"""


# Tool function for Snowflake documentation search
async def search_snowflake_documentation(
    ctx: RunContext[None],
    query: str,
    limit: int = 5,
) -> str:
    """Search official Snowflake documentation for syntax, features, and technical details.

    Use this tool when you need accurate, authoritative information about:
    - SQL syntax and command reference
    - Snowflake features and functionality
    - Best practices and recommendations
    - Technical specifications and configurations
    - Function and operator documentation

    Args:
        query: Search query describing what to look for in documentation
        limit: Maximum number of documentation chunks to return (default: 5)

    Returns:
        Relevant documentation chunks from official Snowflake docs

    Example queries:
        - "CREATE DYNAMIC TABLE syntax"
        - "COPY INTO best practices"
        - "Time Travel retention period"
        - "VARIANT data type usage"
    """
    if cortex_search_client is None:
        return "Documentation search is not available (Cortex Search not configured)"

    try:
        results = await cortex_search_client.search(query, limit=limit)
        formatted = cortex_search_client.format_results(results)
        return formatted
    except Exception as e:
        logger.error(f"Documentation search failed: {e}", exc_info=True)
        return f"Documentation search failed: {str(e)}"


class StatefulAgent:
    """Agent wrapper that maintains conversation history automatically.

    Wraps a PydanticAI agent and manages conversation state internally,
    so callers don't need to manually pass message_history.
    """

    def __init__(self, agent: Agent):
        """Initialize with a PydanticAI agent."""
        self._agent = agent
        self._history: List[ModelMessage] = []
        logger.info("StatefulAgent initialized with empty conversation history")

    async def run_stream_events(self, prompt: str):
        """Stream events while maintaining conversation history.

        Args:
            prompt: User message/query

        Yields:
            Event objects from the underlying agent
        """
        max_500_retries = 2

        for attempt in range(max_500_retries + 1):
            try:
                # Capture the AgentRunResultEvent to update history
                streamed_result = None
                async for event in self._agent.run_stream_events(
                    prompt, message_history=self._history
                ):
                    # Check if this is the agent run result event
                    if isinstance(event, AgentRunResultEvent):
                        streamed_result = event.result
                    yield event

                # Update history from the streamed result
                # The AgentRunResultEvent contains the result with all_messages()
                if streamed_result is not None:
                    self._history = streamed_result.all_messages()
                    logger.debug(
                        f"Updated conversation history to {len(self._history)} messages"
                    )
                else:
                    logger.warning(
                        "No AgentRunResultEvent received from stream, history not updated"
                    )

                # If we got here successfully, break out of retry loop
                break

            except ModelHTTPError as e:
                # Handle 500 errors with retry logic
                if e.status_code == 500 and attempt < max_500_retries:
                    wait_time = 2**attempt  # exponential backoff: 1s, 2s
                    logger.warning(
                        f"Received 500 error from Snowflake Cortex API on attempt {attempt + 1}/{max_500_retries + 1}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Either not a 500 error, or we've exhausted retries
                    if e.status_code == 500:
                        logger.error(
                            f"500 error persisted after {max_500_retries + 1} attempts. "
                            f"Request ID: {e.body.get('request_id', 'unknown') if hasattr(e, 'body') and e.body else 'unknown'}"
                        )
                    raise

    async def run(self, prompt: str):
        """Run agent with history management.

        Args:
            prompt: User message/query

        Returns:
            Agent result object
        """
        result = await self._agent.run(prompt, message_history=self._history)
        self._history = result.all_messages()
        logger.debug(f"Updated conversation history to {len(self._history)} messages")
        return result

    def clear_history(self):
        """Clear conversation history."""
        self._history = []
        logger.info("Cleared conversation history")


def create_dda_agent(
    model_name: str = "claude-4-sonnet",
    mcp_server_url: str = "http://localhost:8000/mcp",
    glean_proxy_url: str = "http://localhost:8001/mcp",
    stateful: bool = True,
) -> Agent:
    """
    Create a PydanticAI agent configured with DDA Native MCP tools and Glean search.
    Uses Snowflake Cortex as the LLM provider instead of OpenAI.

    Args:
        model_name: The Cortex model to use (e.g., 'claude-4-sonnet', 'mistral-large')
        mcp_server_url: URL of the DDA Native MCP server
        glean_proxy_url: URL of the Glean proxy server (set to None to disable Glean)
        stateful: If True, wrap agent in StatefulAgent for automatic conversation memory

    Returns:
        Configured PydanticAI Agent (wrapped in StatefulAgent if stateful=True)
    """
    # Setup OpenAI-compatible client for Snowflake Cortex
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        raise ValueError(
            "SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set in environment"
        )

    # Create client pointing to Snowflake Cortex API
    client = AsyncOpenAI(
        max_retries=5,
        timeout=90.0,
        api_key=snowflake_password,
        base_url=f"https://{snowflake_account}.snowflakecomputing.com/api/v2/cortex/v1",
    )

    # Create OpenAI provider with the Snowflake client
    provider = OpenAIProvider(openai_client=client)

    # Use custom model that handles Snowflake response quirks
    model = SnowflakeCortexModel(model_name, provider=provider)

    # Connect to the DDA Native MCP server
    logger.info(f"Connecting to DDA Native MCP server at {mcp_server_url}")
    dda_server = MCPServerStreamableHTTP(mcp_server_url)

    # Build toolsets list
    toolsets = [dda_server]

    # Optionally connect to Glean proxy
    if glean_proxy_url:
        logger.info(f"Connecting to Glean proxy at {glean_proxy_url}")
        glean_server = MCPServerStreamableHTTP(glean_proxy_url)
        toolsets.append(glean_server)
        logger.info("✓ Agent configured with DDA + Glean toolsets")
    else:
        logger.info("✓ Agent configured with DDA toolset only")

    # Build custom tools list
    custom_tools = []
    if cortex_search_client is not None:
        custom_tools.append(search_snowflake_documentation)
        logger.info("✓ Added Snowflake documentation search tool")

    # Create agent with MCP toolsets, custom tools, and history processors
    agent = Agent(
        model=model,
        toolsets=toolsets,
        tools=custom_tools if custom_tools else None,
        system_prompt=SYSTEM_PROMPT,
        history_processors=[keep_last_n_tokens(25000)],
    )

    logger.info("✓ Agent configured with history limit of 25000 tokens")
    logger.info(
        f"✓ Agent configured with {len(toolsets)} MCP toolsets and {len(custom_tools)} custom tools"
    )

    # Wrap in StatefulAgent if requested (default for CLI use)
    if stateful:
        agent = StatefulAgent(agent)
        logger.info(
            "✓ Agent wrapped in StatefulAgent for automatic conversation memory"
        )

    return agent


# Default agent instance
dda_agent = create_dda_agent()
