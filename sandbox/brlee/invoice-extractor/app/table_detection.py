"""
Table detection and structure parsing for invoice line items.

Applies all extraction logic from LINE_ITEMS_UNIFIED_PROMPT to table data.
Full version from original codebase, modified to remove Snowflake dependencies.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from pydantic import BaseModel

from app.prompts import LINE_ITEMS_UNIFIED_PROMPT
from app.line_item_keywords import GOODS_INDICATORS, SERVICE_INDICATORS, HEADER_PATTERNS

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS FOR LLM CLASSIFICATION
# ============================================================================


class LineItemClassification(BaseModel):
    """Classification result for a single line item."""

    model_config = {"extra": "forbid"}

    row_index: int
    is_line_item: bool  # False for subtotals, headers, etc.
    description: str
    type: str  # "Goods" or "Service"
    amount: str
    quantity: str  # Empty string "" if not applicable
    unit_price: str  # Empty string "" if not applicable
    unit_of_measure: str  # Empty string "" if not applicable
    service_start_date: str  # Empty string "" if not applicable
    service_end_date: str  # Empty string "" if not applicable


class ClassificationOutput(BaseModel):
    """Output structure for classification."""

    model_config = {"extra": "forbid"}

    line_items: list[LineItemClassification]


# ============================================================================
# CONTENT TYPE CLASSIFICATION (local implementation)
# ============================================================================


class ContentTypeClassification(BaseModel):
    """Classification of content type."""
    model_config = {"extra": "forbid"}
    
    content_type: str  # "summary", "detail", or "none"
    is_line_items: bool
    reason: str


def classify_content_type_with_llm(
    content_preview: str,
    model: Any,
    num_items: int = 0,
) -> Dict[str, Any]:
    """
    Use LLM to classify whether content contains line items.
    
    Returns:
        {
            "is_line_items": bool,
            "content_type": "summary" | "detail" | "none",
            "reason": str
        }
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    prompt = f"""Analyze this invoice table content and classify its type.

CONTENT TO ANALYZE:
{content_preview}

NUMBER OF ROWS: {num_items}

CLASSIFICATION OPTIONS:
1. "summary" - High-level invoice summary with category totals (e.g., "AWS Services: $389,195.99", "Total Charges")
   - Usually has fewer items (1-10 rows)
   - Shows aggregated amounts per category/service
   - May be followed by detailed breakdowns on subsequent pages

2. "detail" - Detailed line-by-line breakdown of individual items
   - Usually has many items (10+ rows)
   - Shows individual transactions, campaigns, or items
   - Each row is a distinct billable item

3. "none" - Not a line items table
   - Address/contact information
   - Payment terms/instructions
   - Metadata (invoice number, dates)
   - Empty or irrelevant content

Respond with:
- content_type: "summary", "detail", or "none"
- is_line_items: true if content_type is "summary" or "detail", false otherwise
- reason: Brief explanation (10-20 words)"""

    try:
        msg = [
            SystemMessage(content="You classify invoice table content types."),
            HumanMessage(content=prompt),
        ]
        
        response = model.model.with_structured_output(ContentTypeClassification).invoke(msg)
        result = response.model_dump()
        
        return {
            "is_line_items": result["is_line_items"],
            "content_type": result["content_type"],
            "reason": result["reason"],
        }
    except Exception as e:
        logger.warning(f"Content classification failed: {e}")
        # Default to treating as line items to avoid missing data
        return {
            "is_line_items": True,
            "content_type": "detail",
            "reason": f"Classification failed ({e}), defaulting to detail",
        }


def classify_page_content_type(
    context: str,
    items: List[Dict[str, Any]],
    model: Any,
) -> Tuple[str, bool, str]:
    """
    Classify page content type using LLM.
    
    Returns:
        Tuple of (content_type, is_summary, reason)
    """
    # Build preview from items
    preview = "\n".join([
        f'"{item.get("description", "")[:50]}" (${item.get("amount", "0")})'
        for item in items[:10]
    ])
    
    result = classify_content_type_with_llm(
        content_preview=f"{context}\n\nItems:\n{preview}",
        model=model,
        num_items=len(items),
    )
    
    return (
        result["content_type"],
        result["content_type"] == "summary",
        result["reason"],
    )


# ============================================================================
# BBOX HELPER FUNCTIONS
# ============================================================================


def _tuple_to_bbox(bbox_tuple: Tuple[float, float, float, float]) -> Dict[str, float]:
    """Convert (x0, y0, x1, y1) tuple to bbox dict."""
    return {
        "x0": float(bbox_tuple[0]),
        "y0": float(bbox_tuple[1]),
        "x1": float(bbox_tuple[2]),
        "y1": float(bbox_tuple[3]),
    }


def _empty_bbox() -> Dict[str, float]:
    """Return an empty/zero bbox dict."""
    return {"x0": 0, "y0": 0, "x1": 0, "y1": 0}


def _merge_cell_bboxes(cells: List["TableCell"]) -> Optional[Dict[str, float]]:
    """Merge multiple cell bboxes into one encompassing bbox."""
    valid = [c for c in cells if c.text.strip() and c.bbox.get("x1", 0) > 0]
    if not valid:
        return None
    bbox = {
        "x0": min(c.bbox["x0"] for c in valid),
        "y0": min(c.bbox["y0"] for c in valid),
        "x1": max(c.bbox["x1"] for c in valid),
        "y1": max(c.bbox["y1"] for c in valid),
    }
    # Sanity check: bbox should have positive dimensions
    if bbox["x1"] <= bbox["x0"] or bbox["y1"] <= bbox["y0"]:
        return None
    return bbox


@dataclass
class TableRegion:
    """Detected table region with bounding box."""

    bbox: Dict[str, float]  # {x0, y0, x1, y1} in PDF points
    page: int
    confidence: float
    detection_method: str  # "pdfplumber", "borderless", or "freeform"


@dataclass
class TableCell:
    """Individual cell in a parsed table."""

    text: str
    bbox: Dict[str, float]
    row_idx: int
    col_idx: int
    token_ids: List[int] = field(default_factory=list)


@dataclass
class ParsedTable:
    """Fully parsed table structure."""

    region: TableRegion
    headers: List[str]
    rows: List[List[TableCell]]
    header_bbox: Optional[Dict[str, float]] = None
    header_cells: List[TableCell] = field(default_factory=list)


def _looks_like_data_row(headers: List[str]) -> bool:
    """
    Check if headers look like actual data values rather than column headers.

    This helps detect continuation tables where the first row is actually data,
    not headers (e.g., "21 | ap-campaign-name | Campaign | 1,234.56").

    Returns True if the row looks like data, False if it looks like headers.
    """
    if not headers:
        return False

    # Known header keywords - if any cell contains these, it's likely a real header
    header_keywords = [
        "line",
        "description",
        "item",
        "product",
        "service",
        "campaign",
        "amount",
        "total",
        "price",
        "cost",
        "unit",
        "rate",
        "qty",
        "quantity",
        "from",
        "to",
        "start",
        "end",
        "date",
        "period",
        "#",
        "no",
        "number",
    ]

    keyword_matches = 0
    numeric_cells = 0
    amount_cells = 0

    for h in headers:
        h_lower = h.lower().strip()

        # Check for header keywords
        for kw in header_keywords:
            if kw in h_lower:
                keyword_matches += 1
                break

        # Check if cell looks like a numeric value (line numbers, amounts)
        if re.match(r"^\d+$", h_lower):  # Pure line number like "21"
            numeric_cells += 1
        elif re.search(r"[\d,]+\.\d{2}$", h_lower):  # Amount like "1,234.56"
            amount_cells += 1
        elif re.match(r"^[\d,]+$", h_lower):  # Number with commas
            numeric_cells += 1

    # If we have at least 2 header keyword matches, it's likely a real header row
    if keyword_matches >= 2:
        return False

    # If we have numeric line numbers AND amounts, it's likely a data row
    if numeric_cells >= 1 and amount_cells >= 1:
        return True

    # If most cells are numeric/amounts, it's likely a data row
    if (numeric_cells + amount_cells) >= len(headers) // 2:
        return True

    return False


