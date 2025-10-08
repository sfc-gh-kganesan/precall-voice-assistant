import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from py_protos import invoicestore_pb2


@dataclass
class SubmissionSchema:
    file_ids: list[str]
    lift_ticket: str
    created_at: str | None = None
    id: int | None = None
    status: str | None = None


@dataclass
class InvoiceSchema:
    file_id: str
    lift_ticket: str
    id: int | None = None
    created_at: str | None = None
    status: str | None = None
    status_desc: str | None = None
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    total_amount: str | None = None
    purchase_order_number: str | None = None
    banking_details: str | None = None
    payment_terms: str | None = None
    memo_description: str | None = None
    shipped_to_address: str | None = None
    service_start_date: str | None = None
    service_end_date: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    payment_type: str | None = None
    due_date: str | None = None
    vendor_tax_id: str | None = None
    snowflake_tax_id: str | None = None
    prepaid_flag: str | None = None


@contextmanager
def get_db_connection(db_path: Path):
    conn = sqlite3.connect(db_path.absolute())
    try:
        yield conn
    finally:
        conn.close()


def submission_status_to_enum(status: str) -> invoicestore_pb2.SubmissionStatus:
    status_mapping = {
        "PENDING": invoicestore_pb2.SUBMISSION_STATUS_PENDING,
        "PROCESSING": invoicestore_pb2.SUBMISSION_STATUS_PROCESSING,
        "COMPLETED": invoicestore_pb2.SUBMISSION_STATUS_COMPLETED,
        "FAILED": invoicestore_pb2.SUBMISSION_STATUS_REJECTED,
    }
    return status_mapping.get(status.upper(), invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN)


def submission_status_from_enum(status: invoicestore_pb2.SubmissionStatus) -> str:
    int_mapping = {
        invoicestore_pb2.SUBMISSION_STATUS_PENDING: "PENDING",
        invoicestore_pb2.SUBMISSION_STATUS_PROCESSING: "PROCESSING",
        invoicestore_pb2.SUBMISSION_STATUS_COMPLETED: "COMPLETED",
        invoicestore_pb2.SUBMISSION_STATUS_REJECTED: "REJECTED",
    }
    return int_mapping.get(status, "UNKNOWN")


def invoice_status_to_enum(status: str) -> invoicestore_pb2.InvoiceStatus:
    status_mapping = {
        "PENDING": invoicestore_pb2.INVOICE_STATUS_PENDING,
        "APPROVED": invoicestore_pb2.INVOICE_STATUS_APPROVED,
        "REJECTED": invoicestore_pb2.INVOICE_STATUS_REJECTED,
    }
    return status_mapping.get(status.upper(), invoicestore_pb2.INVOICE_STATUS_UNKNOWN)


def invoice_status_from_enum(status: invoicestore_pb2.InvoiceStatus) -> str:
    int_mapping = {
        invoicestore_pb2.INVOICE_STATUS_PENDING: "PENDING",
        invoicestore_pb2.INVOICE_STATUS_APPROVED: "APPROVED",
        invoicestore_pb2.INVOICE_STATUS_REJECTED: "REJECTED",
    }
    return int_mapping.get(status, "UNKNOWN")


