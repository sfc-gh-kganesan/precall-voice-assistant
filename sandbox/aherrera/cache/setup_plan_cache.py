"""Setup Snowflake table and Cortex Search Service for plan cache experiment."""
import logging
from shared.utils import get_snowpark_session, application_name

logger = logging.getLogger(application_name)

def setup_plan_cache():
    """Create plan cache table and Cortex Search Service."""
    session = get_snowpark_session()

    print("=" * 80)
    print("Setting up Plan Cache infrastructure in Snowflake...")
    print("=" * 80)

    # Step 1: Create table
    print("\n1. Creating cache table...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS AI_FDE.CACHE_EXPERIMENTS.plan_cache (
        query_id VARCHAR(32) PRIMARY KEY,
        query_text TEXT NOT NULL,
        available_tools TEXT,
        plan_response VARIANT NOT NULL,
        metadata VARIANT,
        timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """

    try:
        session.sql(create_table_sql).collect()
        print("✓ Table AI_FDE.CACHE_EXPERIMENTS.plan_cache created successfully")
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        return False

    # Step 2: Create Cortex Search Service
    print("\n2. Creating Cortex Search Service...")
    create_search_service_sql = """
    CREATE CORTEX SEARCH SERVICE IF NOT EXISTS AI_FDE.CACHE_EXPERIMENTS.plan_cache_search
    ON query_text
    WAREHOUSE = AI_FDE_M
    TARGET_LAG = '1 minute'
    AS (
        SELECT
            query_id,
            query_text,
            available_tools,
            plan_response,
            metadata,
            timestamp
        FROM AI_FDE.CACHE_EXPERIMENTS.plan_cache
    )
    """

    try:
        session.sql(create_search_service_sql).collect()
        print("✓ Cortex Search Service AI_FDE.CACHE_EXPERIMENTS.plan_cache_search created successfully")
    except Exception as e:
        print(f"✗ Error creating search service: {e}")
        return False

    # Step 3: Verify setup
    print("\n3. Verifying setup...")
    try:
        # Check table
        table_check = session.sql(
            "SHOW TABLES LIKE 'plan_cache' IN AI_FDE.CACHE_EXPERIMENTS"
        ).collect()

        if table_check:
            print("✓ Table verified")
        else:
            print("✗ Table not found")
            return False

        # Check search service
        service_check = session.sql(
            "SHOW CORTEX SEARCH SERVICES LIKE 'plan_cache_search' IN AI_FDE.CACHE_EXPERIMENTS"
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
    print("✅ Plan cache infrastructure setup complete!")
    print("=" * 80)
    print("\nYou can now run the plan cache experiment.")

    session.close()
    return True

if __name__ == "__main__":
    success = setup_plan_cache()
    exit(0 if success else 1)
