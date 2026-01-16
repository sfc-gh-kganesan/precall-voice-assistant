"""
Extraction nodes for invoice processing.
Standalone version - no Snowflake dependencies.
"""

import logging
import tempfile
import os
import traceback
from typing import Dict, List, Any, Optional

import fitz  # PyMuPDF
from pdf2image import convert_from_path
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage

from app.model import CortexModel
from app.schemas import State, InvoiceFields, LineItem
from app.prompts import TEXT_EXTRACT_PROMPT, LINE_ITEMS_UNIFIED_PROMPT
from app.helpers import (
    extract_text_and_lines_with_bboxes,
    run_tesseract_ocr,
    merge_ocr_results,
    reconstruct_layout_from_bboxes,
    sort_reading_order,
    dehyphenate_text,
    normalize_text,
    validate_with_regex,
    find_and_verify_field_bbox,
    calculate_extraction_confidence,
    filter_line_items_with_confidence,
    normalize_amount,
)

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC OUTPUT SCHEMAS FOR LLM
# ============================================================================


class TextExtractOutput(BaseModel):
    """Output structure for text extraction"""
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


class LineItemOutput(BaseModel):
    """Single line item from invoice"""
    model_config = {"extra": "forbid"}

    row_index: int
    is_line_item: bool
    description: str
    type: str
    amount: str
    unit_of_measure: str
    quantity: str
    unit_price: str
    service_start_date: str
    service_end_date: str


class LineItemsOutput(BaseModel):
    """Output structure for line items extraction"""
    model_config = {"extra": "forbid"}

    line_items: list[LineItemOutput]


# ============================================================================
# EXTRACTION NODES
# ============================================================================


def extract_bounding_boxes(state: State) -> Dict[str, Any]:
    """
    Extract word-level AND line-level bounding boxes from PDF using PyMuPDF + Tesseract OCR.

    This node runs BEFORE run_unified_extractor to provide pre-extracted bounding boxes.

    Returns state with:
    - bounding_boxes: Merged word-level bounding boxes (for field extraction)
    - text_blocks_with_bboxes: Merged line-level bounding boxes
    - page_dimensions: Page dimensions for coordinate conversion
    """
    pdf_path = state["pdf_path"]
    invoice_id = state.get("invoice_id", os.path.basename(pdf_path))

    logger.info(f"Extracting word and line bounding boxes for: {pdf_path}")

    try:
        # Step 1: Run PyMuPDF extraction for both words AND lines
        logger.info("Extracting text with PyMuPDF (words + lines)")
        pymupdf_result = extract_text_and_lines_with_bboxes(pdf_path)
        pymupdf_words = pymupdf_result["words"]
        pymupdf_lines = pymupdf_result["lines"]
        page_dimensions = pymupdf_result["page_dimensions"]

        logger.info(
            f"PyMuPDF extracted {len(pymupdf_words)} words and {len(pymupdf_lines)} lines"
        )

        # Step 2: Run Tesseract OCR at multiple DPIs
        ocr_words_300, ocr_lines_300 = run_tesseract_ocr(
            pdf_path, page_dimensions, dpi=300
        )
        ocr_words_600, ocr_lines_600 = run_tesseract_ocr(
            pdf_path, page_dimensions, dpi=600
        )

        logger.info(f"OCR at 300 DPI: {len(ocr_words_300)} words, {len(ocr_lines_300)} lines")
        logger.info(f"OCR at 600 DPI: {len(ocr_words_600)} words, {len(ocr_lines_600)} lines")

        # Step 3: Merge results from different sources
        merged_words = merge_ocr_results(
            pymupdf_words, ocr_words_300, ocr_words_600
        )
        merged_lines = merge_ocr_results(
            pymupdf_lines, ocr_lines_300, ocr_lines_600
        )

        logger.info(f"Merged: {len(merged_words)} words, {len(merged_lines)} lines")

        return {
            "bounding_boxes": merged_words,
            "text_blocks_with_bboxes": merged_lines,
            "page_dimensions": page_dimensions,
        }

    except Exception as e:
        logger.error(f"Error extracting bounding boxes: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "bounding_boxes": [],
            "text_blocks_with_bboxes": [],
            "page_dimensions": {},
        }


