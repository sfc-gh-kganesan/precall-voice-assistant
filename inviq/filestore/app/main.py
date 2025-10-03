import asyncio
import hashlib
import os
import uuid
from concurrent import futures
from pathlib import Path

import grpc
from py_protos import filestore_pb2, filestore_pb2_grpc

from .db import Db, DbFile


class FileStoreServicer(filestore_pb2_grpc.FileStoreServicer):
    def __init__(self):
        self.upload_dir = Path(os.getenv("FILESTORE_UPLOAD_PATH", "uploads"))
        self.upload_dir.mkdir(exist_ok=True)
        data_dir = Path(os.getenv("FILESTORE_DATA_PATH", "db"))
        db_path = data_dir.joinpath("filestore.db")
        self.db = Db(db_path=db_path)

    def UploadFile(self, request_iterator, context):
        namespace = "local-storage"

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
                return filestore_pb2.UploadResponse(success=False, message="No filename provided", file_id="")

            # Calculate SHA256 hash
            sha256_hash = hashlib.sha256(file_content).hexdigest()

            # Check if file already exists in DB
            existing_file = self.db.lookup_file_by_sha256(sha256_hash, namespace)

            if existing_file is not None:
                return filestore_pb2.UploadResponse(
                    success=True,
                    message="File with matching hash and namespace already exists.",
                    file_id=existing_file.id,
                )

            # Save file to local storage
            file_path = self.upload_dir / f"{file_id}_{filename}"
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Write to database
            self.db.insert_file(DbFile(file_id, sha256_hash, str(file_path), namespace))

            return filestore_pb2.UploadResponse(
                success=True,
                message=f"File uploaded successfully as {file_path.name}",
                file_id=file_id,
            )

        except Exception as e:
            return filestore_pb2.UploadResponse(success=False, message=f"Upload failed: {str(e)}", file_id="")

    def DownloadFile(self, request, context):
        try:
            # Get file info from database
            file_info = self.db.get_file_by_id(request.file_id)

            if file_info is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"File with ID {request.file_id} not found")
                return

            # Read file from local storage
            file_path = Path(file_info.path)
            if not file_path.exists():
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"File {file_path} not found on disk")
                return

            # Stream file content in chunks
            chunk_size = 1024 * 1024  # 1MB chunks
            filename = file_path.name

            with open(file_path, "rb") as f:
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break

                    # Check if this is the last chunk
                    next_chunk = f.read(1)
                    is_last = len(next_chunk) == 0
                    if next_chunk:
                        f.seek(-1, 1)  # Go back one byte

                    yield filestore_pb2.FileChunk(filename=filename, content=chunk_data, is_last=is_last)

                    if is_last:
                        break

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Download failed: {str(e)}")
            return


async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    filestore_pb2_grpc.add_FileStoreServicer_to_server(FileStoreServicer(), server)

    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)

    print(f"Starting filestore gRPC server on {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        print("Server stopped")
        await server.stop(0)


if __name__ == "__main__":
    asyncio.run(serve())
