"""
Code Recommendation Agent - Using Claude Agent SDK

An AI agent that analyzes simulation insights and generates specific code change
recommendations using Claude Agent SDK with GitHub MCP tools and Snowflake Cortex.

Prerequisites:
    1. Start the GitHub proxy server: uv run agentsim/backend/code_agent/github_proxy.py
    2. Complete OAuth flow in browser (opens automatically) if PAT not configured
    3. Install Claude Code: npm install -g @anthropic-ai/claude-code
    4. Then use this agent
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    tool,
    create_sdk_mcp_server,
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# System prompt for the code recommendation agent
CODE_AGENT_SYSTEM_PROMPT = """You are a code review AI that generates specific code improvements from simulation insights.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW (5-10 turns total)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. get_simulation_insights(simulation_id) → Get the insight
2. search_code (1-2 targeted queries) OR get_file_contents → Find code
3. Read relevant files → Understand the issue
4. output_code_recommendation → Generate fix ✅ REQUIRED

⚠️ You MUST call output_code_recommendation or the task FAILS.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Insight: "Add Timeout to HTTP Requests - agent hangs on slow connections"

Turn 1: get_simulation_insights(simulation_id=1)
Turn 2: search_code(q="http client path:support-data-agent/troubleshooting")
        → Found: http_client.py
Turn 3: get_file_contents(path="...http_client.py")
        → Line 45: response = await client.post(url, json=data)  # NO TIMEOUT
Turn 4: output_code_recommendation(
    title="Add timeout to HTTP requests",
    description="HTTP client lacks timeout causing hangs. Adding 30s timeout prevents indefinite waits.",
    file_changes=[{
        "file": "support-data-agent/troubleshooting/app/http_client.py",
        "old_content": "    response = await client.post(url, json=data)",
        "new_content": "    response = await client.post(url, json=data, timeout=30.0)",
        "diff": "--- a/http_client.py\n+++ b/http_client.py\n@@ -45 +45 @@\n-    response = await client.post(url, json=data)\n+    response = await client.post(url, json=data, timeout=30.0)"
    }],
    priority="high"
)

✅ Complete in 4 turns!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Read-only**: Can use search_code, get_file_contents, list_commits. Cannot modify files.

**Search scope**: ALWAYS include "path:{target_path}" in search_code queries.

**Efficiency**: search_code is rate limited (30/min). Use 1-2 targeted searches, then read files.

**Output**: ONE surgical change per insight. Keep old_content/new_content to 5-20 lines max.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOL FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

output_code_recommendation(
    title="Brief fix description (max 50 chars)",
    description="2-3 sentences: issue, why problem, how fix addresses it",
    file_changes=[{
        "file": "full/path/to/file.py",
        "old_content": "exact code to replace",
        "new_content": "improved code",
        "diff": "unified diff format"
    }],
    priority="high|medium|low"
)

