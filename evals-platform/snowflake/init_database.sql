-- ============================================================================
-- Evals Platform - Database Initialization
-- ============================================================================
-- This script creates the core database and schemas for the evals platform.
-- Run this first before running other initialization scripts.
-- ============================================================================

-- Create the main evals platform database
CREATE DATABASE IF NOT EXISTS EVALS_PLATFORM
    COMMENT = 'Central database for evaluation platform serving multiple AI agent projects';

-- Create core schema for evaluation management
CREATE SCHEMA IF NOT EXISTS EVALS_PLATFORM.CORE
    COMMENT = 'Core schema for dataset management, eval runs, and results';

-- Create schema for TruLens data storage
CREATE SCHEMA IF NOT EXISTS EVALS_PLATFORM.TRULENS
    COMMENT = 'Schema for TruLens traces, feedback, and app metadata';

-- Create schema for stages
CREATE SCHEMA IF NOT EXISTS EVALS_PLATFORM.STAGES
    COMMENT = 'Schema for file stages (golden datasets, etc.)';

-- Set context for subsequent operations
USE DATABASE EVALS_PLATFORM;
USE SCHEMA CORE;

-- Grant permissions to roles (adjust as needed for your setup)
-- GRANT USAGE ON DATABASE EVALS_PLATFORM TO ROLE evals_admin;
-- GRANT ALL PRIVILEGES ON SCHEMA EVALS_PLATFORM.CORE TO ROLE evals_admin;
-- GRANT ALL PRIVILEGES ON SCHEMA EVALS_PLATFORM.TRULENS TO ROLE evals_admin;
-- GRANT ALL PRIVILEGES ON SCHEMA EVALS_PLATFORM.STAGES TO ROLE evals_admin;

SELECT 'Database and schemas created successfully!' AS status;

