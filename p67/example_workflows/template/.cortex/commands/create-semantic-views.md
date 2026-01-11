---
name: create-semantic-views
allowed-tools: Bash(*)
description: Analyze workflow spec and create semantic views needed for implementation
---


# Generate Semantic View Proposal

You are a semantic view expert. Your task is to analyze the workflow specification and create necessary semantic views for implementation.

## Instructions

### Step 1: Read the Workflow Specification
Read the file `./workflow_spec.json` to understand the general workflow execution path:
- What queries will be performed.  Read the description of the nodes with type "query_node".

### Step 2: Identify Required Data Elements
From the node of type "query_node", extract:
- **Tables/Views needed**: Read the attribute "description", determine What database tables or views contain the required data
- **Dimensions**: Read the attribute "description" and "question", determine Categorical fields needed for filtering, grouping
- **Facts**: Read the attribute "description", "question", "input_parameters" and "output_parameters", identify numeric/measurable fields for calculations or aggregations (e.g., order_total, quantity, price)
- **Time Dimensions**: Date/timestamp fields for temporal filtering or analysis (e.g., order_date, created_at)
- **Key fields**: Primary keys or unique identifiers needed for lookups (e.g., order_id, customer_id)

### Step 3: Discover Existing Available Semantic Views

Query the user's Snowflake account to discover existing semantic views that are useful:

```sql
-- List all semantic views in the account
SHOW SEMANTIC VIEWS;

-- For each semantic model, describe its structure
DESCRIBE SEMANTIC VIEW <view_name>;
```

Alternatively, query INFORMATION_SCHEMA:

```sql
-- Find semantic models
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.SEMANTIC_MODELS;

-- Get semantic model details
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.SEMANTIC_MODEL_OBJECTS
WHERE SEMANTIC_MODEL_NAME = '<model_name>';
```

If you don't have direct SQL access, ask the user to provide:
- List of available semantic models
- Their table structures
- Available dimensions and facts

### Step 4: Query User's Database Schema

To understand what tables are available, query or ask about:

```sql
-- List databases and schemas
SHOW DATABASES;
SHOW SCHEMAS IN DATABASE <database_name>;

-- List tables in relevant schemas
SHOW TABLES IN SCHEMA <database>.<schema>;

-- Describe table structure
DESCRIBE TABLE <database>.<schema>.<table_name>;
```

### Step 5: Evaluate existing semantic views and propose new semantic views
- If you find any existing semantic views that can answer some questions in this workflow, include them in the proposed semantic views.
- Keep track of those questions in the workflow that cannot be answered by existing semantic views, propose new semantic views to cover that.
- Create a semantic views catalog in `./semantic_views.yaml` that documents all semantic views you propose for this workflow. This file should include existing semantic views that can be used and also new (non-existent) semantic views that need to be created.

#### Structure of semantic_views.yaml
- For any new semantic views, they should be created in database "EGS" and schema "TEMP"

**CRITICAL**: The semantic_views.yaml file MUST follow this EXACT structure. Do NOT add any other fields or sections beyond what is shown here.

**REQUIRED FORMAT** - This is the ONLY valid format:

```yaml
# List of semantic views (both existing and new)
semantic_views:
  - name: "[semantic_view_name]"
    status: "existing"  # or "new" if needs to be created
    database: "[database_name]"
    schema: "[schema_name]"
    information: |
      [Description of what information this semantic view holds.
      Include what business domain it covers, what tables it joins,
      and what analytical capabilities it provides.]
    query_examples:
      - "What is the total revenue by customer for last quarter?"
      - "Show me all pending orders for customer ID 12345"
      - "Calculate average order value by product category"

  - name: "[another_semantic_view_name]"
    status: "new"
    database: "EGS"
    schema: "TEMP"
    information: |
      [Description for new semantic view that needs to be created]
    query_examples:
      - "[Example question 1]"
      - "[Example question 2]"
      - "[Example question 3]"
```