def run_unified_extractor(state: State) -> Dict[str, Any]:
    """
    UNIFIED EXTRACTION: Uses pre-extracted bounding boxes for field extraction.

    This function:
    1. Uses pre-extracted word bounding boxes from state
    2. Uses Cortex LLM to extract invoice fields from merged text
    3. Maps extracted fields to their bounding boxes
    4. Stores all text sources in state for line item extraction
    """
    pdf_path = state["pdf_path"]
    invoice_id = state.get("invoice_id", os.path.basename(pdf_path))

    logger.info(f"Running unified extractor for: {pdf_path}")

    try:
        # Step 1: Get pre-extracted bounding boxes from state
        merged_words = state.get("bounding_boxes", [])

        if not merged_words:
            logger.error("No pre-extracted bounding boxes found in state")
            return {
                "fields_with_bounding_boxes": {},
                "ai_extract_metadata": {},
            }

        logger.info(f"Using {len(merged_words)} pre-extracted words from state")

        # Step 2: Build merged page-by-page text for line item extraction
        merged_pages = []
        try:
            words_by_page = {}
            for word in merged_words:
                page = word.get("page", 1)
                if page not in words_by_page:
                    words_by_page[page] = []
                words_by_page[page].append(word)

            max_page = max(words_by_page.keys()) if words_by_page else 0
            for page_num in range(1, max_page + 1):
                page_words = words_by_page.get(page_num, [])
                if page_words:
                    page_text = reconstruct_layout_from_bboxes(page_words)
                    merged_pages.append({"content": page_text, "page": page_num})
                else:
                    merged_pages.append({"content": "", "page": page_num})

            logger.info(f"Built {len(merged_pages)} pages from bounding boxes")
        except Exception as e:
            logger.warning(f"Could not build merged page text: {e}")

        # Step 3: Build full text from merged words
        words_sorted = sort_reading_order(merged_words)
        full_text = dehyphenate_text(words_sorted)
        full_text = normalize_text(full_text)

        logger.info(f"Full text: {len(full_text)} characters")

        # Step 4: Use LLM to extract fields
        logger.info("Using LLM to extract invoice fields")

        model = CortexModel(
            temperature=0.0,
            max_tokens=1500,
        )

        extraction_prompt = TEXT_EXTRACT_PROMPT.format(invoice_text=full_text)
        msg = [
            SystemMessage(content="You are an invoice data extraction assistant."),
            HumanMessage(content=extraction_prompt),
        ]

        response = model.model.with_structured_output(TextExtractOutput).invoke(msg)
        extracted_fields = response.model_dump()

        logger.info(f"Extracted fields: {extracted_fields}")

        # Apply validation
        extracted_fields = validate_with_regex(extracted_fields)

        # Step 5: Map extracted fields to bounding boxes
        logger.info("Mapping extracted fields to bounding boxes")
        fields_with_bounding_boxes = {}

        for field_name, field_value in extracted_fields.items():
            if field_name == "memo_description":
                continue

            if field_value and field_value != "null":
                bbox_data = find_and_verify_field_bbox(
                    field_name=field_name,
                    field_value=field_value,
                    words_with_bboxes=merged_words,
                    model=model,
                    full_text=full_text,
                    invoice_id=invoice_id,
                )

                if bbox_data:
                    fields_with_bounding_boxes[field_name] = bbox_data

        # Build ai_extract_metadata
        ai_extract_metadata = extracted_fields.copy()
        for field_name, bbox_data in fields_with_bounding_boxes.items():
            ai_extract_metadata[field_name] = bbox_data.get("value")

        logger.info(
            f"✓ Extraction complete: {len(fields_with_bounding_boxes)} fields with bboxes"
        )

        # Calculate extraction confidence
        extraction_confidence = calculate_extraction_confidence(
            extracted_fields, fields_with_bounding_boxes, full_text
        )
        logger.info(
            f"✓ Extraction confidence: {extraction_confidence['score']} - {extraction_confidence['reasoning']}"
        )

        return {
            "fields_with_bounding_boxes": fields_with_bounding_boxes,
            "ai_extract_metadata": ai_extract_metadata,
            "extraction_confidence": extraction_confidence,
            "merged_pages": merged_pages,
            "ai_parse_pages": [],  # Not using AI_PARSE_DOCUMENT in standalone mode
            "ai_parse_text": "",
        }

    except Exception as e:
        logger.error(f"Error in unified extractor: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "fields_with_bounding_boxes": {},
            "ai_extract_metadata": {},
            "merged_pages": [],
            "ai_parse_pages": [],
            "ai_parse_text": "",
        }


