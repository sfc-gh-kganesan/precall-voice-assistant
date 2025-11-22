#!/bin/bash -ex

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"/sandbox/setli/fastapi_o11y

# Export environment variables used from snowflake.yml project definition file
# and bootstrap.sql
source $ROOT/ops/_vars.sh

# Ensure database, schema, stage, image repository and compute pool exist
snow sql -f $ROOT/ops/bootstrap.sql -c $SNOW_CONNECTION

# Build image
REPO_URL=$(snow spcs image-repository url $IMAGE_REPOSITORY -c $SNOW_CONNECTION --database $DATABASE --schema $SCHEMA)
docker build --rm --platform linux/amd64 -t $REPO_URL/$IMAGE:$IMAGE_TAG $ROOT/.

# Login to the spcs registry and push image
snow spcs image-registry login -c $SNOW_CONNECTION
docker push $REPO_URL/$IMAGE:$IMAGE_TAG

# Update service spec with image path
sed -i "" "s|image:.*|image: $REPO_URL/$IMAGE:$IMAGE_TAG|" $ROOT/ops/$SERVICE_SPEC

# Check if service already exists, so we know whether to deploy from scratch or upgrade existing service.
# Note: it would be nice if the snow CLI command could handle this for us...
SERVICE_EXISTS_JQ='
.[]
| select(
    (.name | ascii_downcase) == ($service_name | ascii_downcase) and 
    (.database_name | ascii_downcase) == ($database | ascii_downcase) and 
    (.schema_name | ascii_downcase) == ($schema | ascii_downcase)
)
| true
'

SERVICE_EXISTS=$( \
    snow spcs service list --format json --database $DATABASE --schema $SCHEMA | \
    jq -c "$SERVICE_EXISTS_JQ" --arg service_name "$SERVICE_NAME" --arg database "$DATABASE" --arg schema "$SCHEMA"
)
    
if [ -n "$SERVICE_EXISTS" ]; then
    # upgrade service
    snow spcs service deploy --upgrade -c $SNOW_CONNECTION -p $ROOT/ops
else
    # deploy service
    snow spcs service deploy -c $SNOW_CONNECTION -p $ROOT/ops
fi
    

