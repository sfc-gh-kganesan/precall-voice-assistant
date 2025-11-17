"""API routes for AI-generated insights."""

import asyncio
import logging
import os
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.api.schemas import ImprovementSuggestionResponse, CreateGithubIssueRequest
from backend.models.models import (
    Simulation,
    SimulationStatus,
    ImprovementSuggestion,
    Project,
)
from backend.core.insights_judge import InsightsJudge
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{simulation_id}/ai-insights", response_model=List[ImprovementSuggestionResponse]
)
async def get_ai_insights(simulation_id: int, db: Session = Depends(get_db)):
    """Get AI-generated insights for a simulation.

    If insights haven't been generated yet, they will be generated on-demand.
    """
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Simulation must be completed before generating insights",
        )

    # Check if insights already exist
    existing_insights = (
        db.query(ImprovementSuggestion)
        .filter(ImprovementSuggestion.simulation_id == simulation_id)
        .all()
    )

    if existing_insights and simulation.llm_insights_generated:
        logger.info(
            f"Returning {len(existing_insights)} cached AI insights for simulation {simulation_id}"
        )
        return existing_insights

    # Generate insights if they don't exist
    logger.info(f"Generating AI insights for simulation {simulation_id}")

    # Get Snowflake Cortex configuration from environment
    api_key = os.getenv("SNOWFLAKE_PASSWORD")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    model = os.getenv("SNOWFLAKE_CORTEX_MODEL", "claude-4-sonnet")

    if not api_key or not account:
        raise HTTPException(
            status_code=500,
            detail="Snowflake configuration missing. Set SNOWFLAKE_PASSWORD and SNOWFLAKE_ACCOUNT environment variables.",
        )

    base_url = f"https://{account}.snowflakecomputing.com/api/v2/cortex/v1"

    try:
        judge = InsightsJudge(api_key=api_key, base_url=base_url, model=model)
        insights = await judge.generate_insights(simulation_id, db)

        # Mark insights as generated
        simulation.llm_insights_generated = True
        simulation.llm_insights_generated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Successfully generated {len(insights)} AI insights for simulation {simulation_id}"
        )

        # Automatically generate code recommendations for all insights
        await _generate_code_recommendations_for_insights(simulation, insights, db)

        return insights

    except Exception as e:
        logger.error(f"Failed to generate AI insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate AI insights: {str(e)}"
        )


@router.post(
    "/{simulation_id}/ai-insights/regenerate",
    response_model=List[ImprovementSuggestionResponse],
)
async def regenerate_ai_insights(simulation_id: int, db: Session = Depends(get_db)):
    """Regenerate AI insights for a simulation (delete existing and create new ones)."""
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Simulation must be completed before generating insights",
        )

    logger.info(f"Regenerating AI insights for simulation {simulation_id}")

    # Delete existing insights
    db.query(ImprovementSuggestion).filter(
        ImprovementSuggestion.simulation_id == simulation_id
    ).delete()
    db.commit()

    # Get Snowflake Cortex configuration from environment
    api_key = os.getenv("SNOWFLAKE_PASSWORD")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    model = os.getenv("SNOWFLAKE_CORTEX_MODEL", "claude-4-sonnet")

    if not api_key or not account:
        raise HTTPException(
            status_code=500,
            detail="Snowflake configuration missing. Set SNOWFLAKE_PASSWORD and SNOWFLAKE_ACCOUNT environment variables.",
        )

    base_url = f"https://{account}.snowflakecomputing.com/api/v2/cortex/v1"

    try:
        judge = InsightsJudge(api_key=api_key, base_url=base_url, model=model)
        insights = await judge.generate_insights(simulation_id, db)

        # Mark insights as generated
        simulation.llm_insights_generated = True
        simulation.llm_insights_generated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Successfully regenerated {len(insights)} AI insights for simulation {simulation_id}"
        )

        # Automatically generate code recommendations for all insights
        await _generate_code_recommendations_for_insights(simulation, insights, db)

        return insights

    except Exception as e:
        logger.error(f"Failed to regenerate AI insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to regenerate AI insights: {str(e)}"
        )


