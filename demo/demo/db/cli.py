import typer
from . import server

app = typer.Typer()


@app.callback()
def callback():
    """
    db command
    """


@app.command()
def serve(port: int = 50051):
    """
    Start the Database gRPC service
    """
    print(f"Starting server on port {port}...")
    server.run(port)
