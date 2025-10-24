import logging
import json
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage

from app.prompts import AI_EXTRACT_PROMPT, HUMAN_MESSAGE_PROMPT, SYSTEM_MESSAGE
from app.utils import run_query
from app.model import CortexModel
from app.utils import State, AI_Decision_Output, CLASS_OPTIONS, FRESH_OR_RERUN_OPTIONS
import app.queries as queries

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




def classify_invoice(state: State) -> State:
    """
    Classify the invoice as an invoice or not an invoice.

    Example options:
    CLASS_OPTIONS = ["invoice", "not an invoice"]

    Classification passed to state['classification'].
    """

    relative_path = state["relative_path"]
    logger.info(f"Classifying file as invoice or not: {relative_path}")

    stage_name = state["stage_name"]
    if not stage_name.startswith("@"):
        stage_name = "@" + stage_name

    try:
        # Build class options list with proper SQL string formatting
        class_options_list = ','.join(f"'{opt}'" for opt in CLASS_OPTIONS)
        
        query = queries.CLASSIFY_QUERY.format(
            class_options_list=class_options_list
        )
        rows = run_query(query, 
            {
                "stage_name": stage_name, 
                "relative_path": relative_path
            })
        if rows and len(rows) > 0:
            try:
                classification = json.loads(rows[0].get("CLASSIFICATION")).get('label')

                if classification in CLASS_OPTIONS:
                    return {"classification": classification}
                else: # classification is None or not in CLASS_OPTIONS
                    logger.error(f"Invalid invoice classification: {classification}")
                    return {"classification": CLASS_OPTIONS[1]}
            except IndexError:
                logger.error(f"No invoice classification found for relative path: {relative_path}")
                return {"classification": CLASS_OPTIONS[1]}
            except Exception as e:
                logger.error(f"Error classifying invoice: {str(e)}")
                return {"classification": CLASS_OPTIONS[1]}
        else:
            logger.error(f"No invoice classification found for relative path: {relative_path}")
            return {"classification": CLASS_OPTIONS[1]}
    except Exception as e:
        logger.error(f"Error classifying invoice: {str(e)}")
        return {"classification": CLASS_OPTIONS[1]}


def fresh_or_rerun_router(state: State) -> Literal[FRESH_OR_RERUN_OPTIONS[0], FRESH_OR_RERUN_OPTIONS[1]]:
    """
    Determine if the invoice should be processed from scratch or using existing data.

    Example options:
    FRESH_OR_RERUN_OPTIONS = ["fresh", "rerun"]

    Returns:
        FRESH_OR_RERUN_OPTIONS[0] if the invoice should be processed from scratch
        FRESH_OR_RERUN_OPTIONS[1] if the invoice should be processed using existing data
    """
    
    if state.get("use_existing_ai_extract", False): # LangGraph Studio doesn't default a value for use_existing_ai_extract
        return FRESH_OR_RERUN_OPTIONS[1]
    else:   
        return FRESH_OR_RERUN_OPTIONS[0]


def class_router(state: State) -> Literal["__end__", "run_ai_extract"]:
    """
    Routes workflow to run_ai_extract if invoice classified as invoice or to END otherwise.


    Returns:
        "__end__" if invoice classified as 'not an invoice'
        "run_ai_extract" if invoice classified as 'invoice'
    """

    classification = state["classification"]
    if classification == CLASS_OPTIONS[0]:
        return "run_ai_extract"
    else:
        return "__end__"


def get_ai_extract_metadata(state: State) -> State:
    """
    Get existing AI extract metadata from Snowflake table for the invoice.

    Metadata passed to state['ai_extract_metadata'].
    """

    invoice_id = state["invoice_id"]
    target_table = state["target_table"]

    logger.info(f"Using existing AI extract metadata for invoice_id: {invoice_id}")
    try:
        query = queries.GET_AI_EXTRACT_METADATA_QUERY
        rows = run_query(query, {"invoice_id": invoice_id, "target_table": target_table})

        if rows and len(rows) > 0:
            try:
                return {"ai_extract_metadata": rows[0]}
            except IndexError:
                logger.error(f"No AI extract metadata found for invoice_id: {invoice_id}")
                return {"ai_extract_metadata": {}}
        else:
            logger.error(f"No AI extract metadata found for invoice_id: {invoice_id}")
            return {"ai_extract_metadata": {}}
    except Exception as e:
        logger.error(f"Error getting existing AI extract metadata: {str(e)}")
        return {"ai_extract_metadata": {}}



def run_ai_extract(state: State) -> State:
    """
    Run AI extract on the invoice.
    
    AI extract metadata passed to state['ai_extract_metadata'].
    """

    stage_name = state["stage_name"]
    if not stage_name.startswith("@"):
        stage_name = "@" + stage_name
    relative_path = state["relative_path"]

    logger.info(f"Running AI extract for relative path: {relative_path}")

    try:
        query = queries.RUN_AI_EXTRACT_QUERY
        rows = run_query(query, 
        {
            "stage_name": stage_name, 
            "relative_path": relative_path,
            "ai_extract_prompt": json.dumps(AI_EXTRACT_PROMPT)
        })

        if rows and len(rows) > 0:
            # AI_EXTRACT returns a single row, so extract the first row
            data = json.loads(rows[0].get("INVOICE_METADATA")).get('response')

            return {"ai_extract_metadata": data}
        else:
            logger.error(f"No AI extract metadata found for relative path: {relative_path}")
            return {"ai_extract_metadata": {}}

    except Exception as e:
        logger.error(f"Error running AI extract: {str(e)}")
        return {"ai_extract_metadata": {}}


