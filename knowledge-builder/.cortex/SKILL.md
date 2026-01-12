---
name: multi-env-deployment
description: Safely deploy Snowflake artifacts (Streamlit apps, SPCS services, UDFs, tables) across multiple environments (dev, staging, prod) with validation, testing, and rollback procedures.
allowed-tools: "*"
---

# Multi-Environment Deployment

**When to invoke:** Use when deploying Streamlit apps, SPCS services, UDFs, or other Snowflake artifacts across multiple environments (dev → staging → prod), or when asked to "deploy to prod", "promote to staging", "multi-environment deployment", or "deploy across accounts".

## Role
You are a Snowflake deployment automation expert specializing in safe, reliable deployments across multiple environments and accounts.

## Workflow

### 1. Environment Discovery & Validation
- List available connections: `snowflake_connections_list`
- Identify target environments (typically: dev, staging, prod)
- Verify connection access for each environment
- Check user has necessary privileges in each environment

**Common environment patterns:**
- **Same account, different databases:** `DEV_DB`, `STAGING_DB`, `PROD_DB`
- **Different accounts:** Separate Snowflake connections per environment
- **Hybrid:** Different accounts for prod, shared account for dev/staging

### 2. Artifact Type Detection
Identify what's being deployed:

**Streamlit Apps:**
- Files: `streamlit_app.py`, `environment.yml`, `requirements.txt`
- Deployment: Upload to stage → CREATE STREAMLIT (or use Snowflake CLI)
- Testing: Run locally first, then in each environment

**SPCS Services:**
- Files: `spec.yaml`, Dockerfile, application code
- Deployment: Build image → push to registry → CREATE SERVICE
- Testing: Verify service endpoints, check logs

**UDFs/Procedures:**
- Files: `.sql` files or Python/Java handlers
- Deployment: Execute CREATE FUNCTION/PROCEDURE DDL
- Testing: Run test queries in each environment

**Generic Artifacts:**
- Files: Any files to upload to stages
- Deployment: PUT files to stage
- Testing: Verify file accessibility

**Other Objects:**
- Tables, views, schemas, roles, grants
- Deployment: Execute DDL statements
- Testing: Verify object existence and accessibility

### 3. Pre-Deployment Checks

For each environment:
```sql
-- Verify target database/schema exists
SHOW DATABASES LIKE '<target_db>';
SHOW SCHEMAS LIKE '<target_schema>' IN DATABASE <target_db>;

-- Check warehouse availability
SHOW WAREHOUSES;

-- Verify current role has necessary privileges
SHOW GRANTS TO ROLE <current_role>;
```

**Security checks:**
- No secrets/credentials in code
- Environment-specific configs externalized
- Proper grants/roles defined

**Dependency checks:**
- Required stages exist
- Required tables/views available
- External dependencies accessible

### 4. Environment-Specific Configuration

**Pattern 1: Config files per environment**
```
config/
├── dev.yaml
├── staging.yaml
└── prod.yaml
```

**Pattern 2: Environment variables**
```python
import os
SNOWFLAKE_ENV = os.getenv('SNOWFLAKE_ENV', 'dev')
DB_NAME = f"{SNOWFLAKE_ENV.upper()}_DB"
```

**Pattern 3: Parameterized SQL**
```sql
-- Use variables for environment-specific values
SET db_name = 'DEV_DB';
USE DATABASE IDENTIFIER($db_name);
```

### 5. Deployment Execution

**Streamlit App Deployment:**
```bash
# For each environment connection
snow streamlit deploy \
  --connection <env_connection> \
  --database <db> \
  --schema <schema> \
  --replace \
  <app_name>

# Or use SQL
CREATE OR REPLACE STREAMLIT <app_name>
  ROOT_LOCATION = '@<stage>/<path>'
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = <warehouse>;
```

**SPCS Service Deployment:**
```bash
# Build and push image
docker build -t <image> .
docker tag <image> <registry>/<image>:<env>
docker push <registry>/<image>:<env>

# Deploy service
snow service create <service_name> \
  --connection <env_connection> \
  --compute-pool <pool> \
  --spec-path spec.yaml \
  --min-instances 1 \
  --max-instances 3
```

**UDF/Procedure Deployment:**
```sql
-- Switch to target environment
USE ROLE <role>;
USE WAREHOUSE <warehouse>;
USE DATABASE <database>;
USE SCHEMA <schema>;

-- Deploy function
CREATE OR REPLACE FUNCTION <name>(<params>)
  RETURNS <type>
  LANGUAGE PYTHON
  RUNTIME_VERSION = '3.9'
  HANDLER = '<handler>'
  PACKAGES = (<packages>)
AS
$$
<code>
$$;
```

### 6. Post-Deployment Testing

**Streamlit Apps:**
- Access app URL: `https://<account>.snowflakecomputing.com/streamlit/<app>`
- Verify UI loads
- Test key user flows
- Check data connectivity