def _create_first_row_as_data(
    headers: List[str],
    header_bbox: Optional[Dict[str, float]],
    cell_bboxes: Optional[List[Optional[Tuple[float, float, float, float]]]] = None,
) -> List[TableCell]:
    """
    Convert the first row (incorrectly parsed as headers) back into a data row.
    Used for continuation tables where pdfplumber treats data as headers.
    """
    row_cells = []
    for col_idx, text in enumerate(headers):
        if cell_bboxes and col_idx < len(cell_bboxes) and cell_bboxes[col_idx]:
            cell_bbox = _tuple_to_bbox(cell_bboxes[col_idx])
        elif header_bbox:
            cell_bbox = header_bbox.copy()
        else:
            cell_bbox = _empty_bbox()

        row_cells.append(
            TableCell(
                text=str(text).strip() if text else "",
                bbox=cell_bbox,
                row_idx=0,
                col_idx=col_idx,
                token_ids=[],
            )
        )
    return row_cells


# ============================================================================
# PDF Plumber Table Detection
# ============================================================================


@dataclass
class PdfPlumberTableData:
    """Table data with native cell coordinates from pdfplumber."""

    table_data: List[List[str]]  # Text content
    cell_bboxes: List[
        List[Optional[Tuple[float, float, float, float]]]
    ]  # Cell coordinates
    table_bbox: Tuple[float, float, float, float]
    page: int


