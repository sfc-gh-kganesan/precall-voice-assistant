USE DATABASE setli;
USE SCHEMA sandbox;

-- Create the table
CREATE OR REPLACE TABLE employees (
    name VARCHAR(100),
    job_title VARCHAR(50),
    salary INTEGER
);

-- Insert dummy data
INSERT INTO employees (name, job_title, salary) VALUES
    ('Alice Chen', 'Software Engineer', 145000),
    ('Bob Martinez', 'Product Manager', 175000),
    ('Carol Johnson', 'Executive', 450000),
    ('David Kim', 'Software Engineer', 132000),
    ('Emma Wilson', 'Product Manager', 185000),
    ('Frank Thompson', 'Software Engineer', 158000),
    ('Grace Lee', 'Executive', 520000),
    ('Henry Davis', 'Product Manager', 168000),
    ('Isabel Rodriguez', 'Software Engineer', 142000),
    ('James Brown', 'Executive', 600000);

-- Create and apply row access policy
CREATE OR REPLACE ROW ACCESS POLICY employees_access_policy
AS (job_title VARCHAR) RETURNS BOOLEAN ->
    -- CEO persona can see all rows
    GETVARIABLE('PERSONA') = 'CEO'
    -- HR can see all non-executives
    OR (
        GETVARIABLE('PERSONA') = 'HR'
        AND job_title in ('Software Engineer', 'Product Manager')
    );

ALTER TABLE employees ADD ROW ACCESS POLICY employees_access_policy ON (job_title);

-- Create and apply a masking policy on the salary column
CREATE OR REPLACE MASKING POLICY employees_salary_mask
AS (val INTEGER) RETURNS INTEGER ->
    CASE
        WHEN GETVARIABLE('PERSONA') = 'CEO' THEN val
        ELSE NULL
    END;

ALTER TABLE employees MODIFY COLUMN salary SET MASKING POLICY employees_salary_mask;

-- Create semantic view
CREATE OR REPLACE SEMANTIC VIEW employees_semantic_view
  TABLES (
    employees
      PRIMARY KEY (name)
      COMMENT = 'Employee information table'
  )
  FACTS (
    employees.salary AS employees.salary
      WITH SYNONYMS = ('yearly salary', 'annual salary')
      COMMENT = 'The yearly salary of the employee'
  )
  DIMENSIONS (
    employees.name AS employees.name
      WITH SYNONYMS = ('employee name', 'full name')
      COMMENT = 'The full name of the employee',
    employees.job_title AS employees.job_title
      WITH SYNONYMS = ('role', 'position', 'title')
      COMMENT = 'The job title of the employee'
  );

-- Create the agent
CREATE OR REPLACE AGENT employees_agent
  COMMENT = 'Agent for querying employee data using natural language'
  PROFILE = '{"display_name": "Employee Data Assistant"}'
  FROM SPECIFICATION $$
  {
    "models": {
      "orchestration": "claude-4-sonnet"
    },
    "instructions": {
      "orchestration": "Use the employee_analyst tool to answer questions about employees, salaries, and job titles.",
      "response": "Provide clear, concise answers. When showing salary data, format numbers with commas for readability."
    },
    "tools": [
      {
        "tool_spec": {
          "type": "cortex_analyst_text_to_sql",
          "name": "employee_analyst",
          "description": "Query employee data including names, job titles, and salaries using natural language"
        }
      }
    ],
    "tool_resources": {
      "employee_analyst": {
        "semantic_view": "setli.sandbox.employees_semantic_view",
        "execution_environment": {
          "type": "warehouse",
          "warehouse": "COMPUTE_WH"
        },
        "query_timeout": 60
      }
    }
  }
  $$;

