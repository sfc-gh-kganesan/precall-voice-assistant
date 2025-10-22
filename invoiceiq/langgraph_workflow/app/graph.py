import logging

from langgraph.graph import StateGraph, START, END

from app.utils import ContextSchema, get_persistent_connection, State, AI_Decision_Output, FRESH_OR_RERUN_OPTIONS
import app.nodes as nodes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_graph() -> StateGraph:
    """
    Create the workflow graph.

    Returns:
        Workflow graph compiled for execution
    """

    workflow = StateGraph(
        State, 
        context_schema = ContextSchema,
        output_schema = AI_Decision_Output
        )

    workflow.add_node("run_ai_extract", nodes.run_ai_extract)
    workflow.add_node("classify_invoice", nodes.classify_invoice)
    workflow.add_node("get_ai_extract_metadata", nodes.get_ai_extract_metadata)
    workflow.add_node("record_ai_extract_metadata", nodes.record_ai_extract_metadata)
    workflow.add_node("get_purchase_order_header_metadata", nodes.get_purchase_order_header_metadata)
    workflow.add_node("get_purchase_order_line_item_metadata", nodes.get_purchase_order_line_item_metadata)
    workflow.add_node("call_model", nodes.call_model)
    workflow.add_node("record_ai_decision", nodes.record_ai_decision)

    # Entry point: Decide if need to run from scratch or use existing data and skip classification
    workflow.add_conditional_edges(START, nodes.fresh_or_rerun_router, 
        {FRESH_OR_RERUN_OPTIONS[0]: "classify_invoice", 
        FRESH_OR_RERUN_OPTIONS[1]: "get_ai_extract_metadata"}
        )

    # Fresh run: Classify invoice and run AI extract
    workflow.add_conditional_edges("classify_invoice", nodes.class_router)
    workflow.add_edge("run_ai_extract", "get_purchase_order_header_metadata")
    workflow.add_edge("run_ai_extract", "get_purchase_order_line_item_metadata")
    workflow.add_edge("run_ai_extract", "record_ai_extract_metadata")
    workflow.add_edge("get_purchase_order_header_metadata", "call_model")
    workflow.add_edge("get_purchase_order_line_item_metadata", "call_model")
    workflow.add_edge("call_model", "record_ai_decision")
    workflow.add_edge("record_ai_decision", END)
    workflow.add_edge("record_ai_extract_metadata", END)

    # Rerun: Use existing data and skip classification
    workflow.add_edge("get_ai_extract_metadata", "get_purchase_order_header_metadata")
    workflow.add_edge("get_ai_extract_metadata", "get_purchase_order_line_item_metadata")

    return workflow.compile()



def run_workflow(target_table: str, invoice_id: str, relative_path: str, stage_name: str, use_existing_ai_extract: bool = False) -> AI_Decision_Output | str:
    """
    Run the workflow graph.

    Args:
        target_table: Snowflake table name to store/retrieve the invoice metadata
        invoice_id: Invoice ID to process
        relative_path: Relative path to the invoice file to process
        stage_name: Snowflake stage name where the invoice is stored
        use_existing_ai_extract: Whether to use existing AI extract metadata
            Defaults to False. If True, the workflow will skip the classification and AI extract steps and use existing AI extract metadata from target_table.
            If False, the workflow will classify the invoice, run AI extract, and store the results in target_table.

    Returns:
        Workflow result or error message
    """

    try:
        connection = get_persistent_connection()
    except Exception as e:
        logger.error(f"Error getting connection: {str(e)}")
        return f"Error: Failed to get connection: {str(e)}"

    try:
        graph = create_graph()
        
        inputs = {
            "target_table": target_table,
            "invoice_id": invoice_id,
            "relative_path": relative_path,
            "stage_name": stage_name,
            "use_existing_ai_extract": use_existing_ai_extract,
        }
        logger.info(f"Invoking graph with inputs: {inputs}")

        result = graph.invoke(inputs, context={"connection": connection})
        logger.info("Graph result received")
        return result
        
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}")
        return f"Error: Failed to run workflow: {str(e)}"