def detect_tables_pdfplumber(
    pdf_path: str,
    page_dimensions: Dict[int, Dict[str, float]],
) -> Tuple[List[TableRegion], List[PdfPlumberTableData]]:
    """
    Detect tables using pdfplumber's table detection algorithm.
    Returns table data WITH native cell bounding boxes for pixel-perfect highlighting.

    Returns:
        Tuple of (table_regions, table_data_with_cells)
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed")
        return [], []

    table_regions = []
    table_data_list = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Try default settings first (works well for most bordered tables)
            tables = page.find_tables()

            # If no tables found, try with text-based strategy
            if not tables:
                table_settings_text = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                }
                tables = page.find_tables(table_settings=table_settings_text)

            for table in tables:
                bbox = table.bbox  # (x0, top, x1, bottom)

                # Extract table data (text content)
                table_data = table.extract()

                if table_data and len(table_data) > 1:  # Has header + data
                    # Get cell bounding boxes from table.cells
                    # table.cells is a list of (x0, top, x1, bottom) tuples
                    cell_bboxes = _extract_cell_bboxes_from_table(table, table_data)

                    # Enhance cell text with any cut-off characters
                    # pdfplumber can miss text that's slightly outside cell boundaries
                    enhanced_table_data = _enhance_table_data_with_cutoff_text(
                        page, table_data, cell_bboxes
                    )

                    table_regions.append(
                        TableRegion(
                            bbox={
                                "x0": float(bbox[0]),
                                "y0": float(bbox[1]),
                                "x1": float(bbox[2]),
                                "y1": float(bbox[3]),
                            },
                            page=page_num + 1,
                            confidence=0.95,  # Higher confidence with native coords
                            detection_method="pdfplumber",
                        )
                    )

                    table_data_list.append(
                        PdfPlumberTableData(
                            table_data=enhanced_table_data,
                            cell_bboxes=cell_bboxes,
                            table_bbox=bbox,
                            page=page_num + 1,
                        )
                    )

                    logger.info(
                        f"pdfplumber found table on page {page_num + 1}: "
                        f"{len(enhanced_table_data)} rows, {len(enhanced_table_data[0]) if enhanced_table_data else 0} cols, "
                        f"{len(table.cells)} native cells"
                    )

    logger.info(
        f"pdfplumber found {len(table_regions)} tables with native cell coordinates"
    )
    return table_regions, table_data_list


def _enhance_table_data_with_cutoff_text(
    page: Any,
    table_data: List[List[str]],
    cell_bboxes: List[List[Optional[Tuple[float, float, float, float]]]],
) -> List[List[str]]:
    """
    Enhance table data by checking for cut-off text to the left of cells.

    This fixes cases where pdfplumber's table boundary detection cuts off text
    that should be part of the cell (e.g., "Servicios" becoming "ios").

    Args:
        page: pdfplumber page object
        table_data: 2D list of cell text from table.extract()
        cell_bboxes: 2D list of cell bboxes matching table_data structure

    Returns:
        Enhanced table_data with any cut-off text prepended to affected cells
    """
    if not table_data or not cell_bboxes:
        return table_data

    enhanced_data = []
    for row_idx, row in enumerate(table_data):
        enhanced_row = []
        row_bboxes = cell_bboxes[row_idx] if row_idx < len(cell_bboxes) else []

        for col_idx, cell_text in enumerate(row):
            cell_bbox = row_bboxes[col_idx] if col_idx < len(row_bboxes) else None

            if cell_bbox and cell_text:
                # Try to enhance this cell's text
                enhanced_text = _enhance_cell_text_with_cutoff_chars(
                    page, cell_bbox, cell_text
                )
                enhanced_row.append(enhanced_text)
            else:
                enhanced_row.append(cell_text)

        enhanced_data.append(enhanced_row)

    return enhanced_data


def _enhance_cell_text_with_cutoff_chars(
    page: Any,
    cell_bbox: Tuple[float, float, float, float],
    cell_text: str,
    row_tolerance: float = 5.0,
    left_margin: float = 50.0,
) -> str:
    """
    Enhance cell text with any characters that were cut off to the left of the cell boundary.

    pdfplumber sometimes detects table boundaries that cut off text. This function
    looks for characters immediately to the left of the cell that should be part of it.

    Args:
        page: pdfplumber page object with .chars attribute
        cell_bbox: (x0, y0, x1, y1) tuple of the cell
        cell_text: Text extracted by pdfplumber for this cell
        row_tolerance: Y-coordinate tolerance for matching rows
        left_margin: How far left to look for cut-off text

    Returns:
        Enhanced cell text with any prepended cut-off characters
    """
    if not cell_text or not hasattr(page, "chars"):
        return cell_text

    x0, y0, x1, y1 = cell_bbox

    # Find characters that are:
    # 1. To the left of the cell (x1 < cell x0) but not too far (within left_margin)
    # 2. On the same row (similar y coordinate)
    # 3. Between the left margin search area and the cell

    search_x0 = max(0, x0 - left_margin)

    # Get chars in the left margin area at the same Y level
    cutoff_chars = []
    for char in page.chars:
        # Check if char is in the left margin area (to the left of cell, but not too far)
        if char["x1"] <= x0 and char["x0"] >= search_x0:
            # For multi-line cells, check if char is in the first line
            cell_first_line_y = y0 + row_tolerance
            if y0 - row_tolerance <= char["y0"] <= cell_first_line_y + row_tolerance:
                cutoff_chars.append(char)

    if not cutoff_chars:
        return cell_text

    # Sort by x position and reconstruct text
    cutoff_chars.sort(key=lambda c: c["x0"])

    # Build the prepended text
    prepend_text = ""
    prev_x1 = search_x0
    for char in cutoff_chars:
        # Add space if there's a gap between characters
        if char["x0"] - prev_x1 > 3:  # Small gap tolerance
            prepend_text += " "
        prepend_text += char["text"]
        prev_x1 = char["x1"]

    prepend_text = prepend_text.strip()

    if prepend_text:
        logger.debug(f"Enhanced cell text: '{prepend_text}' + '{cell_text[:30]}...'")
        # Only prepend if the cell text doesn't already start with this text
        if not cell_text.startswith(prepend_text):
            return prepend_text + cell_text

    return cell_text


def _extract_cell_bboxes_from_table(
    table: Any,
    table_data: List[List[str]],
) -> List[List[Optional[Tuple[float, float, float, float]]]]:
    """
    Extract cell bounding boxes from pdfplumber table.
    Maps cells to their row/col positions based on spatial layout.

    Returns a 2D list matching table_data structure with cell bboxes.
    """
    if not table_data:
        return []

    # Get raw cells from pdfplumber - these are (x0, top, x1, bottom) tuples
    raw_cells = list(table.cells) if hasattr(table, "cells") else []

    if not raw_cells:
        # Fallback: return empty bboxes
        return [[None for _ in row] for row in table_data]

    # Sort cells into rows by Y-coordinate
    ROW_TOLERANCE = 5.0

    # Group cells by Y position (row)
    cells_by_row: Dict[float, List[Tuple]] = {}
    for cell in raw_cells:
        x0, y0, x1, y1 = cell
        # Find matching row
        matched_row = None
        for row_y in cells_by_row:
            if abs(y0 - row_y) < ROW_TOLERANCE:
                matched_row = row_y
                break

        if matched_row is not None:
            cells_by_row[matched_row].append(cell)
        else:
            cells_by_row[y0] = [cell]

    # Sort rows by Y and cells within rows by X
    sorted_rows = []
    for row_y in sorted(cells_by_row.keys()):
        row_cells = sorted(cells_by_row[row_y], key=lambda c: c[0])  # Sort by x0
        sorted_rows.append(row_cells)

    # Build result matching table_data structure
    result = []
    for row_idx, row_data in enumerate(table_data):
        row_bboxes = []
        if row_idx < len(sorted_rows):
            row_cells = sorted_rows[row_idx]
            for col_idx in range(len(row_data)):
                if col_idx < len(row_cells):
                    cell = row_cells[col_idx]
                    row_bboxes.append(cell)  # (x0, y0, x1, y1)
                else:
                    row_bboxes.append(None)
        else:
            row_bboxes = [None] * len(row_data)
        result.append(row_bboxes)

    return result


def parse_pdfplumber_table_with_native_bboxes(
    table_data: PdfPlumberTableData,
    region: TableRegion,
    words_with_bboxes: Optional[List[Dict[str, Any]]] = None,
) -> ParsedTable:
    """
    Parse a pdfplumber table using NATIVE cell coordinates.
    This gives pixel-perfect bounding boxes for bordered tables.
    """
    raw_data = table_data.table_data
    cell_bboxes = table_data.cell_bboxes

    if not raw_data or len(raw_data) < 2:
        return ParsedTable(region=region, headers=[], rows=[], header_bbox=None)

    # First row is header
    headers = [str(cell) if cell else "" for cell in raw_data[0]]

    # Header bbox from first row cells
    header_bbox = None
    if cell_bboxes and cell_bboxes[0]:
        valid_header_cells = [c for c in cell_bboxes[0] if c is not None]
        if valid_header_cells:
            header_bbox = {
                "x0": min(c[0] for c in valid_header_cells),
                "y0": min(c[1] for c in valid_header_cells),
                "x1": max(c[2] for c in valid_header_cells),
                "y1": max(c[3] for c in valid_header_cells),
            }

    # Create cells for data rows with native bboxes
    data_rows = []
    for row_idx, (row_text, row_bbox_list) in enumerate(
        zip(raw_data[1:], cell_bboxes[1:]), start=1
    ):
        row_cells = []
        for col_idx, cell_text in enumerate(row_text):
            cell_str = str(cell_text).strip() if cell_text else ""
            cell_bbox = (
                _tuple_to_bbox(row_bbox_list[col_idx])
                if col_idx < len(row_bbox_list) and row_bbox_list[col_idx]
                else _empty_bbox()
            )

            row_cells.append(
                TableCell(
                    text=cell_str,
                    bbox=cell_bbox,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    token_ids=[],
                )
            )

        if row_cells:
            data_rows.append(row_cells)

    return ParsedTable(
        region=region, headers=headers, rows=data_rows, header_bbox=header_bbox
    )


# ============================================================================
# LLM TABLE CLASSIFICATION
# ============================================================================


def _classify_table_type_semantically(
    table: ParsedTable,
    model: Any,
) -> Dict[str, Any]:
    """
    Use LLM to semantically classify whether a table contains line items.

    Uses the local classify_content_type_with_llm() function for
    consistent classification logic between bordered and freeform extraction.

    Returns:
        {
            "is_line_items_table": bool,
            "table_type": "summary" | "detail" | "none",
            "reason": str
        }

    - "summary": High-level invoice summary with totals (e.g., "AWS Service Charges $389,195.99")
    - "detail": Detailed breakdown of individual items/services
    - "none": Not a line items table (e.g., address info, payment terms)
    """
    # Format table for quick classification
    table_preview = _format_table_for_llm(table)
    if not table_preview:
        return {
            "is_line_items_table": False,
            "table_type": "none",
            "reason": "Empty table",
        }

    # Take just the first few rows for quick classification
    lines = table_preview.split("\n")
    preview = "\n".join(
        lines[: min(8, len(lines))]
    )  # Header + separator + up to 6 rows

    # Use local classification function
    result = classify_content_type_with_llm(
        content_preview=preview,
        model=model,
        num_items=len(table.rows) if table.rows else 0,
    )

    # Map to expected return format
    return {
        "is_line_items_table": result.get("is_line_items", True),
        "table_type": result.get("content_type", "detail"),
        "reason": result.get("reason", ""),
    }


def _classify_line_items_with_llm(
    table_text: str,
    table: ParsedTable,
    model: Any,
    page_context: str = "",
    additional_page_context: str = "",
) -> List[Dict[str, Any]]:
    """
    UNIFIED LLM classification function for all table detection strategies.

    This is the single source of truth for line item classification across:
    - Bordered tables (pdfplumber)
    - Borderless tables (Y-clustering)
    - Freeform text (pattern matching)

    Note: Type override based on PO dominant type is handled post-extraction
    in enrich_line_items_from_po_or_invoice (since PO data isn't available during extraction).

    Args:
        table_text: Formatted table text for LLM
        table: ParsedTable object with structure
        model: LLM model for classification
        page_context: Context from previous pages
        additional_page_context: Additional context (PyMuPDF+OCR, AI_PARSE_DOCUMENT) for this page
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    # Build context section for multi-page invoices
    context_section = ""
    if page_context:
        context_section = f"""
=== CONTEXT FROM PREVIOUS PAGE ===
{page_context}

This table is a CONTINUATION of line items from the previous page. Apply CONSISTENT classification.
"""

    # Add additional page context (PyMuPDF+OCR and AI_PARSE_DOCUMENT) for better extraction
    if additional_page_context:
        context_section += f"""

=== ADDITIONAL PAGE CONTEXT ===
The following is additional text extracted from this page using different methods (PyMuPDF+OCR and AI_PARSE_DOCUMENT).
Use this to help identify service dates, quantities, and other details that may not be visible in the table structure.

{additional_page_context}
"""

    # Format the prompt using the unified template from prompts.py
    prompt = LINE_ITEMS_UNIFIED_PROMPT.format(
        context_section=context_section,
        invoice_data=table_text,
    )

    try:
        # Build system message for classification
        system_content = "You are an invoice line item classification assistant."

        msg = [
            SystemMessage(content=system_content),
            HumanMessage(content=prompt),
        ]

        response = model.model.with_structured_output(ClassificationOutput).invoke(msg)
        classifications = response.model_dump()["line_items"]

        # Debug: Log classification results
        total_classified = len(classifications)
        line_item_count = sum(1 for c in classifications if c["is_line_item"])
        invalid_index_count = sum(
            1
            for c in classifications
            if c["is_line_item"]
            and (c["row_index"] < 0 or c["row_index"] >= len(table.rows))
        )

        if line_item_count == 0 and total_classified > 0:
            logger.warning(
                f"Page {table.region.page}: LLM returned {total_classified} classifications but 0 marked as line items"
            )
        if invalid_index_count > 0:
            logger.warning(
                f"Page {table.region.page}: {invalid_index_count} items had invalid row_index (table has {len(table.rows)} rows)"
            )

        # Map classifications back to table rows with bboxes
        line_items = []
        for cls in classifications:
            if not cls["is_line_item"]:
                continue

            row_idx = cls["row_index"]
            if row_idx < 0 or row_idx >= len(table.rows):
                logger.debug(
                    f"Skipping item with invalid row_index {row_idx}: {cls.get('description', '')[:30]}"
                )
                continue

            row = table.rows[row_idx]
            row_bbox = _merge_cell_bboxes(row) if row else None

            line_items.append(
                {
                    "description": cls["description"],
                    "type": cls["type"],
                    "amount": cls["amount"],
                    "quantity": cls["quantity"] or None,
                    "unit_price": cls["unit_price"] or None,
                    "unit_of_measure": cls["unit_of_measure"] or None,
                    "service_start_date": cls["service_start_date"] or None,
                    "service_end_date": cls["service_end_date"] or None,
                    "page": table.region.page,
                    "row_bbox": row_bbox,
                }
            )

        return line_items

    except Exception as e:
        logger.error(f"Error in LLM classification: {e}")
        raise


def _format_table_for_llm(table: ParsedTable) -> str:
    """Format table data as text for LLM processing with explicit row indices."""
    if not table.headers or not table.rows:
        logger.debug(
            f"Table format empty: headers={bool(table.headers)}, rows={len(table.rows) if table.rows else 0}"
        )
        return ""

    lines = []

    # Add headers with row_index column for accurate LLM reference
    lines.append("| row_index | " + " | ".join(table.headers) + " |")
    lines.append("|---|" + "|".join(["---"] * len(table.headers)) + "|")

    # Add all rows with explicit row indices
    for idx, row in enumerate(table.rows):
        row_texts = [cell.text for cell in row]
        # Pad or truncate to match header count
        while len(row_texts) < len(table.headers):
            row_texts.append("")
        row_texts = row_texts[: len(table.headers)]
        lines.append(f"| {idx} | " + " | ".join(row_texts) + " |")

    result = "\n".join(lines)
    logger.debug(
        f"Table format for page {table.region.page} ({len(table.rows)} rows): first 300 chars:\n{result[:300]}"
    )
    return result


# ============================================================================
# LINE ITEM EXTRACTION WITH PROMPT LOGIC (Rule-based fallback)
# ============================================================================

# Pre-compiled skip patterns for performance
SKIP_REGEX = re.compile(
    r"|".join(
        [
            # Subtotals and totals
            r"^\s*(sub)?total\s*$",
            r"^\s*grand\s*total\s*$",
            r"^\s*total\s*(due|amount|general)?\s*$",
            r"^\s*net\s*total\s*$",
            r"^\s*gross\s*total\s*$",
            r"^\s*balance\s*(due)?\s*$",
            # Taxes
            r"^\s*(sales\s*)?tax\s*$",
            r"^\s*vat\s*$",
            r"^\s*iva\s*$",
            r"^\s*gst\s*$",
            r"^\s*igv\s*$",
            r"^\s*impuesto\s*$",
            # Shipping
            r"^\s*shipping\s*(&\s*handling)?\s*$",
            r"^\s*freight\s*$",
            r"^\s*delivery\s*$",
            r"^\s*s\s*&\s*h\s*$",
            r"^\s*envio\s*$",
            # Discounts
            r"^\s*discount\s*$",
            r"^\s*descuento\s*$",
            r"^\s*adjustment\s*$",
            r"^\s*credit\s*$",
            r"^\s*rebate\s*$",
            # Page/summary indicators
            r"^\s*page\s*\d*\s*$",
            r"^\s*continued\s*$",
            r"^\s*carried\s*forward\s*$",
        ]
    ),
    re.IGNORECASE,
)


def map_headers_to_fields(headers: List[str]) -> Dict[str, int]:
    """Map table headers to line item field names using keyword matching."""
    headers_lower = [h.lower().strip() for h in headers]
    mapping = {}

    for field_name, patterns in HEADER_PATTERNS.items():
        for col_idx, header in enumerate(headers_lower):
            if field_name not in mapping and any(
                p in header or header in p for p in patterns
            ):
                mapping[field_name] = col_idx
                break

    logger.info(f"Header mapping: {mapping} from headers: {headers}")
    return mapping


def classify_line_item_type(
    description: str,
    quantity: str,
    unit_price: str,
    unit_of_measure: str,
) -> str:
    """
    Classify line item as "Goods" or "Service" based on prompt logic.

    - Goods: Physical products with quantity/unit_price
    - Service: Intangible services, labor, subscriptions
    """
    desc_lower = description.lower()
    desc_words = set(desc_lower.split())

    # Check for goods indicators (O(1) set intersection)
    if desc_words & GOODS_INDICATORS or any(
        ind in desc_lower for ind in GOODS_INDICATORS
    ):
        return "Goods"

    # Check for service indicators
    if desc_words & SERVICE_INDICATORS or any(
        ind in desc_lower for ind in SERVICE_INDICATORS
    ):
        return "Service"

    # Default: if has quantity/unit_price or UOM → Goods, else Service
    if (quantity and quantity.strip() and unit_price and unit_price.strip()) or (
        unit_of_measure and unit_of_measure.strip()
    ):
        return "Goods"

    return "Service"


def should_skip_row(description: str, amount: str) -> bool:
    """Determine if a row should be skipped (not a real line item)."""
    if not description or not description.strip():
        return True
    return bool(SKIP_REGEX.match(description.lower().strip()))


def normalize_date(date_str: str) -> str:
    """
    Normalize date to YYYY-MM-DD format.
    From LINE_ITEMS_EXTRACT_PROMPT date handling.
    """
    if not date_str or not date_str.strip():
        return ""

    date_str = date_str.strip()

    # Already in correct format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    # Common formats to try
    formats = [
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%m.%d.%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try dateutil as fallback
    try:
        from dateutil import parser as dateutil_parser

        parsed = dateutil_parser.parse(date_str, fuzzy=True)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        pass

    return date_str  # Return original if can't parse


def clean_amount(amount_str: str) -> str:
    """Clean amount string, preserving decimals."""
    if not amount_str:
        return ""

    # Remove currency symbols but keep numbers and separators
    cleaned = re.sub(r"[^\d.,\-]", "", amount_str)
    return cleaned.strip()


def extract_line_item_from_row(
    row: List[TableCell],
    header_mapping: Dict[str, int],
) -> Optional[Dict[str, Any]]:
    """Extract a line item from a parsed table row."""

    def get_cell_text(field: str) -> str:
        col_idx = header_mapping.get(field)
        return (
            row[col_idx].text.strip()
            if col_idx is not None and col_idx < len(row)
            else ""
        )

    def get_cell_bbox(field: str) -> Optional[Dict[str, Any]]:
        col_idx = header_mapping.get(field)
        if col_idx is not None and col_idx < len(row) and row[col_idx].text.strip():
            return {"bbox": row[col_idx].bbox, "token_ids": row[col_idx].token_ids}
        return None

    # Extract core fields
    description = get_cell_text("description")
    amount = get_cell_text("amount")
    quantity = get_cell_text("quantity")
    unit_price = get_cell_text("unit_price")
    unit_of_measure = get_cell_text("unit_of_measure")
    service_start = get_cell_text("service_start_date")
    service_end = get_cell_text("service_end_date")

    if should_skip_row(description, amount):
        return None

    line_type = classify_line_item_type(
        description, quantity, unit_price, unit_of_measure
    )

    # Build line item with type-specific fields
    is_goods = line_type == "Goods"
    line_item: Dict[str, Any] = {
        "description": description,
        "type": line_type,
        "amount": clean_amount(amount),
        "quantity": quantity or None if is_goods else None,
        "unit_price": clean_amount(unit_price) or None if is_goods else None,
        "unit_of_measure": unit_of_measure or None if is_goods else None,
        "service_start_date": None
        if is_goods
        else (normalize_date(service_start) or None),
        "service_end_date": None if is_goods else (normalize_date(service_end) or None),
        "bboxes": {
            "description": get_cell_bbox("description"),
            "amount": get_cell_bbox("amount"),
            "quantity": get_cell_bbox("quantity"),
            "unit_price": get_cell_bbox("unit_price"),
        },
    }

    # Add row bbox using helper
    row_bbox = _merge_cell_bboxes(row) if row else None
    if row_bbox:
        line_item["row_bbox"] = row_bbox

    return line_item


def extract_line_items_from_table(table: ParsedTable) -> List[Dict[str, Any]]:
    """
    Extract all line items from a parsed table.
    """
    # Map headers to fields
    header_mapping = map_headers_to_fields(table.headers)

    if "description" not in header_mapping:
        logger.warning(f"No description column found in headers: {table.headers}")
        # Try to use first column as description
        if table.headers:
            header_mapping["description"] = 0

    if "amount" not in header_mapping:
        logger.warning(f"No amount column found in headers: {table.headers}")
        # Try to use last column as amount
        if table.headers:
            header_mapping["amount"] = len(table.headers) - 1

    line_items = []
    for row in table.rows:
        line_item = extract_line_item_from_row(row, header_mapping)
        if line_item:
            line_items.append(line_item)

    return line_items


# ============================================================================
# PDF LAYOUT CLASSIFIER
# ============================================================================


class PDFLayoutType:
    """Enum-like class for PDF layout types."""

    BORDERED = "bordered"  # Tables with visible borders (pdfplumber)
    FREEFORM = "freeform"  # Everything else - uses LLM extraction


def classify_pdf_layout(
    pdf_path: str,
    words_with_bboxes: List[Dict[str, Any]],
    page_dimensions: Dict[int, Dict[str, float]],
) -> str:
    """
    Classify PDF layout to determine optimal extraction strategy.

    Analyzes:
    1. pdfplumber table detection (bordered tables)
    2. Y-coordinate alignment patterns (borderless tables)
    3. Word density and distribution (freeform text)

    Returns: PDFLayoutType constant
    """
    logger.info("=" * 60)
    logger.info("PDF LAYOUT CLASSIFIER - Analyzing document structure")
    logger.info("=" * 60)

    signals = {
        "bordered_tables": 0,
        "bordered_cells": 0,
        "aligned_rows": 0,
        "words_per_page": 0,
        "has_amount_patterns": False,
    }

    # =========================================================================
    # SIGNAL 1: Check for bordered tables via pdfplumber
    # =========================================================================
    if pdf_path:
        try:
            import pdfplumber

            logger.info("[Signal 1] Checking for bordered tables (pdfplumber)...")

            with pdfplumber.open(pdf_path) as pdf:
                sample_pages = min(3, len(pdf.pages))

                for page_num in range(sample_pages):
                    page = pdf.pages[page_num]
                    tables = page.find_tables()

                    for table in tables:
                        table_data = table.extract()
                        if table.cells and len(table.cells) > 10 and table_data:
                            num_rows = len(table_data)
                            num_cols = len(table_data[0]) if table_data else 0
                            expected_cells = num_rows * num_cols
                            actual_cells = len(table.cells)

                            # Calculate cell coverage ratio
                            coverage = (
                                actual_cells / expected_cells
                                if expected_cells > 0
                                else 0
                            )

                            logger.info(
                                f"  Page {page_num + 1}: Table {actual_cells} cells "
                                f"({num_rows}×{num_cols}={expected_cells} expected, coverage={coverage:.0%})"
                            )

                            # Only count as solid bordered if coverage >= 95%
                            # (nearly all cells detected = solid grid structure)
                            if coverage >= 0.95:
                                signals["bordered_tables"] += 1
                                signals["bordered_cells"] += actual_cells
                            else:
                                logger.info(
                                    f"    → Incomplete grid ({coverage:.0%} < 95%), will use freeform"
                                )

            logger.info(
                f"  → Solid bordered tables: {signals['bordered_tables']}, Total cells: {signals['bordered_cells']}"
            )

        except Exception as e:
            logger.warning(f"  → pdfplumber check failed: {e}")

    # =========================================================================
    # SIGNAL 2: Check Y-alignment for borderless tables
    # =========================================================================
    if words_with_bboxes:
        logger.info("[Signal 2] Checking Y-coordinate alignment patterns...")

        # Analyze first 3 pages
        for page_num in range(1, min(4, max(w["page"] for w in words_with_bboxes) + 1)):
            page_words = [w for w in words_with_bboxes if w["page"] == page_num]

            if page_words:
                # Round Y-positions to 5pt tolerance for clustering
                y_positions = [round(w["bbox"]["y0"] / 5) * 5 for w in page_words]
                y_counts = Counter(y_positions)

                # Count rows with 3+ words aligned (likely table rows)
                page_aligned_rows = sum(1 for count in y_counts.values() if count >= 3)
                signals["aligned_rows"] += page_aligned_rows

        logger.info(f"  → Aligned rows (3+ words): {signals['aligned_rows']}")

    # =========================================================================
    # SIGNAL 3: Check word density and amount patterns
    # =========================================================================
    if words_with_bboxes:
        logger.info("[Signal 3] Checking word density and amount patterns...")

        pages = set(w["page"] for w in words_with_bboxes)
        signals["words_per_page"] = len(words_with_bboxes) / len(pages) if pages else 0

        # Check for amount patterns (currency values)
        amount_pattern = re.compile(r"\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{2})?")
        amount_count = sum(
            1 for w in words_with_bboxes if amount_pattern.search(w.get("text", ""))
        )
        signals["has_amount_patterns"] = amount_count > 10

        logger.info(f"  → Words per page: {signals['words_per_page']:.0f}")
        logger.info(f"  → Amount patterns found: {amount_count}")

    # =========================================================================
    # CLASSIFICATION DECISION (Simple: BORDERED or FREEFORM)
    # =========================================================================
    logger.info("-" * 60)
    logger.info("CLASSIFICATION DECISION:")

    # BORDERED: Only if we have strong pdfplumber table signals
    # This gives us accurate bboxes from native cell coordinates
    if signals["bordered_cells"] > 50:
        result = PDFLayoutType.BORDERED
        logger.info(f"  → BORDERED (strong signal: {signals['bordered_cells']} cells)")
    elif signals["bordered_tables"] >= 2 and signals["bordered_cells"] > 20:
        result = PDFLayoutType.BORDERED
        logger.info(f"  → BORDERED (multiple tables: {signals['bordered_tables']})")
    elif signals["bordered_tables"] >= 1 and signals["bordered_cells"] > 10:
        result = PDFLayoutType.BORDERED
        logger.info(f"  → BORDERED (table detected: {signals['bordered_cells']} cells)")
    else:
        # FREEFORM: Everything else - use old LLM-based extraction
        result = PDFLayoutType.FREEFORM
        logger.info("  → FREEFORM (no bordered tables detected)")

    logger.info("=" * 60)

    return result


# ============================================================================
# STRATEGY-SPECIFIC EXTRACTORS
# ============================================================================


def _build_page_context(
    page_num: int,
    merged_pages: List[Dict[str, Any]],
    ai_parse_pages: List[Dict[str, Any]],
) -> str:
    """
    Build additional context for a page from merged_pages and ai_parse_pages.

    This provides PyMuPDF+OCR and AI_PARSE_DOCUMENT text for better extraction context.
    """
    context_parts = []

    # Get merged page text (PyMuPDF + OCR) - 0-indexed
    page_idx = page_num - 1
    if page_idx >= 0 and page_idx < len(merged_pages):
        merged_text = merged_pages[page_idx].get("content", "")
        if merged_text:
            # Truncate if too long (first 2000 chars for context)
            if len(merged_text) > 2000:
                merged_text = merged_text[:2000] + "..."
            context_parts.append(f"=== PAGE TEXT (PyMuPDF + OCR) ===\n{merged_text}")

    # Get AI_PARSE_DOCUMENT text - 0-indexed
    if page_idx >= 0 and page_idx < len(ai_parse_pages):
        ai_text = ai_parse_pages[page_idx].get("content", "")
        if ai_text:
            # Truncate if too long (first 2000 chars for context)
            if len(ai_text) > 2000:
                ai_text = ai_text[:2000] + "..."
            context_parts.append(f"=== PAGE TEXT (AI_PARSE_DOCUMENT) ===\n{ai_text}")

    return "\n\n".join(context_parts) if context_parts else ""


def _find_next_table(
    current_page: int,
    current_table_idx: int,
    page_tables: List[Tuple[TableRegion, PdfPlumberTableData]],
    tables_by_page: Dict[int, List[Tuple[TableRegion, PdfPlumberTableData]]],
    sorted_pages: List[int],
    words_with_bboxes: List[Dict[str, Any]],
) -> Optional[Tuple[ParsedTable, int]]:
    """
    Find the next table after the current one (same page or next page).

    Args:
        current_page: Current page number
        current_table_idx: Index of current table within page_tables
        page_tables: List of tables on current page
        tables_by_page: All tables organized by page
        sorted_pages: Sorted list of page numbers with tables
        words_with_bboxes: Words for parsing tables

    Returns:
        Tuple of (ParsedTable, page_number) or None if no more tables
    """
    # First, check for more tables on the same page
    if current_table_idx + 1 < len(page_tables):
        next_region, next_table_data = page_tables[current_table_idx + 1]
        next_parsed = parse_pdfplumber_table_with_native_bboxes(
            next_table_data, next_region, words_with_bboxes
        )
        return (next_parsed, current_page)

    # No more tables on current page - look at next pages
    current_page_idx = (
        sorted_pages.index(current_page) if current_page in sorted_pages else -1
    )

    for next_page_idx in range(current_page_idx + 1, len(sorted_pages)):
        next_page = sorted_pages[next_page_idx]
        next_page_tables = tables_by_page.get(next_page, [])

        if next_page_tables:
            # Found tables on next page - return the first one
            next_region, next_table_data = next_page_tables[0]
            next_parsed = parse_pdfplumber_table_with_native_bboxes(
                next_table_data, next_region, words_with_bboxes
            )
            return (next_parsed, next_page)

    # No more tables in document
    return None


def _extract_bordered(
    pdf_path: str,
    words_with_bboxes: List[Dict[str, Any]],
    page_dimensions: Dict[int, Dict[str, float]],
    llm_model: Any,
    merged_pages: List[Dict[str, Any]] = None,
    ai_parse_pages: List[Dict[str, Any]] = None,
) -> Tuple[List[ParsedTable], List[Dict[str, Any]]]:
    """
    Extract line items from bordered tables using pdfplumber.

    Uses INCREMENTAL processing with semantic classification:
    1. Process tables page by page
    2. Use LLM to semantically classify each table (summary vs detail vs none)
    3. If a SUMMARY table with line items is found on early pages, extract and EXIT EARLY
    4. If DETAIL tables are found, continue processing with context passing
    5. Uses additional context from merged_pages (PyMuPDF+OCR) and ai_parse_pages for better extraction

    Note: Type override based on PO dominant type is handled post-extraction
    in enrich_line_items_from_po_or_invoice (since PO data isn't available during extraction).
    """
    merged_pages = merged_pages or []
    ai_parse_pages = ai_parse_pages or []
    logger.info(
        "[STRATEGY: BORDERED] Using pdfplumber with incremental semantic classification"
    )

    parsed_tables = []
    all_line_items = []

    try:
        table_regions, table_data_list = detect_tables_pdfplumber(
            pdf_path, page_dimensions
        )

        if not table_regions or not table_data_list:
            logger.info("  → No tables detected by pdfplumber")
            return [], []

        # Group tables by page for incremental processing
        tables_by_page: Dict[int, List[Tuple[TableRegion, "PdfPlumberTableData"]]] = {}
        for region, table_data in zip(table_regions, table_data_list):
            page = region.page
            if page not in tables_by_page:
                tables_by_page[page] = []
            tables_by_page[page].append((region, table_data))

        # Track state for incremental processing
        found_summary_table = False
        summary_line_items = []
        found_main_detail_table = False
        found_detail_table = False  # Track if we've found an explicit "detail" table
        main_table_headers = None
        previous_page_context = ""
        items_by_page: Dict[
            int, List[Dict[str, Any]]
        ] = {}  # Track items for retroactive checking

        # Process tables INCREMENTALLY page by page
        sorted_pages = sorted(tables_by_page.keys())
        logger.info(f"  → Processing {len(sorted_pages)} pages incrementally")

        # Log if we have additional context available
        if merged_pages:
            logger.info(
                f"  → Using additional context: {len(merged_pages)} merged pages (PyMuPDF+OCR)"
            )
        if ai_parse_pages:
            logger.info(
                f"  → Using additional context: {len(ai_parse_pages)} AI_PARSE_DOCUMENT pages"
            )

        for page_num in sorted_pages:
            page_tables = tables_by_page[page_num]
            page_parsed_tables = []

            for region, table_data in page_tables:
                parsed = parse_pdfplumber_table_with_native_bboxes(
                    table_data, region, words_with_bboxes
                )

                if not parsed.rows:
                    continue

                # Basic structural check (permissive - 1+ rows with headers or numeric data)
                if not _looks_like_line_items_table_basic(parsed):
                    continue

                # SEMANTIC CLASSIFICATION: Use LLM to determine table type
                classification = _classify_table_type_semantically(parsed, llm_model)

                if not classification["is_line_items_table"]:
                    logger.debug(
                        f"  Page {page_num}: Skipped table - {classification['reason']}"
                    )
                    continue

                table_type = classification["table_type"]
                logger.info(
                    f"  Page {page_num}: Found {table_type.upper()} table with {len(parsed.rows)} rows"
                )

                # Handle SUMMARY tables - extract and potentially exit early (pages 1-10)
                if table_type == "summary" and page_num <= 10:
                    # Format and extract line items from summary table
                    table_text = _format_table_for_llm(parsed)
                    if table_text:
                        try:
                            # Build additional page context from merged_pages and ai_parse_pages
                            additional_context = _build_page_context(
                                page_num, merged_pages, ai_parse_pages
                            )
                            items = _classify_line_items_with_llm(
                                table_text,
                                parsed,
                                llm_model,
                                previous_page_context,
                                additional_page_context=additional_context,
                            )
                            if items:
                                logger.info(
                                    f"  Page {page_num}: SUMMARY table extracted {len(items)} line items"
                                )
                                summary_line_items.extend(items)
                                items_by_page[page_num] = (
                                    items  # Track for potential retroactive check
                                )
                                found_summary_table = True

                                # TABLE-AWARE EARLY EXIT: Peek at next table (same page or next page)
                                # to decide if we should exit with summary
                                if not parsed_tables and not all_line_items:
                                    current_table_idx = page_tables.index(
                                        (region, table_data)
                                    )
                                    next_table_info = _find_next_table(
                                        current_page=page_num,
                                        current_table_idx=current_table_idx,
                                        page_tables=page_tables,
                                        tables_by_page=tables_by_page,
                                        sorted_pages=sorted_pages,
                                        words_with_bboxes=words_with_bboxes,
                                    )

                                    if next_table_info is None:
                                        # No more tables in document - exit with summary
                                        logger.info(
                                            "  ✓ EARLY EXIT: Summary found, no more tables in document"
                                        )
                                        return [], summary_line_items

                                    next_parsed, next_page = next_table_info
                                    if next_parsed and next_parsed.rows:
                                        next_classification = (
                                            _classify_table_type_semantically(
                                                next_parsed, llm_model
                                            )
                                        )
                                        next_type = next_classification.get(
                                            "table_type"
                                        )

                                        if next_type == "detail":
                                            # Next table is detail - confirms our summary, exit now
                                            logger.info(
                                                f"  ✓ EARLY EXIT: Summary on page {page_num} confirmed by DETAIL table on page {next_page}"
                                            )
                                            return [], summary_line_items
                                        elif next_type == "summary":
                                            # Next table is also summary - multi-section invoice, continue processing
                                            logger.info(
                                                f"  Page {page_num}: Next table (page {next_page}) is also SUMMARY - continuing"
                                            )
                                        # If next_type is "none", continue processing
                        except Exception as e:
                            logger.warning(
                                f"  Page {page_num}: Summary extraction failed: {e}"
                            )
                    continue  # Don't add summary tables to detail processing

                # Handle DETAIL tables - trigger retroactive check if this is explicitly a "detail" table
                if table_type == "detail" and page_num >= 2 and not found_detail_table:
                    found_detail_table = True
                    logger.info(f"  Page {page_num}: Found explicit DETAIL table")

                    # RETROACTIVE CHECK: If we have items from page 1, re-evaluate if page 1 was summary
                    if 1 in items_by_page and not found_summary_table:
                        page1_items = items_by_page[1]
                        logger.info(
                            f"  → Retroactive check: Re-evaluating page 1 ({len(page1_items)} items) as potential summary..."
                        )

                        # If page 1 has significantly fewer items than current page, it might be summary
                        # Use the LLM to confirm
                        # Build context showing page 1 items vs current detail page
                        retroactive_context = f"""
=== PAGE 1 ITEMS ({len(page1_items)} items) ===
{chr(10).join([f'"{item.get("description", "")[:50]}" (${item.get("amount", "0")})' for item in page1_items])}

=== PAGE {page_num} - IDENTIFIED AS DETAIL TABLE ===
This page contains detailed breakdown items.

Given that page {page_num} is a DETAIL breakdown, is page 1 a SUMMARY of those details?
"""
                        p1_content_type, p1_is_summary, _ = classify_page_content_type(
                            retroactive_context, page1_items, llm_model
                        )

                        if p1_is_summary and p1_content_type == "summary":
                            logger.info(
                                f"  ✓ RETROACTIVE: Page 1 confirmed as SUMMARY with {len(page1_items)} items"
                            )
                            return [], page1_items  # Return only page 1 summary items

                # Handle DETAIL tables with continuation logic
                if found_main_detail_table and main_table_headers and parsed.headers:
                    if _looks_like_data_row(parsed.headers):
                        first_row_as_data = _create_first_row_as_data(
                            parsed.headers,
                            parsed.header_bbox,
                            table_data.cell_bboxes[0]
                            if table_data.cell_bboxes
                            else None,
                        )
                        parsed = ParsedTable(
                            region=parsed.region,
                            headers=main_table_headers,
                            rows=[first_row_as_data] + parsed.rows,
                            header_bbox=parsed.header_bbox,
                        )
                        logger.info(
                            f"  Page {page_num}: Continuation table, restored first row as data"
                        )

                if (
                    not found_main_detail_table
                    and parsed.headers
                    and not _looks_like_data_row(parsed.headers)
                ):
                    found_main_detail_table = True
                    main_table_headers = parsed.headers

                page_parsed_tables.append(parsed)
                parsed_tables.append(parsed)
                logger.info(
                    f"  Page {page_num}: Added DETAIL table with {len(parsed.rows)} rows"
                )

            # If we found a summary table with line items and NO detail tables yet, EXIT EARLY
            if found_summary_table and summary_line_items and not parsed_tables:
                logger.info(
                    f"  ✓ EARLY EXIT: Found summary table on page {page_num} with {len(summary_line_items)} line items, skipping {len(sorted_pages) - page_num} remaining pages"
                )
                return [], summary_line_items

            # Extract line items from this page's detail tables (with context)
            if page_parsed_tables:
                page_items = []
                for table in page_parsed_tables:
                    table_text = _format_table_for_llm(table)
                    if table_text:
                        try:
                            # Build additional page context from merged_pages and ai_parse_pages
                            additional_context = _build_page_context(
                                page_num, merged_pages, ai_parse_pages
                            )
                            items = _classify_line_items_with_llm(
                                table_text,
                                table,
                                llm_model,
                                previous_page_context,
                                additional_page_context=additional_context,
                            )
                            logger.info(
                                f"LLM classified {len(items)} line items from table on page {page_num}"
                            )
                            page_items.extend(items)
                            all_line_items.extend(items)

                            # Update context for next page
                            if items:
                                context_items = items[-3:] if len(items) > 3 else items
                                previous_page_context = (
                                    f"Previous page had {len(items)} line items. Last items: "
                                    + "; ".join(
                                        [
                                            f"{item.get('description', '')[:30]} - {item.get('type', '')} - {item.get('amount', '')}"
                                            for item in context_items
                                        ]
                                    )
                                )
                        except Exception as e:
                            logger.warning(
                                f"LLM classification failed for page {page_num}: {e}"
                            )

                # Track items by page for potential retroactive checking
                if page_items:
                    items_by_page[page_num] = page_items

        # Handle summary vs detail preference:
        # - ONLY prefer summary if it was found BEFORE any detail tables (early exit already handled this)
        # - If we found detail items first, keep them (summary found later is likely just payment info)
        # - The early exit logic already handled the case where summary is found first
        if found_summary_table and summary_line_items and not all_line_items:
            # Summary found but no detail items - use summary
            logger.info(
                f"  → Using summary table with {len(summary_line_items)} items (no detail items found)"
            )
            return [], summary_line_items
        elif all_line_items:
            # We have detail items - use those (don't replace with later "summary")
            if found_summary_table:
                logger.info(
                    f"  → Keeping {len(all_line_items)} detail items (ignoring later summary with {len(summary_line_items)} items)"
                )

            logger.info(
                f"  → Extracted {len(all_line_items)} line items from {len(parsed_tables)} tables"
            )

    except Exception as e:
        logger.error(f"  → Bordered extraction failed: {e}")
        import traceback

        traceback.print_exc()

    return parsed_tables, all_line_items


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def detect_and_parse_tables(
    page_images: List[Image.Image],
    page_dimensions: Dict[int, Dict[str, float]],
    words_with_bboxes: List[Dict[str, Any]],
    pdf_path: str = None,
    use_llm_classification: bool = True,
    llm_model: Any = None,
    merged_pages: List[Dict[str, Any]] = None,
    ai_parse_pages: List[Dict[str, Any]] = None,
) -> Tuple[List[ParsedTable], List[Dict[str, Any]]]:
    """
    Main entry point: detect tables, parse structure, extract line items.

    Uses intelligent routing based on PDF layout classification:
    1. BORDERED - pdfplumber with native cell coordinates (pixel-perfect)
    2. BORDERLESS - Y-coordinate row clustering + LLM verification
    3. FREEFORM - Text pattern extraction
    4. HYBRID - Try multiple strategies in priority order

    Note: Type override based on PO dominant type is handled post-extraction
    in enrich_line_items_from_po_or_invoice (since PO data isn't available during extraction).

    Args:
        page_images: List of page images (PIL)
        page_dimensions: Page dimensions in PDF points
        words_with_bboxes: OCR words with bounding boxes
        pdf_path: Path to PDF file (for pdfplumber extraction)
        use_llm_classification: Whether to use LLM for Goods/Service classification
        llm_model: Optional pre-initialized LLM model
        merged_pages: Optional merged text per page (PyMuPDF + OCR) for additional context
        ai_parse_pages: Optional AI_PARSE_DOCUMENT text per page for additional context

    Returns:
        Tuple of (parsed_tables, line_items)
    """
    logger.info("=" * 70)
    logger.info("TABLE DETECTION & LINE ITEM EXTRACTION")
    logger.info("=" * 70)

    # =========================================================================
    # STEP 1: Classify PDF layout to determine optimal strategy
    # =========================================================================
    layout_type = classify_pdf_layout(pdf_path, words_with_bboxes, page_dimensions)

    parsed_tables = []
    all_line_items = []

    # =========================================================================
    # MODEL SELECTION: Use provided model or create default
    # =========================================================================
    from app.model import CortexModel

    # Use provided model or create a default Sonnet model
    model = (
        llm_model
        if llm_model
        else CortexModel(
            temperature=0.0,
            max_tokens=8000,
        )
    )

    # =========================================================================
    # STEP 2: Route to appropriate strategy
    # - BORDERED: Use pdfplumber (accurate bboxes)
    # - FREEFORM: Return empty, let nodes.py use old LLM extraction
    # =========================================================================

    if layout_type == PDFLayoutType.BORDERED:
        # Use pdfplumber - best for bordered tables with accurate bboxes
        parsed_tables, all_line_items = _extract_bordered(
            pdf_path,
            words_with_bboxes,
            page_dimensions,
            model,
            merged_pages=merged_pages or [],
            ai_parse_pages=ai_parse_pages or [],
        )

        if all_line_items:
            # Count bboxes from pdfplumber
            items_with_bbox = sum(
                1
                for li in all_line_items
                if (li.get("row_bbox") or {}).get("x1", 0) > 0
            )
            logger.info(
                f"✓ BORDERED strategy successful: {len(all_line_items)} line items, {items_with_bbox} with bboxes"
            )
        else:
            # Bordered detected but no items extracted - fall back to freeform
            logger.info(
                "  → Bordered tables found but no line items, will use FREEFORM"
            )
            layout_type = PDFLayoutType.FREEFORM

    if layout_type == PDFLayoutType.FREEFORM:
        # Return empty - nodes.py will use the old LLM-based extraction
        logger.info("✓ FREEFORM: Returning empty, nodes.py will use old LLM extraction")
        all_line_items = []

    if all_line_items:
        logger.info(f"✓ Final result: {len(all_line_items)} line items extracted")
    else:
        logger.info("→ No items from table detection, falling back to LLM extraction")

    logger.info("=" * 70)

    return parsed_tables, all_line_items


def _has_numeric_data(rows: List[List[TableCell]], check_limit: int = 5) -> bool:
    """Check if rows contain numeric data (likely amounts)."""
    for row in rows[:check_limit]:
        for cell in row:
            text = cell.text.strip()
            if any(c.isdigit() for c in text) and any(c in text for c in ".,"):
                return True
    return False


def _looks_like_line_items_table_basic(parsed: ParsedTable) -> bool:
    """
    Basic structural check for potential line items table.

    This is a PERMISSIVE check - we want to catch all potential tables
    and let the semantic LLM classification make the final decision.

    Requirements:
    - At least 1 row of data (after header)
    - Has headers OR has numeric data
    """
    if not parsed.rows:
        return False

    # Must have at least 1 data row
    if len(parsed.rows) < 1:
        return False

    # Accept if it has headers (most structured tables do)
    if parsed.headers and len(parsed.headers) > 0:
        return True

    # Accept if it has numeric data (amounts, prices)
    if _has_numeric_data(parsed.rows):
        return True

    return False


def get_table_bboxes(parsed_tables: List[ParsedTable]) -> List[Dict[str, Any]]:
    """
    Get table bounding boxes for frontend highlighting.
    """
    return [
        {
            "bbox": table.region.bbox,
            "page": table.region.page,
            "confidence": table.region.confidence,
            "type": "line_items_table",
            "detection_method": table.region.detection_method,
            "header_bbox": table.header_bbox,
            "row_count": len(table.rows),
            "column_count": len(table.headers),
        }
        for table in parsed_tables
    ]
