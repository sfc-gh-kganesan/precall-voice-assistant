#!/bin/bash
set -e

# P67 Dashboard Native App Deployment Script
# Usage: ./deploy-native-app.sh [--skip-build] [--skip-frontend] [--patch] [--channel CHANNEL]
#
# IMPORTANT: This native app deployment has a known architectural limitation.
# The dashboard proxy cannot authenticate to P67's controld service because:
# 1. Native apps have isolated SPCS internal DNS (can't use internal://controld...)
# 2. Must use controld's PUBLIC endpoint which requires Snowflake OAuth
# 3. SPCS ingress strips Authorization headers before forwarding to containers
# 4. Browser CSP blocks OAuth redirects (302) from the proxy
#
# RECOMMENDED: Use the standalone SPCS service (deploy.sh) for now.
# FUTURE SOLUTION: Deploy dashboard service INSIDE the P67 native app.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
SNOWFLAKE_ACCOUNT="sfengineering-aifde"
REGISTRY="${SNOWFLAKE_ACCOUNT}.registry.snowflakecomputing.com"
IMAGE_REPO="p67_src/dash/img_repo"
IMAGE_NAME="p67-dash"
APP_PACKAGE="P67_DASH_PKG"
APP_NAME="P67_DASH_APP"
STAGE="P67_SRC.DASH.NATIVE_APP_STAGE"
RELEASE_CHANNEL="QA"

# NOTE: This URL requires OAuth - root cause of 302/CSP issue
# TODO: When moving dashboard inside P67 native app, change to internal DNS
P67_API_URL="https://frb46h6e-sfengineering-aifde.snowflakecomputing.app"

# Parse arguments
SKIP_BUILD=false
SKIP_FRONTEND=false
PATCH_ONLY=false
for arg in "$@"; do
  case $arg in
    --skip-build) SKIP_BUILD=true ;;
    --skip-frontend) SKIP_FRONTEND=true ;;
    --patch) PATCH_ONLY=true ;;
    --channel=*) RELEASE_CHANNEL="${arg#*=}" ;;
    --channel)
      shift
      RELEASE_CHANNEL="$1"
      ;;
    --help)
      echo "Usage: ./deploy-native-app.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --skip-build     Skip Docker build (use existing local image)"
      echo "  --skip-frontend  Skip frontend rebuild (use existing dist/)"
      echo "  --patch          Create patch instead of new version"
      echo "  --channel NAME   Release channel (default: QA)"
      echo "  --help           Show this help message"
      echo ""
      echo "Release Channels: ALPHA, QA, DEFAULT"
      echo ""
      echo "KNOWN LIMITATION: Native app cannot auth to P67 controld public endpoint."
      echo "Use deploy.sh for standalone SPCS deployment instead."
      exit 0
      ;;
  esac
done

# Generate version tag
VERSION="v$(date +%s)"
FULL_IMAGE="${REGISTRY}/${IMAGE_REPO}/${IMAGE_NAME}:${VERSION}"

echo "=========================================="
echo "P67 Dashboard Native App Deployment"
echo "=========================================="
echo "Version Tag: ${VERSION}"
echo "Image: ${FULL_IMAGE}"
echo "App Package: ${APP_PACKAGE}"
echo "App: ${APP_NAME}"
echo "Release Channel: ${RELEASE_CHANNEL}"
echo "Patch Mode: ${PATCH_ONLY}"
echo ""
echo "WARNING: Native app has 302/CSP issue due to OAuth requirement."
echo "         Use standalone SPCS (deploy.sh) for working deployment."
echo ""

# Step 1: Build frontend
if [ "$SKIP_FRONTEND" = false ]; then
  echo "[1/6] Building frontend..."
  pnpm run build
  echo "Frontend build complete."
else
  echo "[1/6] Skipping frontend build (--skip-frontend)"
fi
echo ""

# Step 2: Build Docker image
if [ "$SKIP_BUILD" = false ]; then
  echo "[2/6] Building Docker image for linux/amd64..."
  docker build --platform linux/amd64 -t "${IMAGE_NAME}:latest" .
  echo "Docker build complete."
else
  echo "[2/6] Skipping Docker build (--skip-build)"
fi
echo ""

# Step 3: Tag and push to Snowflake registry
echo "[3/6] Pushing image to Snowflake registry..."
echo "Tagging as ${FULL_IMAGE}"
docker tag "${IMAGE_NAME}:latest" "${FULL_IMAGE}"

# Ensure logged into registry
echo "Ensuring registry authentication..."
snow spcs image-registry login --quiet 2>/dev/null || snow spcs image-registry login

echo "Pushing to registry (this may take a moment)..."
if ! docker push "${FULL_IMAGE}"; then
  echo "Push failed. Re-authenticating..."
  snow spcs image-registry login
  docker push "${FULL_IMAGE}"
fi
echo "Push complete."
echo ""

