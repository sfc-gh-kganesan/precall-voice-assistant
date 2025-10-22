import uvicorn
import asyncio
from fastapi import FastAPI, Request

from graph import run_workflow
from utils import is_running_in_spcs_container, unpack_function_request

app = FastAPI()


@app.post("/process")
async def process(request: Request) -> str | dict:
    """
    Process a request to the LangGraph service function.

    If running in SPCS container, the request body is unpacked and the workflow is run for each input.
    If running locally, the request body is unpacked and the workflow is run for the single input.
    The response is returned in the same format as the input.

    For running localy, we extract the 'name' key from the request body and run the workflow with that value.

    Args:
        request: The request object

    Returns:
        A string or dictionary containing the result of the workflow.
    """

    try:
        body = await request.json()

        if is_running_in_spcs_container():
            inputs = unpack_function_request(body)
            if not inputs:
                return {"Error": "No data provided to process."}

            response = []
            n = len(inputs) # Number of distinct rows to process
            try:
                if n > 10: # Use asynchronous concurrency if there are more than 10 rows to process
                    tasks = [run_workflow(*input[1:]) for input in inputs]
                    results = await asyncio.gather(*tasks)
                    for i, input in enumerate(inputs):
                        response.append([input[0], results[i]])
                    return {"data": response}
                else:
                    for input in inputs:
                        result = await run_workflow(*input[1:])
                        response.append([input[0], result])
                return {"data": response}
            except Exception as e:
                return {"Error running workflow": str(e)}

        else:
           
            if not body:
                return {"Error": "No data provided to process."}
            try:
                result = await run_workflow(body)
                return result
            except Exception as e:
                return {"Error running workflow": str(e)}


    except Exception as e:
        return {"Error unpacking request.": str(e)}
    

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)