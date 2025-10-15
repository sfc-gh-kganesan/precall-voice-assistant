import logging
from typing import Dict
import json

from snowflake.connector import DictCursor
from langgraph.runtime import get_runtime
from langchain_core.tools import tool

from app.utils import ContextSchema, get_persistent_connection


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_query(query: str, params: dict = None) -> Dict[str, str]|None:
    """
    Run a query against the database.
    
    Args:
        query: SQL query string with %(name)s placeholders for parameters
        params: Dictionary of parameters to bind to the query
    """
    connection = None
    close_connection = False
    
    # Try to get connection from runtime context
    try:
        runtime = get_runtime(ContextSchema)
        connection = runtime.context.connection
        logger.info("Using connection from runtime context")
    except Exception as e:
        logger.info(f"Could not get connection from runtime: {str(e)}")
        connection = None
    
    # If no connection in context, create a temporary one (for LangGraph Studio)
    if not connection:
        logger.info("No connection in context, creating temporary connection")
        try:
            connection = get_persistent_connection()
            close_connection = True  # We created it, so we should close it
        except Exception as e:
            logger.error(f"Error creating connection: {str(e)}")
            return f"Error creating Snowflake connection: {str(e)}"
    
    try:
        with connection.cursor(DictCursor) as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        logger.error(f"Error running query: {str(e)}")
        raise
    finally:
        # Close connection if we created it temporarily
        if close_connection and connection:
            connection.close()

# TODO - Make table names dynamic and have agent ignore
@tool
def get_invoice_metadata(invoice_id: str) -> Dict[str, str] | str:
    """
    Get invoice(s) metadata associated with a specific invoice ID from the database.
    
    Args:
        invoice_id: The invoice id to look up
        
    Returns:
        A dictionary containing the invoice metadata
    """


    logger.info(f"Getting invoice metadata for invoice_id: {invoice_id}")

    # Prior AI decisions may influence future decisions despite changes and need to revisit
    query = """SELECT 
        * 
        EXCLUDE (AI_DECISION, AI_REASONING)
        FROM INVOICEIQ.SERVICE.INVOICES
        WHERE INVOICE_ID = %(invoice_id)s"""
    try:
        rows = run_query(query, {"invoice_id": invoice_id})

        if rows:
            if rows[0]["AI_PROCESSED_AT"] is not None:
                logger.info(f"Invoice has already been processed. No further action is needed.")
                return "Invoice has already been processed. No further action is needed."
            return rows
        else:
            return {}

    except Exception as e:
        logger.error(f"Error getting invoice metadata: {str(e)}")
        return f"Error getting invoice metadata: {str(e)}"
        
@tool
def get_purchase_order_header_metadata(purchase_order_number: str) -> Dict[str, str] | str:
    """
    Get purchase order header metadata associated with a specific purchase order number from the database.
    
    Args:
        purchase_order_number: The purchase order number to look up
        
    Returns:
        A dictionary containing the purchase order header metadata
    """


    logger.info(f"Getting purchase order header metadata for purchase_order_number: {purchase_order_number}")

    query = f"""SELECT 
        * 
        FROM INVOICEIQ.SERVICE.PURCHASE_ORDER
        where PO_HEADER_NUMBER = '{purchase_order_number}'"""
    try:
        rows = run_query(query)

        if rows:
            return rows
        else:
            return {}

    except Exception as e:
        logger.error(f"Error getting purchase order header metadata: {str(e)}")
        return f"Error getting purchase order header metadata: {str(e)}"


@tool
def get_purchase_order_line_item_metadata(purchase_order_number: str) -> Dict[str, str] | str:
    """
    Get purchase order line item metadata associated with a specific purchase order number from the database.
    
    Args:
        purchase_order_number: The purchase order number to look up
        
    Returns:
        A dictionary containing the purchase order line item metadata
    """


    logger.info(f"Getting purchase order line item metadata for purchase_order_number: {purchase_order_number}")

    query = f"""SELECT 
        * 
        FROM INVOICEIQ.SERVICE.PURCHASE_ORDER_LINE_ITEM
        where PO_HEADER_NUMBER = '{purchase_order_number}'"""
    try:
        rows = run_query(query)

        if rows:
            return rows
        else:
            return {}

    except Exception as e:
        logger.error(f"Error getting purchase order line item metadata: {str(e)}")
        return f"Error getting purchase order line item metadata: {str(e)}"



@tool
def return_final_result(invoice_id: str, ai_decision: str, ai_reasoning: str) -> Dict[str, str]:
    """
    Returns the final decision to approve or reject the invoice and corresponding reasoning behind the decision.
    
    Args:
        invoice_id: The invoice_id being processed
        ai_decision: The final decision to approve or reject the invoice. Value should be one of `approve` or `reject`.
        ai_reasoning: The reasoning behind the final decision to approve or reject the invoice
        
    Returns:
        The final decision to approve or reject the invoice and corresponding reasoning behind the decision.
    """

    ai_decision = ai_decision.lower()

    logger.info(f"Recording the final result for invoice_id: {invoice_id}")

    logger.info(f"Final decision: {ai_decision}")
    try:
        logger.info(f"Final reasoning (truncated): {ai_reasoning[:20]}")
    except IndexError:
        logger.info(f"Final reasoning: {ai_reasoning}")

    return {
            "invoice_id": invoice_id,
            "ai_decision": ai_decision,
            "ai_reasoning": ai_reasoning
        }