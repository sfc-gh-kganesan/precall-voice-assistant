"""
External-Facing PydanticAI Agent (No DDA Tools)

An AI agent WITHOUT access to DDA diagnostic tools, designed for external
or public-facing scenarios. Uses Glean for internal knowledge and Cortex
for Snowflake documentation, but does NOT have access to customer-specific
diagnostic data (DDA tools).

IMPORTANT: This agent enforces PII protection and will NOT share:
- Customer names or account identifiers
- Email addresses or contact information
- Specific customer data or details

Uses Snowflake Cortex as the LLM provider.
"""

import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types import chat
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.instrumented import InstrumentationSettings
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from services.cortex_search import CortexSearchClient
from services.history import keep_last_n_messages

# Load environment variables
load_dotenv()

# Setup logging + tracing
logger = logging.getLogger(__name__)
from opentelemetry import trace

from otel_config import tracer

# Initialize Cortex Search client (global instance)
cortex_search_client = None
try:
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if snowflake_account and snowflake_password:
        cortex_search_client = CortexSearchClient(
            account=snowflake_account,
            password=snowflake_password,
            service_name=os.getenv("CORTEX_SEARCH_SERVICE", "cke_snowflake_docs_service"),
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
    """Custom model that handles Snowflake Cortex API response quirks"""

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


# System prompt for the external agent with PII protection
EXTERNAL_SYSTEM_PROMPT = """You are an External Snowflake Support Assistant. You help with general
Snowflake questions, best practices, and internal knowledge search, but you do NOT have access to
customer-specific diagnostic tools or data.

**CRITICAL: PII PROTECTION**

You are an EXTERNAL-FACING agent. You MUST NEVER share:
- ❌ Customer names or organization names
- ❌ Account identifiers (account IDs, locators)
- ❌ Email addresses or contact information
- ❌ Specific customer details or case information
- ✅ You MAY share generalized, anonymized insights and best practices

If asked about specific customers or cases, politely explain that you don't have access to
customer-specific diagnostic data and can only provide general guidance.

**Your Tools:**

**Snowflake Documentation Search (search_snowflake_documentation):**
- Official Snowflake documentation for syntax, features, configurations, and best practices
- Always accurate and up-to-date
- Best for: SQL command reference, function documentation, feature explanations, configuration options
- Use when you need authoritative "how-to" information

**Glean Knowledge Tools:**
- Internal Snowflake knowledge base, presentations, conversations, and code repositories
- Best for: Past incident solutions, internal procedures, employee expertise, tribal knowledge
- Use when you need internal context or historical approaches to similar problems
- Remember: When sharing insights from Glean, anonymize any customer-specific information

**Tool Usage Strategy:**

**CRITICAL: For Snowflake feature/syntax questions - ONLY use search_snowflake_documentation FIRST. Do NOT use Glean tools for standard documentation queries.**

**DEFAULT to Snowflake Documentation (search_snowflake_documentation) for:**
- SQL syntax questions (e.g., "How do I use CREATE DYNAMIC TABLE?")
- Feature documentation (e.g., "What are the Time Travel retention limits?", "Tell me about Cortex LLM functions")
- Command reference (e.g., "COPY INTO best practices")
- Configuration options (e.g., "How do I set up replication?")
- Standard "how-to" questions about Snowflake features
- Function and operator documentation
- Snowflake services and capabilities (e.g., "What is Snowflake Cortex?", "How do I use Dynamic Tables?")

**Examples - Use ONLY documentation search:**
- "What are Cortex LLM functions?" → search_snowflake_documentation ONLY
- "How do I create a stream?" → search_snowflake_documentation ONLY
- "What's the syntax for COPY INTO?" → search_snowflake_documentation ONLY

**Use Glean Knowledge Tools ONLY when:**
- Documentation search was already performed and didn't fully answer the question
- Questions explicitly ask about internal procedures, past incidents, or "how we've handled" something
- Need historical/longitudinal knowledge (e.g., "How have we handled X issue before?")
- Looking for internal employee expertise, tribal knowledge, or code examples
- Complex troubleshooting requiring patterns from past incidents
- Questions about internal processes (NOT product features)

**Examples - Use Glean (after trying docs):**
- "How have support teams handled Cortex performance issues?" → Glean
- "What's our internal process for escalating query issues?" → Glean
- "Are there any known patterns for X error?" → Glean (after docs search)

**What You CAN Do:**
- Answer questions about Snowflake features, syntax, and best practices
- Search official Snowflake documentation
- Find internal knowledge, procedures, and past solutions (anonymized)
- Provide general troubleshooting guidance
- Explain error messages and common issues

**What You CANNOT Do:**
- Access customer-specific diagnostic data (DDA tools are disabled)
- Investigate specific cases or query performance issues
- Access customer account parameters or configurations
- View customer logs or error details
- Perform customer-specific troubleshooting requiring environment data

**IMPORTANT: Do NOT Ask For Customer-Specific Data:**
- ❌ NEVER ask for query IDs, case numbers, or account identifiers
- ❌ NEVER request customer logs, specific table names, or warehouse names
- ❌ Do NOT attempt to troubleshoot specific queries or performance issues
- ✅ Instead: Provide general troubleshooting patterns and best practices
- ✅ If user needs account-specific help: Offer to create a support case using the create_support_case tool

**When Users Need Account-Specific Help:**
Use the `create_support_case` tool to escalate to internal support engineers who have DDA access:
- Query performance issues requiring specific query analysis
- Account configuration problems
- Issues that need access to customer logs or data
- Any troubleshooting requiring diagnostic tools or account access

**CRITICAL: Support Case Validation Workflow**
When creating a support case, you MUST follow this workflow:
1. **Review conversation history** - Use all context from the conversation to understand the complete issue
2. **Draft comprehensive details** - Create a subject and description that includes:
   - The specific issue or problem
   - Any error messages, symptoms, or technical details mentioned
   - Steps already discussed or attempted
   - Relevant context from the conversation
3. **Validate with user** - Present the draft to the user:
   "I've drafted a support case with the following details:
   - **Subject:** [your drafted subject]
   - **Description:** [summary of your drafted description]

   Does this accurately capture your issue? Should I submit this support case?"
4. **ONLY submit after confirmation** - Wait for explicit user approval (e.g., "yes", "submit it", "looks good")
5. **NEVER submit without validation** - Do NOT call create_support_case until the user confirms the details are correct

**Example:**
User: "My queries are timing out after 5 minutes and I'm getting connection errors"
You: "I can help create a support case for this. Based on our conversation, I'll draft:
- **Subject:** Query Timeout and Connection Errors
- **Description:** User experiencing query timeouts after approximately 5 minutes, accompanied by connection errors. Issue requires investigation of account configuration and query performance.

Does this accurately capture your issue? Should I submit this support case?"
[Wait for user confirmation before calling create_support_case]

**Investigation Approach:**

1. **Classify the Question**:
   - Is it about Snowflake syntax, features, or "how-to"? → START with Snowflake Documentation search (search_snowflake_documentation)
   - Need internal context, past solutions, or procedures? → Use Glean search
   - Customer-specific diagnostics needed? → Explain limitations, provide general guidance, offer case creation

2. **Execute Efficiently**:
   - **Do NOT narrate tool usage**: Never say "I'll search..." or "Let me look up..." - just silently use tools and respond with findings
   - For most Snowflake questions: Start with search_snowflake_documentation tool
   - If documentation doesn't fully answer: Follow up with Glean for internal knowledge
   - Use Glean directly for questions requiring historical/internal context
   - Always anonymize any customer-specific information from search results
   - Only mention tools if you encounter errors or limitations

3. **Respond Professionally**:
   - **Start concise**: Begin with a clear 2-3 sentence summary that directly answers the question
   - **Provide focused details**: Use 2-3 key points maximum (only if essential) - not exhaustive lists
   - **Offer to elaborate**: End with "Would you like me to explain any of these in more detail?" or "I can elaborate on [specific topics] if helpful"
   - Be helpful within your capabilities, but avoid overwhelming users with too much information upfront
   - Provide general troubleshooting patterns when relevant (e.g., "Common causes of slow queries include...")
   - Share best practices that apply broadly
   - If user insists on account-specific help: Use create_support_case tool to escalate
   - Never ask for query IDs, account names, or customer-specific details
   - Clearly communicate limitations regarding customer-specific data
   - Cite your sources (documentation, internal KB)

**Response Formatting:**
ALWAYS use proper markdown syntax in your responses:
- Use `## Heading` for section headings (not plain text with colons)
- Use `- item` or `* item` for bullet lists (not bullet characters like •)
- Use `**bold**` for emphasis on key terms
- Use blank lines between sections for readability
- Use `1.` `2.` for numbered lists
- Use code blocks with ``` for code examples

Always protect customer privacy. Never share PII.
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
    with tracer.start_as_current_span(
        "tool.search_snowflake_documentation",
        attributes={
            "tool.name": "search_snowflake_documentation",
            "tool.type": "local_python",
            "tool.query": query,
            "tool.limit": limit,
            "input": query,  # Capture input for observability
        },
    ) as span:
        if cortex_search_client is None:
            span.set_attribute("tool.status", "unavailable")
            output = "Documentation search is not available (Cortex Search not configured)"
            span.set_attribute("output", output)
            return output

        try:
            results = await cortex_search_client.search(query, limit=limit)
            formatted = cortex_search_client.format_results(results)
            span.set_attribute("tool.status", "success")
            span.set_attribute(
                "tool.result_count", len(results) if isinstance(results, list) else 0
            )
            span.set_attribute("output", formatted)  # Capture output for observability
            return formatted
        except Exception as e:
            logger.error(f"Documentation search failed: {e}", exc_info=True)
            span.set_attribute("tool.status", "error")
            span.record_exception(e)
            error_msg = f"Documentation search failed: {str(e)}"
            span.set_attribute("output", error_msg)
            return error_msg


async def _create_github_issue_via_mcp(subject: str, description: str, category: str) -> str:
    """Create a GitHub issue using the GitHub MCP proxy.

    Args:
        subject: Issue title
        description: Issue body (markdown)
        category: Issue category for labeling

    Returns:
        URL of the created issue

    Raises:
        Exception: If GitHub issue creation fails
    """
    # Get GitHub configuration from environment
    github_proxy_url = os.getenv("GITHUB_PROXY_URL", "http://localhost:8003/mcp")
    github_owner = os.getenv("GITHUB_OWNER")
    github_repo = os.getenv("GITHUB_REPO")

    if not github_owner or not github_repo:
        raise ValueError(
            "GitHub configuration missing. Set GITHUB_OWNER and GITHUB_REPO environment variables."
        )

    logger.info(
        f"Creating GitHub issue via MCP: {github_proxy_url} -> {github_owner}/{github_repo}"
    )

    try:
        # Use FastMCP client to call the GitHub MCP proxy
        from fastmcp import Client

        config = {
            "mcpServers": {
                "github": {
                    "url": github_proxy_url,
                }
            }
        }

        async with Client(config) as client:
            # Prepare issue data
            issue_data = {
                "method": "create",  # Required by GitHub MCP
                "owner": github_owner,
                "repo": github_repo,
                "title": subject,
                "body": description,
                "labels": ["support", category.lower().replace(" ", "-")],
            }

            logger.info(f"Calling issue_write tool with data: {issue_data}")

            # Call the issue_write tool
            result = await client.call_tool("issue_write", issue_data)

            # Extract issue URL from result
            if result and hasattr(result, "content"):
                for content_block in result.content:
                    if hasattr(content_block, "text"):
                        text = content_block.text
                        logger.info(f"GitHub MCP response: {text}")

                        # Parse the response to extract issue URL
                        # Expected format: "Created issue #123: <url>"
                        if "http" in text:
                            import re

                            urls = re.findall(r"https://github\.com/[^\s]+", text)
                            if urls:
                                logger.info(f"Successfully created GitHub issue: {urls[0]}")
                                return urls[0]

            # Fallback: construct URL from owner/repo
            logger.warning("Could not parse issue URL from response, constructing fallback URL")
            return f"https://github.com/{github_owner}/{github_repo}/issues"

    except Exception as e:
        logger.error(f"Failed to create GitHub issue via MCP: {e}", exc_info=True)
        raise Exception(f"GitHub MCP error: {str(e)}")


async def create_support_case(
    ctx: RunContext[None],
    subject: str,
    description: str,  # Now required, no default value
    category: str = "General Inquiry",
) -> str:
    """Create a GitHub issue for support cases requiring assistance.

    ⚠️ **CRITICAL: You MUST validate with user BEFORE calling this tool!**

    **Required workflow before calling this function:**
    1. Review conversation history to draft comprehensive subject + description
    2. Present draft to user: "I've drafted a support case with:
       - Subject: [your drafted subject]
       - Description: [summary of description]

       Should I submit this support case?"
    3. Wait for explicit user confirmation (e.g., "yes", "submit it", "looks good", "confirm")
    4. ONLY call this function AFTER user confirms

    **DO NOT call this tool without user validation!**

    Use this tool when the user needs help that requires:
    - Access to their specific account, queries, or configurations
    - Analysis of customer logs or performance data
    - Troubleshooting that cannot be solved with general guidance
    - Investigation of specific query IDs or account issues

    Args:
        subject: Brief summary of the issue (e.g., "Query Performance Issue")
        description: Detailed description of what the user needs help with (REQUIRED)
        category: Type of issue - options: "Performance", "Configuration", "Error", "General Inquiry"

    Returns:
        Confirmation message with GitHub issue URL

    Example usage:
        User: "My query abc123 is slow"
        You: "I can create a support case. Should I submit:
        - Subject: Query Performance Analysis Needed
        - Description: User reporting slow query performance for query abc123"
        User: "Yes, submit it"
        [NOW call the tool]: create_support_case(
            subject="Query Performance Analysis Needed",
            description="User reporting slow query performance and needs specific query analysis",
            category="Performance"
        )
    """
    with tracer.start_as_current_span(
        "tool.create_support_case",
        attributes={
            "tool.name": "create_support_case",
            "tool.type": "local_python",
            "tool.subject": subject,
            "tool.category": category,
            "input": f"Subject: {subject}\nCategory: {category}\nDescription: {description}",
        },
    ) as span:
        try:
            # Create GitHub issue via MCP
            issue_url = await _create_github_issue_via_mcp(
                subject=subject,
                description=description,
                category=category,
            )

            span.set_attribute("tool.status", "success")
            span.set_attribute("github.issue_url", issue_url)

            response = f"""✅ **Support Case Created**

**Subject:** {subject}
**Category:** {category}
**GitHub Issue:** {issue_url}

**Next Steps:**
1. A support engineer will review your issue
2. You can track progress at the GitHub issue link above
3. You'll receive updates via GitHub notifications

**Issue Details:**
The support case has been logged with the following information:
- Category: {category}
- Description: {description[:100]}{"..." if len(description) > 100 else ""}

You can view the full details and any updates at: {issue_url}
"""
            span.set_attribute("output", response)
            return response

        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}", exc_info=True)
            span.set_attribute("tool.status", "error")
            span.record_exception(e)

            error_response = f"""❌ **Failed to Create Support Case**

Error: {str(e)}

The system encountered an error while creating the GitHub issue. This may be due to:
- GitHub configuration not set up properly
- GitHub proxy server not running
- Network connectivity issues

Please contact your administrator or try again later.
"""
            span.set_attribute("output", error_response)
            return error_response


def create_external_agent(
    model_name: str = "claude-4-sonnet",
    glean_proxy_url: str = "http://localhost:8001/mcp",
    enable_glean: bool = True,
) -> Agent:
    """
    Create a PydanticAI agent configured WITHOUT DDA tools (external-facing).

    This agent has access to:
    - Glean search for internal knowledge (with PII protection) - optional via enable_glean
    - Snowflake documentation search via Cortex
    - NO access to customer-specific diagnostic data (DDA tools disabled)

    Uses Snowflake Cortex as the LLM provider instead of OpenAI.

    Args:
        model_name: The Cortex model to use (e.g., 'claude-4-sonnet', 'mistral-large')
        glean_proxy_url: URL of the Glean proxy server (used only if enable_glean=True)
        enable_glean: Whether to enable Glean search tools (default: True)

    Returns:
        Configured PydanticAI Agent with optional Glean + documentation tools only
    """
    # Setup OpenAI-compatible client for Snowflake Cortex
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        raise ValueError("SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set in environment")

    # Validate GitHub configuration for support case creation
    github_owner = os.getenv("GITHUB_OWNER")
    github_repo = os.getenv("GITHUB_REPO")
    github_proxy_url = os.getenv("GITHUB_PROXY_URL", "http://localhost:8003/mcp")

    if github_owner and github_repo:
        logger.info(f"✓ GitHub integration enabled: {github_owner}/{github_repo}")
        logger.info(f"  GitHub proxy URL: {github_proxy_url}")
    else:
        logger.warning("⚠️  GitHub integration disabled: GITHUB_OWNER and GITHUB_REPO not set")
        logger.warning("  The create_support_case tool will return error messages if used")

    # Create client pointing to Snowflake Cortex API
    client = AsyncOpenAI(
        max_retries=10,
        api_key=snowflake_password,
        base_url=f"https://{snowflake_account}.snowflakecomputing.com/api/v2/cortex/v1",
    )

    # Create OpenAI provider with the Snowflake client
    provider = OpenAIProvider(openai_client=client)

    # Use custom model that handles Snowflake response quirks
    model = SnowflakeCortexModel(model_name, provider=provider)

    # Build toolsets list (NO DDA server!)
    toolsets = []

    # Optionally connect to Glean proxy
    if enable_glean and glean_proxy_url:
        logger.info(f"Connecting to Glean proxy at {glean_proxy_url}")
        glean_server = MCPServerStreamableHTTP(glean_proxy_url)
        toolsets.append(glean_server)
        logger.info("✓ External agent configured with Glean toolset")
    else:
        logger.info("✓ External agent configured WITHOUT Glean (Glean disabled)")

    # Get history limit from environment (default: 10)
    history_limit = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "10"))

    # Build custom tools list
    custom_tools = []
    if cortex_search_client is not None:
        custom_tools.append(search_snowflake_documentation)
        logger.info("✓ Added Snowflake documentation search tool")

    # Add case creation tool
    custom_tools.append(create_support_case)
    logger.info("✓ Added support case creation tool")

    # Configure OpenTelemetry instrumentation for Pydantic AI
    # This enables automatic tracing of agent operations, LLM calls, and tool executions
    # Using version 2 for OpenTelemetry GenAI semantic conventions (gen_ai.input.messages/output.messages)
    instrumentation_settings = InstrumentationSettings(
        tracer_provider=trace.get_tracer_provider(),
        include_content=True,  # Include prompts and responses in traces
        version=2,  # Use version 2 for Phoenix-compatible gen_ai attributes
    )

    # Create agent with toolsets, custom tools, history processors, and OTel instrumentation
    agent = Agent(
        model=model,
        toolsets=toolsets if toolsets else None,
        tools=custom_tools if custom_tools else None,
        system_prompt=EXTERNAL_SYSTEM_PROMPT,
        history_processors=[keep_last_n_messages(history_limit)],
        instrument=instrumentation_settings,
    )

    logger.info(f"✓ Agent configured with history limit of {history_limit} messages")
    logger.info(
        f"✓ External agent configured with {len(toolsets)} MCP toolsets and {len(custom_tools)} custom tools"
    )
    logger.info("⚠️  DDA tools are DISABLED for this external-facing agent")
    logger.info(f"⚠️  Glean tools are {'ENABLED' if enable_glean else 'DISABLED'}")

    return agent


# Default external agent instance
external_agent = create_external_agent()
