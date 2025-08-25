from typing import List
import grpc
from .grpc import db_pb2
from .grpc import db_pb2_grpc


class DbClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def channel(self) -> grpc.Channel:
        return grpc.insecure_channel(f"{self.host}:{self.port}")

    def ListWorkflows(self) -> List[str]:
        with self.channel() as channel:
            stub = db_pb2_grpc.DbStub(channel)
            response = stub.ListWorkflows(db_pb2.ListWorkflowsRequest())
            return [w for w in response.workflows]
