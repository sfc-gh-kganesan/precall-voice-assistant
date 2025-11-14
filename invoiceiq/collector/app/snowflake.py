import os
from contextlib import contextmanager
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


@contextmanager
def connection(
    *,
    account: str,
    user: str | None = None,
    password: str | None = None,
    warehouse: str,
    role: str,
    database: str | None = None,
    schema: str | None = None,
):
    token_path = Path("/snowflake/session/token")
    using_token = token_path.is_file()

    creds = {
        "account": account,
        "warehouse": warehouse,
        "role": role,
        "client_session_keep_alive": True,
    }

    if not using_token:
        if not user:
            raise ValueError("Snowflake user must be provided")
        if not password:
            raise ValueError("Snowflake password must be provided")
        creds["user"] = user
        creds["password"] = password
    else:
        token_value = token_path.read_text().strip()
        creds["authenticator"] = "oauth"
        creds["token"] = token_value
        creds["protocol"] = "https"

        host = os.getenv("SNOWFLAKE_HOST")
        port = os.getenv("SNOWFLAKE_PORT")
        if host:
            creds["host"] = host
        if port:
            creds["port"] = port

    if database:
        creds["database"] = database

    if schema:
        creds["schema"] = schema

    conn = snowflake.connector.connect(**creds)

    try:
        yield conn
    finally:
        conn.close()


def whoami(**connection_kwargs):
    try:
        with connection(**connection_kwargs) as conn:
            with conn.cursor() as cur:
                cur.execute("select current_user(), current_role(), current_warehouse()")
                result = cur.fetchone()
                if result is not None:
                    logger.info(f"Snowflake user: {result[0]}")
                    logger.info(f"Snowflake role: {result[1]}")
                    logger.info(f"Snowflake warehouse: {result[2]}")
    except Exception as e:
        logger.error(e)


def stage_put_files(
    local_dir: Path,
    file_glob: str,
    *,
    database: str,
    schema: str,
    stage: str,
    **connection_kwargs,
) -> list[str]:
    """
    Upload local files to remote Snowflake stage

    Args:
      local_dir: absolute path to local directory on disk containing files
        file_glob: glob expression to select which files to upload
    """
    stage_path = f"@{database}.{schema}.{stage}"
    file_str = f"{local_dir}/{file_glob}"
    result_files = []
    conn_kwargs = {**connection_kwargs}
    conn_kwargs.setdefault("database", database)
    conn_kwargs.setdefault("schema", schema)
    with connection(**conn_kwargs) as conn:
        with conn.cursor() as cur:
            query = f"put file://{file_str} {stage_path} auto_compress=false"
            logger.debug(f"⚡{query}")
            cur.execute(query)
            results = cur.fetchall()
            result_files = [row[0] for row in results]
            for f in result_files:
                logger.info(f"✅ Uploaded {stage_path}/{f}")
            return result_files


def insert_ticket_metadata(
    submission_id: str,
    ticket_number: str,
    email: str,
    *,
    database: str,
    schema: str,
    table: str,
    **connection_kwargs,
):
    table_ref = table
    query = f"""
        insert into {table_ref} (
            submission_id,
            ticket_number,
            email
            )
        select
            %s,
            %s,
            %s
    """

    data = (submission_id, ticket_number, email)

    conn_kwargs = {**connection_kwargs}
    conn_kwargs.setdefault("database", database)
    conn_kwargs.setdefault("schema", schema)
    with connection(**conn_kwargs) as conn:
        with conn.cursor() as cur:
            logger.debug(f"⚡{query} ({data})")
            cur.execute(query, data)
            logger.info(f"✅ Inserted metadata for ticket {ticket_number} in submission {submission_id}")


def insert_file_metadata(
    submission_id: str,
    relative_path: str,
    ticket_number: str,
    *,
    database: str,
    schema: str,
    table: str,
    **connection_kwargs,
):
    table_ref = table
    query = f"""
        insert into {table_ref} (
            submission_id,
            relative_path,
            ticket_number
            )
        select
            %s,
            %s,
            %s
    """

    data = (submission_id, relative_path, ticket_number)

    conn_kwargs = {**connection_kwargs}
    conn_kwargs.setdefault("database", database)
    conn_kwargs.setdefault("schema", schema)
    with connection(**conn_kwargs) as conn:
        with conn.cursor() as cur:
            logger.debug(f"⚡{query} ({data})")
            cur.execute(query, data)
            logger.info(f"✅ Inserted metadata for file {relative_path} in submission {submission_id}")
