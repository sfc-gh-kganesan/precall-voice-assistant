from typing import Union

from fastapi import FastAPI
from demo.db.client import DbClient

app = FastAPI()
db = DbClient(host="localhost", port=50051)

@app.get("/")
def read_root():
    return {"ok": True}


@app.get("/workflows")
def read_workflows():
    wf = db.ListWorkflows()
    return {"workflows": wf}


@app.get("/workflow/{id}")
def read_workflow(id: int):
    return {"id": id}
