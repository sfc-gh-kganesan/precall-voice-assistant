"""
Output schemas for invoice extraction.
"""
from typing import TypedDict, NotRequired, List, Dict, Any, Optional
from pydantic import BaseModel


# ============================================================================
# Bounding Box Schema
# ============================================================================

class BoundingBox(BaseModel):
    """Bounding box coordinates for a field or line item cell."""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = 1


class FieldWithBBox(BaseModel):
    """A field value with optional bounding box."""
    value: str
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = None


# ============================================================================
# Line Item Schema
# ============================================================================

class LineItemOutput(BaseModel):
    """Extracted line item with optional bounding boxes per cell."""
    line_number: int
    description: str
    type: str  # "Goods" or "Service"
    amount: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    unit_of_measure: Optional[str] = None
    service_start_date: Optional[str] = None
    service_end_date: Optional[str] = None
    matched_po_line: Optional[int] = None


# ============================================================================
# Invoice Fields Schema (Simple version for output)
# ============================================================================

class InvoiceFieldsOutput(BaseModel):
    """Extracted invoice header fields."""
    invoice_number: str = ""
    snowflake_entity: str = ""
    vendor_name: str = ""
    invoice_date: str = ""
    total_amount: str = ""
    tax_amount: str = ""
    currency: str = ""
    purchase_order_number: str = ""
    memo_description: str = ""


class InvoiceFields(BaseModel):
    """Invoice header fields for internal use."""
    invoice_number: str = ""
    snowflake_entity: str = ""
    vendor_name: str = ""
    invoice_date: str = ""
    total_amount: str = ""
    tax_amount: str = ""
    currency: str = ""
    purchase_order_number: str = ""
    memo_description: str = ""


class LineItem(BaseModel):
    """Line item for internal use."""
    line_number: int = 0
    description: str = ""
    type: str = "Service"
    amount: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    unit_of_measure: Optional[str] = None
    service_start_date: Optional[str] = None
    service_end_date: Optional[str] = None


# ============================================================================
# Full Extraction Output
# ============================================================================

class ExtractionConfidence(BaseModel):
    """Confidence score and reasoning for the extraction."""
    score: float
    reasoning: str


class ExtractionOutput(BaseModel):
    """Complete extraction result."""
    fields: InvoiceFieldsOutput
    line_items: List[LineItemOutput]
    fields_with_bounding_boxes: Dict[str, Any] = {}
    extraction_confidence: Dict[str, Any] = {}


# ============================================================================
# Internal State TypedDict (for LangGraph)
# ============================================================================

class State(TypedDict):
    """Internal state for the extraction graph."""
    # Input
    invoice_id: NotRequired[str]
    pdf_path: str
    
    # Classification
    classification: NotRequired[str]  # "invoice" or "not an invoice"
    
    # Extracted text and bboxes
    bounding_boxes: NotRequired[List[Dict[str, Any]]]  # Word-level bboxes
    text_blocks_with_bboxes: NotRequired[List[Dict[str, Any]]]  # Line-level bboxes
    page_dimensions: NotRequired[Dict[int, Dict[str, float]]]
    merged_pages: NotRequired[List[Dict[str, Any]]]  # Page-by-page text
    ai_parse_pages: NotRequired[List[Dict[str, Any]]]  # AI parse pages (empty for standalone)
    ai_parse_text: NotRequired[str]
    full_text: NotRequired[str]
    page_count: NotRequired[int]
    
    # Extracted fields
    ai_extract_metadata: NotRequired[Dict[str, Any]]
    fields_with_bounding_boxes: NotRequired[Dict[str, Any]]
    extraction_confidence: NotRequired[Dict[str, Any]]
    
    # Line items
    line_items: NotRequired[List[Dict[str, Any]]]
    table_bboxes: NotRequired[List[Dict[str, Any]]]
    
    # Translation (for non-English)
    translation_with_bounding_boxes: NotRequired[List[Dict[str, Any]]]
    
    # Final output
    extraction_output: NotRequired[ExtractionOutput]


# Alias for backwards compatibility
ExtractionState = State


# ============================================================================
# LLM Output Schemas (for structured output)
# ============================================================================

class TextExtractOutput(BaseModel):
    """LLM output structure for field extraction."""
    model_config = {"extra": "forbid"}
    
    invoice_number: str
    snowflake_entity: str
    vendor_name: str
    invoice_date: str
    total_amount: str
    tax_amount: str
    currency: str
    purchase_order_number: str
    memo_description: str


class LineItemLLMOutput(BaseModel):
    """Single line item from LLM extraction."""
    model_config = {"extra": "forbid"}
    
    row_index: int = -1
    is_line_item: bool = True
    description: str
    type: str  # "Goods" or "Service"
    amount: str
    quantity: str = ""
    unit_price: str = ""
    unit_of_measure: str = ""
    service_start_date: str = ""
    service_end_date: str = ""


class LineItemsLLMOutput(BaseModel):
    """LLM output structure for line items extraction."""
    model_config = {"extra": "forbid"}
    
    line_items: List[LineItemLLMOutput]

