#!/bin/sh
set -e

# Read DATABASE_URL from SPCS secret file, fall back to env var
SECRET_FILE="/opt/creds/postgres_connection_url/secret_string"
if [ -f "$SECRET_FILE" ]; then
    export DATABASE_URL="$(cat "$SECRET_FILE")"
    echo "Loaded DATABASE_URL from SPCS secret."
elif [ -z "$DATABASE_URL" ]; then
    echo "ERROR: No DATABASE_URL found (checked $SECRET_FILE and env)."
    exit 1
fi

# Ensure SSL is enabled (required by Snowflake Postgres)
case "$DATABASE_URL" in
    *sslmode=*) ;;
    *\?*) export DATABASE_URL="${DATABASE_URL}&sslmode=require" ;;
    *)    export DATABASE_URL="${DATABASE_URL}?sslmode=require" ;;
esac

echo "Running database migrations..."
cd /app/packages/db
# Snowflake Postgres uses self-signed certificates
NODE_TLS_REJECT_UNAUTHORIZED=0 npx prisma migrate deploy
echo "Migrations complete."

cd /app/services/${SERVICE_NAME}
exec node dist/index.js
