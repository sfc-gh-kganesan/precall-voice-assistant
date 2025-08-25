import grpc
from concurrent import futures
from .grpc import db_pb2
from .grpc import db_pb2_grpc


class DbService(db_pb2_grpc.DbServicer):
    def ListWorkflows(self, request, context):
        print("Invoke ListWorkflows()")
        response = db_pb2.ListWorkflowsResponse()
        response.workflows.append("wf1")
        response.workflows.append("wf2")
        response.workflows.append("wf3")
        return response


def run(port: int) -> grpc.server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    db_pb2_grpc.add_DbServicer_to_server(DbService(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    server.wait_for_termination()
    return server

