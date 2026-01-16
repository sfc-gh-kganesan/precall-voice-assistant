"""
LangGraph workflow for invoice extraction.
Standalone version - no Snowflake dependencies.
"""

import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from app.schemas import State, ExtractionOutput
from app.nodes import (
    extract_bounding_boxes,
    run_unified_extractor,
    extract_line_items,
    extract_line_items_with_tables,
    collect_extraction_output,
)

logger = logging.getLogger(__name__)


def create_extraction_graph(use_table_detection: bool = True) -> StateGraph:
    """
    Create the extraction-only LangGraph workflow.
    
    Flow:
        START → extract_bounding_boxes → run_unified_extractor 
        → extract_line_items → collect_extraction_output → END
    
    Args:
        use_table_detection: If True, use hybrid table detection for line items.
                            If False, use pure LLM page-by-page extraction.
    
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("extract_bounding_boxes", extract_bounding_boxes)
    workflow.add_node("run_unified_extractor", run_unified_extractor)
    
    # Choose line item extraction strategy
    if use_table_detection:
        workflow.add_node("extract_line_items", extract_line_items_with_tables)
    else:
        workflow.add_node("extract_line_items", extract_line_items)
    
    workflow.add_node("collect_output", collect_extraction_output)
    
    # Define flow
    workflow.add_edge(START, "extract_bounding_boxes")
    workflow.add_edge("extract_bounding_boxes", "run_unified_extractor")
    workflow.add_edge("run_unified_extractor", "extract_line_items")
    workflow.add_edge("extract_line_items", "collect_output")
    workflow.add_edge("collect_output", END)
    
    return workflow.compile()


async def extract_invoice(
    pdf_path: str,
    invoice_id: str = None,
    use_table_detection: bool = True,
) -> Dict[str, Any]:
    """
    Run extraction workflow on a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        invoice_id: Optional identifier for the invoice
        use_table_detection: Whether to use table detection for line items
    
    Returns:
        ExtractionOutput as dict
    """
    import os
    
    if invoice_id is None:
        invoice_id = os.path.basename(pdf_path)
    
    graph = create_extraction_graph(use_table_detection=use_table_detection)
    
    result = await graph.ainvoke({
        "pdf_path": pdf_path,
        "invoice_id": invoice_id,
    })
    
    # Return the extraction output
    extraction_output = result.get("extraction_output")
    if extraction_output:
        return extraction_output.model_dump()
    
    # Fallback: build output from state
    from app.schemas import InvoiceFieldsOutput, LineItemOutput, ExtractionOutput
    
    ai_metadata = result.get("ai_extract_metadata", {})
    line_items = result.get("line_items", [])
    
    fields = InvoiceFieldsOutput(
        invoice_number=ai_metadata.get("invoice_number", ""),
        snowflake_entity=ai_metadata.get("snowflake_entity", ""),
        vendor_name=ai_metadata.get("vendor_name", ""),
        invoice_date=ai_metadata.get("invoice_date", ""),
        total_amount=ai_metadata.get("total_amount", ""),
        tax_amount=ai_metadata.get("tax_amount", ""),
        currency=ai_metadata.get("currency", ""),
        purchase_order_number=ai_metadata.get("purchase_order_number", ""),
        memo_description=ai_metadata.get("memo_description", ""),
    )
    
    line_items_out = [
        LineItemOutput(
            line_number=item.get("line_number", idx + 1),
            description=item.get("description", ""),
            type=item.get("type", "Service"),
            amount=item.get("amount"),
            quantity=item.get("quantity"),
            unit_price=item.get("unit_price"),
            unit_of_measure=item.get("unit_of_measure"),
            service_start_date=item.get("service_start_date"),
            service_end_date=item.get("service_end_date"),
            matched_po_line=item.get("matched_po_line"),
        )
        for idx, item in enumerate(line_items)
    ]
    
    output = ExtractionOutput(
        fields=fields,
        line_items=line_items_out,
        fields_with_bounding_boxes=result.get("fields_with_bounding_boxes", {}),
        extraction_confidence=result.get("extraction_confidence", {}),
    )
    
    return output.model_dump()


def extract_invoice_sync(
    pdf_path: str,
    invoice_id: str = None,
    use_table_detection: bool = True,
) -> Dict[str, Any]:
    """
    Synchronous version of extract_invoice.
    
    Args:
        pdf_path: Path to the PDF file
        invoice_id: Optional identifier for the invoice
        use_table_detection: Whether to use table detection for line items
    
    Returns:
        ExtractionOutput as dict
    """
    import asyncio
    
    return asyncio.run(extract_invoice(
        pdf_path=pdf_path,
        invoice_id=invoice_id,
        use_table_detection=use_table_detection,
    ))

