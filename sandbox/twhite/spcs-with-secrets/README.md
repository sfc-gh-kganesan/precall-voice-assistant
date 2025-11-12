# Snowflake Container Services (SPCS) - Enhanced API Demo

This project demonstrates how to use **Snowflake Container Services (SPCS)** with:
- **Secrets management** for secure credential handling
- **Network rules** and **External Access Integrations** for controlled API access
- **Rate limiting/throttling** using token bucket algorithm
- **File persistence** to Snowflake internal stages
- A **Rust application** running in a containerized job service

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Snowflake Account                             │
│                                                                  │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐           │
│  │  Secrets   │   │  Network   │   │   Stage      │           │
│  │  - API Key │   │   Rules    │   │  (Results)   │           │
│  └─────┬──────┘   └──────┬─────┘   └──────▲───────┘           │
│        │                 │                 │                    │
│        │    ┌────────────┴──────┐         │                    │
│        └───►│ External Access   │         │                    │
│             │   Integration     │         │                    │
│             └────────┬──────────┘         │                    │
│                      │                    │                    │
│  ┌───────────────────▼────────────────────┴──────────────┐    │
│  │         Container Service (Job)                       │    │
│  │  ┌────────────────────────────────────────────────┐   │    │
│  │  │  Rust Application                              │   │    │
│  │  │  1. Reads secrets from env vars                │   │    │
│  │  │  2. Makes rate-limited API calls (2 req/s)     │   │    │
│  │  │  3. Tracks metrics (timing, status)            │   │    │
│  │  │  4. Persists results to JSON                   │   │    │
│  │  │  5. Uploads to Snowflake stage                 │   │    │
│  │  └────────────────────────────────────────────────┘   │    │
│  └───────────────────────────────────────────────────────┘    │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
                 ┌──────────────────┐
                 │  External APIs   │
                 │  (Public)        │
                 └──────────────────┘
```

## 📋 Prerequisites

1. **Snowflake Account** with:
   - ACCOUNTADMIN role (or appropriate privileges)
   - Snowflake Container Services enabled
   - A warehouse for SQL operations

2. **Local Development Tools**:
   - Docker Desktop
   - SnowSQL or Snowflake CLI
   - Rust and Cargo (optional, for local testing)

## 🚀 Quick Start

### Step 1: Clone and Navigate

```bash
cd sandbox/twhite/spcs-with-secrets
```

### Step 2: Set Up Snowflake Resources

Run the SQL setup script in your Snowflake account:

```bash
# Using SnowSQL
snow sql -f setup.sql

# Or copy/paste the contents into Snowsight
```

This creates:
- Database: `SPCS_DEMO`
- Schema: `API_JOBS`
- Image repository: `spcs_demo_repo`
- Internal stage: `api_results_stage` (for file persistence)
- Network rule: `allow_public_api`
- External access integration: `api_access_integration`
- Secrets: `api_key_secret`, `basic_auth_secret`
- Compute pool: `job_pool`

### Step 3: Build and Push Docker Image

```bash
# 1. Build the Docker image
docker build -t spcs-api-demo:latest .

# 2. Get your Snowflake repository URL
# Run in Snowflake: SHOW IMAGE REPOSITORIES;
# Example output: <org>-<account>.registry.snowflakecomputing.com/spcs_demo/api_jobs/spcs_demo_repo

# 3. Login to Snowflake registry
docker login <your-org>-<your-account>.registry.snowflakecomputing.com

# 4. Tag the image
docker tag spcs-api-demo:latest \
  <your-org>-<your-account>.registry.snowflakecomputing.com/spcs_demo/api_jobs/spcs_demo_repo/spcs-api-demo:latest

# 5. Push to Snowflake
docker push \
  <your-org>-<your-account>.registry.snowflakecomputing.com/spcs_demo/api_jobs/spcs_demo_repo/spcs-api-demo:latest
```

### Step 4: Create the Service

Wait for the compute pool to be ACTIVE or IDLE:

```sql
SHOW COMPUTE POOLS;
```

Then create the service:

```sql
USE DATABASE SPCS_DEMO;
USE SCHEMA API_JOBS;

CREATE OR REPLACE SERVICE api_job_service
  IN COMPUTE POOL job_pool
  FROM SPECIFICATION $$