class Db:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database using the init.sql script."""
        sql_file = Path(__file__).parent.parent / "sql" / "init.sql"

        with get_db_connection(self.db_path) as conn:
            with open(sql_file) as f:
                sql_script = f.read()
            conn.executescript(sql_script)

    def insert_submission(
        self, file_ids: list[str], lift_ticket: str, status: invoicestore_pb2.SubmissionStatus
    ) -> SubmissionSchema | None:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO submission (file_ids, lift_ticket, status)
                    VALUES (?, ?, ?)
                    RETURNING file_ids, lift_ticket, created_at, id, status
                """,
                (json.dumps(file_ids), lift_ticket, submission_status_from_enum(status)),
            )
            new_row = cursor.fetchone()
            conn.commit()
        return SubmissionSchema(*new_row) if new_row else None

    def get_submission_by_id(self, id: int) -> SubmissionSchema | None:
        """Retrieve a submission record by its ID."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT file_ids, lift_ticket, created_at, id, status FROM submission WHERE id = ?",
                (id,),
            )
            row = cursor.fetchone()
            if row:
                return SubmissionSchema(*row)
            return None

    def get_submission_by_lift_ticket(self, lift_ticket: str) -> SubmissionSchema | None:
        """Retrieve a submission record by its lift ticket."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT file_ids, lift_ticket, created_at, id, status FROM submission WHERE lift_ticket = ?",
                (lift_ticket,),
            )
            row = cursor.fetchone()
            if row:
                return SubmissionSchema(
                    file_ids=json.loads(row[0]),
                    lift_ticket=row[1],
                    created_at=row[2],
                    id=row[3],
                    status=row[4],
                )
            return None

    def get_oldest_pending_submission(self) -> SubmissionSchema | None:
        """Retrieve the oldest submission with PENDING status."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT file_ids, lift_ticket, created_at, id, status
                   FROM submission
                   WHERE status = ?
                   ORDER BY created_at ASC
                   LIMIT 1""",
                ("PENDING",),
            )
            row = cursor.fetchone()
            if row:
                return SubmissionSchema(
                    file_ids=json.loads(row[0]),
                    lift_ticket=row[1],
                    created_at=row[2],
                    id=row[3],
                    status=row[4],
                )
            return None

    def create_invoice(self, invoice: InvoiceSchema) -> InvoiceSchema | None:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO invoice (
                  lift_ticket,
                  file_id,
                  status,
                  vendor_name,
                  invoice_number,
                  invoice_date,
                  total_amount,
                  purchase_order_number,
                  banking_details,
                  payment_terms,
                  memo_description,
                  shipped_to_address,
                  service_start_date,
                  service_end_date,
                  quantity,
                  unit_price,
                  payment_type,
                  due_date,
                  vendor_tax_id,
                  snowflake_tax_id,
                  prepaid_flag
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING file_id, lift_ticket, id, created_at, status, status_desc, vendor_name,
                          invoice_number, invoice_date, total_amount, purchase_order_number,
                          banking_details, payment_terms, memo_description, shipped_to_address,
                          service_start_date, service_end_date, quantity, unit_price, payment_type,
                          due_date, vendor_tax_id, snowflake_tax_id, prepaid_flag
              """,
                (
                    invoice.lift_ticket,
                    invoice.file_id,
                    invoice_status_from_enum(invoicestore_pb2.INVOICE_STATUS_PENDING),
                    invoice.vendor_name,
                    invoice.invoice_number,
                    invoice.invoice_date,
                    invoice.total_amount,
                    invoice.purchase_order_number,
                    invoice.banking_details,
                    invoice.payment_terms,
                    invoice.memo_description,
                    invoice.shipped_to_address,
                    invoice.service_start_date,
                    invoice.service_end_date,
                    invoice.quantity,
                    invoice.unit_price,
                    invoice.payment_type,
                    invoice.due_date,
                    invoice.vendor_tax_id,
                    invoice.snowflake_tax_id,
                    invoice.prepaid_flag,
                ),
            )
            new_row = cursor.fetchone()
            conn.commit()
            return InvoiceSchema(*new_row) if new_row else None

    def approve_invoice(self, invoice_id) -> bool:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE invoice
                SET status = ?
                WHERE id = ?
                """,
                (invoice_status_from_enum(invoicestore_pb2.INVOICE_STATUS_APPROVED), invoice_id),
            )
            conn.commit()
            return True

    def reject_invoice(self, invoice_id, reason) -> bool:
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE invoice
                SET status = ?,
                    status_desc = ?
                WHERE id = ?
                """,
                (invoice_status_from_enum(invoicestore_pb2.INVOICE_STATUS_REJECTED), reason, invoice_id),
            )
            conn.commit()
            return True

    def list_invoices(self, status_filter=None, limit=100, offset=0) -> tuple[list[InvoiceSchema], int]:
        """
        List invoices with optional filtering and pagination.

        Returns:
            tuple: (list of invoices, total count)
        """
        with get_db_connection(self.db_path) as conn:
            # Build the query with optional status filter
            where_clause = ""
            params = []

            if status_filter:
                where_clause = "WHERE status = ?"
                params.append(status_filter)

            # Get total count
            count_query = f"SELECT COUNT(*) FROM invoice {where_clause}"
            cursor = conn.execute(count_query, params)
            total_count = cursor.fetchone()[0]

            # Get paginated results
            query = f"""
                SELECT id, created_at, lift_ticket, file_id, status, status_desc,
                       vendor_name, invoice_number, invoice_date, total_amount,
                       purchase_order_number, banking_details, payment_terms,
                       memo_description, shipped_to_address, service_start_date,
                       service_end_date, quantity, unit_price, payment_type,
                       due_date, vendor_tax_id, snowflake_tax_id, prepaid_flag
                FROM invoice
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """

            cursor = conn.execute(query, params + [limit, offset])
            rows = cursor.fetchall()

            invoices = []
            for row in rows:
                invoices.append(
                    InvoiceSchema(
                        id=row[0],
                        created_at=row[1],
                        lift_ticket=row[2],
                        file_id=row[3],
                        status=row[4],
                        status_desc=row[5],
                        vendor_name=row[6],
                        invoice_number=row[7],
                        invoice_date=row[8],
                        total_amount=row[9],
                        purchase_order_number=row[10],
                        banking_details=row[11],
                        payment_terms=row[12],
                        memo_description=row[13],
                        shipped_to_address=row[14],
                        service_start_date=row[15],
                        service_end_date=row[16],
                        quantity=row[17],
                        unit_price=row[18],
                        payment_type=row[19],
                        due_date=row[20],
                        vendor_tax_id=row[21],
                        snowflake_tax_id=row[22],
                        prepaid_flag=row[23],
                    )
                )

            return invoices, total_count
