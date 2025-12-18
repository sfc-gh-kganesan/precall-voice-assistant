-- Create agent registry table
CREATE TABLE IF NOT EXISTS AI_FDE.SALES_AI_PLATFORM.${AGENT_REGISTRY_TABLE} (
    agent_id STRING,
    name STRING,
    description STRING,
    version STRING,
    icon STRING,
    runtime STRING,
    entrypoint STRING,
    tags ARRAY,
    input_schema VARIANT,
    output_schema VARIANT,
    embedding VECTOR(FLOAT, 1024),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);


-- Create agent memory
CREATE TABLE IF NOT EXISTS AI_FDE.SALES_AI_PLATFORM.${AGENT_MEMORY_TABLE} (
    agent_id STRING,
    memory_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    memory_type STRING,
    content VARIANT,
    metadata VARIANT
);

-- Create agent run logs
CREATE TABLE IF NOT EXISTS AI_FDE.SALES_AI_PLATFORM.${AGENT_RUN_LOGS_TABLE} (
    run_id STRING,
    agent_id STRING,
    run_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    input VARIANT,
    output VARIANT,
    status STRING,
    error_message STRING
);