**IMPORTANT RULES**:
1. ✅ MUST have top-level key `semantic_views:` (plural) containing a list
2. ✅ Each semantic view MUST have exactly these 5 fields: `name`, `status`, `database`, `schema`, `information`, `query_examples`
3. ✅ `status` must be either "existing" or "new"
4. ✅ `query_examples` must be a list of natural language questions
5. ❌ DO NOT add fields like: `workflow_name`, `query_nodes`, `existing_semantic_views_evaluation`, `recommended_new_semantic_views`, `alternative_data_sources`, `implementation_notes`, `validation_requirements`
6. ❌ DO NOT add any analysis or metadata sections - ONLY the semantic_views list

**Example of correct semantic_views.yaml**:
```yaml
# List of semantic views (both existing and new)
semantic_views:
  - name: "customer_order_analysis_view"
    status: "new"
    database: "EGS"
    schema: "TEMP"
    information: |
      Customer order analysis semantic view for workflow processing.
      Built on SALES.ANALYTICS.ORDER_DETAILS table.
      Supports order lookup, customer information retrieval, and order amount validation.
    query_examples:
      - "Does order ORD-2024-001 exist?"
      - "What is the customer name for order ORD-2024-001?"
      - "Show me the total amount for order ORD-2024-001"
```

Write the complete semantic views catalog to `./semantic_views.yaml` following this EXACT format.

### Step 6: Create New Semantic View Definitions

For each semantic view with `status: "new"` in the catalog, suggest a name of the new semantic view that reflect its purpose. Create a corresponding YAML file following Snowflake's semantic model YAML structure:

**File:** `./new_semantic_views/[view_name].yaml`

**CRITICAL**: The correct Snowflake semantic model structure requires:
1. ✅ Use `description` field (NOT `label` - that field is invalid)
2. ✅ Nest `dimensions`, `time_dimensions`, `facts` inside each table definition (NOT at model level)
3. ✅ Only `verifiedQueries` (NOT `verified_queries`) is valid for example queries

**✅ CORRECT Structure:**

```yaml
name: "[view_name]"

description: |
  [Detailed description of what this semantic view represents
  and what business questions it can answer]

tables:
  - name: "[base_table_name]"
    base_table:
      database: "[DATABASE_NAME]"
      schema: "[SCHEMA_NAME]"
      table: "[TABLE_NAME]"
    description: "[Purpose of this table in the model]"
    primary_key:
      columns:
        - "[primary_key_column]"

    # ✅ IMPORTANT: dimensions, time_dimensions, facts are INSIDE the table definition
    dimensions:
      - name: "[dimension_name]"
        synonyms:
          - "[alternative_name_1]"
          - "[alternative_name_2]"
        description: "[What this dimension represents]"
        expr: "[table_name].[column_name]"
        data_type: "VARCHAR(100)"  # or "NUMBER(10,2)", "DATE", etc.
        unique: false  # true if this is a unique identifier

    time_dimensions:
      - name: "[time_dimension_name]"
        synonyms:
          - "[alternative_name]"
        description: "[What this time dimension represents]"
        expr: "[table_name].[column_name]"
        data_type: "TIMESTAMP"  # or "DATE"

    facts:
      - name: "[fact_name]"
        synonyms:
          - "[alternative_name]"
        description: "[What this fact represents - unaggregated numeric value]"
        expr: "[table_name].[column_name]"
        data_type: "NUMBER(10,2)"

  - name: "[joined_table_name]"
    base_table:
      database: "[DATABASE_NAME]"
      schema: "[SCHEMA_NAME]"
      table: "[TABLE_NAME]"
    description: "[Purpose of this table in the model]"
    primary_key:
      columns:
        - "[primary_key_column]"

    dimensions:
      - name: "[another_dimension]"
        description: "[Description]"
        expr: "[joined_table_name].[column_name]"
        data_type: "VARCHAR(100)"

# Relationships are defined at the model level (not inside tables)
relationships:
  - name: "[relationship_name]"
    left_table: "[base_table_name]"
    right_table: "[joined_table_name]"
    relationship_columns:
      - left_column: "[join_key_left]"
        right_column: "[join_key_right]"

# Metrics are defined at the model level (OPTIONAL - see warning below)
metrics:
  - name: "[metric_name]"
    synonyms:
      - "[alternative_name]"
    description: "[What this metric calculates]"
    expr: "COUNT(*)"  # Only COUNT(*) is guaranteed to work. SUM/AVG may fail validation.

# Optional: Verified queries for testing (use camelCase: verifiedQueries)
verifiedQueries:
  - name: "[query_name]"
    question: "[Example natural language question]"
    sql: |
      SELECT [columns]
      FROM [database].[schema].[table] as [table_alias]
      WHERE [conditions]

# Optional: Custom instructions for Cortex Analyst
# customInstructions: |
#   [Instructions for how to interpret this semantic model]
```

