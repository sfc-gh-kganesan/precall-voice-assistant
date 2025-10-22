# START: Change these variables as desired
COMPUTE_POOL=sandbox_compute_pool_cpu
DATABASE=JSUMMER
SCHEMA=SANDBOX
STAGE=DROPBOX
IMAGE_REPOSITORY=image_repository
IMAGE=langgraph-service-function
TAG=latest
SERVICE_NAME=langgraph
# END: Do not change below this line

# Environment variables re-used in snowflake.yml project definition file
export COMPUTE_POOL=$COMPUTE_POOL
export DATABASE=$DATABASE
export SCHEMA=$SCHEMA
export STAGE=$STAGE
export IMAGE_REPOSITORY=$IMAGE_REPOSITORY

echo "Creating database if not exists"
snow object create database name=$DATABASE --if-not-exists

echo "Creating schema if not exists"
snow object create schema name=$SCHEMA --database $DATABASE --if-not-exists

echo "Creating compute pool"
snow spcs compute-pool deploy $SNOW_CONNECT || true

echo "Creating image repository"
snow spcs image-repository deploy $SNOW_CONNECT --database $DATABASE --schema $SCHEMA || true

echo "Logging in to image registry"
snow spcs image-registry login $SNOW_CONNECT

echo "Getting image repository URL"
REPO_URL=$(snow spcs image-repository url $IMAGE_REPOSITORY$SNOW_CONNECT --database $DATABASE --schema $SCHEMA)
echo "REPO_URL: $REPO_URL"

echo "Updating service_spec.yaml with image path"
sed -i "" "s|image:.*|image: $REPO_URL/$IMAGE:$TAG|" service_spec.yaml

echo "Building image"
docker build --rm --platform linux/amd64 -t $REPO_URL/$IMAGE:$TAG ../.

echo "Pushing image to repository"
docker push $REPO_URL/$IMAGE:$TAG

echo "Dropping service if exists"
snow spcs service drop $SERVICE_NAME $SNOW_CONNECT --database $DATABASE --schema $SCHEMA || true

echo "Deploying service"
snow spcs service deploy $SNOW_CONNECT

echo "Deploying function"
snow sql -q "!source function.sql" $SNOW_CONNECT --database $DATABASE --schema $SCHEMA

