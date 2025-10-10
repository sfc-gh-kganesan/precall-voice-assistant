import os
from contextlib import contextmanager
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


@contextmanager
def connection():
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER", "svc_invoiceiq"),
        password=os.getenv("SNOWFLAKE_PAT"),
        account=os.getenv("SNOWFLAKE_ACCOUNT", "SFENGINEERING-AIFDE"),
        role=os.getenv("SNOWFLAKE_ROLE", "invoiceiq_admin"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "compute_wh"),
        database=os.getenv("SNOWFLAKE_DATABASE", "invoiceiq"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "service"),
    )
    try:
        yield conn
    finally:
        conn.close()


def whoami():
    try:
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select current_user(), current_role(), current_warehouse()")
                result = cur.fetchone()
                if result is not None:
                    logger.info(f"Snowflake user: {result[0]}")
                    logger.info(f"Snowflake role: {result[1]}")
                    logger.info(f"Snowflake warehouse: {result[2]}")
    except Exception as e:
        logger.error(e)


def stage_put_files(local_dir: Path, file_glob: str) -> list[str]:
    """
    Upload local files to remote Snowflake stage

    Args:
        local_dir: absolute path to local directory on disk containing files
        file_glob: glob expression to select which files to upload
    """
    db = os.getenv("SNOWFLAKE_DATABASE", "invoiceiq")
    schema = os.getenv("SNOWFLAKE_SCHEMA", "service")
    stage = os.getenv("SNOWFLAKE_STAGE", "ticket_attachments")
    stage_path = f"@{db}.{schema}.{stage}"
    file_str = f"{local_dir}/{file_glob}"
    result_files = []
    with connection() as conn:
        with conn.cursor() as cur:
            query = f"put file://{file_str} {stage_path} auto_compress=false"
            logger.debug(f"⚡{query}")
            cur.execute(query)
            results = cur.fetchall()
            result_files = [row[0] for row in results]
            for f in result_files:
                logger.info(f"✅ Uploaded {stage_path}/{f}")
            return result_files


def insert_ticket_metadata(submission_id: str, ticket_number: str, email: str):
    query = """
        insert into invoiceiq.service.ticket_metadata (
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

    with connection() as conn:
        with conn.cursor() as cur:
            logger.debug(f"⚡{query} ({data})")
            cur.execute(query, data)
            logger.info(f"✅ Inserted metadata for ticket {ticket_number} in submission {submission_id}")


def insert_file_metadata(submission_id: str, relative_path: str):
    query = """
        insert into invoiceiq.service.file_metadata (
                submission_id,
                relative_path
        )
        select
            %s,
            %s
    """

    data = (submission_id, relative_path)

    with connection() as conn:
        with conn.cursor() as cur:
            logger.debug(f"⚡{query} ({data})")
            cur.execute(query, data)
            logger.info(f"✅ Inserted metadata for file {relative_path} in submission {submission_id}")