**SPCS Services:**
```sql
-- Check service status
SHOW SERVICES LIKE '<service_name>';

-- Verify service is RUNNING
DESC SERVICE <service_name>;

-- Check logs
CALL SYSTEM$GET_SERVICE_LOGS('<service_name>', 0, '<container>', 50);

-- Test endpoints
SELECT SYSTEM$SEND_REQUEST('<service_endpoint>', 'GET', {});
```

**UDFs/Procedures:**
```sql
-- Test function
SELECT <function_name>(<test_inputs>);

-- Verify output
-- Check performance
SHOW FUNCTIONS LIKE '<function_name>';
```

### 7. Rollback Procedures

**If deployment fails:**

**For Streamlit:**
```sql
-- Restore previous version
CREATE OR REPLACE STREAMLIT <app_name>
  FROM '@<stage>/<previous_version>';
```

**For SPCS:**
```sql
-- Roll back to previous spec
ALTER SERVICE <service_name>
  FROM SPECIFICATION_FILE = '@<stage>/<previous_spec.yaml>';
```

**For UDFs:**
```sql
-- Restore from backup
-- (Keep versioned copies in stage)
CREATE OR REPLACE FUNCTION <name>
AS '<previous_version>';
```

### 8. Deployment Validation Report

Track what was deployed where:
```
Artifact: <name>
Type: <Streamlit/SPCS/UDF/etc>
Version: <version/commit>

Environments:
✅ DEV     - <connection> - <db>.<schema>.<object>
✅ STAGING - <connection> - <db>.<schema>.<object>
✅ PROD    - <connection> - <db>.<schema>.<object>

Test Results: <PASS/FAIL>
Rollback Plan: <procedure>
```

## Output Format

```
🚀 MULTI-ENVIRONMENT DEPLOYMENT

ARTIFACT: <name>
TYPE: <Streamlit/SPCS/UDF/Table/etc>
VERSION: <version>

📋 ENVIRONMENTS:
- DEV: <connection> → <target_location>
- STAGING: <connection> → <target_location>
- PROD: <connection> → <target_location>

✅ PRE-DEPLOYMENT CHECKS:
[✓] Connections validated
[✓] No secrets in code
[✓] Dependencies available
[✓] Privileges verified

🔄 DEPLOYMENT SEQUENCE:

1. DEV Environment
   Status: ✅ SUCCESS / ❌ FAILED
   Location: <db>.<schema>.<object>
   Tests: ✅ PASSED

2. STAGING Environment
   Status: ✅ SUCCESS / ❌ FAILED
   Location: <db>.<schema>.<object>
   Tests: ✅ PASSED

3. PROD Environment
   Status: ✅ SUCCESS / ❌ FAILED
   Location: <db>.<schema>.<object>
   Tests: ✅ PASSED

📝 DEPLOYMENT DETAILS:
- Command executed: <command>
- Configuration: <env-specific config>
- Dependencies: <packages/libraries>

🔗 ACCESS URLS:
- DEV: <url>
- STAGING: <url>
- PROD: <url>

⚠️  ROLLBACK PLAN:
If issues detected:
1. <rollback step>
2. <rollback step>

VERDICT: ✅ DEPLOYED / ⚠️  PARTIAL / ❌ FAILED
```

## Best Practices

- **Always deploy to dev first**, validate, then promote
- **Use consistent naming** across environments (suffixes like `_DEV`, `_PROD`)
- **Externalize configs** - no hardcoded environment values
- **Version everything** - use git tags, stage versioning
- **Test in each environment** - don't assume staging = prod
- **Automate testing** - write smoke tests for each deployment
- **Document rollback** - know how to undo before deploying
- **Use separate connections** - never deploy to prod from dev connection
- **Monitor post-deployment** - watch for errors in first hour
- **Communicate deployments** - notify stakeholders of prod changes

## Safety Gates

**MUST CHECK before PROD deployment:**
- [ ] Successfully deployed to DEV
- [ ] Successfully deployed to STAGING
- [ ] All tests passing in DEV and STAGING
- [ ] No secrets/credentials exposed
- [ ] Rollback plan documented
- [ ] Stakeholders notified (if required)
- [ ] Off-peak hours (for high-impact changes)

**AUTO-BLOCK PROD deployment if:**
- DEV or STAGING deployment failed
- Tests failing in lower environments
- Security scan found issues
- Missing required approvals (if applicable)

## Environment-Specific Considerations

**Streamlit:**
- Different warehouse sizes per environment
- Feature flags for environment-specific behavior
- Sample data in dev, full data in prod

**SPCS:**
- Different compute pools per environment
- Different image tags (`:dev`, `:staging`, `:prod`)
- Different min/max instances

**UDFs:**
- Same code, different data access patterns
- Performance testing in staging before prod
- Consider warehouse size for expensive UDFs

## Tools & Commands

**Snowflake CLI:**
```bash
snow streamlit deploy --connection <env>
snow service create --connection <env>
snow stage copy @source @destination --connection <env>
```

**SQL-based:**
```sql
-- Use connection context
-- Execute DDL/DML
-- Verify deployment
```

**Git integration:**
```bash
# Tag releases
git tag -a v1.0.0-prod -m "Production release"
git push origin v1.0.0-prod
```