def extract_line_items(state: State) -> Dict[str, Any]:
    """
    Extract line items from the invoice using page-by-page LLM extraction.

    This function:
    1. Uses pre-extracted merged page texts from unified extractor
    2. Extracts line items from each page separately
    3. Merges all line items from all pages
    """
    pdf_path = state["pdf_path"]
    invoice_id = state.get("invoice_id", os.path.basename(pdf_path))

    logger.info(f"Extracting line items (freeform) for: {invoice_id}")

    try:
        # Step 1: Get page texts from state
        merged_pages = state.get("merged_pages", [])

        # Fallback: extract directly from PDF
        if not merged_pages:
            logger.warning("No pre-extracted pages in state, extracting from PDF")
            doc = fitz.open(pdf_path)
            merged_pages = [
                {"content": page.get_text(), "page": i + 1}
                for i, page in enumerate(doc)
            ]
            doc.close()

        logger.info(f"PDF has {len(merged_pages)} page(s)")

        if not merged_pages:
            logger.warning("No pages found in PDF")
            return {"line_items": []}

        # Step 2: Extract line items from each page
        model = CortexModel(
            temperature=0.0,
            max_tokens=10000,
        )
        all_line_items = []
        previous_page_context = ""

        for page_num, page_data in enumerate(merged_pages, 1):
            page_text = page_data.get("content", "")

            if len(page_text) < 100:
                logger.info(f"Page {page_num}: Skipping (too little text)")
                continue

            logger.info(f"Page {page_num}: Extracting line items ({len(page_text)} chars)")

            try:
                context_section = ""
                if previous_page_context:
                    context_section = f"""
=== CONTEXT FROM PREVIOUS PAGES ===
{previous_page_context}

This page is a CONTINUATION of line items from previous pages.
"""

                extraction_prompt = LINE_ITEMS_UNIFIED_PROMPT.format(
                    context_section=context_section,
                    invoice_data=page_text,
                )

                system_content = (
                    "You are an invoice line items extraction assistant. "
                    'CRITICAL: Every line item MUST have a "type" field set to either "Goods" or "Service".'
                )

                msg = [
                    SystemMessage(content=system_content),
                    HumanMessage(content=extraction_prompt),
                ]

                response = model.model.with_structured_output(LineItemsOutput).invoke(msg)
                raw_items = response.model_dump()["line_items"]

                # Filter to only valid line items
                page_line_items = [
                    item for item in raw_items if item.get("is_line_item", True)
                ]

                if page_line_items:
                    logger.info(
                        f"Page {page_num}: Found {len(page_line_items)} line items"
                    )
                    for item in page_line_items:
                        item["page"] = page_num

                    all_line_items.extend(page_line_items)

                    # Update context for next page
                    context_items = page_line_items[-5:] if len(page_line_items) > 5 else page_line_items
                    items_summary = "; ".join([
                        f'"{item.get("description", "")[:40]}" ({item.get("type", "")})'
                        for item in context_items
                    ])
                    previous_page_context = f"Extracted {len(all_line_items)} items so far. Recent: {items_summary}"
                else:
                    logger.info(f"Page {page_num}: No line items found")

            except Exception as page_error:
                logger.error(f"Page {page_num}: Error: {str(page_error)}")
                continue

        logger.info(f"Extracted {len(all_line_items)} line items across all pages")

        # Step 3: Filter and normalize
        ai_metadata = state.get("ai_extract_metadata", {})
        invoice_date = ai_metadata.get("invoice_date") if isinstance(ai_metadata, dict) else None

        filtered_line_items = filter_line_items_with_confidence(
            all_line_items,
            model,
            invoice_date=invoice_date,
        )

        # Step 4: Assign line numbers and normalize amounts
        final_line_items = []
        for idx, item in enumerate(filtered_line_items, start=1):
            normalized_amount = normalize_amount(item.get("amount") or "", return_string=True)
            normalized_unit_price = normalize_amount(item.get("unit_price") or "", return_string=True)
            normalized_quantity = normalize_amount(item.get("quantity") or "", return_string=True)

            final_line_items.append({
                "line_number": idx,
                "description": item.get("description") or "",
                "type": item.get("type") or "Service",
                "quantity": normalized_quantity or item.get("quantity"),
                "unit_price": normalized_unit_price or item.get("unit_price"),
                "amount": normalized_amount or item.get("amount"),
                "unit_of_measure": item.get("unit_of_measure"),
                "service_start_date": item.get("service_start_date"),
                "service_end_date": item.get("service_end_date"),
                "matched_po_line": None,
            })

        logger.info(f"Final: {len(final_line_items)} line items")

        return {"line_items": final_line_items}

    except Exception as e:
        logger.error(f"Error extracting line items: {str(e)}")
        logger.error(traceback.format_exc())
        return {"line_items": []}