async def _generate_code_recommendations_for_insights(
    simulation: Simulation, insights: List[ImprovementSuggestion], db: Session
):
    """Generate code recommendations for all insights using the code agent.

    Args:
        simulation: The simulation object
        insights: List of improvement suggestions
        db: Database session
    """
    # Get project configuration
    project = db.query(Project).filter(Project.id == simulation.project_id).first()
    if not project:
        logger.warning(
            f"Project {simulation.project_id} not found, skipping code recommendations"
        )
        return

    # Check if GitHub configuration exists
    if not project.github_owner or not project.github_repo:
        logger.info(
            f"No GitHub configuration for project {project.id}, skipping code recommendations"
        )
        return

    try:
        # Import code agent module
        from backend.code_agent.code_agent import generate_recommendation_for_insight

        target_repo = f"{project.github_owner}/{project.github_repo}"
        target_path = project.target_path or ""

        logger.info(f"Generating code recommendations for {len(insights)} insights")
        logger.info(f"Target: {target_repo}/{target_path}")

        # Generate recommendations for each insight (with rate limiting)
        for i, insight in enumerate(insights):
            try:
                recommendation = await generate_recommendation_for_insight(
                    insight.id, target_repo=target_repo, target_path=target_path
                )

                if recommendation:
                    logger.info(
                        f"Generated code recommendation for insight {insight.id}"
                    )
                else:
                    logger.warning(
                        f"No code recommendation generated for insight {insight.id}"
                    )

                # Rate limiting: wait between insights to avoid API limits
                if i < len(insights) - 1:
                    await asyncio.sleep(5)

            except Exception as e:
                logger.error(
                    f"Failed to generate code recommendation for insight {insight.id}: {e}"
                )
                continue

    except Exception as e:
        logger.error(f"Failed to generate code recommendations: {e}", exc_info=True)


@router.post("/{simulation_id}/insights/{insight_id}/create-github-issue")
async def create_github_issue_for_insight(
    simulation_id: int,
    insight_id: int,
    request: CreateGithubIssueRequest = Body(default=CreateGithubIssueRequest()),
    db: Session = Depends(get_db),
):
    """Create a GitHub issue for a specific insight with its code recommendation.

    Args:
        simulation_id: ID of the simulation
        insight_id: ID of the insight
        request: Optional custom title and body for the issue
        db: Database session

    Returns:
        Updated insight with github_issue_url
    """
    # Verify simulation exists
    simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Get the insight
    insight = (
        db.query(ImprovementSuggestion)
        .filter(
            ImprovementSuggestion.id == insight_id,
            ImprovementSuggestion.simulation_id == simulation_id,
        )
        .first()
    )

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Check if issue already exists
    if insight.code_recommendation and insight.code_recommendation.get(
        "github_issue_url"
    ):
        raise HTTPException(
            status_code=400,
            detail=f"GitHub issue already exists: {insight.code_recommendation['github_issue_url']}",
        )

    # Get project configuration
    project = db.query(Project).filter(Project.id == simulation.project_id).first()
    if not project or not project.github_owner or not project.github_repo:
        raise HTTPException(
            status_code=400,
            detail="Project GitHub configuration is missing. Please configure github_owner and github_repo for this project.",
        )

    try:
        # Use custom title/body if provided, otherwise build defaults
        if request.title and request.body:
            issue_title = request.title
            issue_body = request.body
            logger.info(f"Using custom title and body for insight {insight_id}")
        else:
            # Build comprehensive issue body from insight data
            issue_body = _build_github_issue_body(insight, simulation, project)
            issue_title = f"[AgentSim] {insight.title}"
            logger.info(f"Generated default title and body for insight {insight_id}")

        # Create the GitHub issue using GitHub MCP
        issue_url = await _create_github_issue_via_mcp(
            owner=project.github_owner,
            repo=project.github_repo,
            title=issue_title,
            body=issue_body,
            labels=["agentsim", f"priority-{insight.priority}", insight.category],
        )

        # Update the insight with the issue URL
        if not insight.code_recommendation:
            insight.code_recommendation = {}

        insight.code_recommendation["github_issue_url"] = issue_url
        insight.code_recommendation["status"] = "issue_created"
        db.commit()

        logger.info(f"Created GitHub issue for insight {insight_id}: {issue_url}")

        return {
            "success": True,
            "issue_url": issue_url,
            "insight_id": insight_id,
        }

    except Exception as e:
        logger.error(
            f"Failed to create GitHub issue for insight {insight_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create GitHub issue: {str(e)}",
        )