DO NOT output JSON as text. ALWAYS call the tool.
"""


# In-process MCP tool for database access
@tool(
    "get_simulation_insights",
    "Retrieve improvement insights from a simulation by ID",
    {"simulation_id": int},
)
async def get_simulation_insights(args):
    """
    Get insights from database for a given simulation.

    Args:
        args: Dict with simulation_id

    Returns:
        MCP tool response with insights as JSON text
    """
    simulation_id = args["simulation_id"]
    logger.info(f"Fetching insights for simulation {simulation_id}")

    try:
        # Import here to avoid circular imports
        from backend.database import get_db
        from backend.models.models import ImprovementSuggestion

        # Get database session
        db = next(get_db())

        # Query insights for this simulation
        insights = (
            db.query(ImprovementSuggestion)
            .filter(ImprovementSuggestion.simulation_id == simulation_id)
            .all()
        )

        if not insights:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"No insights found for simulation {simulation_id}",
                    }
                ]
            }

        # Format insights as JSON
        insights_data = [
            {
                "id": insight.id,
                "category": insight.category,
                "title": insight.title,
                "description": insight.description,
                "priority": insight.priority,
                "evidence": insight.evidence,
            }
            for insight in insights
        ]

        return {
            "content": [{"type": "text", "text": json.dumps(insights_data, indent=2)}]
        }

    except Exception as e:
        logger.error(f"Failed to get simulation insights: {e}", exc_info=True)
        return {
            "content": [
                {"type": "text", "text": f"Error retrieving insights: {str(e)}"}
            ]
        }


@tool(
    "output_code_recommendation",
    "Output a structured code recommendation with file changes",
    {
        "title": {"type": "string", "maxLength": 100},
        "description": {"type": "string"},
        "file_changes": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["file", "old_content", "new_content", "diff"],
                "properties": {
                    "file": {"type": "string"},
                    "old_content": {"type": "string"},
                    "new_content": {"type": "string"},
                    "diff": {"type": "string"},
                },
            },
        },
        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
    },
)
async def output_code_recommendation(args):
    """
    Output structured code recommendation as JSON.

    This tool ensures valid JSON output with the required schema.
    Use this tool to return your final code recommendation.

    Args:
        args: Dict with required keys:
            - title (str): Concise description (max 100 chars)
            - description (str): 2-3 sentence explanation
            - file_changes (list): Array of dicts with file, old_content, new_content, diff
            - priority (str): "high", "medium", or "low"

    Returns:
        MCP tool response with JSON
    """
    # Validate structure
    required_keys = ["title", "description", "file_changes", "priority"]
    for key in required_keys:
        if key not in args:
            error_msg = f"Error: Missing required key '{key}'"
            logger.error(error_msg)
            return {"content": [{"type": "text", "text": error_msg}]}

    # Parse file_changes if it's a JSON string (common with LLM-generated tool calls)
    if isinstance(args["file_changes"], str):
        try:
            args["file_changes"] = json.loads(args["file_changes"])
            logger.info("Parsed file_changes from JSON string to list")
        except json.JSONDecodeError as e:
            error_msg = f"Error: file_changes must be valid JSON: {str(e)}"
            logger.error(error_msg)
            return {"content": [{"type": "text", "text": error_msg}]}

    # Validate file_changes structure
    if not isinstance(args["file_changes"], list):
        error_msg = "Error: file_changes must be a list"
        logger.error(error_msg)
        return {"content": [{"type": "text", "text": error_msg}]}

    if len(args["file_changes"]) == 0:
        error_msg = "Error: file_changes must contain at least one change"
        logger.error(error_msg)
        return {"content": [{"type": "text", "text": error_msg}]}

    # Validate each file change
    for i, change in enumerate(args["file_changes"]):
        if not isinstance(change, dict):
            error_msg = f"Error: file_changes[{i}] must be an object/dict"
            logger.error(error_msg)
            return {"content": [{"type": "text", "text": error_msg}]}

        required_change_keys = ["file", "old_content", "new_content", "diff"]
        for key in required_change_keys:
            if key not in change:
                error_msg = f"Error: file_changes[{i}] missing required key '{key}'"
                logger.error(error_msg)
                return {"content": [{"type": "text", "text": error_msg}]}

    # Validate priority
    if args["priority"] not in ["high", "medium", "low"]:
        error_msg = f"Error: priority must be 'high', 'medium', or 'low', got '{args['priority']}'"
        logger.error(error_msg)
        return {"content": [{"type": "text", "text": error_msg}]}

    # Return as JSON
    logger.info(f"Code recommendation generated: {args['title']}")
    return {"content": [{"type": "text", "text": json.dumps(args, indent=2)}]}


# Create in-process MCP server with our custom tools
agentsim_mcp_server = create_sdk_mcp_server(
    name="agentsim-tools",
    version="1.0.0",
    tools=[get_simulation_insights, output_code_recommendation],
)


# Hook to block write operations - only allow read-only GitHub tools
async def block_github_write_operations(
    input_data: dict, tool_use_id: str, context: dict
) -> Optional[dict]:
    """
    PreToolUse hook that blocks GitHub write operations.

    This ensures the code agent can only READ from GitHub, not write/modify.
    The UI and other clients can still use write operations.

    Args:
        input_data: Dict containing tool_name and other tool invocation data
        tool_use_id: Unique ID for this tool use
        context: Execution context

    Returns:
        None to allow execution, or dict with hookSpecificOutput to block
    """
    # Extract tool name from input_data
    tool_name = input_data.get("tool_name", "")

    # List of write operations to block
    write_tools = {
        "mcp__github__create_or_update_file",
        "mcp__github__delete_file",
        "mcp__github__push_files",
        "mcp__github__create_branch",
        "mcp__github__create_repository",
        "mcp__github__fork_repository",
        "mcp__github__create_pull_request",
        "mcp__github__merge_pull_request",
        "mcp__github__update_pull_request",
        "mcp__github__update_pull_request_branch",
        "mcp__github__pull_request_review_write",
        "mcp__github__add_comment_to_pending_review",
        "mcp__github__issue_write",
        "mcp__github__sub_issue_write",
        "mcp__github__add_issue_comment",
        "mcp__github__assign_copilot_to_issue",
        "mcp__github__request_copilot_review",
    }

    if tool_name in write_tools:
        logger.warning(f"Blocked write operation: {tool_name}")
        # Return hook-specific output format for denial
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Write operations are disabled for the code recommendation agent. Please use read-only tools.",
            }
        }

    # Allow all other tools
    return None


async def create_code_agent(
    target_repo: str = "snowflakedb/aura",
    github_proxy_url: str = "http://localhost:8003/mcp",
) -> ClaudeSDKClient:
    """
    Create a Claude Agent SDK client configured for code recommendations.

    Args:
        target_repo: Target repository (e.g., 'snowflakedb/aura')
        github_proxy_url: URL of the GitHub MCP proxy server

    Returns:
        Configured ClaudeSDKClient
    """
    # Get Snowflake Cortex credentials from environment
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        raise ValueError(
            "SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set in environment"
        )

    # Configure SDK to use Snowflake Cortex as backend
    # Set environment variables that the SDK will use
    # Use account name as-is (keep hyphens, lowercase for URL)
    # Use /api/v2/cortex/anthropic endpoint which works with Claude Agent SDK
    # Note: The documented endpoint /inference:complete works for direct HTTP but not SDK
    account_for_url = snowflake_account.lower()
    cortex_base_url = (
        f"https://{account_for_url}.snowflakecomputing.com/api/v2/cortex/anthropic"
    )
    os.environ["ANTHROPIC_BASE_URL"] = cortex_base_url
    os.environ["ANTHROPIC_AUTH_TOKEN"] = snowflake_password
    os.environ["ANTHROPIC_MODEL"] = "claude-sonnet-4-5"
    os.environ["ANTHROPIC_SMALL_FAST_MODEL"] = "claude-4-sonnet"

    logger.info(f"Configuring Claude Agent SDK to use Cortex at {cortex_base_url}")

    # Set target repository context
    system_prompt = CODE_AGENT_SYSTEM_PROMPT + f"\n\nTarget Repository: {target_repo}"

    # Configure agent options
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-5",  # Cortex model name
        mcp_servers={
            "agentsim": agentsim_mcp_server,  # In-process (DB access)
            "github": {  # External proxy (GitHub API)
                "type": "http",  # HTTP transport (matches FastMCP)
                "url": github_proxy_url,
            },
        },
        allowed_tools=[
            # AgentSim tools (database access)
            "mcp__agentsim__get_simulation_insights",
            "mcp__agentsim__output_code_recommendation",
            # GitHub READ-ONLY tools for code analysis
            # File/Code Access
            "mcp__github__get_file_contents",
            "mcp__github__search_code",
            # Repository Structure
            "mcp__github__list_branches",
            "mcp__github__list_commits",
            "mcp__github__get_commit",
            # Releases & Tags
            "mcp__github__get_latest_release",
            "mcp__github__get_release_by_tag",
            "mcp__github__get_tag",
            "mcp__github__list_releases",
            "mcp__github__list_tags",
            # Issues & PRs (read-only)
            "mcp__github__issue_read",
            "mcp__github__list_issues",
            "mcp__github__search_issues",
            "mcp__github__pull_request_read",
            "mcp__github__list_pull_requests",
            "mcp__github__search_pull_requests",
            # Repository Search
            "mcp__github__search_repositories",
            "mcp__github__search_users",
            # Team Info
            "mcp__github__get_team_members",
            "mcp__github__get_teams",
            "mcp__github__get_me",
            # Labels (read-only)
            "mcp__github__get_label",
            "mcp__github__list_issue_types",
            # EXPLICITLY EXCLUDED (write operations):
            # - mcp__github__create_or_update_file
            # - mcp__github__delete_file
            # - mcp__github__push_files
            # - mcp__github__create_pull_request
            # - mcp__github__create_branch
            # - mcp__github__merge_pull_request
            # - mcp__github__fork_repository
            # - mcp__github__issue_write
            # - mcp__github__sub_issue_write
            # - mcp__github__pull_request_review_write
            # - mcp__github__add_comment_to_pending_review
            # - mcp__github__add_issue_comment
            # - mcp__github__update_pull_request
            # - mcp__github__update_pull_request_branch
            # - mcp__github__assign_copilot_to_issue
            # - mcp__github__request_copilot_review
            # - mcp__github__create_repository
        ],
        system_prompt=system_prompt,
        max_turns=20,
        hooks={"PreToolUse": [block_github_write_operations]},  # Block write operations
    )

    logger.info("✓ Claude Agent SDK configured successfully")
    return ClaudeSDKClient(options=options)


async def generate_recommendation_for_insight(
    insight_id: int,
    target_repo: str = "snowflakedb/aura",
    target_path: str = "support-data-agent/troubleshooting",
) -> Optional[Dict[str, Any]]:
    """
    Generate a code recommendation for a single improvement insight.

    Args:
        insight_id: ID of the ImprovementSuggestion to generate recommendation for
        target_repo: GitHub repository to analyze
        target_path: Path within the repository to focus on

    Returns:
        Code recommendation dict with file_changes, status, etc.
    """
    from backend.database import get_db
    from backend.models.models import ImprovementSuggestion

    logger.info(f"Generating code recommendation for insight {insight_id}")

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
        if insight.code_recommendation:
            logger.info(f"Insight {insight_id} already has a code recommendation")
            return insight.code_recommendation

        # Create the agent
        async with await create_code_agent(target_repo=target_repo) as client:
            # Build focused prompt for this single insight
            prompt = f"""Generate ONE concise code recommendation for this insight:

