DATABASE=JSUMMER
SCHEMA=SANDBOX
REPO=sfengineering-aifde.registry.snowflakecomputing.com/jsummer/sandbox/image_repository
IMAGE=langgraph-service-function
TAG=latest
SERVICE_NAME=langgraph

# echo "Creating database if not exists"
# snow object create database $DATABASE --if-not-exists

# echo "Creating schema if not exists"
# snow object create schema $SCHEMA --database $DATABASE --if-not-exists

# echo "Creating compute pool"
# snow spcs compute-pool deploy $SNOW_CONNECT || true

# echo "Creating image repository"
# snow spcs image-repository deploy $SNOW_CONNECT --database $DATABASE --schema $SCHEMA || true

# echo "Logging in to image registry"
# snow spcs image-registry login $SNOW_CONNECT

# echo "Building image"
# docker build --rm --platform linux/amd64 -t $REPO/$IMAGE:$TAG ../.

# echo "Pushing image to repository"
# docker push $REPO/$IMAGE:$TAG

# echo "Dropping service if exists"
snow spcs service drop $SERVICE_NAME $SNOW_CONNECT --database $DATABASE --schema $SCHEMA || true

echo "Deploying service"
snow spcs service deploy $SNOW_CONNECT

echo "Deploying function"
snow sql -q "!source function.sql" $SNOW_CONNECT --database $DATABASE --schema $SCHEMA




