import asyncio
import logging
from concurrent import futures

import grpc
from py_protos import invoicestore_pb2, invoicestore_pb2_grpc

from .db import Db

logger = logging.getLogger(__name__)


class InvoiceStoreServicer(invoicestore_pb2_grpc.InvoiceStoreServicer):
    def __init__(self):
        self.db = Db(db_path="invoicestore.db")

    def Submit(self, request, context):
        try:
            logger.info(f"Received submission request for lift ticket: {request.lift_ticket}")
            # Validate request
            if not request.lift_ticket:
                return invoicestore_pb2.SubmissionResponse(
                    success=False,
                    message="Lift ticket is required",
                    status=invoicestore_pb2.SUBMISSION_STATUS_REJECTED,
                )

            if not request.file_ids:
                return invoicestore_pb2.SubmissionResponse(
                    success=False,
                    message="At least one file ID is required",
                    status=invoicestore_pb2.SUBMISSION_STATUS_REJECTED,
                )

            # Insert submission into database
            submission = self.db.insert_submission(
                list(request.file_ids),
                request.lift_ticket,
                invoicestore_pb2.SUBMISSION_STATUS_PENDING,
            )

            if submission is None:
                return invoicestore_pb2.SubmissionResponse(success=False, message="Failed to create submission")

            return invoicestore_pb2.SubmissionResponse(
                success=True,
                message=f"Successfully processed {len(request.file_ids)} file(s) for lift ticket {request.lift_ticket}",
                status=invoicestore_pb2.SUBMISSION_STATUS_PENDING,
            )

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return invoicestore_pb2.SubmissionResponse(
                success=False,
                message=f"Upload failed: {str(e)}",
                status=invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN,
            )


async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    invoicestore_pb2_grpc.add_InvoiceStoreServicer_to_server(InvoiceStoreServicer(), server)

    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)

    print(f"Starting invoicestore gRPC server on {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        print("Server stopped")
        await server.stop(0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
