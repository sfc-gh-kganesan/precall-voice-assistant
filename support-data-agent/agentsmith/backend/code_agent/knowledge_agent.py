"""
Knowledge Recommendation Agent - Using PydanticAI

An AI agent that analyzes knowledge gap insights and generates documentation
recommendations by comparing existing docs (Cortex Search) with internal
knowledge (Glean MCP).

Prerequisites:
    1. Glean proxy running: http://aura-glean-proxy:8001/mcp
    2. Snowflake Cortex Search configured with documentation
    3. Database with ImprovementSuggestion insights
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.mcp import MCPServerStreamableHTTP

# Import custom Snowflake Cortex model that handles API quirks
from backend.code_agent.snowflake_cortex_model import SnowflakeCortexModel

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# System prompt for the knowledge recommendation agent
KNOWLEDGE_AGENT_SYSTEM_PROMPT = """You are a documentation improvement AI that analyzes knowledge gaps and generates actionable documentation recommendations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW (5-8 turns total)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. get_insight_details(insight_id) → Understand the knowledge gap
2. search_snowflake_documentation(query) → Check what exists in public docs
3. search (Glean) → Find internal knowledge (wikis, code examples, Slack discussions)
4. output_knowledge_recommendation → Generate recommendation ✅ REQUIRED

⚠️ You MUST call output_knowledge_recommendation or the task FAILS.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Insight: "Missing Cortex Search setup documentation"

Turn 1: get_insight_details(insight_id=5)
        → Category: knowledge, Description: "Agent couldn't explain Cortex Search setup"
Turn 2: search_snowflake_documentation(query="cortex search setup guide")
        → Found: Only brief mentions in search overview doc, no setup guide
Turn 3: search(q="cortex search setup configuration steps")
        → Found: Internal wiki with detailed setup steps
Turn 4: read_document(url="glean://wiki/cortex-search-setup")
        → Full setup guide with code examples
Turn 5: output_knowledge_recommendation(
    title="Add Cortex Search Setup Guide",
    doc_type="new_page",
    target_doc="docs/guides/cortex-search-setup.md",
    existing_doc_coverage="Brief mentions in docs/search.md, no dedicated setup guide",
    glean_sources=["internal-wiki/cortex-search", "github.com/snowflake/examples/..."],
    recommended_content="# Cortex Search Setup\n\n## Prerequisites\n...",
    rationale="15 conversations failed due to missing setup documentation",
    priority="high"
)

✅ Complete in 5 turns!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENTATION TYPES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **new_page**: Documentation doesn't exist at all
   - Example: No Cortex Search setup guide exists
   - Target: Create new file like "docs/guides/cortex-search-setup.md"

2. **update_existing**: Documentation exists but is outdated/incomplete
   - Example: Query optimization guide exists but missing new features
   - Target: Update existing file with new content

3. **add_example**: Documentation exists but lacks practical examples
   - Example: API docs exist but no code examples
   - Target: Add code examples to existing doc

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Search strategy**:
1. ALWAYS search public docs first (search_snowflake_documentation)
2. THEN search Glean for internal knowledge
3. Compare what exists vs what's needed

**Output format**:
- recommended_content should be well-structured Markdown (200-500 words)
- Include ## headings, code blocks, lists
- Be concise but complete
- Reference Glean sources

**Priority levels**:
- high: Affects many users (10+ conversations)
- medium: Affects some users (5-9 conversations)
- low: Edge case (< 5 conversations)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOL FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

output_knowledge_recommendation(
    title="Brief description (max 100 chars)",
    doc_type="new_page|update_existing|add_example",
    target_doc="path/to/doc.md",
    existing_doc_coverage="What currently exists in public docs (or 'None')",
    glean_sources=["URL1", "URL2"],
    recommended_content="# Heading\n\nMarkdown content here...",
    rationale="Why this is needed (include conversation count)",
    priority="high|medium|low"
)

