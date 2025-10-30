-- ============================================================================
-- Evals Platform - Stages Initialization
-- ============================================================================
-- This script creates stages for storing golden dataset files (PDFs, etc.)
-- Run after init_database.sql and init_tables.sql
-- ============================================================================

USE DATABASE EVALS_PLATFORM;
USE SCHEMA STAGES;

-- ============================================================================
-- Stage: GOLDEN_DATA
-- Purpose: Store golden dataset files (PDFs, images, etc.) for evaluation
-- ============================================================================
CREATE STAGE IF NOT EXISTS GOLDEN_DATA
    COMMENT = 'Storage for golden dataset files across all projects'
    DIRECTORY = (ENABLE = TRUE);

-- ============================================================================
-- Project-specific directories (logical organization)
-- ============================================================================
-- Files should be organized by project, e.g.:
-- @EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/invoice_001.pdf
-- @EVALS_PLATFORM.STAGES.GOLDEN_DATA/sales-ai-platform/transcript_001.txt
-- @EVALS_PLATFORM.STAGES.GOLDEN_DATA/support-data-agent/ticket_001.json

-- Grant permissions (adjust as needed)
-- GRANT READ, WRITE ON STAGE EVALS_PLATFORM.STAGES.GOLDEN_DATA TO ROLE evals_admin;

-- Display stage information
DESC STAGE GOLDEN_DATA;

SELECT 'Stages created successfully!' AS status;

-- ============================================================================
-- Usage Examples
-- ============================================================================
-- Upload files using SnowSQL:
--   PUT file:///path/to/invoice_001.pdf @EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/;
--
-- List files in stage:
--   LIST @EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/;
--
-- Reference in queries:
--   SELECT * FROM @EVALS_PLATFORM.STAGES.GOLDEN_DATA/invoiceiq/ (FILE_FORMAT => 'YOUR_FORMAT');

