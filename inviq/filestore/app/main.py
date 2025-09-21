import asyncio
import uuid
from concurrent import futures
from pathlib import Path

import grpc
from py_protos import filestore_pb2, filestore_pb2_grpc


class FileStoreServicer(filestore_pb2_grpc.FileStoreServicer):
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

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

            return filestore_pb2.UploadResponse(
                success=True,
                message=f"File uploaded successfully as {file_path.name}",
                file_id=file_id,
            )

        except Exception as e:
            return filestore_pb2.UploadResponse(
                success=False, message=f"Upload failed: {str(e)}", file_id=""
            )


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