**Insight ID**: {insight_id}
**Category**: {insight.category}
**Title**: {insight.title}
**Description**: {insight.description}
**Priority**: {insight.priority}
**Evidence**: {insight.evidence}

Target Repository: {target_repo}/{target_path}

⚠️ CRITICAL SEARCH RESTRICTION:
- ONLY search within: {target_path}
- ALWAYS use: path:{target_path} in ALL search_code queries
- Example: search_code(q="error handling path:{target_path}")
- Do NOT search the entire repository

Requirements:
- Keep code changes minimal and surgical (5-20 lines max)
- Focus on the ONE most impactful fix for this specific issue
- Include: title, description (2-3 sentences), file_changes array (1 change), priority

Output Method:
- Call output_code_recommendation tool with the structured data
- Do NOT return JSON as text
- The tool ensures proper formatting and validation"""

            # Send query to agent
            await client.query(prompt)

            # Collect agent responses and extract tool call results
            # The Claude Agent SDK returns UserMessage objects with ToolResultBlock content
            tool_results = []
            async for message in client.receive_response():
                logger.info(f"Agent message type: {type(message)}, content: {message}")

                # Check for UserMessage with ToolResultBlock (this is where tool results are)
                if hasattr(message, "content") and isinstance(message.content, list):
                    for content_block in message.content:
                        # Look for ToolResultBlock type
                        if (
                            hasattr(content_block, "__class__")
                            and content_block.__class__.__name__ == "ToolResultBlock"
                        ):
                            # Extract the content from the tool result
                            if hasattr(content_block, "content") and isinstance(
                                content_block.content, list
                            ):
                                for result_item in content_block.content:
                                    if (
                                        isinstance(result_item, dict)
                                        and result_item.get("type") == "text"
                                    ):
                                        tool_results.append(result_item)
                        # Also check for dict-based tool results
                        elif (
                            isinstance(content_block, dict)
                            and content_block.get("type") == "tool_result"
                        ):
                            tool_results.append(content_block)

                # Legacy: Check for other message structures
                elif hasattr(message, "tool_use"):
                    tool_results.append(message)
                elif hasattr(message, "content") and isinstance(message.content, str):
                    # Might be JSON from the tool
                    try:
                        data = json.loads(message.content)
                        tool_results.append(data)
                    except json.JSONDecodeError:
                        pass

            # Try to extract recommendation from tool results
            code_rec = parse_agent_recommendation_from_messages(tool_results)

            if not code_rec:
                logger.warning(
                    f"No valid recommendation generated for insight {insight_id}"
                )
                return None

            # Add metadata
            code_rec.update(
                {
                    "target_repo": target_repo,
                    "target_path": target_path,
                    "github_issue_url": None,
                    "github_pr_url": None,
                    "status": "pending",
                    "generated_at": datetime.utcnow().isoformat(),
                }
            )

            # Save to database
            insight.code_recommendation = code_rec
            db.commit()

            logger.info(
                f"✓ Generated and saved code recommendation for insight {insight_id}"
            )
            return code_rec

    except Exception as e:
        logger.error(
            f"Failed to generate recommendation for insight {insight_id}: {e}",
            exc_info=True,
        )
        return None


def parse_agent_recommendation_from_messages(
    tool_results: list,
) -> Optional[Dict[str, Any]]:
    """
    Parse the agent's tool call results to extract code recommendation.

    The agent should call the output_code_recommendation tool, which returns
    a JSON string. We need to extract that JSON from the tool results.

    Args:
        tool_results: List of tool results from agent execution

    Returns:
        Dict with title, description, file_changes, priority or None
    """
    if not tool_results:
        logger.error("No tool results to parse")
        return None

    logger.info(f"Parsing {len(tool_results)} tool results")

    # Try each result to find valid recommendation
    for i, result in enumerate(tool_results):
        logger.debug(f"Processing tool result {i}: {type(result)}")

        # Extract JSON from various possible structures
        json_text = None

        if isinstance(result, dict):
            # Check for direct 'text' key (from ToolResultBlock content)
            if "text" in result and "type" in result and result["type"] == "text":
                json_text = result["text"]

            # Check for direct tool result structure
            elif "content" in result:
                content = result["content"]
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            json_text = item.get("text")
                            break
                elif isinstance(content, str):
                    json_text = content

            # Check for output field
            elif "output" in result:
                json_text = result["output"]

            # Maybe the result itself is the data
            elif all(
                key in result
                for key in ["title", "description", "file_changes", "priority"]
            ):
                # This IS the recommendation
                if validate_recommendation(result):
                    return result

        elif isinstance(result, str):
            json_text = result

        # Try to parse JSON text
        if json_text:
            logger.debug(
                f"Found JSON text in tool result {i}, length: {len(json_text)}, preview: {json_text[:200]}"
            )
            try:
                data = (
                    json.loads(json_text) if isinstance(json_text, str) else json_text
                )

                # Validate required keys
                if validate_recommendation(data):
                    logger.info(
                        f"Successfully parsed recommendation from tool result {i}"
                    )
                    return data
                else:
                    if isinstance(data, dict):
                        logger.debug(
                            f"Tool result {i} missing required keys: {list(data.keys())}"
                        )
                    else:
                        logger.debug(f"Tool result {i} is not a dict: {type(data)}")

            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON from tool result {i}: {e}")
                continue

    # No valid recommendation found
    logger.error("No valid recommendation found in tool results")
    logger.debug(f"Tool results preview: {str(tool_results)[:500]}")
    return None


def validate_recommendation(data: Any) -> bool:
    """
    Validate that data contains a valid code recommendation structure.

    Args:
        data: Data to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False

    required_keys = ["title", "description", "file_changes", "priority"]
    if not all(key in data for key in required_keys):
        return False

    # Validate file_changes is a non-empty list
    if not isinstance(data["file_changes"], list) or len(data["file_changes"]) == 0:
        logger.warning("file_changes is not a non-empty list")
        return False

    # Validate each file change
    required_change_keys = ["file", "old_content", "new_content", "diff"]
    for i, change in enumerate(data["file_changes"]):
        if not isinstance(change, dict):
            logger.warning(f"file_changes[{i}] is not a dict")
            return False
        if not all(key in change for key in required_change_keys):
            logger.warning(f"file_changes[{i}] missing required keys")
            return False

    # Validate priority
    if data["priority"] not in ["high", "medium", "low"]:
        logger.warning(f"Invalid priority: {data['priority']}")
        return False

    return True


