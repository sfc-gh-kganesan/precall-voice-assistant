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
  - name: "purchase_order_validation_view"
    status: "new"
    database: "TEMP"
    schema: "PUBLIC"
    information: |
      Purchase order validation semantic view for invoice processing.
      Built on FINANCE.FPA.PURCHASE_ORDER_LINE table.
      Supports PO existence checks, vendor lookup, and amount validation.
    query_examples:
      - "Does purchase order PO-2024-001 exist?"
      - "What is the vendor for purchase order PO-2024-001?"
      - "Show me the total amount for purchase order PO-2024-001"
```

Write the complete semantic views catalog to `./semantic_views.yaml` following this EXACT format.

### Step 6: Create New Semantic View Definitions

For each semantic view with `status: "new"` in the catalog, suggest a name of the new semantic view that reflect its purpose. Create a corresponding YAML file following Snowflake's semantic model YAML structure:

**File:** `./new_semantic_views/[view_name].yaml`

```yaml
name: "[view_name]"
label: "[Human Readable Name]"
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

  - name: "[joined_table_name]"
    base_table:
      database: "[DATABASE_NAME]"
      schema: "[SCHEMA_NAME]"
      table: "[TABLE_NAME]"
    description: "[Purpose of this table in the model]"
    primary_key:
      columns:
        - "[primary_key_column]"

relationships:
  - name: "[relationship_name]"
    left_table: "[base_table_name]"
    right_table: "[joined_table_name]"
    relationship_columns:
      - left_column: "[join_key_left]"
        right_column: "[join_key_right]"

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

metrics:
  - name: "[metric_name]"
    synonyms:
      - "[alternative_name]"
    description: "[What this metric calculates]"
    expr: "SUM([table_name].[column_name])"  # or AVG, COUNT, etc.

  - name: "[computed_metric_name]"
    synonyms:
      - "[alternative_name]"
    description: "[What this computed metric represents]"
    expr: "SUM([table_name].[column_1]) / COUNT([table_name].[column_2])"

filters:
  - name: "[filter_name]"
    synonyms:
      - "[alternative_name]"
    description: "[What this filter does]"
    expr: "[table_name].[column_name] = '[value]'"

# Optional: Default time dimension for time-based queries
default_time_dimension: "[time_dimension_name]"

# Optional: Row access policies
# row_access_policies:
#   - policy_name: "[policy_name]"
#     description: "[description]"
```

Create one YAML file for each new semantic view under `./new_semantic_views/`

### Step 7: Validate YAML Syntax

- Before using the YAML files to create semantic views in Snowflake, make sure its syntax is correct based on Snowflake semantic view yaml structure.
- Perform thorough syntax validation:

#### 7.1 Check YAML Structure

For each YAML file in `./new_semantic_views/`, verify:

1. **Valid YAML syntax** - The file can be parsed without errors
2. **Required fields are present**:
   - `name`, `label`, `description`
   - At least one table in `tables` section
   - At least one dimension or measure

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
  - name: "purchase_amount"
    expr: "orders.PURCHASE_AMOUNT"
```

**✅ CORRECT**:
```yaml
metrics:
  - name: "total_purchase_amount"
    expr: "SUM(orders.PURCHASE_AMOUNT)"
```

Common aggregation functions: `SUM()`, `AVG()`, `COUNT()`, `MIN()`, `MAX()`, `COUNT(DISTINCT ...)`

**Metric Counting Best Practices**:
- For row counts: Use `COUNT(*)` 
- For distinct counts on primary keys: Use `COUNT(DISTINCT table.PRIMARY_KEY_COL)`
- For distinct counts on non-primary keys: Use `COUNT(DISTINCT table.UNIQUE_COL)` only if the column is truly unique
- Avoid `COUNT(DISTINCT ...)` on non-unique columns as it may not be supported

**Examples**:
```yaml
metrics:
  - name: "total_rows"
    expr: "COUNT(*)"  # ✅ Count all rows
  
  - name: "distinct_customers"
    expr: "COUNT(DISTINCT orders.CUSTOMER_ID)"  # ✅ Count unique customers
```

**CRITICAL**: Metrics should aggregate **base table columns directly**, NOT fact names:

**❌ INCORRECT** (referencing fact name):
```yaml
facts:
  - name: "line_amount"
    expr: "orders.ORDER_LINE_AMOUNT"
    data_type: "NUMBER(10,2)"

metrics:
  - name: "total_line_value"
    expr: "SUM(orders.line_amount)"  # ❌ WRONG - referencing fact name
```

**✅ CORRECT** (referencing base column):
```yaml
facts:
  - name: "line_amount"
    expr: "orders.ORDER_LINE_AMOUNT"
    data_type: "NUMBER(10,2)"

metrics:
  - name: "total_line_value"
    expr: "SUM(orders.ORDER_LINE_AMOUNT)"  # ✅ CORRECT - referencing base column
```

**NOTE**: If you need unaggregated numeric values, use `facts:` instead of `metrics:`.

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
- [ ] Tables use `base_table:` with `database:`, `schema:`, `table:` fields
- [ ] Relationships are in separate `relationships:` section (not inline joins)
- [ ] All metrics have aggregation functions in `expr` (use `facts:` for unaggregated values)
- [ ] All data types use Snowflake-specific format (VARCHAR(n), NUMBER(p,s), DATE, TIMESTAMP)
- [ ] Boolean values use correct SQL syntax (TRUE/FALSE not true/false)
- [ ] String literals in filters use single quotes
- [ ] All table references in `expr` exist in `tables` section
- [ ] `default_time_dimension` references a valid time dimension with TIMESTAMP or DATE data type
- [ ] Using `metrics:` not `measures:` for aggregated calculations

#### 7.8 Fix Any Issues

If validation finds errors:

1. Document the specific line numbers and issues found
2. Correct the syntax errors in the YAML files
3. Re-run validation to confirm fixes
4. Only proceed to deployment after all validation passes

**IMPORTANT**: Do not attempt to create semantic views in Snowflake until all YAML files pass validation.

### Step 8: Create semantic views
- Under `./new_semantic_views`, upload all YAML files to Snowflake stage
1. Create stage to upload the YAML file
- `CREATE STAGE IF NOT EXISTS EGS.TEMP.SEMANTIC_VIEWS`

2. Upload all the YAML files to the stage using SQL PUT command:
- `PUT file:[yaml_file_path] @EGS.TEMP.SEMANTIC_VIEWS AUTO_COMPRESS=FALSE OVERWRITE=TRUE`

3. Create the semantic views 
- Using the SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML stored procedure, create a separated semantic view for each yaml file under database "EGS" and schema "TEMP"

Summarize what you have done so far.