**❌ COMMON MISTAKES TO AVOID:**

1. **❌ Using `label` field:**
```yaml
name: "my_view"
label: "My View"  # ❌ WRONG - this field doesn't exist
```
Use `description` instead.

2. **❌ Dimensions/facts at model level:**
```yaml
tables:
  - name: "orders"
    base_table: ...

dimensions:  # ❌ WRONG - dimensions at model level
  - name: "order_id"
```
Dimensions must be nested inside their table.

3. **❌ Using `verified_queries` (snake_case):**
```yaml
verified_queries:  # ❌ WRONG - should be camelCase
  - name: "test"
```
Use `verifiedQueries` (camelCase).

4. **❌ Metrics without aggregation:**
```yaml
metrics:
  - name: "amount"
    expr: "orders.AMOUNT"  # ❌ WRONG - no aggregation
```
Metrics MUST have aggregation functions like `SUM(orders.AMOUNT)`.

Create one YAML file for each new semantic view under `./new_semantic_views/`

### Step 7: Validate YAML Syntax

**CRITICAL**: Before deploying to Snowflake, validate each YAML file to catch errors early. Use the semantic view reflection/validation tool available in your environment.

#### 7.0 Validate Using Reflection Tool

For each YAML file, run validation to check if it conforms to Snowflake's semantic model schema:

**Common validation errors and fixes:**

1. **Error: "has no field named 'label'"**
   - ❌ Remove the `label` field
   - ✅ Use `description` instead

2. **Error: "has no field named 'dimensions'"** (at model level)
   - ❌ Dimensions are at the wrong level
   - ✅ Move dimensions, time_dimensions, facts inside the `tables` section

3. **Error: "has no field named 'verified_queries'"**
   - ❌ Wrong case format
   - ✅ Use `verifiedQueries` (camelCase)

4. **Error: "Unsupported expression in the definition of derived metric [METRIC_NAME]"**
   - Caused by: `COUNT(DISTINCT ...)`, `SUM(table.column)`, or complex expressions
   - **Fix**: Remove the metric entirely or use only `COUNT(*)`
   - Define numeric values as facts instead - Cortex Analyst will aggregate them at query time

**Validation workflow:**
1. Read the YAML file
2. Run validation/reflection
3. If errors occur, read the error message carefully - it will list valid fields
4. Fix the YAML file based on the error
5. Re-validate until successful
6. Only proceed to Step 8 after ALL files validate successfully

#### 7.1 Check YAML Structure

For each YAML file in `./new_semantic_views/`, verify:

1. **Valid YAML syntax** - The file can be parsed without errors
2. **Required fields are present**:
   - `name`, `description` (NOT `label`)
   - At least one table in `tables` section
   - At least one dimension or fact (nested inside tables)

#### 7.2 Validate Relationships Syntax

**CRITICAL**: Verify that all table relationships use the correct Snowflake semantic model format.

**❌ INCORRECT format** (common mistake - inline joins):
```yaml
tables:
  - name: "orders"
    joins:
      - type: "left"
        left_table: "orders"
        left_column: "ORDER_ID"
```

**✅ CORRECT format** (separate relationships section):
```yaml
tables:
  - name: "orders"
    base_table:
      database: "DB"
      schema: "SCHEMA"
      table: "ORDERS"
    primary_key:
      columns:
        - "ORDER_ID"

relationships:
  - name: "orders_to_customers"
    left_table: "orders"
    right_table: "customers"
    relationship_columns:
      - left_column: "CUSTOMER_ID"
        right_column: "CUSTOMER_ID"
```