spec:
  containers:
  - name: api-client
    image: /spcs_demo/api_jobs/spcs_demo_repo/spcs-api-demo:latest
    env:
      API_KEY:
        secretKeyRef:
          key: api_key_secret
      API_ENDPOINT: "https://api.publicapis.org/entries"
      NUM_REQUESTS: "10"
      RATE_LIMIT: "2"
      STAGE_PATH: "@api_results_stage"
    volumeMounts:
    - name: output
      mountPath: /tmp/spcs_output
  volumes:
  - name: output
    source: "@api_results_stage"
  externalAccessIntegrations:
  - api_access_integration
$$
MIN_INSTANCES = 1
MAX_INSTANCES = 1
COMMENT = 'Job service for rate-limited API requests with file persistence';
```

### Step 5: Monitor the Service

```sql
-- Check service status
SHOW SERVICES IN SCHEMA;

-- View service details
DESC SERVICE api_job_service;

-- Check service logs (wait a moment for the job to run)
CALL SYSTEM$GET_SERVICE_LOGS('api_job_service', 0, 'api-client');

-- Check service status
CALL SYSTEM$GET_SERVICE_STATUS('api_job_service');

-- View persisted result files
LIST @api_results_stage;

-- Query results from a specific run
SELECT $1 FROM @api_results_stage/api_results_<run-id>.json 
  (FILE_FORMAT => (TYPE = JSON));
```

## 🧪 Testing Locally (Optional)

You can test the Rust application locally before deploying to SPCS:

```bash
# Set environment variables
export API_KEY="test-key-12345"
export API_ENDPOINT="https://api.publicapis.org/entries"
export NUM_REQUESTS="5"
export RATE_LIMIT="2"
export STAGE_PATH="@api_results_stage"

# Run with cargo
cargo run

# Or build and run with Docker
docker build -t spcs-api-demo:latest .
docker run \
  -e API_KEY="test-key-12345" \
  -e API_ENDPOINT="https://api.publicapis.org/entries" \
  -e NUM_REQUESTS="5" \
  -e RATE_LIMIT="2" \
  -e STAGE_PATH="@api_results_stage" \
  spcs-api-demo:latest
```

## 📝 How It Works

### 1. Secrets Management

The application reads secrets from environment variables that Snowflake injects:

```rust
let api_key = env::var("API_KEY")
    .context("API_KEY environment variable not found")?;
```

In the service specification:

```yaml
env:
  API_KEY:
    secretKeyRef:
      key: api_key_secret  # References Snowflake secret
```

### 2. Network Rules

The network rule defines which external hosts the container can access:

```sql
CREATE NETWORK RULE allow_public_api
  TYPE = HOST_PORT
  MODE = EGRESS
  VALUE_LIST = (
    'api.publicapis.org:443',
    'httpbin.org:443'
  );
```

### 3. External Access Integration

Links the network rule to the service:

```sql
CREATE EXTERNAL ACCESS INTEGRATION api_access_integration
  ALLOWED_NETWORK_RULES = (allow_public_api)
  ENABLED = TRUE;
```

### 4. Rate Limiting

The application uses the `governor` crate to implement token bucket rate limiting:

```rust
use governor::{Quota, RateLimiter};

// Create rate limiter: 2 requests per second
let quota = Quota::per_second(nonzero!(2u32));
let limiter = Arc::new(RateLimiter::direct(quota));

// Wait for permission before each request
limiter.until_ready().await;
make_api_request(&endpoint, &key).await?;
```

This ensures API calls respect rate limits, preventing throttling by external services. The rate limit is configurable via the `RATE_LIMIT` environment variable.

### 5. File Persistence to Snowflake Stage

Results are persisted to a Snowflake internal stage:

1. **Local file creation**: Results are saved as JSON to `/tmp/spcs_output/`
2. **Stage upload**: Files are uploaded using the Snowflake CLI:
   ```rust
   Command::new("snow")
       .args(["stage", "put", file_path, "@api_results_stage", "--overwrite"])
       .output()?;
   ```
3. **Volume mounting**: The service spec mounts the stage as a volume:
   ```yaml
   volumeMounts:
   - name: output
     mountPath: /tmp/spcs_output
   volumes:
   - name: output
     source: "@api_results_stage"
   ```

Results include:
- Request ID and timestamp
- Duration and status for each request
- Success/failure counts
- Effective throughput metrics

### 6. Job Service

The container runs as a job service (runs to completion), making multiple rate-limited API calls and persisting results before exiting.

## 📚 Key Files

| File | Description |
|------|-------------|
| `src/main.rs` | Rust application with rate limiting and stage persistence |
| `Cargo.toml` | Rust dependencies (governor, chrono, uuid, etc.) |
| `Dockerfile` | Multi-stage build including Snowflake CLI |
| `setup.sql` | Complete Snowflake setup with stage creation |
| `service-spec.yaml` | Service specification (reference) |
| `README.md` | This file |

## ⚙️ Configuration Options

The application accepts the following environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `API_KEY` | API authentication key (from secret) | *Required* | `demo-key-123` |
| `API_ENDPOINT` | Target API URL | `https://api.publicapis.org/entries` | Any HTTPS URL |
| `NUM_REQUESTS` | Number of requests to make | `10` | `5`, `20`, `100` |
| `RATE_LIMIT` | Requests per second | `2` | `1`, `5`, `10` |
| `STAGE_PATH` | Snowflake stage for results | `@api_results_stage` | `@my_stage` |

