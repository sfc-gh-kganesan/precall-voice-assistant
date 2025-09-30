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
    id: int | None = None
    created_at: str | None = None
    status: int | None = None


@contextmanager
def get_db_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def status_to_enum(status: str) -> invoicestore_pb2.SubmissionStatus:
    status_mapping = {
        "PENDING": invoicestore_pb2.SUBMISSION_STATUS_PENDING,
        "PROCESSING": invoicestore_pb2.SUBMISSION_STATUS_PROCESSING,
        "COMPLETED": invoicestore_pb2.SUBMISSION_STATUS_COMPLETED,
        "FAILED": invoicestore_pb2.SUBMISSION_STATUS_REJECTED,
    }
    return status_mapping.get(status.upper(), invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN)


def status_from_enum(status: invoicestore_pb2.SubmissionStatus) -> str:
    int_mapping = {
        invoicestore_pb2.SUBMISSION_STATUS_PENDING: "PENDING",
        invoicestore_pb2.SUBMISSION_STATUS_PROCESSING: "PROCESSING",
        invoicestore_pb2.SUBMISSION_STATUS_COMPLETED: "COMPLETED",
        invoicestore_pb2.SUBMISSION_STATUS_REJECTED: "REJECTED",
    }
    return int_mapping.get(status, "UNKNOWN")


class Db:
    def __init__(self, db_path: str):
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
                    RETURNING *
                """,
                (json.dumps(file_ids), lift_ticket, status_from_enum(status)),
            )
            new_row = cursor.fetchone()
            conn.commit()
        return SubmissionSchema(*new_row) if new_row else None

    def get_submission_by_id(self, id: int) -> SubmissionSchema | None:
        """Retrieve a submission record by its ID."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, file_ids, lift_ticket, created_at FROM submission WHERE id = ?",
                (id,),
            )
            row = cursor.fetchone()
            if row:
                return SubmissionSchema(*row)
            return None
