"""Test script for conversation loader with real Snowflake data."""

import asyncio
import logging
import os

# IMPORTANT: Load .env BEFORE importing any backend modules
from dotenv import load_dotenv

load_dotenv()

# Now import backend modules (after dotenv is loaded)
from backend.database import get_db, USE_SNOWFLAKE
from backend.core.conversation_loader import ConversationLoader

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_conversation_loader():
    """Test loading conversations from Snowflake."""
    logger.info("=" * 60)
    logger.info("Testing ConversationLoader with real Snowflake data")
    logger.info("=" * 60)
    logger.info(f"USE_SNOWFLAKE: {USE_SNOWFLAKE}")
    logger.info(f"SNOWFLAKE_ACCOUNT: {os.getenv('SNOWFLAKE_ACCOUNT')}")
    logger.info(f"SNOWFLAKE_DATABASE: {os.getenv('SNOWFLAKE_DATABASE')}")
    logger.info(f"SNOWFLAKE_SCHEMA: {os.getenv('SNOWFLAKE_SCHEMA')}")

    if not USE_SNOWFLAKE:
        logger.error("❌ USE_SNOWFLAKE is not enabled! Check .env file")
        return

    # Get database session
    db = next(get_db())

    try:
        # Initialize loader
        loader = ConversationLoader(db)

        # Test 1: Load specific conversation by ID
        logger.info("\n" + "=" * 60)
        logger.info("Test 1: Load specific conversation")
        logger.info("=" * 60)
        conversation_id = "web-1763610847147-8p1ddq19i"
        logger.info(f"Loading conversation: {conversation_id}")

        scenario = await loader.get_conversation_by_id(conversation_id)

        if scenario:
            logger.info("✅ Successfully loaded conversation!")
            logger.info(f"\nPersona: {scenario.persona.name}")
            logger.info(f"Technical Level: {scenario.persona.technical_level}")
            logger.info(f"Tone: {scenario.persona.tone}")
            logger.info(f"Edge Case: {scenario.persona.edge_case}")
            logger.info(f"\nInitial Query: {scenario.initial_query[:100]}...")
            logger.info(f"Expected Outcome: {scenario.expected_outcome}")
            logger.info(f"Complexity: {scenario.complexity}")
            logger.info(f"Category: {scenario.category}")
            logger.info(f"\nMetadata: {scenario.metadata}")
        else:
            logger.error("❌ Failed to load conversation")

        # Test 2: Load recent conversations (last 7 days, limit 5)
        logger.info("\n" + "=" * 60)
        logger.info("Test 2: Load recent conversations (last 7 days, limit 5)")
        logger.info("=" * 60)

        scenarios = await loader.load_conversations(limit=5)
        logger.info(f"✅ Loaded {len(scenarios)} conversations")

        for i, s in enumerate(scenarios, 1):
            logger.info(f"\n--- Conversation {i} ---")
            logger.info(f"ID: {s.metadata.get('conversation_id')}")
            logger.info(f"Type: {s.metadata.get('interaction_type')}")
            logger.info(f"Messages: {s.metadata.get('message_count')}")
            logger.info(f"Has Errors: {s.metadata.get('has_errors')}")
            logger.info(f"Query: {s.initial_query[:80]}...")

        # Test 3: Load conversations with errors only
        logger.info("\n" + "=" * 60)
        logger.info("Test 3: Load conversations with errors only")
        logger.info("=" * 60)

        error_scenarios = await loader.load_conversations(
            include_errors_only=True, limit=3
        )
        logger.info(f"✅ Found {len(error_scenarios)} conversations with errors")

        for i, s in enumerate(error_scenarios, 1):
            logger.info(f"\n--- Error Conversation {i} ---")
            logger.info(f"ID: {s.metadata.get('conversation_id')}")
            logger.info(f"Messages: {s.metadata.get('message_count')}")
            logger.info(f"Query: {s.initial_query[:80]}...")

    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
    finally:
        db.close()

    logger.info("\n" + "=" * 60)
    logger.info("Testing complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_conversation_loader())
