import asyncio
import hashlib
import sqlite3
import uuid
from concurrent import futures
from pathlib import Path

import grpc
from py_protos import filestore_pb2, filestore_pb2_grpc


class FileStoreServicer(filestore_pb2_grpc.FileStoreServicer):
    def __init__(self):
        self.upload_dir = Path("local-storage")
        self.upload_dir.mkdir(exist_ok=True)
        self.db_path = "filestore.db"

    def UploadFile(self, request_iterator, context):
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

            if not filename:
                return filestore_pb2.UploadResponse(
                    success=False, message="No filename provided", file_id=""
                )

            file_path = self.upload_dir / f"{file_id}_{filename}"
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Calculate SHA256 hash
            sha256_hash = hashlib.sha256(file_content).hexdigest()

            # Write to database
            self.insert_file_record(file_id, sha256_hash, str(file_path), "default")

            return filestore_pb2.UploadResponse(
                success=True,
                message=f"File uploaded successfully as {file_path.name}",
                file_id=file_id,
            )

        except Exception as e:
            return filestore_pb2.UploadResponse(
                success=False, message=f"Upload failed: {str(e)}", file_id=""
            )

    def insert_file_record(self, file_id, sha256_hash, file_path, namespace):
        """Insert a new file record into the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO file (id, sha256, path, namespace)
                       VALUES (?, ?, ?, ?)""",
                    (file_id, sha256_hash, file_path, namespace),
                )
                conn.commit()
                print(
                    f'Inserted file "{file_path}" record into database under namespace {namespace}'  # noqa: E501
                )
        except Exception as e:
            print(f"Warning: Could not insert file record: {e}")


async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    filestore_pb2_grpc.add_FileStoreServicer_to_server(FileStoreServicer(), server)

    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)

    print(f"Starting gRPC server on {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        print("Server stopped")
        await server.stop(0)


if __name__ == "__main__":
    asyncio.run(serve())
