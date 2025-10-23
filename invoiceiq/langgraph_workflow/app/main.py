# main.py
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, Request


from app.graph import run_workflow
from app.utils import unpack_function_request, is_running_in_spcs_container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/healthcheck")
def readiness_probe():
    return {"status": "healthy"}

@app.post("/process")
async def process_invoice(request: Request):
    """
    Process invoice endpoint that handles both direct API calls and Snowflake service function calls.
    Snowflake sends data in format: {"data": [[0, "target_table", "invoice_id", "relative_path", "stage_name"]]}
    Direct API calls send: {"target_table": "value", "invoice_id": "value", "relative_path": "value", "stage_name": "value"}
    """
    try:
        # Get the raw request body
        body = await request.json()
        if is_running_in_spcs_container():
            inputs = unpack_function_request(body)
            if not inputs:
                return {"data": [[0, "Error: Invalid request. Either input is empty or doesn't follow Snowflake service function format."]]}
            response = []
            n = len(inputs)
            logger.info(f"Processing {n} rows")
            try:
                if n > 2:
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
                return {"data": [[0, f"Error: Failed to process invoice_id: {str(e)}"]]}
        
        else:
            if not body:
                return "Error: Invalid request. Either input is empty or doesn't follow Snowflake service function format."
            try:
                result = await run_workflow(**body)
                return result
            except Exception as e:
                return f"Error: Failed to process request: {str(e)}"

        
    except Exception as e:
        logger.error(f"Failed to process invoice_id: {str(e)}")
        # Try to preserve row index if available, otherwise use 0
        try:
            if "data" in body and isinstance(body["data"], list) and len(body["data"]) > 0:
                row_index = body["data"][0][0]
            else:
                row_index = 0
        except:
            row_index = 0
        
        return {"data": [[row_index, f"Error: Failed to process invoice_id: {str(e)}"]]}


if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)