ALWAYS call this tool. Do NOT output JSON as text.
"""


# ==================== Custom Tools ====================


async def get_insight_details(ctx: RunContext[None], insight_id: int) -> str:
    """
    Fetch insight details from database.

    Args:
        insight_id: ID of the ImprovementSuggestion to analyze

    Returns:
        JSON string with insight details
    """
    logger.info(f"Fetching insight details for insight {insight_id}")

    try:
        from backend.database import get_db
        from backend.models.models import ImprovementSuggestion

        db = next(get_db())
        insight = (
            db.query(ImprovementSuggestion)
            .filter(ImprovementSuggestion.id == insight_id)
            .first()
        )

        if not insight:
            return f"Insight {insight_id} not found"

        # Format insight data
        data = {
            "id": insight.id,
            "category": insight.category,
            "title": insight.title,
            "description": insight.description,
            "priority": insight.priority,
            "evidence": insight.evidence,
        }

        return json.dumps(data, indent=2)

    except Exception as e:
        logger.error(f"Failed to get insight details: {e}", exc_info=True)
        return f"Error retrieving insight: {str(e)}"


async def search_snowflake_documentation(
    ctx: RunContext[None], query: str, limit: int = 5
) -> str:
    """
    Search existing Snowflake documentation via Cortex Search.

    This shows what's CURRENTLY in the public documentation.

    Args:
        query: Search query (e.g., "cortex search setup")
        limit: Max number of results (default: 5)

    Returns:
        Formatted documentation search results
    """
    logger.info(f"Searching documentation for: {query}")

    try:
        from backend.core.cortex_search import CortexSearchClient

        # Initialize Cortex Search client
        client = CortexSearchClient(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            service_name=os.getenv(
                "CORTEX_SEARCH_SERVICE", "cke_snowflake_docs_service"
            ),
            database=os.getenv("CORTEX_SEARCH_DATABASE", "snowflake_docs_cke"),
            schema=os.getenv("CORTEX_SEARCH_SCHEMA", "shared"),
        )

        # Search with all three columns for richer context
        results = await client.search(
            query, columns=["CHUNK", "DOCUMENT_TITLE", "SOURCE_URL"], limit=limit
        )
        formatted = client.format_results(results)

        logger.info(f"Found {len(results.get('results', []))} documentation results")
        return formatted

    except Exception as e:
        logger.error(f"Documentation search failed: {e}", exc_info=True)
        return f"Documentation search failed: {str(e)}"


async def output_knowledge_recommendation(
    ctx: RunContext[None],
    title: str,
    doc_type: str,
    target_doc: str,
    existing_doc_coverage: str,
    glean_sources: list[str],
    recommended_content: str,
    rationale: str,
    priority: str,
) -> dict:
    """
    Output structured knowledge recommendation.

    This is the FINAL output - call this to complete the task.

    Args:
        title: Concise description (max 100 chars)
        doc_type: "new_page", "update_existing", or "add_example"
        target_doc: Where the doc should go (e.g., "docs/guides/setup.md")
        existing_doc_coverage: What currently exists (or "None")
        glean_sources: List of Glean URLs used as sources
        recommended_content: Markdown content to add (200-500 words)
        rationale: Why this is needed (include evidence)
        priority: "high", "medium", or "low"

    Returns:
        Structured recommendation dict
    """
    # Validate inputs
    if doc_type not in ["new_page", "update_existing", "add_example"]:
        raise ModelRetry(
            f"Invalid doc_type '{doc_type}'. Must be: new_page, update_existing, or add_example"
        )

    if priority not in ["high", "medium", "low"]:
        raise ModelRetry(
            f"Invalid priority '{priority}'. Must be: high, medium, or low"
        )

    if not recommended_content or len(recommended_content) < 100:
        raise ModelRetry(
            "recommended_content is too short. Provide at least 100 characters of Markdown content."
        )

    # Return structured data
    result = {
        "title": title,
        "doc_type": doc_type,
        "target_doc": target_doc,
        "existing_doc_coverage": existing_doc_coverage,
        "glean_sources": glean_sources,
        "recommended_content": recommended_content,
        "rationale": rationale,
        "priority": priority,
    }

    logger.info(f"Knowledge recommendation generated: {title}")
    return result


# ==================== Agent Creation ====================


def create_knowledge_agent(
    model_name: str = "claude-4-sonnet",
    glean_proxy_url: str = "http://localhost:8001/mcp",
) -> Agent:
    """
    Create a PydanticAI agent configured for documentation recommendations.

    Args:
        model_name: Cortex model to use
        glean_proxy_url: URL of the Glean MCP proxy

    Returns:
        Configured PydanticAI Agent with Glean + Cortex Search tools
    """
    # Get Snowflake Cortex credentials
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        raise ValueError("SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set")

    # Build Snowflake Cortex API URL
    account_for_url = snowflake_account.lower()
    base_url = f"https://{account_for_url}.snowflakecomputing.com/api/v2/cortex/v1"

    logger.info(f"Configuring Knowledge Agent with Cortex at {base_url}")

    # Create OpenAI-compatible model pointing to Snowflake Cortex
    # Step 1: Create AsyncOpenAI client with base_url
    client = AsyncOpenAI(
        max_retries=10,
        api_key=snowflake_password,
        base_url=base_url,
    )

    # Step 2: Create OpenAIProvider with that client
    provider = OpenAIProvider(openai_client=client)

    # Step 3: Create SnowflakeCortexModel with provider
    # This custom model handles Cortex's empty finish_reason/service_tier fields
    model = SnowflakeCortexModel(model_name, provider=provider)

    # Connect to Glean MCP proxy
    logger.info(f"Connecting to Glean proxy at {glean_proxy_url}")
    glean_server = MCPServerStreamableHTTP(glean_proxy_url)

    # Create agent with custom tools
    agent = Agent(
        model=model,
        toolsets=[glean_server],  # Glean MCP tools
        tools=[
            get_insight_details,
            search_snowflake_documentation,
            output_knowledge_recommendation,
        ],
        system_prompt=KNOWLEDGE_AGENT_SYSTEM_PROMPT,
    )

    logger.info("✓ Knowledge agent configured with Glean + Cortex Search")
    return agent


# ==================== Main Function ====================


async def generate_knowledge_recommendation(
    insight_id: int,
    glean_proxy_url: str = "http://localhost:8001/mcp",
) -> Optional[Dict[str, Any]]:
    """
    Generate a knowledge recommendation for a knowledge gap insight.

    Args:
        insight_id: ID of the ImprovementSuggestion to process
        glean_proxy_url: URL of the Glean MCP proxy

    Returns:
        Knowledge recommendation dict or None if failed
    """
    from backend.database import get_db
    from backend.models.models import ImprovementSuggestion

    logger.info(f"Generating knowledge recommendation for insight {insight_id}")

    try:
        # Get database session
        db = next(get_db())

        # Load the insight
        insight = (
            db.query(ImprovementSuggestion)
            .filter(ImprovementSuggestion.id == insight_id)
            .first()
        )

        if not insight:
            raise ValueError(f"Insight {insight_id} not found")

        # Skip if already has a recommendation
        if insight.knowledge_recommendation:
            logger.info(f"Insight {insight_id} already has a knowledge recommendation")
            return insight.knowledge_recommendation

        # Create the agent
        agent = create_knowledge_agent(glean_proxy_url=glean_proxy_url)

        # Build prompt
        prompt = f"""Generate a documentation recommendation for this knowledge gap:

