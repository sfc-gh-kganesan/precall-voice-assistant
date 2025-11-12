#### Step 1: Navigate to Backend Directory

```bash
cd /Users/vsrinivas/Desktop/aura/invoiceiq/backend
```

#### Step 2: Set Connection Environment Variable

```bash
# If using a named connection (e.g., 'invoiceiq')
export INVOICEIQ_SNOW_CONNECT="-c invoiceiq"

# Or use default connection
export INVOICEIQ_SNOW_CONNECT=""
```

#### Step 3: Login to Snowflake Image Registry

```bash
snow spcs image-registry login $INVOICEIQ_SNOW_CONNECT
```

This authenticates Docker to push images to Snowflake.

#### Step 4: Build Docker Image

Build the image for AMD64 architecture (required by SPCS):

```bash
docker build --rm --platform linux/amd64 \
  -t sfengineering-aifde.registry.snowflakecomputing.com/invoiceiq/service/image_repository/invoiceiq-backend:latest \
  .
```

**What happens:**
1. Pulls base image: `ghcr.io/astral-sh/uv:python3.11-bookworm-slim`
2. Installs dependencies from `pyproject.toml` and `uv.lock`
3. Copies application code from `app/`
4. Sets up uvicorn to serve FastAPI on port 8001

**Build time**: ~2-5 minutes

#### Step 5: Push Image to Snowflake Registry

```bash
docker push sfengineering-aifde.registry.snowflakecomputing.com/invoiceiq/service/image_repository/invoiceiq-backend:latest