# Step 4: Update native-app YAML files with new version
echo "[4/6] Updating native app configuration files..."

# Update dashboard_service_spec.yml
cat > native-app/dashboard_service_spec.yml <<EOF
spec:
  containers:
    - name: dashboard
      image: /p67_src/dash/img_repo/p67-dash:${VERSION}
      env:
        P67_API_URL: "${P67_API_URL}"
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

# Update manifest.yml with new image reference
sed -i.bak "s|p67-dash:v[0-9]*|p67-dash:${VERSION}|g" native-app/manifest.yml
rm -f native-app/manifest.yml.bak

echo "Configuration files updated."
echo ""

# Step 5: Upload files to stage
echo "[5/6] Uploading files to stage..."
snow sql -q "PUT file://${SCRIPT_DIR}/native-app/manifest.yml @${STAGE}/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
snow sql -q "PUT file://${SCRIPT_DIR}/native-app/setup.sql @${STAGE}/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
snow sql -q "PUT file://${SCRIPT_DIR}/native-app/readme.md @${STAGE}/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
snow sql -q "PUT file://${SCRIPT_DIR}/native-app/dashboard_service_spec.yml @${STAGE}/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
echo "Files uploaded to stage."
echo ""

# Step 6: Create version or patch
echo "[6/6] Creating application package version..."

# Get current version info
CURRENT_VERSION=$(snow sql -q "SHOW VERSIONS IN APPLICATION PACKAGE ${APP_PACKAGE}" --format json 2>/dev/null | grep -o '"version":"[^"]*"' | tail -1 | cut -d'"' -f4 || echo "")

if [ "$PATCH_ONLY" = true ] && [ -n "$CURRENT_VERSION" ]; then
  echo "Adding patch to version ${CURRENT_VERSION}..."
  snow sql -q "ALTER APPLICATION PACKAGE ${APP_PACKAGE} ADD PATCH FOR VERSION ${CURRENT_VERSION} USING '@${STAGE}'"
  ACTION="Patch added to ${CURRENT_VERSION}"
else
  # Generate new version name
  NEW_VERSION="V$(date +%Y%m%d_%H%M%S)"
  echo "Creating new version ${NEW_VERSION}..."
  snow sql -q "ALTER APPLICATION PACKAGE ${APP_PACKAGE} ADD VERSION ${NEW_VERSION} USING '@${STAGE}'"
  
  # Set as release directive
  echo "Setting release directive for channel ${RELEASE_CHANNEL}..."
  snow sql -q "ALTER APPLICATION PACKAGE ${APP_PACKAGE} SET RELEASE DIRECTIVE ${RELEASE_CHANNEL} ACCOUNTS=(*) VERSION=${NEW_VERSION}"
  
  ACTION="Version ${NEW_VERSION} created"
  CURRENT_VERSION="${NEW_VERSION}"
fi
echo ""

# Upgrade the installed application
echo "Upgrading installed application..."
snow sql -q "ALTER APPLICATION ${APP_NAME} UPGRADE"
echo ""

# Wait for service to be ready
echo "Waiting for service to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT + 1))
  
  STATUS=$(snow sql -q "SELECT SYSTEM\$GET_SERVICE_STATUS('${APP_NAME}.V1.DASHBOARD_SERVICE')" --format json 2>/dev/null | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4 2>/dev/null || echo "PENDING")
  
  if [ "$STATUS" = "READY" ]; then
    echo "Service is READY!"
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "ERROR: Service failed to start!"
    echo "Check logs with: snow sql -q \"CALL SYSTEM\$GET_SERVICE_LOGS('${APP_NAME}.V1.DASHBOARD_SERVICE', '0', 'dashboard', 100)\""
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
echo "${ACTION}"
echo "Image: ${FULL_IMAGE}"
echo ""

ENDPOINT=$(snow sql -q "SHOW ENDPOINTS IN SERVICE ${APP_NAME}.V1.DASHBOARD_SERVICE" --format json 2>/dev/null | grep -o '"ingress_url":"[^"]*"' | cut -d'"' -f4 || echo "")
if [ -n "$ENDPOINT" ]; then
  echo "Endpoint: https://${ENDPOINT}"
else
  echo "Endpoint: (run SHOW ENDPOINTS to retrieve)"
fi
echo ""
echo "KNOWN ISSUE: 302/CSP errors expected due to OAuth requirement."
echo "Use standalone SPCS deployment (deploy.sh) for working version."
echo ""
echo "To check logs:"
echo "  snow sql -q \"CALL SYSTEM\\\$GET_SERVICE_LOGS('${APP_NAME}.V1.DASHBOARD_SERVICE', '0', 'dashboard', 100)\""
echo ""
echo "To check status:"
echo "  snow sql -q \"SELECT SYSTEM\\\$GET_SERVICE_STATUS('${APP_NAME}.V1.DASHBOARD_SERVICE')\""