def parse_agent_recommendation(response_text: str) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: Legacy function for backward compatibility.
    Parse the agent's response to extract code recommendation.

    The agent should call the output_code_recommendation tool, which returns
    a JSON string with title, description, file_changes, and priority.

    Args:
        response_text: Raw text response from agent (includes tool call results)

    Returns:
        Dict with title, description, file_changes, priority or None
    """
    logger.warning("Using deprecated parse_agent_recommendation function")

    # Try direct JSON parse first (tool returns valid JSON)
    try:
        data = json.loads(response_text.strip())
        if validate_recommendation(data):
            return data
        logger.warning(f"JSON parsed but invalid. Found keys: {list(data.keys())}")
        return None
    except json.JSONDecodeError:
        # Response contains non-JSON text, try to extract JSON object
        pass

    # Fallback: Extract first complete JSON object using bracket counting
    start = response_text.find("{")
    if start == -1:
        logger.error("No opening brace found in response")
        logger.debug(f"Response preview: {response_text[:200]}")
        return None

    # Count brackets to find matching closing brace
    count = 0
    end = start
    for i in range(start, len(response_text)):
        if response_text[i] == "{":
            count += 1
        elif response_text[i] == "}":
            count -= 1
            if count == 0:
                end = i + 1
                break

    if count != 0:
        logger.error(f"Unmatched braces in JSON (count={count})")
        return None

    # Extract and parse the JSON substring
    json_str = response_text[start:end]
    try:
        data = json.loads(json_str)
        if validate_recommendation(data):
            return data
        logger.warning(f"Extracted JSON but invalid. Found keys: {list(data.keys())}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extracted JSON: {e}")
        logger.error(f"Attempted to parse: {json_str[:300]}...")
        return None


async def generate_recommendations_for_simulation(
    simulation_id: int,
    target_repo: str = "snowflakedb/aura",
    target_path: str = "support-data-agent/troubleshooting",
) -> int:
    """
    Generate code recommendations for all insights in a simulation.

    Args:
        simulation_id: ID of the simulation to analyze
        target_repo: GitHub repository to analyze
        target_path: Path within the repository to focus on

    Returns:
        Number of recommendations successfully generated
    """
    from backend.database import get_db
    from backend.models.models import ImprovementSuggestion

    logger.info(f"Generating recommendations for simulation {simulation_id}")

    try:
        # Get database session
        db = next(get_db())

        # Load all insights for this simulation
        insights = (
            db.query(ImprovementSuggestion)
            .filter(ImprovementSuggestion.simulation_id == simulation_id)
            .all()
        )

        if not insights:
            logger.warning(f"No insights found for simulation {simulation_id}")
            return 0

        logger.info(f"Found {len(insights)} insights to process")

        # Generate recommendation for each insight
        success_count = 0
        for i, insight in enumerate(insights):
            try:
                rec = await generate_recommendation_for_insight(
                    insight.id, target_repo, target_path
                )
                if rec:
                    success_count += 1

                # Rate limiting: wait between insights to avoid GitHub API limits
                if i < len(insights) - 1:
                    logger.info(
                        f"Processed insight {i + 1}/{len(insights)}. Waiting 5s before next (rate limiting)..."
                    )
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Failed to process insight {insight.id}: {e}")
                continue

        logger.info(
            f"Generated {success_count}/{len(insights)} code recommendations for simulation {simulation_id}"
        )
        return success_count

    except Exception as e:
        logger.error(
            f"Failed to generate recommendations for simulation {simulation_id}: {e}",
            exc_info=True,
        )
        return 0


async def test_agent(simulation_id: int = 1):
    """
    Simple test function to verify the agent works.

    Args:
        simulation_id: Simulation ID to analyze
    """
    print("=" * 70)
    print("Code Recommendation Agent - Test (Claude Agent SDK)")
    print("=" * 70)
    print(f"\nSimulation ID: {simulation_id}")
    print("\nPrerequisites:")
    print(
        "  1. GitHub proxy running: uv run agentsim/backend/code_agent/github_proxy.py"
    )
    print("  2. Claude Code installed: npm install -g @anthropic-ai/claude-code")
    print("  3. SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD in .env")
    print("\nConnecting to GitHub proxy and Cortex...\n")

    try:
        count = await generate_recommendations_for_simulation(simulation_id)

        print(f"\n✓ Successfully generated {count} code recommendations")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.exception("Failed to run agent")

        # Check if it's a connection error
        error_str = str(e)
        if "401" in error_str or "Unauthorized" in error_str:
            print("\n⚠️  Authentication Error:")
            print("   Make sure the GitHub proxy is running with OAuth completed.")
            print("   Run: uv run agentsim/backend/code_agent/github_proxy.py")
        elif "Connection" in error_str or "refused" in error_str:
            print("\n⚠️  Connection Error:")
            print("   The GitHub proxy doesn't appear to be running.")
            print(
                "   Start it with: uv run agentsim/backend/code_agent/github_proxy.py"
            )
        elif "SNOWFLAKE" in error_str:
            print("\n⚠️  Configuration Error:")
            print("   Set SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD in .env")

        sys.exit(1)


if __name__ == "__main__":
    # Get simulation ID from command line or use default
    simulation_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    # Run the test
    asyncio.run(test_agent(simulation_id))