def _build_github_issue_body(
    insight: ImprovementSuggestion, simulation: Simulation, project: Project
) -> str:
    """Build comprehensive GitHub issue body with insight details and code recommendation.

    Args:
        insight: The improvement suggestion
        simulation: The simulation
        project: The project

    Returns:
        Markdown-formatted issue body
    """
    # Base issue information
    body_parts = [
        f"## {insight.category.title()} Issue",
        f"\n**Priority:** {insight.priority.upper()}",
        f"\n**Source:** AgentSim Simulation #{simulation.id}",
        f"\n### Description\n\n{insight.description}",
    ]

    # Add evidence section
    if insight.evidence:
        body_parts.append("\n### Evidence\n")

        if insight.evidence.get("pattern"):
            body_parts.append(f"**Pattern:** {insight.evidence['pattern']}\n")

        conv_ids = insight.evidence.get("conversation_ids", [])
        if conv_ids:
            body_parts.append(
                f"**Affected Conversations:** {len(conv_ids)} conversations\n"
            )
            body_parts.append(f"- IDs: {', '.join(map(str, conv_ids[:10]))}")
            if len(conv_ids) > 10:
                body_parts.append(f" ... and {len(conv_ids) - 10} more")
            body_parts.append("\n")

        personas = insight.evidence.get("affected_personas", [])
        if personas:
            body_parts.append(f"**Affected Personas:** {', '.join(personas)}\n")

    # Add code recommendation section
    if insight.code_recommendation:
        body_parts.append("\n### Proposed Code Changes\n")
        body_parts.append(f"{insight.code_recommendation.get('description', '')}\n")

        file_changes = insight.code_recommendation.get("file_changes", [])
        if file_changes:
            body_parts.append("\n#### File Changes\n")
            for i, change in enumerate(file_changes, 1):
                file_path = change.get("file", "unknown")
                body_parts.append(f"\n**{i}. {file_path}**\n")
                body_parts.append("```diff")
                body_parts.append(change.get("diff", "No diff available"))
                body_parts.append("```\n")

    # Add implementation checklist
    body_parts.append("\n### Implementation Checklist\n")

    if insight.code_recommendation and insight.code_recommendation.get("file_changes"):
        for i, change in enumerate(insight.code_recommendation["file_changes"], 1):
            file_path = change.get("file", "unknown")
            body_parts.append(f"- [ ] Update `{file_path}`")
    else:
        body_parts.append("- [ ] Investigate the issue")
        body_parts.append("- [ ] Implement the fix")

    body_parts.append("- [ ] Add/update tests")
    body_parts.append("- [ ] Run simulation to verify fix")
    body_parts.append("- [ ] Update documentation if needed")

    # Add footer with metadata
    body_parts.append(
        f"\n---\n*Generated by AgentSim from [simulation {simulation.id}]()*"
    )

    return "\n".join(body_parts)


async def _create_github_issue_via_mcp(
    owner: str, repo: str, title: str, body: str, labels: List[str] = None
) -> str:
    """Create a GitHub issue using the GitHub MCP server.

    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        title: Issue title
        body: Issue body (markdown)
        labels: List of labels to apply

    Returns:
        URL of the created issue
    """
    # Check if GitHub proxy is available
    github_proxy_url = os.getenv("GITHUB_PROXY_URL", "http://localhost:8003/mcp")

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
                "owner": owner,
                "repo": repo,
                "title": title,
                "body": body,
            }

            if labels:
                issue_data["labels"] = labels

            # Call the issue_write tool
            result = await client.call_tool("issue_write", issue_data)

            # Extract issue URL from result
            if result and hasattr(result, "content"):
                for content_block in result.content:
                    if hasattr(content_block, "text"):
                        text = content_block.text
                        # Parse the response to extract issue URL
                        # Expected format: "Created issue #123: <url>"
                        if "http" in text:
                            import re

                            urls = re.findall(r"https://github\.com/[^\s]+", text)
                            if urls:
                                return urls[0]

            # Fallback: construct URL from owner/repo
            logger.warning(
                "Could not parse issue URL from response, constructing manually"
            )
            return f"https://github.com/{owner}/{repo}/issues"

    except Exception as e:
        logger.error(f"Failed to create GitHub issue via MCP: {e}", exc_info=True)
        raise Exception(f"GitHub MCP error: {str(e)}")
