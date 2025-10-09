# main.py

import logging
import uvicorn
from fastapi import FastAPI, Request
from langchain_core.messages import HumanMessage

from .graph import run_workflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/healthcheck")
def readiness_probe():
    return {"status": "healthy"}

@app.post("/process")
async def process_ticket(request: Request):
    """
    Process ticket endpoint that handles both direct API calls and Snowflake service function calls.
    Snowflake sends data in format: {"data": [[0, "ticket_number"]]}
    Direct API calls send: {"ticket_number": "value"}
    """
    try:
        # Get the raw request body
        body = await request.json()
        is_snowflake_format = False
        
        # Extract ticket number and determine response format
        if "data" in body and isinstance(body["data"], list) and len(body["data"]) > 0:
            # Snowflake service function format: {"data": [[0, "xyz"]]}
            input_rows = body["data"]
            ticket_number = input_rows[0][1] if len(input_rows[0]) > 1 else input_rows[0][0]
            row_index = input_rows[0][0]  # Preserve the row index
            is_snowflake_format = True

        elif body: # If Direct API call is sent we expect the body to be the ticket number or the LLM to extract it
            ticket_number = body
            row_index = 0

        else:
            return {"data": [[0, "Error: Invalid request. Either input is empty or doesn't follow Snowflake service function format."]]}


        ai_response = run_workflow(f"Process ticket: {ticket_number}")
        
        # Return response in appropriate format
        if is_snowflake_format:
            return {"data": [[row_index, ai_response]]}
        else:
            return {"response": ai_response}

        
    except Exception as e:
        logger.error(f"Failed to process ticket: {str(e)}")
        # Try to preserve row index if available, otherwise use 0
        try:
            if "data" in body and isinstance(body["data"], list) and len(body["data"]) > 0:
                row_index = body["data"][0][0]
            else:
                row_index = 0
        except:
            row_index = 0
        
        return {"data": [[row_index, f"Error: Failed to process ticket: {str(e)}"]]}


if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)