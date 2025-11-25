"""
PydanticAI Agent for DDA Service

An AI agent that uses the DDA Native MCP server tools to help support engineers
diagnose Snowflake customer issues. Uses Snowflake Cortex as the LLM provider.
"""

import asyncio
import logging
import os
import re
from typing import List

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types import chat
from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    ModelMessage,
    ModelSettings,
    RunContext,
)
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import ModelRequest, RetryPromptPart
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
        logger.info(
            "✅ SnowflakeCortexModel._completions_create override is registered"
        )
        # Test to verify our override is active
        logger.info(
            f"Method resolution order: {[c.__name__ for c in self.__class__.__mro__]}"
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
        """Force index assignment and clean arguments for Snowflake Cortex.

        Snowflake Cortex sends index=0 for all parallel tool call chunks (not None),
        causing pydantic-ai's routing logic to fail and concatenate tool names.
        We always assign indices based on tool_call_id regardless of existing values.

        Also cleans invalid JSON in tool call arguments (trailing null bytes, whitespace).

        Args:
            chunk: Tool call chunk from streaming response

        Returns:
            Chunk with corrected index field and cleaned arguments
        """
        if hasattr(chunk, "id") and chunk.id:
            # Use tool_call_id as stable identifier, assign sequential indices
            if chunk.id not in self._tool_call_index_map:
                self._tool_call_index_map[chunk.id] = len(self._tool_call_index_map)
                logger.info(
                    f"✨ Assigning index {self._tool_call_index_map[chunk.id]} to tool_call_id={chunk.id}"
                )
            # Always overwrite existing index (Snowflake sends 0 for all)
            chunk.index = self._tool_call_index_map[chunk.id]

        # Clean tool call arguments if present (PRIMARY DEFENSE against invalid JSON)
        if hasattr(chunk, "function") and hasattr(chunk.function, "arguments"):
            if chunk.function.arguments:
                original_args = chunk.function.arguments
                # Remove trailing null bytes and control characters
                cleaned_args = re.sub(r"[\x00-\x1f]+$", "", original_args)
                # Remove trailing whitespace
                cleaned_args = cleaned_args.rstrip()

                if cleaned_args != original_args:
                    logger.warning(
                        f"⚠️ Cleaned invalid JSON in tool call arguments: "
                        f"removed {len(original_args) - len(cleaned_args)} trailing characters"
                    )
                    logger.debug(f"  Original: {repr(original_args[-50:])}")
                    logger.debug(f"  Cleaned:  {repr(cleaned_args[-50:])}")
                    chunk.function.arguments = cleaned_args

        return chunk

    async def _completions_create(
        self, messages, stream, model_settings, model_request_parameters
    ):
        """Log outbound requests to Snowflake Cortex.

        Note: We don't filter messages here as that breaks streaming!
        Filtering happens via history_processors before streaming starts.
        """

        logger.info("═" * 50)
        logger.info("REQUEST TO SNOWFLAKE CORTEX")
        logger.info("═" * 50)
        logger.info(f"Stream: {stream}")
        logger.info(f"Model Settings: {model_settings}")
        logger.info(f"Total messages in history: {len(messages)}")

        # Log message types for debugging
        logger.info(f"Messages type: {type(messages)}")
        if len(messages) > 0:
            logger.info(f"First message type: {type(messages[0])}")

        # Check for tool_calls in message history
        for i, msg in enumerate(messages):
            # Try multiple ways to access message data
            if isinstance(msg, dict):
                role = msg.get("role", "dict-unknown")
                content = str(msg.get("content", ""))[:50]
                tool_calls = msg.get("tool_calls", [])
            elif hasattr(msg, "role"):
                role = getattr(msg, "role", "attr-unknown")
                content = str(getattr(msg, "content", ""))[:50]
                tool_calls = getattr(msg, "tool_calls", []) or []
            else:
                logger.warning(f"Message {i}: Unknown message format: {type(msg)}")
                logger.warning(f"  Message repr: {repr(msg)[:200]}")
                continue

            logger.info(f"Message {i}: role={role}, content_preview={content}")

            # Check for tool_calls (assistant messages)
            if tool_calls:
                logger.info(f"  ↳ Contains {len(tool_calls)} tool_calls")

                for tc_idx, tc in enumerate(tool_calls):
                    if isinstance(tc, dict):
                        tool_name = tc.get("function", {}).get("name", "unknown")
                        tool_id = tc.get("id", "unknown")
                    else:
                        tool_name = (
                            getattr(tc.function, "name", "unknown")
                            if hasattr(tc, "function")
                            else "unknown"
                        )
                        tool_id = getattr(tc, "id", "unknown")

                    # Check for concatenated names (corruption indicator)
                    if len(tool_name) > 80:  # Suspiciously long
                        logger.error(
                            f"  ❌ CORRUPTED TOOL NAME at index {tc_idx}: {tool_name}"
                        )
                    else:
                        logger.info(
                            f"    Tool {tc_idx}: {tool_name} (id={tool_id[:20] if tool_id and len(tool_id) > 20 else tool_id}...)"
                        )

            # Check for tool role (tool response messages)
            if role == "tool":
                if isinstance(msg, dict):
                    tool_call_id = msg.get("tool_call_id", "unknown")
                    content_preview = str(msg.get("content", ""))[:100]
                else:
                    tool_call_id = getattr(msg, "tool_call_id", "unknown")
                    content_preview = str(getattr(msg, "content", ""))[:100]
                logger.info(
                    f"  ↳ Tool response for call_id={tool_call_id[:20] if tool_call_id and len(tool_call_id) > 20 else tool_call_id}..."
                )
                logger.debug(f"  Content preview: {content_preview}")

        logger.info("═" * 50)

        # Call parent to make actual request
        try:
            result = await super()._completions_create(
                messages, stream, model_settings, model_request_parameters
            )
            logger.info("✅ Request to Snowflake Cortex succeeded")
            return result
        except Exception as e:
            logger.error(f"❌ Request to Snowflake Cortex failed: {e}")
            raise

    async def _process_streamed_response(self, response, model_request_parameters):
        """Process streamed response and normalize chunks before pydantic-ai processes them."""
        logger.info(
            "🔍 _process_streamed_response called - applying synthetic index fix"
        )
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

                # Log every chunk we process
                logger.debug(f"📦 Processing chunk: {type(chunk).__name__}")

                # Normalize tool call chunks if present
                if hasattr(chunk, "choices"):
                    for choice in chunk.choices:
                        if (
                            hasattr(choice, "delta")
                            and hasattr(choice.delta, "tool_calls")
                            and choice.delta.tool_calls
                        ):
                            logger.info(
                                f"🔧 Found {len(choice.delta.tool_calls)} tool_call chunks to normalize"
                            )
                            choice.delta.tool_calls = [
                                self._normalizer(tc) for tc in choice.delta.tool_calls
                            ]
                            logger.info(
                                f"✅ Normalized {len(choice.delta.tool_calls)} tool_call chunks"
                            )
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
   - **IMPORTANT: Call only ONE tool at a time. Never call multiple tools simultaneously.**
   - Wait for each tool's results before deciding on the next tool call
   - Don't use multiple tools when one will suffice
   - For syntax questions, documentation alone is sufficient
   - For customer diagnostics, start with DDA to get environment-specific data

3. **Analyze & Synthesize**:
   - Combine insights from your tool calls
   - Provide clear, actionable findings with supporting evidence
   - Cite your sources

Always be thorough but concise. Format technical details clearly. Choose the right tool for each question type.
"""


def filter_retry_prompts_from_history(
    messages: list[ModelMessage],
) -> list[ModelMessage]:
    """
    Filter RetryPromptPart from message history before sending to Snowflake Cortex.

    Snowflake Cortex returns 500 errors when it receives RetryPromptPart messages.
    This history processor runs BEFORE each model request (outside streaming context),
    safely removing these problematic messages.

    Args:
        messages: Message history to filter

    Returns:
        Filtered message history without RetryPromptPart messages
    """
    filtered = []
    retry_count = 0

    for msg in messages:
        # Check if this is a ModelRequest with RetryPromptPart
        if isinstance(msg, ModelRequest):
            # Filter out RetryPromptPart from parts using proper isinstance check
            original_parts = msg.parts
            filtered_parts = []

            for part in original_parts:
                if isinstance(part, RetryPromptPart):
                    retry_count += 1
                    logger.debug(f"🛡️ Filtering RetryPromptPart: {str(part)[:100]}...")
                else:
                    filtered_parts.append(part)

            # If we removed all parts, skip this message entirely (even if it's the last message)
            # Snowflake Cortex rejects placeholder messages, so it's better to skip entirely
            if not filtered_parts:
                logger.debug(
                    "🛡️ Skipping empty ModelRequest after filtering RetryPromptPart"
                )
                continue

            # If we filtered some parts, create new ModelRequest with remaining parts
            if len(filtered_parts) < len(original_parts):
                msg = ModelRequest(parts=filtered_parts)

        filtered.append(msg)

    if retry_count > 0:
        logger.info(
            f"🛡️ History processor filtered {retry_count} RetryPromptPart messages "
            f"(prevents 500 errors from Snowflake Cortex)"
        )

    return filtered


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
    glean_proxy_url: str = "http://localhost:8006/mcp",
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

    # Create agent with MCP toolsets, custom tools, and history filter
    agent = Agent(
        model=model,
        toolsets=toolsets,
        tools=custom_tools if custom_tools else None,
        system_prompt=SYSTEM_PROMPT,
        history_processors=[
            filter_retry_prompts_from_history,  # Filter RetryPromptPart before requests
            keep_last_n_tokens(25000),
        ],
        model_settings=ModelSettings(
            parallel_tool_calls=False
        ),  # Disable parallel tool calls for Snowflake Cortex stability
    )

    logger.info("✓ Agent configured with RetryPromptPart filter (prevents 500 errors)")
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
