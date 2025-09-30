import os
import logging
import grpc
from fastapi import FastAPI, HTTPException

# Import gRPC stubs
from py_protos import (
    invoicestore_pb2,
    invoicestore_pb2_grpc,
)

# --- Environment Variables for Service Discovery ---
INVOICESTORE_GRPC_URL = os.getenv("INVOICESTORE_GRPC_URL", "localhost:50051")

# --- FastAPI App Initialization ---
app = FastAPI(title="InvoiceIQ Gateway API", version="0.1.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- API Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/test-invoicestore-failure")
async def test_invoicestore_failure():
    """
    A temporary test endpoint to confirm connectivity to the InvoiceStore.
    It intentionally sends an invalid request to trigger a failure response.
    """
    logger.info("Gateway: Sending intentional failure request to InvoiceStore...")
    try:
        async with grpc.aio.insecure_channel(INVOICESTORE_GRPC_URL) as channel:
            stub = invoicestore_pb2_grpc.InvoiceStoreStub(channel)
            # Send an invalid request with an empty lift_ticket and no file_ids
            request = invoicestore_pb2.SubmissionRequest(lift_ticket="", file_ids=[])
            response = await stub.Submit(request)

            # We expect this to fail, so receiving a success response is unexpected
            if response.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected success from InvoiceStore: {response.message}",
                )

            # Return the failure message from the service
            return {
                "message": "Successfully received expected failure from InvoiceStore.",
                "service_response": response.message,
                "service_success_flag": response.success,
            }
    except grpc.aio.AioRpcError as e:
        # This is the most likely outcome if the service is unreachable
        logger.error(f"gRPC error while testing InvoiceStore: {e.details()}")
        raise HTTPException(
            status_code=502,
            detail=f"Error communicating with InvoiceStore: {e.details()}",
        )
