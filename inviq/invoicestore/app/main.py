import asyncio
import logging
import os
from concurrent import futures
from pathlib import Path

import grpc
from loguru import logger
from py_protos import invoicestore_pb2, invoicestore_pb2_grpc

from .db import Db, InvoiceSchema, submission_status_to_enum


class InvoiceStoreServicer(invoicestore_pb2_grpc.InvoiceStoreServicer):
    def __init__(self):
        data_dir = Path(os.getenv("INVOICESTORE_DATA_PATH", "db"))
        db_path = data_dir.joinpath("invoicestore.db")
        self.db = Db(db_path=db_path)

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

    def GetSubmission(self, request, context):
        try:
            logger.info(f"Received get submission request for lift ticket: {request.lift_ticket}")

            # Validate request
            if not request.lift_ticket:
                return invoicestore_pb2.GetSubmissionResponse(
                    success=False,
                    message="Lift ticket is required",
                    file_ids=[],
                    status=invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN,
                )

            # Get submission from database
            submission = self.db.get_submission_by_lift_ticket(request.lift_ticket)

            if submission is None:
                return invoicestore_pb2.GetSubmissionResponse(
                    success=False,
                    message=f"No submission found for lift ticket: {request.lift_ticket}",
                    file_ids=[],
                    status=invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN,
                )

            return invoicestore_pb2.GetSubmissionResponse(
                success=True,
                message=f"Found submission for lift ticket {request.lift_ticket} "
                f"with {len(submission.file_ids)} file(s)",
                file_ids=submission.file_ids,
                status=submission_status_to_enum(submission.status or "unknown"),
            )

        except Exception as e:
            logger.error(f"Get submission failed: {e}")
            return invoicestore_pb2.GetSubmissionResponse(
                success=False,
                message=f"Get submission failed: {str(e)}",
                file_ids=[],
                status=invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN,
            )

    def GetOldestPendingSubmission(self, request, context):
        try:
            logger.info("Received get oldest pending submission request")

            # Get oldest pending submission from database
            submission = self.db.get_oldest_pending_submission()

            if submission is None:
                return invoicestore_pb2.GetOldestPendingSubmissionResponse(
                    success=False,
                    message="No pending submissions found",
                    lift_ticket="",
                    file_ids=[],
                )

            return invoicestore_pb2.GetOldestPendingSubmissionResponse(
                success=True,
                message=f"Found pending submission for lift ticket {submission.lift_ticket}",
                lift_ticket=submission.lift_ticket,
                file_ids=submission.file_ids,
            )

        except Exception as e:
            logger.error(f"Get oldest pending submission failed: {e}")
            return invoicestore_pb2.GetOldestPendingSubmissionResponse(
                success=False,
                message=f"Get oldest pending submission failed: {str(e)}",
                lift_ticket="",
                file_ids=[],
            )

    def CreateInvoice(self, request, context):
        try:
            logger.info(f"Received CreateInvoice request for lift ticket: {request.lift_ticket}")

            # Validate required fields
            if not request.lift_ticket:
                return invoicestore_pb2.CreateInvoiceResponse(
                    success=False, message="Lift ticket is required", invoice_id=0
                )

            if not request.file_id:
                return invoicestore_pb2.CreateInvoiceResponse(
                    success=False, message="File ID is required", invoice_id=0
                )

            invoice = InvoiceSchema(
                lift_ticket=request.lift_ticket,
                file_id=request.file_id,
                vendor_name=request.vendor_name or None,
                invoice_number=request.invoice_number or None,
                invoice_date=request.invoice_date or None,
                total_amount=request.total_amount or None,
                purchase_order_number=request.purchase_order_number or None,
                banking_details=request.banking_details or None,
                payment_terms=request.payment_terms or None,
                memo_description=request.memo_description or None,
                shipped_to_address=request.shipped_to_address or None,
                service_start_date=request.service_start_date or None,
                service_end_date=request.service_end_date or None,
                quantity=request.quantity or None,
                unit_price=request.unit_price or None,
                payment_type=request.payment_type or None,
                due_date=request.due_date or None,
                vendor_tax_id=request.vendor_tax_id or None,
                snowflake_tax_id=request.snowflake_tax_id or None,
                prepaid_flag=request.prepaid_flag or None,
            )

            # Insert invoice into database
            created_invoice = self.db.create_invoice(invoice)

            if created_invoice is None:
                return invoicestore_pb2.CreateInvoiceResponse(
                    success=False, message="Failed to create invoice", invoice_id=0
                )

            return invoicestore_pb2.CreateInvoiceResponse(
                success=True,
                message=f"Successfully created invoice for {request.lift_ticket}",
                invoice_id=created_invoice.id,
            )

        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return invoicestore_pb2.CreateInvoiceResponse(
                success=False, message=f"Failed to create invoice: {e}", invoice_id=0
            )

    def ApproveInvoice(self, request, context):
        try:
            logger.info(f"Received ApproveInvoice request for invoice ID: {request.invoice_id}")

            # Validate invoice_id
            if not request.invoice_id or request.invoice_id <= 0:
                return invoicestore_pb2.ApproveInvoiceResponse(succes=False, message="Valid invoice ID is required")

            # Approve the invoice
            result = self.db.approve_invoice(request.invoice_id)

            if not result:
                return invoicestore_pb2.ApproveInvoiceResponse(
                    succes=False, message=f"Failed to approve invoice {request.invoice_id}"
                )

            return invoicestore_pb2.ApproveInvoiceResponse(
                succes=True, message=f"Successfully approved invoice {request.invoice_id}"
            )

        except Exception as e:
            logger.error(f"Failed to approve invoice: {e}")
            return invoicestore_pb2.ApproveInvoiceResponse(succes=False, message=f"Failed to approve invoice: {e}")

    def RejectInvoice(self, request, context):
        try:
            logger.info(f"Received RejectInvoice request for invoice ID: {request.invoice_id}")

            # Validate invoice_id
            if not request.invoice_id or request.invoice_id <= 0:
                return invoicestore_pb2.RejectInvoiceResponse(succes=False, message="Valid invoice ID is required")

            # Validate reason
            if not request.reason:
                return invoicestore_pb2.RejectInvoiceResponse(succes=False, message="Rejection reason is required")

            # Reject the invoice
            result = self.db.reject_invoice(request.invoice_id, request.reason)

            if not result:
                return invoicestore_pb2.RejectInvoiceResponse(
                    succes=False, message=f"Failed to reject invoice {request.invoice_id}"
                )

            return invoicestore_pb2.RejectInvoiceResponse(
                succes=True, message=f"Successfully rejected invoice {request.invoice_id}"
            )

        except Exception as e:
            logger.error(f"Failed to reject invoice: {e}")
            return invoicestore_pb2.RejectInvoiceResponse(succes=False, message=f"Failed to reject invoice: {e}")

    def ListInvoices(self, request, context):
        """List invoices with optional filtering and pagination."""
        try:
            logger.info(
                f"Listing invoices with status filter: {request.status}, "
                f"limit: {request.limit}, offset: {request.offset}"
            )

            # Set defaults
            limit = request.limit if request.limit > 0 else 100
            offset = request.offset if request.offset >= 0 else 0
            status_filter = request.status if request.status else None

            # Get invoices from database
            invoices, total_count = self.db.list_invoices(status_filter=status_filter, limit=limit, offset=offset)

            # Convert to protobuf messages
            pb_invoices = []
            for invoice in invoices:
                pb_invoice = invoicestore_pb2.Invoice(
                    id=invoice.id or 0,
                    created_at=invoice.created_at or "",
                    lift_ticket=invoice.lift_ticket or "",
                    file_id=invoice.file_id or "",
                    status=invoice.status or "",
                    status_desc=invoice.status_desc or "",
                    vendor_name=invoice.vendor_name or "",
                    invoice_number=invoice.invoice_number or "",
                    invoice_date=invoice.invoice_date or "",
                    total_amount=invoice.total_amount or "",
                    purchase_order_number=invoice.purchase_order_number or "",
                    banking_details=invoice.banking_details or "",
                    payment_terms=invoice.payment_terms or "",
                    memo_description=invoice.memo_description or "",
                    shipped_to_address=invoice.shipped_to_address or "",
                    service_start_date=invoice.service_start_date or "",
                    service_end_date=invoice.service_end_date or "",
                    quantity=invoice.quantity or "",
                    unit_price=invoice.unit_price or "",
                    payment_type=invoice.payment_type or "",
                    due_date=invoice.due_date or "",
                    vendor_tax_id=invoice.vendor_tax_id or "",
                    snowflake_tax_id=invoice.snowflake_tax_id or "",
                    prepaid_flag=invoice.prepaid_flag or "",
                )
                pb_invoices.append(pb_invoice)

            logger.info(f"Successfully retrieved {len(pb_invoices)} invoices (total: {total_count})")

            return invoicestore_pb2.ListInvoicesResponse(
                success=True,
                message=f"Successfully retrieved {len(pb_invoices)} invoices",
                invoices=pb_invoices,
                total_count=total_count,
            )

        except Exception as e:
            logger.error(f"Failed to list invoices: {e}")
            return invoicestore_pb2.ListInvoicesResponse(
                success=False,
                message=f"Failed to list invoices: {e}",
                invoices=[],
                total_count=0,
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
