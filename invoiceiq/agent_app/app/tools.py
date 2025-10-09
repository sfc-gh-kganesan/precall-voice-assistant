import logging
from typing import Dict

from snowflake.connector import DictCursor
from langgraph.runtime import get_runtime
from langchain_core.tools import tool

from .utils import ContextSchema


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_query(query: str) -> Dict[str, str]|None:
    """
    Run a query against the database.
    """
    try: # Get connection from runtime
        runtime = get_runtime(ContextSchema)
        connection = runtime.context.connection
    except Exception as e:
        logger.error(f"Error getting connection from runtime: {str(e)}")
        return f"Error getting Snowflake connection: {str(e)}"
    if not connection:
        return f"Error getting Snowflake connection from runtime: No connection available"
    
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        logger.error(f"Error running query: {str(e)}")
        raise


@tool
def get_ticket_metadata(ticket_number: str) -> Dict[str, str] | str:
    """
    Get metadata for a specific LIFT ticket number and corresponding email from the database.
    
    Args:
        ticket_number: The ticket number to look up
        
    Returns:
        A dictionary containing the ticket metadata
    """

    logger.info(f"Getting ticket metadata for ticket number: {ticket_number}")

    query = f"""SELECT * EXCLUDE (ai_result, ai_decision, ai_reasoning) FROM invoiceiq.service.ticket_metadata 
                WHERE ticket_number = '{ticket_number}'"""  
    try:
        rows = run_query(query)

        if rows:
            return rows
        else:
            return {}

    except Exception as e:
        logger.error(f"Error getting ticket metadata: {str(e)}")
        return f"Error getting ticket metadata: {str(e)}"


@tool
def get_invoice_metadata(ticket_number: str) -> Dict[str, str] | str:
    """
    Get invoice(s) metadata associated with a specific LIFT ticket number from the database.
    
    Args:
        ticket_number: The ticket number to look up
        
    Returns:
        A dictionary containing the invoice(s) metadata
    """


    logger.info(f"Getting invoice metadata for ticket number: {ticket_number}")

    query = f"""SELECT 
        inv.* 
        FROM invoiceiq.service.file_metadata inv
        join invoiceiq.service.ticket_metadata tick
        using (submission_id)
        where tick.ticket_number = '{ticket_number}'"""
    try:
        rows = run_query(query)

        if rows:
            return rows
        else:
            return {}

    except Exception as e:
        logger.error(f"Error getting invoice metadata: {str(e)}")
        return f"Error getting invoice metadata: {str(e)}"


@tool
def return_final_result(ticket_number: str, summary: str, relevant_details: str) -> Dict[str, str] | str:
    """
    Return the final result based on the summary and relevant details.
    
    Args:
        ticket_number: The ticket number being processed
        summary: The summary of the ticket being processed
        relevant_details: The relevant details of the ticket being processed
        
    Returns:
        A dictionary containing the final result
    """

    logger.info(f"Returning final result for ticket number: {ticket_number}")

    return {
        "ticket_number": ticket_number,
        "summary": summary,
        "relevant_details": relevant_details
        }
