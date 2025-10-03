import argparse
from pathlib import Path

import grpc
from py_protos import extractor_pb2, extractor_pb2_grpc


def extract_file(path: str, grpc_url: str) -> None:
    channel = grpc.insecure_channel(grpc_url)
    stub = extractor_pb2_grpc.ExtractorStub(channel)

    file = Path(path)

    if not file.exists():
        print(f"ERROR: {path} does not exist")
        return

    def chunk_generator():
        chunk_size = 1024 * 1024  # 1MB chunks
        filename = file.name or "unknown"

        for i in range(0, len(content), chunk_size):
            chunk_data = content[i : i + chunk_size]
            is_last = (i + chunk_size) >= len(content)

            yield extractor_pb2.FileChunk(filename=filename, content=chunk_data, is_last=is_last)

    content = file.read_bytes()
    response = stub.Extract(chunk_generator())
    print(response)
    channel.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test client to exercise the extractor service")
    parser.add_argument(
        "--filename", type=str, default="../collector/test_files/invoice_01.pdf", help="Path to input file"
    )
    parser.add_argument("--grpc_url", type=str, default="localhost:50052", help="extractor grpc url")
    args = parser.parse_args()
    extract_file(args.filename, args.grpc_url)
