"""Setup Snowflake table and Cortex Search Service for tool cache experiment."""
import logging
from shared.utils import get_snowpark_session, application_name

logger = logging.getLogger(application_name)

def setup_tool_cache():
    """Create tool cache table and Cortex Search Service."""
    session = get_snowpark_session()

    print("=" * 80)
    print("Setting up Tool Cache infrastructure in Snowflake...")
    print("=" * 80)

    # Step 1: Create table
    print("\n1. Creating tool cache table...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS AI_FDE.CACHE_EXPERIMENTS.tool_cache (
        cache_id VARCHAR(36) PRIMARY KEY DEFAULT UUID_STRING(),
        tool_name VARCHAR(100) NOT NULL,
        input_text TEXT NOT NULL,
        output_text TEXT NOT NULL,
        metadata VARIANT,
        timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """

    try:
        session.sql(create_table_sql).collect()
        print("✓ Table AI_FDE.CACHE_EXPERIMENTS.tool_cache created successfully")
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        return False

    # Step 2: Create Cortex Search Service
    print("\n2. Creating Cortex Search Service...")
    create_search_service_sql = """
    CREATE CORTEX SEARCH SERVICE IF NOT EXISTS AI_FDE.CACHE_EXPERIMENTS.tool_cache_search
    ON input_text
    ATTRIBUTES tool_name
    WAREHOUSE = AI_FDE_M
    TARGET_LAG = '1 minute'
    AS (
        SELECT
            cache_id,
            tool_name,
            input_text,
            output_text,
            metadata,
            timestamp
        FROM AI_FDE.CACHE_EXPERIMENTS.tool_cache
    )
    """

    try:
        session.sql(create_search_service_sql).collect()
        print("✓ Cortex Search Service AI_FDE.CACHE_EXPERIMENTS.tool_cache_search created successfully")
        print("  Note: Search service indexes 'input_text' with 'tool_name' as filterable attribute")
    except Exception as e:
        print(f"✗ Error creating search service: {e}")
        return False

    # Step 3: Verify setup
    print("\n3. Verifying setup...")
    try:
        # Check table
        table_check = session.sql(
            "SHOW TABLES LIKE 'tool_cache' IN AI_FDE.CACHE_EXPERIMENTS"
        ).collect()

        if table_check:
            print("✓ Table verified")
            # Show table structure
            desc = session.sql("DESCRIBE TABLE AI_FDE.CACHE_EXPERIMENTS.tool_cache").collect()
            print("  Columns:")
            for col in desc:
                print(f"    - {col['name']}: {col['type']}")
        else:
            print("✗ Table not found")
            return False

        # Check search service
        service_check = session.sql(
            "SHOW CORTEX SEARCH SERVICES LIKE 'tool_cache_search' IN AI_FDE.CACHE_EXPERIMENTS"
        ).collect()

        if service_check:
            print("✓ Search service verified")
        else:
            print("✗ Search service not found")
            return False

    except Exception as e:
        print(f"✗ Error verifying setup: {e}")
        return False

    print("\n" + "=" * 80)
    print("✅ Tool cache infrastructure setup complete!")
    print("=" * 80)
    print("\nKey features:")
    print("  - Single table for all tools with tool_name column")
    print("  - Cortex Search Service with tool_name as filterable attribute")
    print("  - Enables semantic matching within specific tool's cached results")
    print("\nYou can now run the tool cache experiment.")

    session.close()
    return True

if __name__ == "__main__":
    success = setup_tool_cache()
    exit(0 if success else 1)
