#!/bin/bash
set -e

# P67 Dashboard SPCS Deployment Script
# Usage: ./deploy.sh [--skip-build] [--skip-frontend]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
SNOWFLAKE_ACCOUNT="sfengineering-aifde"
REGISTRY="${SNOWFLAKE_ACCOUNT}.registry.snowflakecomputing.com"
IMAGE_REPO="p67_src/dash/img_repo"
IMAGE_NAME="p67-dash"
SERVICE_NAME="P67_SRC.DASH.P67_DASH"
COMPUTE_POOL="SANDBOX_COMPUTE_POOL_CPU"
SNOW_CONN="${SNOW_CONN:-default}"
P67_API_URL="http://controld.ghw6if.svc.spcs.internal:80"

# Parse arguments
SKIP_BUILD=false
SKIP_FRONTEND=false
for arg in "$@"; do
  case $arg in
    --skip-build) SKIP_BUILD=true ;;
    --skip-frontend) SKIP_FRONTEND=true ;;
    --help)
      echo "Usage: ./deploy.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --skip-build     Skip Docker build (use existing local image)"
      echo "  --skip-frontend  Skip frontend rebuild (use existing dist/)"
      echo "  --help           Show this help message"
      exit 0
      ;;
  esac
done

# Generate version tag
VERSION="v$(date +%s)"
FULL_IMAGE="${REGISTRY}/${IMAGE_REPO}/${IMAGE_NAME}:${VERSION}"

echo "=========================================="
echo "P67 Dashboard SPCS Deployment"
echo "=========================================="
echo "Version: ${VERSION}"
echo "Image: ${FULL_IMAGE}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Step 1: Build frontend
if [ "$SKIP_FRONTEND" = false ]; then
  echo "[1/5] Building frontend..."
  pnpm run build
  echo "Frontend build complete."
else
  echo "[1/5] Skipping frontend build (--skip-frontend)"
fi
echo ""

# Step 2: Build Docker image
if [ "$SKIP_BUILD" = false ]; then
  echo "[2/5] Building Docker image for linux/amd64..."
  docker build --platform linux/amd64 -t "${IMAGE_NAME}:latest" .
  echo "Docker build complete."
else
  echo "[2/5] Skipping Docker build (--skip-build)"
fi
echo ""

# Step 3: Tag and push to Snowflake registry
echo "[3/5] Pushing image to Snowflake registry..."
echo "Tagging as ${FULL_IMAGE}"
docker tag "${IMAGE_NAME}:latest" "${FULL_IMAGE}"

echo "Pushing to registry (this may take a moment)..."
docker push "${FULL_IMAGE}"
echo "Push complete."
echo ""

# Step 4: Update SPCS service
echo "[4/5] Updating SPCS service..."

# Resolve controld's public ingress URL dynamically for dashboard UI display
CONTROLD_INGRESS=$(snow sql -c "${SNOW_CONN}" -q "SHOW ENDPOINTS IN SERVICE P67.APP.CONTROLD" --format json 2>/dev/null | jq -r '.[0].ingress_url // empty')
if [ -n "$CONTROLD_INGRESS" ]; then
  P67_CONTROLD_ENDPOINT="https://${CONTROLD_INGRESS}"
  echo "Resolved controld endpoint: ${P67_CONTROLD_ENDPOINT}"
fi

SPEC=$(cat <<EOF
spec:
  containers:
    - name: dashboard
      image: /${IMAGE_REPO}/${IMAGE_NAME}:${VERSION}
      env:
        P67_API_URL: "${P67_API_URL}"
        P67_CONTROLD_ENDPOINT: "${P67_CONTROLD_ENDPOINT}"
        PORT: "3001"
      resources:
        requests:
          memory: 256M
          cpu: 0.5
        limits:
          memory: 512M
          cpu: 1
      readinessProbe:
        path: /health
        port: 3001
  endpoints:
    - name: dashboard
      port: 3001
      public: true
EOF
)

snow sql -c "${SNOW_CONN}" -q "ALTER SERVICE ${SERVICE_NAME} FROM SPECIFICATION \$\$${SPEC}\$\$"
echo "Service update initiated."
echo ""

# Step 5: Wait for service to be ready
echo "[5/5] Waiting for service to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT + 1))
  
  STATUS=$(snow sql -c "${SNOW_CONN}" -q "SELECT SYSTEM\$GET_SERVICE_STATUS('${SERVICE_NAME}')" --format json 2>/dev/null | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
  
  if [ "$STATUS" = "READY" ]; then
    echo "Service is READY!"
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "ERROR: Service failed to start!"
    echo "Check logs with: snow sql -q \"CALL SYSTEM\$GET_SERVICE_LOGS('${SERVICE_NAME}', '0', 'dashboard', 100)\""
    exit 1
  else
    echo "  Status: ${STATUS:-PENDING} (attempt ${ATTEMPT}/${MAX_ATTEMPTS})"
    sleep 5
  fi
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
  echo "WARNING: Timed out waiting for service. Check status manually."
fi
echo ""

# Get endpoint URL
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
ENDPOINT=$(snow sql -c "${SNOW_CONN}" -q "SHOW ENDPOINTS IN SERVICE ${SERVICE_NAME}" --format json 2>/dev/null | jq -r '.[0].ingress_url // empty')
echo "Endpoint: https://${ENDPOINT}"
echo "Version: ${VERSION}"
echo ""
echo "To check logs:"
echo "  snow sql -q \"CALL SYSTEM\\\$GET_SERVICE_LOGS('${SERVICE_NAME}', '0', 'dashboard', 100)\""
echo ""
echo "To check status:"
echo "  snow sql -q \"SELECT SYSTEM\\\$GET_SERVICE_STATUS('${SERVICE_NAME}')\""