def extract_line_items_with_tables(state: State) -> Dict[str, Any]:
    """
    Extract line items using hybrid table detection.

    This function:
    1. Uses pdfplumber for bordered tables (pixel-perfect bboxes)
    2. Falls back to LLM page-by-page extraction if no tables detected
    """
    pdf_path = state["pdf_path"]
    invoice_id = state.get("invoice_id", os.path.basename(pdf_path))
    bounding_boxes = state.get("bounding_boxes", [])

    logger.info(f"Extracting line items with table detection for: {invoice_id}")

    try:
        from app.table_detection import detect_and_parse_tables, get_table_bboxes

        # Step 1: Get page dimensions
        doc = fitz.open(pdf_path)
        page_dimensions = {}
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect
            page_dimensions[page_num] = {"width": rect.width, "height": rect.height}
        doc.close()

        # Step 2: Convert PDF to images
        page_images = convert_from_path(pdf_path, dpi=300)

        # Step 3: Create LLM model
        model = CortexModel(
            temperature=0.0,
            max_tokens=8000,
        )

        # Step 4: Get additional text context from state
        merged_pages = state.get("merged_pages", [])
        ai_parse_pages = state.get("ai_parse_pages", [])

        # Step 5: Detect tables and extract line items
        logger.info("Running hybrid table detection + LLM classification")
        parsed_tables, table_line_items = detect_and_parse_tables(
            page_images=page_images,
            page_dimensions=page_dimensions,
            words_with_bboxes=bounding_boxes,
            pdf_path=pdf_path,
            use_llm_classification=True,
            llm_model=model,
            merged_pages=merged_pages,
            ai_parse_pages=ai_parse_pages,
        )

        if table_line_items:
            logger.info(f"Table extraction found {len(table_line_items)} line items")

            table_bboxes = get_table_bboxes(parsed_tables)

            # Filter and normalize
            ai_metadata = state.get("ai_extract_metadata", {})
            invoice_date = ai_metadata.get("invoice_date") if isinstance(ai_metadata, dict) else None

            filtered_line_items = filter_line_items_with_confidence(
                table_line_items,
                model,
                invoice_date=invoice_date,
            )

            # Normalize amounts
            normalized_line_items = []
            for idx, item in enumerate(filtered_line_items, start=1):
                normalized_amount = normalize_amount(item.get("amount") or "", return_string=True)
                normalized_unit_price = normalize_amount(item.get("unit_price") or "", return_string=True)
                normalized_quantity = normalize_amount(item.get("quantity") or "", return_string=True)

                normalized_item = item.copy()
                normalized_item["line_number"] = idx
                normalized_item["amount"] = normalized_amount or item.get("amount")
                normalized_item["unit_price"] = normalized_unit_price or item.get("unit_price")
                normalized_item["quantity"] = normalized_quantity or item.get("quantity")
                normalized_line_items.append(normalized_item)

            return {
                "line_items": normalized_line_items,
                "table_bboxes": table_bboxes,
            }

        else:
            logger.info("No tables detected, falling back to LLM extraction")
            return extract_line_items(state)

    except ImportError as e:
        logger.warning(f"Table detection dependencies not available: {e}")
        return extract_line_items(state)

    except Exception as e:
        logger.error(f"Error in table-based extraction: {str(e)}")
        logger.error(traceback.format_exc())
        return extract_line_items(state)


def collect_extraction_output(state: State) -> Dict[str, Any]:
    """
    Collect all extraction results into a single output.
    This is the final node in the extraction-only graph.
    """
    from app.schemas import ExtractionOutput, InvoiceFieldsOutput, LineItemOutput

    ai_extract_metadata = state.get("ai_extract_metadata", {})
    line_items = state.get("line_items", [])

    # Build output
    fields = InvoiceFieldsOutput(
        invoice_number=ai_extract_metadata.get("invoice_number", ""),
        snowflake_entity=ai_extract_metadata.get("snowflake_entity", ""),
        vendor_name=ai_extract_metadata.get("vendor_name", ""),
        invoice_date=ai_extract_metadata.get("invoice_date", ""),
        total_amount=ai_extract_metadata.get("total_amount", ""),
        tax_amount=ai_extract_metadata.get("tax_amount", ""),
        currency=ai_extract_metadata.get("currency", ""),
        purchase_order_number=ai_extract_metadata.get("purchase_order_number", ""),
        memo_description=ai_extract_metadata.get("memo_description", ""),
    )

    line_items_output = [
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

    return {
        "extraction_output": ExtractionOutput(
            fields=fields,
            line_items=line_items_output,
            fields_with_bounding_boxes=state.get("fields_with_bounding_boxes", {}),
            extraction_confidence=state.get("extraction_confidence", {}),
        )
    }