**Insight ID**: {insight_id}
**Category**: {insight.category}
**Title**: {insight.title}
**Description**: {insight.description}
**Priority**: {insight.priority}
**Evidence**: {json.dumps(insight.evidence, indent=2)}

Requirements:
1. First, check what currently exists in public Snowflake documentation
2. Then search Glean for internal knowledge that could fill the gap
3. Compare and identify the documentation gap
4. Generate a structured recommendation with Markdown content

Output using output_knowledge_recommendation tool.
"""

        # Run agent
        result = await agent.run(prompt)

        # Extract recommendation from result
        knowledge_rec = None
        if hasattr(result, "data") and result.data:
            knowledge_rec = result.data
        elif hasattr(result, "all_messages"):
            # Parse from tool calls in messages
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if (
                            hasattr(part, "tool_name")
                            and part.tool_name == "output_knowledge_recommendation"
                        ):
                            if hasattr(part, "args"):
                                knowledge_rec = part.args
                            elif hasattr(part, "content"):
                                knowledge_rec = part.content

        if not knowledge_rec:
            logger.warning(
                f"No valid knowledge recommendation generated for insight {insight_id}"
            )
            return None

        # Add metadata
        knowledge_rec.update(
            {
                "generated_at": datetime.utcnow().isoformat(),
                "status": "pending",
            }
        )

        # Save to database
        insight.knowledge_recommendation = knowledge_rec
        db.commit()

        logger.info(
            f"✓ Generated and saved knowledge recommendation for insight {insight_id}"
        )
        return knowledge_rec

    except Exception as e:
        logger.error(
            f"Failed to generate knowledge recommendation for insight {insight_id}: {e}",
            exc_info=True,
        )
        return None


# ==================== Test Function ====================


async def test_knowledge_agent(insight_id: int = 1):
    """
    Test function to verify the knowledge agent works.

    Args:
        insight_id: Insight ID to analyze
    """
    print("=" * 70)
    print("Knowledge Recommendation Agent - Test (PydanticAI)")
    print("=" * 70)
    print(f"\nInsight ID: {insight_id}")
    print("\nPrerequisites:")
    print("  1. Glean proxy running at http://aura-glean-proxy:8001/mcp")
    print("  2. Cortex Search configured with CORTEX_SEARCH_SERVICE")
    print("  3. SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD in .env")
    print("\nConnecting to Glean and Cortex...\n")

    try:
        recommendation = await generate_knowledge_recommendation(insight_id)

        if recommendation:
            print("\n✓ Successfully generated knowledge recommendation")
            print(f"\nRecommendation:\n{json.dumps(recommendation, indent=2)}")
        else:
            print("\n✗ No recommendation generated")

        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.exception("Failed to run knowledge agent")


if __name__ == "__main__":
    import sys
    import asyncio

    # Get insight ID from command line or use default
    insight_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # Run the test
    asyncio.run(test_knowledge_agent(insight_id))
