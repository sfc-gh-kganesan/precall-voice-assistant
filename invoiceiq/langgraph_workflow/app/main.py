# main.py

import logging
import uvicorn
from fastapi import FastAPI, Request
from langchain_core.messages import HumanMessage

from app.graph import run_workflow

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
        is_snowflake_format = False
        
        # Extract invoice_id and determine response format
        if "data" in body and isinstance(body["data"], list) and len(body["data"]) > 0:
            # Snowflake service function format: {"data": [[0, "target_table", "invoice_id", "relative_path", "stage_name"]]}
            input_rows = body["data"]
            target_table = input_rows[0][1]
            invoice_id = input_rows[0][2]
            relative_path = input_rows[0][3]
            stage_name = input_rows[0][4]
            try:
                use_existing_ai_extract = input_rows[0][5]
            except IndexError:
                use_existing_ai_extract = False
            row_index = input_rows[0][0]  # Preserve the row index
            is_snowflake_format = True

        elif body: # If Direct API call is sent we expect the body to be the invoice_id or the LLM to extract it
            target_table = body["target_table"]
            invoice_id = body["invoice_id"]
            relative_path = body["relative_path"]
            stage_name = body["stage_name"]
            use_existing_ai_extract = bool(body.get("use_existing_ai_extract", False))
            row_index = 0

        else:
            return {"data": [[0, "Error: Invalid request. Either input is empty or doesn't follow Snowflake service function format."]]}


        ai_response = run_workflow(target_table, invoice_id, relative_path, stage_name, use_existing_ai_extract)
        
        # Return response in appropriate format
        if is_snowflake_format:
            return {"data": [[row_index, ai_response]]}
        else:
            return {"response": ai_response}

        
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