def record_to_table(state: State):
    """
    Record AI extract and invoice metadata into Snowflake target_table in state.
    """

    if state.get("use_existing_ai_extract", False): # # LangGraph Studio doesn't default a value for use_existing_ai_extract
        return None
    
    invoice_id = state["invoice_id"]
    logger.info(f"Recording AI extract metadata for invoice_id: {invoice_id}")

    ai_extract_metadata = state["ai_extract_metadata"]
    target_table = state["target_table"]

    try:
        if ai_extract_metadata:
            json_string = json.dumps(ai_extract_metadata)

            # Use string formatting for table name (identifier) but keep parameterized queries for data values
            query = queries.RECORD_METADATA_QUERY
            rows = run_query(query, 
            {
                "json_string": json_string,
                "invoice_id": invoice_id,
                "target_table": target_table
            })
            logger.info(f"Number of rows inserted with AI Extract: {rows[0].get('number of rows inserted')}")
            return None
    except Exception as e:
        logger.error(f"Error recording AI extract metadata: {str(e)}")
        return None


def get_purchase_order_header_metadata(state: State) -> State:
    """
    Get purchase order header metadata from Snowflake table for the invoice.
    
    Metadata passed to state['purchase_order_header_metadata'].
    """

    invoice_id = state["invoice_id"]
    logger.info(f"Getting purchase order header metadata for invoice_id: {invoice_id}")

    ai_extract_metadata = state["ai_extract_metadata"]
    purchase_order_number = ai_extract_metadata.get("purchase_order_number")

    if not purchase_order_number:
        logger.warning(f"No purchase order number found in AI extract metadata")
        return {"purchase_order_header_metadata": {}}

    query = queries.GET_PURCHASE_ORDER_HEADER_METADATA_QUERY

    try:
        rows = run_query(query, {"purchase_order_number": purchase_order_number})

        if rows:
            return {"purchase_order_header_metadata": rows}
        else:
            logger.warning(f"No purchase order header metadata found for purchase_order_number: {purchase_order_number}")
            return {"purchase_order_header_metadata": {}}

    except Exception as e:
        logger.error(f"Error getting purchase order header metadata: {str(e)}")
        return {"purchase_order_header_metadata": {}}


def get_purchase_order_line_item_metadata(state: State) -> State:
    """
    Get purchase order line item metadata from Snowflake table for the invoice.
    
    Metadata passed to state['purchase_order_line_item_metadata'].
    """

    invoice_id = state["invoice_id"]
    logger.info(f"Getting purchase order line item metadata for invoice_id: {invoice_id}")

    ai_extract_metadata = state["ai_extract_metadata"]
    purchase_order_number = ai_extract_metadata.get("purchase_order_number")

    if not purchase_order_number:
        logger.warning(f"No purchase order number found in AI extract metadata")
        return {"purchase_order_line_item_metadata": {}}

    query = queries.GET_PURCHASE_ORDER_LINE_ITEM_METADATA_QUERY

    try:
        rows = run_query(query, {"purchase_order_number": purchase_order_number})

        if rows:
            return {"purchase_order_line_item_metadata": rows}
        else:
            logger.warning(f"No purchase order line item metadata found for purchase_order_number: {purchase_order_number}") 
            return {"purchase_order_line_item_metadata": {}}

    except Exception as e:
        logger.error(f"Error getting purchase order line item metadata: {str(e)}")
        return {"purchase_order_line_item_metadata": {}}


def call_model(state: State) -> State:
    """
    Call the model to determine if the invoice should be approved or rejected.
    
    AI decision passed to state['ai_decision'].
    AI reasoning passed to state['ai_reasoning'].
    """

    invoice_id = state["invoice_id"]
    logger.info(f"Calling model for invoice_id: {invoice_id}")

    model = CortexModel()
    ai_extract_metadata = state["ai_extract_metadata"]
    purchase_order_header_metadata = state["purchase_order_header_metadata"]
    purchase_order_line_item_metadata = state["purchase_order_line_item_metadata"]

    logger.info(f"Calling model: {model.model_name}")

    try:
        msg = [
            SystemMessage(content=SYSTEM_MESSAGE),
            HumanMessage(content=HUMAN_MESSAGE_PROMPT.format(
                ai_extract_metadata=ai_extract_metadata,
                purchase_order_header_metadata=purchase_order_header_metadata,
                purchase_order_line_item_metadata=purchase_order_line_item_metadata))
        ]
        response = model.model.with_structured_output(AI_Decision_Output).invoke(msg)
        logger.info(f"Model response received: {response.ai_decision}")
        
        return {"ai_decision": response.ai_decision, "ai_reasoning": response.ai_reasoning}
    except Exception as e:
        logger.error(f"Error calling model: {str(e)}")
        return {"ai_decision": "error", "ai_reasoning": f"Error: {str(e)}"}


def record_ai_decision(state: State):
    """
    Record AI decision into Snowflake target_table in state.
    """

    invoice_id = state["invoice_id"]
    logger.info(f"Recording AI decision for invoice_id: {invoice_id}")
    
    ai_decision = state["ai_decision"]
    ai_reasoning = state["ai_reasoning"]
    target_table = state["target_table"]

    try:
        query = queries.RECORD_AI_DECISION_QUERY
        rows = run_query(query, {"ai_decision": ai_decision, "ai_reasoning": ai_reasoning, "invoice_id": invoice_id, "target_table": target_table})
        logger.info(f"Number of rows updated with AI Decision: {rows[0].get('number of rows updated')}")
        return None
    except Exception as e:
        logger.error(f"Error recording AI decision: {str(e)}")