Check that relationships are defined at the model level, not inline within tables.

#### 7.3 Validate Metric Expressions

All metrics must include aggregation functions in their `expr` field:

**❌ INCORRECT**:
```yaml
metrics:
  - name: "order_amount"
    expr: "orders.AMOUNT"  # ❌ Missing aggregation
```

**✅ CORRECT**:
```yaml
metrics:
  - name: "total_order_amount"
    expr: "SUM(orders.AMOUNT)"  # ✅ Uses aggregation
```

**⚠️ METRICS WARNING**: Many metric expressions fail with "Unsupported expression" errors.

**What works**:
- ✅ `COUNT(*)` - Always safe

**What often fails**:
- ❌ `COUNT(DISTINCT column)` - Not supported
- ❌ `SUM(table.column)` - Often causes errors
- ❌ `AVG()`, complex expressions - Limited support

**Recommended approach**:
```yaml
facts:
  - name: "order_amount"
    expr: "orders.AMOUNT"
    data_type: "NUMBER(10,2)"

metrics:
  - name: "row_count"
    expr: "COUNT(*)"  # Use COUNT(*) only, or omit metrics entirely
```

Cortex Analyst automatically aggregates facts at query time, making metrics optional.

#### 7.4 Validate Data Types

Ensure all dimensions, time_dimensions, facts, and metrics use valid Snowflake data types:

**Valid dimension data types**: `VARCHAR(n)`, `NUMBER(p,s)`, `DATE`, `TIMESTAMP`, `BOOLEAN`
**Valid time_dimension data types**: `DATE`, `TIMESTAMP`, `TIMESTAMP_NTZ`, `TIMESTAMP_LTZ`
**Valid fact data types**: `NUMBER(p,s)`, `FLOAT`, `INTEGER`
**Valid metric data types**: Inferred from aggregation expression (no data_type field needed)

#### 7.5 Check Boolean and String Literals

In filter expressions and dimensions:

**For boolean comparisons**:
```yaml
# Use uppercase TRUE/FALSE for Snowflake boolean columns
expr: "product_inspections.IS_RESELLABLE = TRUE"

# Or use appropriate string/numeric representation if stored differently
expr: "product_inspections.IS_RESELLABLE = 'true'"  # if stored as text
expr: "product_inspections.IS_RESELLABLE = 1"       # if stored as number
```

**For string comparisons**, always use single quotes:
```yaml
expr: "orders.ORDER_STATUS = 'COMPLETED'"
```

#### 7.6 Validate Table References

Ensure all `expr` fields reference tables that are defined in the `tables` section:

```yaml
# If you reference "orders.PURCHASE_DATE" in a dimension,
# make sure "orders" exists in the tables section
```

#### 7.7 Create Validation Checklist

For each YAML file, verify:

- [ ] YAML syntax is valid (no parsing errors)
- [ ] ✅ Uses `description` field (NOT `label` - that field is invalid)
- [ ] ✅ Dimensions, time_dimensions, facts are nested INSIDE each table (NOT at model level)
- [ ] ✅ Uses `verifiedQueries` (camelCase, NOT `verified_queries` snake_case)
- [ ] Tables use `base_table:` with `database:`, `schema:`, `table:` fields
- [ ] Relationships are in separate `relationships:` section (not inline joins)
- [ ] Metrics use only `COUNT(*)` or are omitted entirely (SUM/AVG/COUNT DISTINCT often fail)
- [ ] Numeric values are defined as **facts**, not metrics
- [ ] All data types use Snowflake-specific format (VARCHAR(n), NUMBER(p,s), DATE, TIMESTAMP)
- [ ] Boolean values use correct SQL syntax (TRUE/FALSE not true/false)
- [ ] String literals in filters use single quotes
- [ ] All table references in `expr` exist in `tables` section
- [ ] Using `metrics:` not `measures:` for aggregated calculations

#### 7.8 Fix Any Issues

