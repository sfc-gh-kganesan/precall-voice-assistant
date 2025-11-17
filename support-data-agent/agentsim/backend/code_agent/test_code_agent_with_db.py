"""
Test Code Agent with Database Simulations

Interactive script to test the code recommendation agent with actual
simulation data from your database.

Prerequisites:
    1. GitHub proxy running: uv run agentsim/backend/code_agent/github_proxy.py
    2. GITHUB_TOKEN set in .env
    3. SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD set (for Cortex)
    4. Database with simulations and insights

Usage:
    uv run agentsim/backend/code_agent/test_code_agent_with_db.py
"""

import asyncio
import logging
import sys
from typing import List, Dict, Any

from backend.database import get_db
from backend.models.models import (
    Simulation,
    ImprovementSuggestion,
    Project,
)
from code_agent import generate_recommendation_for_insight

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def list_simulations() -> List[Dict[str, Any]]:
    """
    Query and display all simulations from the database.

    Returns:
        List of simulation info dicts
    """
    db = next(get_db())

    try:
        simulations = db.query(Simulation).all()

        if not simulations:
            print("\n⚠ No simulations found in database")
            return []

        # Build simulation info list
        sim_info = []
        for sim in simulations:
            # Get project name
            project = db.query(Project).filter(Project.id == sim.project_id).first()
            project_name = project.name if project else "Unknown"

            # Count insights
            insights_count = (
                db.query(ImprovementSuggestion)
                .filter(ImprovementSuggestion.simulation_id == sim.id)
                .count()
            )

            # Count insights with code recommendations
            recs_count = (
                db.query(ImprovementSuggestion)
                .filter(
                    ImprovementSuggestion.simulation_id == sim.id,
                    ImprovementSuggestion.code_recommendation.isnot(None),
                )
                .count()
            )

            sim_info.append(
                {
                    "id": sim.id,
                    "project_name": project_name,
                    "status": sim.status.value,
                    "num_conversations": sim.num_simulations,
                    "insights_count": insights_count,
                    "recommendations_count": recs_count,
                    "created_at": sim.created_at.strftime("%Y-%m-%d %H:%M"),
                    "llm_insights_generated": sim.llm_insights_generated,
                }
            )

        return sim_info

    finally:
        db.close()


def display_simulations(simulations: List[Dict[str, Any]]):
    """Display simulations in a formatted table."""
    print("\n" + "=" * 100)
    print("AVAILABLE SIMULATIONS")
    print("=" * 100)
    print(
        f"{'ID':<5} {'Project':<25} {'Status':<12} {'Convos':<8} {'Insights':<10} {'Recs':<6} {'Created':<18}"
    )
    print("-" * 100)

    for sim in simulations:
        insights_str = f"{sim['insights_count']}"
        recs_str = f"{sim['recommendations_count']}/{sim['insights_count']}"

        print(
            f"{sim['id']:<5} {sim['project_name']:<25} {sim['status']:<12} "
            f"{sim['num_conversations']:<8} {insights_str:<10} {recs_str:<6} {sim['created_at']:<18}"
        )

    print("=" * 100)


def list_insights(simulation_id: int) -> List[ImprovementSuggestion]:
    """
    Query and display all insights for a simulation.

    Args:
        simulation_id: ID of simulation

    Returns:
        List of ImprovementSuggestion objects
    """
    db = next(get_db())

    try:
        insights = (
            db.query(ImprovementSuggestion)
            .filter(ImprovementSuggestion.simulation_id == simulation_id)
            .all()
        )

        if not insights:
            print(f"\n⚠ No insights found for simulation {simulation_id}")
            return []

        return insights

    finally:
        db.close()


def display_insights(insights: List[ImprovementSuggestion]):
    """Display insights in a formatted table."""
    print("\n" + "=" * 120)
    print("IMPROVEMENT INSIGHTS")
    print("=" * 120)
    print(f"{'ID':<5} {'Category':<20} {'Title':<40} {'Priority':<10} {'Has Rec?':<10}")
    print("-" * 120)

    for insight in insights:
        has_rec = "✓ Yes" if insight.code_recommendation else "✗ No"
        title = insight.title[:37] + "..." if len(insight.title) > 40 else insight.title

        print(
            f"{insight.id:<5} {insight.category:<20} {title:<40} "
            f"{insight.priority:<10} {has_rec:<10}"
        )

    print("=" * 120)


def display_insight_details(insight: ImprovementSuggestion):
    """Display detailed information about an insight."""
    print("\n" + "=" * 100)
    print("INSIGHT DETAILS")
    print("=" * 100)
    print(f"ID:          {insight.id}")
    print(f"Category:    {insight.category}")
    print(f"Title:       {insight.title}")
    print(f"Priority:    {insight.priority}")
    print(f"\nDescription:\n{insight.description}")
    print(f"\nEvidence:\n{insight.evidence}")

    if insight.code_recommendation:
        print("\n✓ Already has code recommendation")
        rec = insight.code_recommendation
        if isinstance(rec, dict):
            print(f"  Title: {rec.get('title', 'N/A')}")
            print(f"  Priority: {rec.get('priority', 'N/A')}")
            print(f"  Files changed: {len(rec.get('file_changes', []))}")
    else:
        print("\n✗ No code recommendation yet")

    print("=" * 100)