## 🔒 Security Best Practices

This demo follows Snowflake security best practices:

1. **Secrets are never hardcoded** - stored in Snowflake secrets
2. **Network access is restricted** - only allowed hosts via network rules
3. **Principle of least privilege** - external access integration limits scope
4. **Audit trail** - all secret access is logged in Snowflake
5. **Secret values are masked** - DESCRIBE SECRET shows metadata only

## 🔄 Secret Types Supported

Snowflake supports multiple secret types:

| Type | Use Case | Example |
|------|----------|---------|
| `GENERIC_STRING` | API keys, tokens | This demo |
| `PASSWORD` | Basic auth (username/password) | Included in setup |
| `OAUTH2` | OAuth client credentials | External services |
| `CLOUD_PROVIDER_TOKEN` | AWS IAM, Azure, GCP | Cloud resources |

## 🧹 Cleanup

To remove all resources:

```sql
USE DATABASE SPCS_DEMO;
USE SCHEMA API_JOBS;

-- Drop service first
DROP SERVICE IF EXISTS api_job_service;

-- Drop compute pool (requires services to be dropped first)
DROP COMPUTE POOL IF EXISTS job_pool;

-- Drop secrets
DROP SECRET IF EXISTS api_key_secret;
DROP SECRET IF EXISTS basic_auth_secret;

-- Drop integrations and rules
DROP EXTERNAL ACCESS INTEGRATION IF EXISTS api_access_integration;
DROP NETWORK RULE IF EXISTS allow_public_api;

-- Drop stage
DROP STAGE IF EXISTS api_results_stage;

-- Drop image repository
DROP IMAGE REPOSITORY IF EXISTS spcs_demo_repo;

-- Drop schema and database
DROP SCHEMA IF EXISTS API_JOBS;
DROP DATABASE IF EXISTS SPCS_DEMO;
```

## 📖 References

- [Snowflake CREATE SECRET Documentation](https://docs.snowflake.com/en/sql-reference/sql/create-secret)
- [API Authentication and Secrets](https://docs.snowflake.com/en/user-guide/api-authentication)
- [Snowflake Container Services Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview)
- [Network Rules](https://docs.snowflake.com/en/sql-reference/sql/create-network-rule)

## 🐛 Troubleshooting

### Compute Pool Not Starting

```sql
-- Check compute pool status
SHOW COMPUTE POOLS;

-- May take 2-5 minutes to reach ACTIVE/IDLE state
```

### Service Creation Fails

```sql
-- Verify image exists
SHOW IMAGES IN IMAGE REPOSITORY spcs_demo_repo;

-- Check compute pool is ready
SHOW COMPUTE POOLS;
```

### No Logs Available

```sql
-- Wait a moment for the service to start, then:
CALL SYSTEM$GET_SERVICE_LOGS('api_job_service', 0, 'api-client', 100);
```

### Network Access Denied

Verify the network rule includes your API host:

```sql
SHOW NETWORK RULES;
DESC NETWORK RULE allow_public_api;
```

## 💡 Features Demonstrated

✅ **Secrets Management**: Secure API key injection from Snowflake secrets  
✅ **Network Security**: Whitelist-based egress control via network rules  
✅ **Rate Limiting**: Token bucket algorithm prevents API throttling  
✅ **File Persistence**: Results saved to Snowflake internal stage  
✅ **Metrics Tracking**: Detailed timing and success/failure statistics  
✅ **Idiomatic Rust**: Proper error handling with `anyhow::Result`  
✅ **Multi-stage Build**: Optimized Docker image with separate build/runtime layers

## 💡 Next Steps

- Implement exponential backoff and retry logic for failed requests
- Add OAuth2 authentication with authorization code flow
- Create a long-running service with continuous processing
- Implement streaming results to a Snowflake table
- Use multiple containers for parallel processing
- Add Prometheus metrics export

## 📝 License

This is a demo project for educational purposes.