If validation finds errors:

1. Document the specific line numbers and issues found
2. Correct the syntax errors in the YAML files
3. Re-run validation to confirm fixes
4. Only proceed to deployment after all validation passes

**IMPORTANT**: Do not attempt to create semantic views in Snowflake until all YAML files pass validation.

### Step 8: Create Semantic Views in Snowflake

**IMPORTANT**: Use the `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML` stored procedure with inline YAML content. Do NOT use stages or PUT commands.

#### 8.1 Read Each YAML File

For each validated YAML file in `./new_semantic_views/`, read the complete file content.

#### 8.2 Create Semantic View Using Stored Procedure

Use the following SQL pattern to create each semantic view:

```sql
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'EGS.TEMP',  -- Target database.schema
  $$
[PASTE FULL YAML CONTENT HERE]
  $$
);
```

**Example:**

```sql
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'EGS.TEMP',
  $$
name: "customer_order_view"
description: |
  Customer order semantic view for workflow processing.
  Built on SALES.ANALYTICS.ORDERS table.

tables:
  - name: "orders"
    base_table:
      database: "SALES"
      schema: "ANALYTICS"
      table: "ORDERS"
    description: "Customer orders with details"
    primary_key:
      columns:
        - "ORDER_ID"

    dimensions:
      - name: "order_id"
        synonyms:
          - "order_number"
          - "order_ref"
        description: "The unique order identifier"
        expr: "orders.ORDER_ID"
        data_type: "VARCHAR(16777216)"
        unique: true

    facts:
      - name: "order_amount"
        synonyms:
          - "total_amount"
        description: "Order total amount"
        expr: "orders.AMOUNT"
        data_type: "NUMBER(38,2)"

verifiedQueries:
  - name: "check_order_exists"
    question: "Does order ORD-12345 exist?"
    sql: |
      SELECT
        CASE WHEN COUNT(*) > 0 THEN TRUE ELSE FALSE END as order_exists,
        orders.ORDER_ID as order_id
      FROM SALES.ANALYTICS.ORDERS as orders
      WHERE orders.ORDER_ID = 'ORD-12345'
      GROUP BY orders.ORDER_ID
  $$
);
```

**Expected Output:**
```
Semantic view was successfully created.
```

#### 8.3 Verify Creation

After creating each semantic view, verify it was created successfully:

```sql
-- List all semantic views in the schema
SHOW SEMANTIC VIEWS IN SCHEMA EGS.TEMP;

-- Describe the specific semantic view to see all components
DESCRIBE SEMANTIC VIEW EGS.TEMP.[VIEW_NAME];
```

#### 8.4 Repeat for All YAML Files

Create one semantic view for each YAML file in `./new_semantic_views/` directory.

#### 8.5 Summary Report

After all semantic views are created, provide a summary:

```
✅ Semantic Views Created Successfully

Created the following semantic views:

1. EGS.TEMP.CUSTOMER_ORDER_VIEW
   - Tables: 1 (orders based on SALES.ANALYTICS.ORDERS)
   - Dimensions: 7
   - Facts: 4
   - Metrics: 3
   - Verified Queries: 5

2. EGS.TEMP.[ANOTHER_VIEW_NAME]
   - Tables: [count]
   - Dimensions: [count]
   - Facts: [count]
   - Metrics: [count]
   - Verified Queries: [count]

All semantic views are now available in Snowflake for use with Cortex Analyst.
```

**Troubleshooting:**

If you encounter errors during creation:
1. **"Field not found" error**: Check that you're not using invalid fields like `label`, and that dimensions/facts are nested inside tables
2. **"Unable to parse yaml to protobuf"**: Validate the YAML structure matches the schema (Step 7)
3. **"Base table not found"**: Verify the database, schema, and table names are correct and accessible
4. **"SQL compilation error" in verified queries**: Test the SQL separately to ensure it's valid
5. **"Unsupported expression in the definition of derived metric"**: Remove the failing metric. Use only `COUNT(*)` or omit metrics entirely. Define numeric values as facts instead.

Summarize what you have done so far.