async def test_code_agent_for_insight(insight_id: int):
    """
    Test the code agent by generating a recommendation for a specific insight.

    Args:
        insight_id: ID of the insight to generate recommendation for
    """
    print("\n" + "=" * 100)
    print("TESTING CODE AGENT")
    print("=" * 100)
    print(f"Insight ID: {insight_id}")
    print("\nPrerequisites check:")
    print("  ✓ Database connection")
    print("  ? GitHub proxy (checking...)")
    print("  ? Snowflake Cortex credentials (checking...)")
    print()

    try:
        # Generate recommendation using the code_agent module
        recommendation = await generate_recommendation_for_insight(
            insight_id=insight_id,
            target_repo="snowflakedb/aura",
            target_path="support-data-agent/troubleshooting",
        )

        if recommendation:
            print("\n" + "=" * 100)
            print("✓ CODE RECOMMENDATION GENERATED SUCCESSFULLY!")
            print("=" * 100)
            print(f"\nTitle: {recommendation.get('title', 'N/A')}")
            print(f"Priority: {recommendation.get('priority', 'N/A')}")
            print(f"\nDescription:\n{recommendation.get('description', 'N/A')}")

            file_changes = recommendation.get("file_changes", [])
            print(f"\nFile Changes ({len(file_changes)}):")
            for i, change in enumerate(file_changes, 1):
                print(f"\n{i}. {change.get('file', 'N/A')}")
                print(f"\nOld Content:\n{change.get('old_content', 'N/A')}")
                print(f"\nNew Content:\n{change.get('new_content', 'N/A')}")
                print(f"\nDiff:\n{change.get('diff', 'N/A')}")

            print("\n" + "=" * 100)
            print("Recommendation saved to database!")
            print("=" * 100)
            return True
        else:
            print("\n✗ Failed to generate recommendation")
            return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error("Failed to generate recommendation", exc_info=True)

        # Provide helpful hints
        error_str = str(e)
        if "Connection" in error_str or "refused" in error_str:
            print("\n💡 Hint: Make sure the GitHub proxy is running:")
            print("   uv run agentsim/backend/code_agent/github_proxy.py")
        elif "SNOWFLAKE" in error_str:
            print("\n💡 Hint: Check SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD in .env")

        return False


async def interactive_mode():
    """Run interactive mode where user selects simulation and insight."""
    print("=" * 100)
    print("CODE AGENT TESTING - INTERACTIVE MODE")
    print("=" * 100)

    # Step 1: List and select simulation
    simulations = list_simulations()
    if not simulations:
        print("\nNo simulations available. Please run a simulation first.")
        return False

    display_simulations(simulations)

    print("\nSelect a simulation to test (or 'q' to quit):")
    sim_id_input = input("Simulation ID: ").strip()

    if sim_id_input.lower() == "q":
        return False

    try:
        sim_id = int(sim_id_input)
    except ValueError:
        print("Invalid simulation ID")
        return False

    # Verify simulation exists
    if not any(s["id"] == sim_id for s in simulations):
        print(f"Simulation {sim_id} not found")
        return False

    # Step 2: List insights for the selected simulation
    insights = list_insights(sim_id)
    if not insights:
        print(f"\nNo insights available for simulation {sim_id}")
        return False

    display_insights(insights)

    print("\nSelect an insight to test (or 'q' to quit):")
    insight_id_input = input("Insight ID: ").strip()

    if insight_id_input.lower() == "q":
        return False

    try:
        insight_id = int(insight_id_input)
    except ValueError:
        print("Invalid insight ID")
        return False

    # Verify insight exists
    insight = next((i for i in insights if i.id == insight_id), None)
    if not insight:
        print(f"Insight {insight_id} not found")
        return False

    # Step 3: Display insight details
    display_insight_details(insight)

    # Step 4: Confirm and test
    print("\nGenerate code recommendation for this insight?")
    confirm = input("Proceed? (y/n): ").strip().lower()

    if confirm != "y":
        print("Cancelled")
        return False

    # Step 5: Run the code agent
    success = await test_code_agent_for_insight(insight_id)
    return success


async def quick_test(insight_id: int):
    """Quick test mode - directly test a specific insight ID."""
    print("=" * 100)
    print("CODE AGENT TESTING - QUICK MODE")
    print("=" * 100)

    # Verify insight exists
    db = next(get_db())
    try:
        insight = (
            db.query(ImprovementSuggestion)
            .filter(ImprovementSuggestion.id == insight_id)
            .first()
        )

        if not insight:
            print(f"\n✗ Insight {insight_id} not found in database")
            return False

        display_insight_details(insight)

    finally:
        db.close()

    # Run the test
    success = await test_code_agent_for_insight(insight_id)
    return success


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Quick mode - test specific insight ID
        try:
            insight_id = int(sys.argv[1])
            success = asyncio.run(quick_test(insight_id))
        except ValueError:
            print(f"Invalid insight ID: {sys.argv[1]}")
            print("Usage: python test_code_agent_with_db.py [insight_id]")
            sys.exit(1)
    else:
        # Interactive mode
        success = asyncio.run(interactive_mode())

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
