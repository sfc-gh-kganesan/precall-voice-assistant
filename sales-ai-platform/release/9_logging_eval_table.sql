-- ============================================================================
-- Table: USE_CASE_SUMMARY_EVAL_RESULTS
-- Purpose: Store evaluation results for use case summaries.
-- ============================================================================
CREATE TABLE IF NOT EXISTS ${DATABASE}.${SCHEMA}.use_case_summary_eval_results(
    eval_id VARCHAR,
    record_creation_dttm DATETIME DEFAULT CURRENT_TIMESTAMP(),
    activity_id VARCHAR,
    owner_id VARCHAR,
    salesforce_account_id VARCHAR,
    accuracy FLOAT,
    groundedness FLOAT,
    completeness FLOAT,
    actionability FLOAT,
    eval_dttm DATETIME DEFAULT CURRENT_TIMESTAMP(),
    graph_version VARCHAR
);

-- ============================================================================
-- Table: USE_CASE_SUMMARY_EVAL_CORRECTNESS_RESULTS
-- Purpose: Store evaluation success/failure results for use case summaries.
-- ============================================================================
CREATE TABLE IF NOT EXISTS ${DATABASE}.${SCHEMA}.use_case_summary_eval_correctness_results(
    eval_id VARCHAR,
    graph_version VARCHAR,
    eval_success BOOLEAN,
    eval_error_message VARCHAR,
    error_stage VARCHAR,
    eval_dttm DATETIME DEFAULT CURRENT_TIMESTAMP()
);
