# main.py
import uvicorn
from fastapi import FastAPI, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from typing import Any, Dict

from .graph import create_graph

# class ProcessTicketRequest(BaseModel):
#     ticket_number: str

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

        elif "ticket_number" in body:
            # Direct API call format: {"ticket_number": "value"}
            ticket_number = body["ticket_number"]
            row_index = 0

        else:
            return {"data": [[0, "Error: Invalid request format. Expected 'ticket_number' or 'data' field."]]}
        
        # Process the ticket (common logic)
        graph = create_graph()
        inputs = {"messages": [HumanMessage(content=f"Process ticket: {ticket_number}")]}
        result = graph.invoke(inputs)
        ai_response = result["messages"][-1].content
        
        # Return response in appropriate format
        if is_snowflake_format:
            return {"data": [[row_index, ai_response]]}
        else:
            return {"response": ai_response}
        
    except Exception as e:
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