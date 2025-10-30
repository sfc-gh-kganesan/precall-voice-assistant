-- ============================================================================
-- Evals Platform - Core Tables
-- ============================================================================
-- This script creates all core tables for the evals platform.
-- Run after init_database.sql
-- ============================================================================

USE DATABASE EVALS_PLATFORM;
USE SCHEMA CORE;

-- ============================================================================
-- Table: GOLDEN_DATASETS
-- Purpose: Track evaluation datasets for different projects
-- ============================================================================
CREATE TABLE IF NOT EXISTS GOLDEN_DATASETS (
    dataset_id VARCHAR(100) PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL,
    dataset_name VARCHAR(200) NOT NULL,
    stage_location VARCHAR(500) NOT NULL,
    description VARCHAR(1000),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    metadata VARIANT,
    CONSTRAINT unique_project_dataset UNIQUE (project_name, dataset_name)
)
COMMENT = 'Catalog of golden datasets for evaluation across projects';

-- ============================================================================
-- Table: GOLDEN_RECORDS
-- Purpose: Individual golden records within datasets
-- ============================================================================
CREATE TABLE IF NOT EXISTS GOLDEN_RECORDS (
    record_id VARCHAR(100) PRIMARY KEY,
    dataset_id VARCHAR(100) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    input_data VARIANT NOT NULL,
    expected_outputs VARIANT NOT NULL,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    metadata VARIANT
)
COMMENT = 'Golden records with input data and expected outputs for evaluation. References GOLDEN_DATASETS(dataset_id)';

-- ============================================================================
-- Table: EVAL_RUNS
-- Purpose: Track evaluation run executions
-- ============================================================================
CREATE TABLE IF NOT EXISTS EVAL_RUNS (
    request_id VARCHAR(100) PRIMARY KEY,
    dataset_id VARCHAR(100) NOT NULL,
    project_name VARCHAR(100) NOT NULL,
    run_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    total_records INTEGER,
    processed_records INTEGER DEFAULT 0,
    config VARIANT,
    summary_metrics VARIANT,
    error_message VARCHAR(5000),
    completed_at TIMESTAMP_NTZ
)
COMMENT = 'Evaluation run metadata and summary results. References GOLDEN_DATASETS(dataset_id). Valid status values: running, completed, failed, cancelled';

-- ============================================================================
-- Table: EVAL_RESULTS
-- Purpose: Detailed results for each record in an eval run
-- ============================================================================
CREATE TABLE IF NOT EXISTS EVAL_RESULTS (
    result_id VARCHAR(100) PRIMARY KEY,
    request_id VARCHAR(100) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    actual_outputs VARIANT NOT NULL,
    validation_results VARIANT NOT NULL,
    trulens_record_id VARCHAR(100),
    execution_time_ms INTEGER,
    error_message VARCHAR(5000),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Detailed evaluation results for individual records. References EVAL_RUNS(request_id) and GOLDEN_RECORDS(record_id)';

-- ============================================================================
-- Views for common queries
-- ============================================================================

-- View: Recent eval runs with summary
CREATE OR REPLACE VIEW VW_RECENT_EVAL_RUNS AS
SELECT 
    er.request_id,
    er.project_name,
    gd.dataset_name,
    er.run_timestamp,
    er.status,
    er.total_records,
    er.processed_records,
    er.completed_at,
    DATEDIFF('second', er.run_timestamp, COALESCE(er.completed_at, CURRENT_TIMESTAMP())) AS duration_seconds,
    er.summary_metrics,
    er.error_message
FROM EVAL_RUNS er
JOIN GOLDEN_DATASETS gd ON er.dataset_id = gd.dataset_id
ORDER BY er.run_timestamp DESC;

-- View: Eval results with golden record context
CREATE OR REPLACE VIEW VW_EVAL_RESULTS_DETAILED AS
SELECT 
    evr.result_id,
    evr.request_id,
    er.project_name,
    er.run_timestamp,
    evr.record_id,
    gr.file_path,
    gr.input_data,
    gr.expected_outputs,
    evr.actual_outputs,
    evr.validation_results,
    evr.trulens_record_id,
    evr.execution_time_ms,
    evr.error_message,
    evr.created_at
FROM EVAL_RESULTS evr
JOIN EVAL_RUNS er ON evr.request_id = er.request_id
JOIN GOLDEN_RECORDS gr ON evr.record_id = gr.record_id;

SELECT 'Core tables and views created successfully!' AS status;

