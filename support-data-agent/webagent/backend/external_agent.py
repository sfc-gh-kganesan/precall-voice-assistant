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
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.history import keep_last_n_messages
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
    if cortex_search_client is None:
        return "Documentation search is not available (Cortex Search not configured)"

    try:
        results = await cortex_search_client.search(query, limit=limit)
        formatted = cortex_search_client.format_results(results)
        return formatted
    except Exception as e:
        logger.error(f"Documentation search failed: {e}", exc_info=True)
        return f"Documentation search failed: {str(e)}"


async def create_support_case(
    ctx: RunContext[None],
    subject: str,
    description: str,
    category: str = "General Inquiry",
) -> str:
    """Create a Snowflake support case for issues requiring account-specific assistance.

    Use this tool when the user needs help that requires:
    - Access to their specific account, queries, or configurations
    - Analysis of customer logs or performance data
    - Troubleshooting that cannot be solved with general guidance
    - Investigation of specific query IDs or account issues

    Args:
        subject: Brief summary of the issue (e.g., "Query Performance Issue")
        description: Detailed description of what the user needs help with
        category: Type of issue - options: "Performance", "Configuration", "Error", "General Inquiry"

    Returns:
        Confirmation message with case details and next steps

    Example usage:
        When user says "My query abc123 is slow", respond with:
        "I can help you create a support case for account-specific query analysis."
        Then call: create_support_case(
            subject="Query Performance Analysis Needed",
            description="User reporting slow query performance and needs specific query analysis",
            category="Performance"
        )
    """
    # TODO: Integrate with actual case creation system (Jira, Salesforce, etc.)
    # For now, return a stub response

    logger.info(f"[STUB] Support case created: {subject} (Category: {category})")
    logger.info(f"[STUB] Description: {description}")

    return f"""✅ **Support Case Created**

**Subject:** {subject}
**Category:** {category}
**Status:** Submitted

**Next Steps:**
1. A Snowflake support engineer will reach out within 24 hours
2. They have access to your account data and diagnostic tools
3. You'll receive a case number and tracking link via email shortly

**What to prepare for the engineer:**
- Query IDs or specific examples of the issue
- Your account name and region
- Any error messages or screenshots
- Timeframe when the issue occurred
- Steps to reproduce (if applicable)

**In the meantime:**
While you wait for the support engineer, here are some general best practices that might help with similar issues:

"""


def create_external_agent(
    model_name: str = "claude-4-sonnet",
    glean_proxy_url: str = "http://localhost:8001/mcp",
) -> Agent:
    """
    Create a PydanticAI agent configured WITHOUT DDA tools (external-facing).

    This agent has access to:
    - Glean search for internal knowledge (with PII protection)
    - Snowflake documentation search via Cortex
    - NO access to customer-specific diagnostic data (DDA tools disabled)

    Uses Snowflake Cortex as the LLM provider instead of OpenAI.

    Args:
        model_name: The Cortex model to use (e.g., 'claude-4-sonnet', 'mistral-large')
        glean_proxy_url: URL of the Glean proxy server (set to None to disable Glean)

    Returns:
        Configured PydanticAI Agent with Glean + documentation tools only
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
    if glean_proxy_url:
        logger.info(f"Connecting to Glean proxy at {glean_proxy_url}")
        glean_server = MCPServerStreamableHTTP(glean_proxy_url)
        toolsets.append(glean_server)
        logger.info("✓ External agent configured with Glean toolset")
    else:
        logger.info("✓ External agent configured without Glean")

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

    # Create agent with toolsets, custom tools, and history processors
    agent = Agent(
        model=model,
        toolsets=toolsets if toolsets else None,
        tools=custom_tools if custom_tools else None,
        system_prompt=EXTERNAL_SYSTEM_PROMPT,
        history_processors=[keep_last_n_messages(history_limit)],
    )

    logger.info(f"✓ Agent configured with history limit of {history_limit} messages")
    logger.info(
        f"✓ External agent configured with {len(toolsets)} MCP toolsets and {len(custom_tools)} custom tools"
    )
    logger.info("⚠️  DDA tools are DISABLED for this external-facing agent")

    return agent


# Default external agent instance
external_agent = create_external_agent()
