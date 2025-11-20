-- Seed load test data

-- Deterministic reset
TRUNCATE TABLE ai_fde.sales_ai_platform_loadtest.seed_engagement_details;

-- Insert repeated real-world rows
INSERT INTO ai_fde.sales_ai_platform_loadtest.seed_engagement_details
(activity_id, owner_id, salesforce_account_id, activity_date)
SELECT
    activity_id,
    owner_id,
    salesforce_account_id,
    activity_date
FROM Sales.engagement360_pitch.all_engagement_details
LIMIT ${LOAD_TEST_ROW_COUNT};
