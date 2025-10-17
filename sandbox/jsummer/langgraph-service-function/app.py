import uvicorn
from fastapi import FastAPI, Request

from graph import run_workflow
from utils import is_running_in_spcs_container, unpack_function_request

app = FastAPI()


@app.post("/process")
async def process(request: Request):

    try:
        body = await request.json()

        if is_running_in_spcs_container():
            name = unpack_function_request(body)

        else:
            name = body.get("name")

    except Exception as e:
        return {"Error unpacking request.": str(e)}

    try:
        if not name:
            return {"Error": "Name is required"}
        else:
            result = run_workflow(name)
    except Exception as e:
        return {"Error running workflow": str(e)}

    if is_running_in_spcs_container():
        return {"data": [[0, result]]}
    else:
        return {"result": result}
    


if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)