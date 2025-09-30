import asyncio
import os
import uuid
from concurrent import futures
from pathlib import Path
from pprint import pprint

import grpc
import snowflake.connector
from dotenv import load_dotenv
from loguru import logger
from py_protos import extractor_pb2, extractor_pb2_grpc
from py_util import fs

load_dotenv()


def get_sfconn():
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        authenticator="SNOWFLAKE_JWT",
        private_key_file=os.getenv("SNOWFLAKE_KEY"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        role=os.getenv("SNOWFLAKE_ROLE"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

    return conn


def upload_file_to_stage(cur, fp):
    file_path = fs.get_repo_abs_path(fp)
    logger.info(f"uploading file {file_path}")
    cur.execute(f"put file://{file_path} @inviq.service.tmpfiles auto_compress=false")
    logger.info("success! Now refreshing the @inviq.service.tmpfiles stage...")
    cur.execute("alter stage inviq.service.tmpfiles refresh")


def extract_fields(cur, fp):
    cur.execute("call inviq.service.extract_invoice_file(%s)", (fp))
    cols = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row:
        return dict(zip(cols, row, strict=False))
    else:
        return {}


class ExtractorService(extractor_pb2_grpc.ExtractorServicer):
    def __init__(self):
        self.upload_dir = Path("local-storage")
        self.upload_dir.mkdir(exist_ok=True)

    def Extract(self, request_iterator, context):
        logger.info("Received Extraction request.")
        try:
            file_id = str(uuid.uuid4())
            filename = None
            file_content = b""

            for chunk in request_iterator:
                if filename is None:
                    filename = chunk.filename

                    file_content += chunk.content

                    if chunk.is_last:
                        break

            # Save file to local storage
            file_path = self.upload_dir.joinpath(f"{file_id}_{filename}").resolve()

            with open(file_path, "wb") as f:
                f.write(file_content)

        except Exception as e:
            return extractor_pb2.ExtractResponse(success=False, message=f"Upload failed: {str(e)}", file_id="")

        fields = {}
        try:
            conn = get_sfconn()
            cur = conn.cursor()
            cur.execute("select current_user(), current_role(), current_warehouse()")
            result = cur.fetchone()
            if result is not None:
                logger.info(f"Snowflake user: {result[0]}")
                logger.info(f"Snowflake role: {result[1]}")
                logger.info(f"Snowflake warehouse: {result[2]}")
            upload_file_to_stage(cur, file_path)
            fields = extract_fields(cur, file_path.name)
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(e)

        logger.info("extracted data:\n")
        pprint(fields)
        return extractor_pb2.ExtractResponse(
            success=True,
            message="File extracted successfully",
            file_id=file_id,
            furl=str(fields["FILE_URL"]),
            purchase_order_number=str(fields["PURCHASE_ORDER_NUMBER"]),
            payment_terms=str(fields["PAYMENT_TERMS"]),
            total_amount=str(fields["TOTAL_AMOUNT"]),
            vendor_name=str(fields["VENDOR_NAME"]),
        )


async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    extractor_pb2_grpc.add_ExtractorServicer_to_server(ExtractorService(), server)

    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)

    logger.info(f"Starting extractor gRPC server on {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        await server.stop(0)


if __name__ == "__main__":
    asyncio.run(serve())
