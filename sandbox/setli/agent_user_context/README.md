# Cortex Agent invocation with session variables

This is a simple example showing how to create and call a Cortex Agent with session variables, which
can be used to enforce row based access policies.

## Instructions

1. Apply the SQL (modify the db and schema as needed) -- `snow sql -f employees.sql`
2. Call the agent -- `./run_agent.sh`
