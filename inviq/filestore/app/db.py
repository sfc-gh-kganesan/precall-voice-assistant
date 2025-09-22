import sqlite3
from dataclasses import dataclass


@dataclass
class DbFile:
    id: str
    sha256: str
    path: str
    namespace: str
    created_at: str | None = None


class Db:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def insert_file(self, file: DbFile):
        """Initialize the database with the required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO file (id, sha256, path, namespace)
                    VALUES (?, ?, ?, ?)""",
                (file.id, file.sha256, file.path, file.namespace),
            )
            conn.commit()

    def get_file_by_id(self, file_id: str) -> DbFile | None:
        """Retrieve a file record by its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, sha256, path, namespace, created_at FROM file WHERE id = ?",
                (file_id,),
            )
            row = cursor.fetchone()
            if row:
                return DbFile(*row)
            return None

    def lookup_file_by_sha256(self, sha256: str, namespace: str) -> DbFile | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT
                    id, sha256, path, namespace, created_at
                FROM
                    file
                WHERE sha256 = ? AND namespace = ?
                """,
                (sha256, namespace),
            )
            row = cursor.fetchone()
            if row:
                return DbFile(*row)
            return None
