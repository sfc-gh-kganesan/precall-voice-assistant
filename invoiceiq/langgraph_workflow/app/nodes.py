import logging
import json
from typing import Literal, Dict, List, Tuple, Optional, Any
import tempfile
import requests
import os
import traceback
import re
from datetime import datetime

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from app.prompts import (
    AI_EXTRACT_PROMPT,
    HUMAN_MESSAGE_PROMPT,
    SYSTEM_MESSAGE,
    TEXT_EXTRACT_PROMPT,
)
from app.utils import run_query
from app.model import CortexModel
from app.utils import (
    State,
    AI_Decision_Output,
    CLASS_OPTIONS,
    FRESH_OR_RERUN_OPTIONS,
    EXTRACTION_METHOD_OPTIONS,
)
import app.queries as queries
from app.helpers import (
    normalize_text,
    normalize_number_variations,
    sort_reading_order,
    dehyphenate_text,
    validate_with_regex,
    extract_text_with_bboxes,
    find_text_bboxes,
    normalize_date_to_snowflake_format,
)

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
        class_options_list = ",".join(f"'{opt}'" for opt in CLASS_OPTIONS)

        query = queries.CLASSIFY_QUERY.format(class_options_list=class_options_list)
        rows = run_query(
            query, {"stage_name": stage_name, "relative_path": relative_path}
        )
        if rows and len(rows) > 0:
            try:
                classification = json.loads(rows[0].get("CLASSIFICATION")).get("label")
                parsed_text = rows[0].get("PARSED_TEXT", "")

                if classification in CLASS_OPTIONS:
                    return {
                        "classification": classification,
                        "parsed_text": parsed_text,
                    }
                else:  # classification is None or not in CLASS_OPTIONS
                    logger.error(f"Invalid invoice classification: {classification}")
                    return {
                        "classification": CLASS_OPTIONS[1],
                        "parsed_text": parsed_text,
                    }
            except IndexError:
                logger.error(
                    f"No invoice classification found for relative path: {relative_path}"
                )
                return {"classification": CLASS_OPTIONS[1]}
            except Exception as e:
                logger.error(f"Error classifying invoice: {str(e)}")
                return {"classification": CLASS_OPTIONS[1]}
        else:
            logger.error(
                f"No invoice classification found for relative path: {relative_path}"
            )
            return {"classification": CLASS_OPTIONS[1]}
    except Exception as e:
        logger.error(f"Error classifying invoice: {str(e)}")
        return {"classification": CLASS_OPTIONS[1]}


def fresh_or_rerun_router(
    state: State,
) -> Literal[FRESH_OR_RERUN_OPTIONS[0], FRESH_OR_RERUN_OPTIONS[1]]:
    """
    Determine if the invoice should be processed from scratch or using existing data.

    Example options:
    FRESH_OR_RERUN_OPTIONS = ["fresh", "rerun"]

    Returns:
        FRESH_OR_RERUN_OPTIONS[0] if the invoice should be processed from scratch
        FRESH_OR_RERUN_OPTIONS[1] if the invoice should be processed using existing data
    """

    if state.get(
        "use_existing_ai_extract", False
    ):  # LangGraph Studio doesn't default a value for use_existing_ai_extract
        return FRESH_OR_RERUN_OPTIONS[1]
    else:
        return FRESH_OR_RERUN_OPTIONS[0]


def class_router(state: State) -> Literal["__end__", "detect_extraction_method"]:
    """
    Routes workflow to detect_extraction_method if invoice classified as invoice or to END otherwise.


    Returns:
        "__end__" if invoice classified as 'not an invoice'
        "detect_extraction_method" if invoice classified as 'invoice'
    """

    classification = state["classification"]
    if classification == CLASS_OPTIONS[0]:
        return "detect_extraction_method"
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
        rows = run_query(
            query, {"invoice_id": invoice_id, "target_table": target_table}
        )

        if rows and len(rows) > 0:
            try:
                return {"ai_extract_metadata": rows[0]}
            except IndexError:
                logger.error(
                    f"No AI extract metadata found for invoice_id: {invoice_id}"
                )
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
        rows = run_query(
            query,
            {
                "stage_name": stage_name,
                "relative_path": relative_path,
                "ai_extract_prompt": json.dumps(AI_EXTRACT_PROMPT),
            },
        )

        if rows and len(rows) > 0:
            # AI_EXTRACT returns a single row, so extract the first row
            data = json.loads(rows[0].get("INVOICE_METADATA"))

            return {"ai_extract_metadata": data}
        else:
            logger.error(
                f"No AI extract metadata found for relative path: {relative_path}"
            )
            return {"ai_extract_metadata": {}}

    except Exception as e:
        logger.error(f"Error running AI extract: {str(e)}")
        return {"ai_extract_metadata": {}}


def run_text_extractor(state: State) -> State:
    """
    Extract text with bounding boxes using PyMuPDF and Cortex LLM.

    This function:
    1. Extracts all text by words with bounding boxes using PyMuPDF
    2. Gets the full text content from AI_PARSE_DOCUMENT
    3. Uses Cortex LLM to extract invoice fields from the text
    4. Maps extracted fields to their bounding boxes using deterministic algorithm + LLM

    Extracted metadata with bounding boxes passed to state['text_extract_metadata'].
    """

    stage_name = state["stage_name"]
    if not stage_name.startswith("@"):
        stage_name = "@" + stage_name
    relative_path = state["relative_path"]

    logger.info(f"Running text extractor for relative path: {relative_path}")

    try:
        # Step 1: Use cached parsed text from classification (avoids redundant AI_PARSE_DOCUMENT call)
        full_text = state.get("parsed_text", "")

        if not full_text:
            logger.warning("No parsed text in state, falling back to AI_PARSE_DOCUMENT")
            text_query = queries.GET_FULL_TEXT_QUERY
            text_rows = run_query(
                text_query, {"stage_name": stage_name, "relative_path": relative_path}
            )

            if not text_rows or len(text_rows) == 0:
                logger.error(
                    f"No text content found for relative path: {relative_path}"
                )
                return {
                    "bounding_boxes": [],
                    "fields_with_bounding_boxes": {},
                    "ai_extract_metadata": {},
                }

            full_text_data = json.loads(text_rows[0].get("CONTENT"))
            full_text = full_text_data.get("content", "")

        if not full_text:
            logger.error(f"Empty text content for relative path: {relative_path}")
            return {
                "bounding_boxes": [],
                "fields_with_bounding_boxes": {},
                "ai_extract_metadata": {},
            }

        logger.info(f"Using text: {len(full_text)} characters")

        # Normalize text for better LLM extraction
        full_text = normalize_text(full_text)
        logger.info(f"Text normalized")

        # Step 2: Get presigned URL and download PDF
        logger.info("Getting presigned URL for PDF")
        url_query = queries.GET_PDF_FILE_QUERY
        url_rows = run_query(
            url_query, {"stage_name": stage_name, "relative_path": relative_path}
        )

        if not url_rows or len(url_rows) == 0:
            logger.error(f"No presigned URL found for relative path: {relative_path}")
            return {"text_extract_metadata": {}}

        presigned_url = url_rows[0].get("PRESIGNED_URL")

        # Download PDF to temporary file
        logger.info("Downloading PDF file")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            response = requests.get(presigned_url)
            response.raise_for_status()
            tmp_file.write(response.content)

        # Step 3: Extract text with bounding boxes using PyMuPDF
        logger.info("Extracting text with bounding boxes using PyMuPDF")
        words_with_bboxes = extract_text_with_bboxes(tmp_path)
        logger.info(f"Extracted {len(words_with_bboxes)} words with bounding boxes")

        # Clean up temporary file
        os.unlink(tmp_path)

        # Improve text quality: sort reading order and dehyphenate
        words_sorted = sort_reading_order(words_with_bboxes)
        full_text_improved = dehyphenate_text(words_sorted)

        # Use improved text if available, fallback to cached
        if full_text_improved and len(full_text_improved) > len(full_text) * 0.8:
            full_text = full_text_improved
            logger.info("Using improved text (sorted + dehyphenated)")

        # Step 4: Use Cortex LLM to extract fields from full text
        logger.info("Using Cortex LLM to extract fields")
        # Use extraction-optimized settings: low temp, limited tokens, JSON enforced
        model = CortexModel(temperature=0.0, max_tokens=1500)

        # Create extraction prompt
        extraction_prompt = TEXT_EXTRACT_PROMPT.format(invoice_text=full_text)

        msg = [
            SystemMessage(content="You are an invoice data extraction assistant."),
            HumanMessage(content=extraction_prompt),
        ]

        # Define the output structure for field extraction
        # Cortex requires simple string types without Optional
        class TextExtractOutput(BaseModel):
            """Output structure for text extraction"""

            model_config = {"extra": "forbid"}

            classification: str
            invoice_number: str
            snowflake_entity: str
            vendor_name: str
            invoice_date: str
            total_amount: str
            tax_amount: str
            currency: str
            purchase_order_number: str
            payment_terms: str
            due_date: str
            memo_description: str

        response = model.model.with_structured_output(TextExtractOutput).invoke(msg)
        extracted_fields = response.model_dump()

        logger.info(f"Extracted fields: {extracted_fields}")

        # Apply regex validation
        extracted_fields = validate_with_regex(extracted_fields)

        # Additional semantic validation
        if extracted_fields.get("snowflake_entity"):
            entity = extracted_fields["snowflake_entity"].lower()
            if "snowflake" not in entity and entity not in ["bonbono", "wpp"]:
                logger.warning(
                    f"Snowflake entity may be incorrect: {extracted_fields['snowflake_entity']}"
                )

        if extracted_fields.get("vendor_name"):
            vendor = extracted_fields["vendor_name"].lower()
            if "snowflake" in vendor:
                logger.warning(
                    f"Vendor contains 'Snowflake', may be swapped with customer: {extracted_fields['vendor_name']}"
                )

        # Step 5: Find bounding boxes for each extracted field with evidence validation
        logger.info("Mapping extracted fields to bounding boxes")
        fields_with_bounding_boxes = {}

        for field_name, field_value in extracted_fields.items():
            if field_value and field_value != "null":
                logger.info(
                    f"Finding bounding boxes for field '{field_name}': {field_value}"
                )
                bbox_data = find_text_bboxes(
                    field_value, words_with_bboxes, model, full_text
                )

                if bbox_data:
                    # Validate evidence: check if extracted value appears in actual PDF text
                    evidence = bbox_data.get("evidence", "")
                    value_normalized = (
                        field_value.lower()
                        .replace(" ", "")
                        .replace(",", "")
                        .replace(".", "")
                    )
                    evidence_normalized = (
                        evidence.lower()
                        .replace(" ", "")
                        .replace(",", "")
                        .replace(".", "")
                    )

                    if (
                        value_normalized
                        and evidence_normalized
                        and value_normalized not in evidence_normalized
                    ):
                        logger.warning(
                            f"Evidence mismatch for '{field_name}': extracted='{field_value}', evidence='{evidence}'"
                        )
                        bbox_data["confidence"] = max(
                            0, bbox_data.get("confidence", 100) - 20
                        )  # Reduce confidence

                    fields_with_bounding_boxes[field_name] = bbox_data
                    conf = bbox_data.get("confidence", 100)
                    logger.info(
                        f"Found bounding box for '{field_name}' on page {bbox_data['page']} (confidence: {conf})"
                    )
                else:
                    logger.warning(
                        f"No bounding box found for field '{field_name}': {field_value}"
                    )

        # Build ai_extract_metadata from ALL extracted fields (not just those with bboxes)
        # This ensures fields are saved to database even if we couldn't find their bounding boxes
        ai_extract_metadata = {}
        for field_name, field_value in extracted_fields.items():
            if field_value and field_value != "null":
                ai_extract_metadata[field_name] = field_value

        # Return bounding boxes, fields with bounding boxes, and ai_extract_metadata
        return {
            "bounding_boxes": words_with_bboxes,
            "fields_with_bounding_boxes": fields_with_bounding_boxes,
            "ai_extract_metadata": ai_extract_metadata,
        }

    except Exception as e:
        logger.error(f"Error running text extractor: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "bounding_boxes": [],
            "fields_with_bounding_boxes": {},
            "ai_extract_metadata": {},
        }


def run_ocr_extractor(state: State) -> State:
    """
    Extract text with bounding boxes using Tesseract OCR for scanned PDFs.

    This function:
    1. Converts PDF pages to images
    2. Uses Tesseract OCR to extract text with word-level bounding boxes
    3. Uses Cortex LLM to extract invoice fields from the text
    4. Maps extracted fields to their bounding boxes

    Extracted metadata with bounding boxes passed to state.
    """

    stage_name = state["stage_name"]
    if not stage_name.startswith("@"):
        stage_name = "@" + stage_name
    relative_path = state["relative_path"]

    logger.info(f"Running OCR extractor for relative path: {relative_path}")

    try:
        # Step 1: Get presigned URL and download PDF
        logger.info("Getting presigned URL for PDF")
        url_query = queries.GET_PDF_FILE_QUERY
        url_rows = run_query(
            url_query, {"stage_name": stage_name, "relative_path": relative_path}
        )

        if not url_rows or len(url_rows) == 0:
            logger.error(f"No presigned URL found for relative path: {relative_path}")
            return {
                "bounding_boxes": [],
                "fields_with_bounding_boxes": {},
                "ai_extract_metadata": {},
            }

        presigned_url = url_rows[0].get("PRESIGNED_URL")

        # Download PDF to temporary file
        logger.info("Downloading PDF file")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            response = requests.get(presigned_url)
            response.raise_for_status()
            tmp_file.write(response.content)

        # Step 2: Get PDF page dimensions for proper coordinate normalization
        logger.info("Getting PDF page dimensions")
        doc = fitz.open(tmp_path)
        page_dimensions = {}
        for page_num in range(len(doc)):
            page = doc[page_num]
            rect = page.rect
            page_dimensions[page_num] = {"width": rect.width, "height": rect.height}
        doc.close()

        # Step 3: Convert PDF to images
        logger.info("Converting PDF pages to images")
        images = convert_from_path(tmp_path, dpi=300)  # High DPI for better OCR

        # Step 4: Extract text with bounding boxes using Tesseract OCR
        logger.info("Extracting text with bounding boxes using Tesseract OCR")
        words_with_bboxes = []
        full_text_parts = []

        for page_num, image in enumerate(images):
            # Run Tesseract OCR with detailed data
            ocr_data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )

            # Get image dimensions and PDF page dimensions
            img_width, img_height = image.size
            pdf_width = page_dimensions[page_num]["width"]
            pdf_height = page_dimensions[page_num]["height"]

            # Calculate scale factors to convert from image pixels to PDF points
            scale_x = pdf_width / img_width
            scale_y = pdf_height / img_height

            # Extract words with bounding boxes
            for i in range(len(ocr_data["text"])):
                word_text = ocr_data["text"][i].strip()
                conf = int(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0

                # Skip empty words or low confidence
                if word_text and conf > 30:  # Confidence threshold
                    x = ocr_data["left"][i]
                    y = ocr_data["top"][i]
                    w = ocr_data["width"][i]
                    h = ocr_data["height"][i]

                    # Convert from image coordinates to PDF points
                    # CRITICAL: Use top-left origin (no Y-flip) for OCR coordinates
                    # React-pdf-highlighter expects top-left origin for image-based PDFs
                    pdf_x0 = x * scale_x
                    pdf_x1 = (x + w) * scale_x
                    pdf_y0 = y * scale_y
                    pdf_y1 = (y + h) * scale_y

                    words_with_bboxes.append(
                        {
                            "bbox": {
                                "x0": float(pdf_x0),
                                "x1": float(pdf_x1),
                                "y0": float(pdf_y0),
                                "y1": float(pdf_y1),
                            },
                            "page": page_num + 1,  # 1-indexed page numbers
                            "text": word_text,
                            "type": "Word",
                        }
                    )

                    full_text_parts.append(word_text)

        logger.info(f"Extracted {len(words_with_bboxes)} words via OCR")

        # Clean up temporary file
        os.unlink(tmp_path)

        # Improve OCR text quality: sort reading order and dehyphenate
        words_sorted = sort_reading_order(words_with_bboxes)
        full_text = dehyphenate_text(words_sorted)

        # Normalize text for better LLM extraction (fix OCR artifacts)
        full_text = normalize_text(full_text)
        logger.info(
            f"OCR text processed: sorted, dehyphenated, normalized ({len(full_text)} chars)"
        )

        # Step 4: Use Cortex LLM to extract fields from full text
        logger.info("Using Cortex LLM to extract fields")
        # Use extraction-optimized settings: low temp, limited tokens, JSON enforced
        model = CortexModel(temperature=0.0, max_tokens=1500)

        # Create extraction prompt
        extraction_prompt = TEXT_EXTRACT_PROMPT.format(invoice_text=full_text)

        msg = [
            SystemMessage(content="You are an invoice data extraction assistant."),
            HumanMessage(content=extraction_prompt),
        ]

        # Define the output structure for field extraction
        # Cortex requires simple string types without Optional
        class TextExtractOutput(BaseModel):
            """Output structure for text extraction"""

            model_config = {"extra": "forbid"}

            classification: str
            invoice_number: str
            snowflake_entity: str
            vendor_name: str
            invoice_date: str
            total_amount: str
            tax_amount: str
            currency: str
            purchase_order_number: str
            payment_terms: str
            due_date: str
            memo_description: str

        response = model.model.with_structured_output(TextExtractOutput).invoke(msg)
        extracted_fields = response.model_dump()

        logger.info(f"Extracted fields: {extracted_fields}")

        # Apply regex validation
        extracted_fields = validate_with_regex(extracted_fields)

        # Additional semantic validation
        if extracted_fields.get("snowflake_entity"):
            entity = extracted_fields["snowflake_entity"].lower()
            if "snowflake" not in entity and entity not in ["bonbono", "wpp"]:
                logger.warning(
                    f"Snowflake entity may be incorrect: {extracted_fields['snowflake_entity']}"
                )

        if extracted_fields.get("vendor_name"):
            vendor = extracted_fields["vendor_name"].lower()
            if "snowflake" in vendor:
                logger.warning(
                    f"Vendor contains 'Snowflake', may be swapped with customer: {extracted_fields['vendor_name']}"
                )

        # Step 5: Find bounding boxes for each extracted field
        logger.info("Mapping extracted fields to bounding boxes")
        fields_with_bounding_boxes = {}

        for field_name, field_value in extracted_fields.items():
            if field_value and field_value != "null":
                logger.info(
                    f"Finding bounding boxes for field '{field_name}': {field_value}"
                )
                bbox_data = find_text_bboxes(
                    field_value, words_with_bboxes, model, full_text
                )

                if bbox_data:
                    fields_with_bounding_boxes[field_name] = bbox_data
                    logger.info(
                        f"Found bounding box for field '{field_name}' on page {bbox_data['page']}"
                    )
                else:
                    logger.warning(
                        f"No bounding box found for field '{field_name}': {field_value}"
                    )

        # Build ai_extract_metadata from extracted fields for backward compatibility with downstream nodes
        ai_extract_metadata = {}
        for field_name, bbox_data in fields_with_bounding_boxes.items():
            ai_extract_metadata[field_name] = bbox_data.get("value")

        # Return bounding boxes, fields with bounding boxes, and ai_extract_metadata
        return {
            "bounding_boxes": words_with_bboxes,
            "fields_with_bounding_boxes": fields_with_bounding_boxes,
            "ai_extract_metadata": ai_extract_metadata,
        }

    except Exception as e:
        logger.error(f"Error running OCR extractor: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "bounding_boxes": [],
            "fields_with_bounding_boxes": {},
            "ai_extract_metadata": {},
        }


def run_hybrid_extractor(state: State) -> State:
    """
    Extract text with bounding boxes using both PyMuPDF and Tesseract OCR for hybrid PDFs.

    This function:
    1. Uses PyMuPDF to extract text from pages with native text
    2. Uses Tesseract OCR for pages with scanned images
    3. Combines all extracted text and bounding boxes
    4. Uses Cortex LLM to extract invoice fields
    5. Maps extracted fields to their bounding boxes

    Extracted metadata with bounding boxes passed to state.
    """

    stage_name = state["stage_name"]
    if not stage_name.startswith("@"):
        stage_name = "@" + stage_name
    relative_path = state["relative_path"]

    logger.info(f"Running hybrid extractor for relative path: {relative_path}")

    try:
        # Step 1: Get presigned URL and download PDF
        logger.info("Getting presigned URL for PDF")
        url_query = queries.GET_PDF_FILE_QUERY
        url_rows = run_query(
            url_query, {"stage_name": stage_name, "relative_path": relative_path}
        )

        if not url_rows or len(url_rows) == 0:
            logger.error(f"No presigned URL found for relative path: {relative_path}")
            return {
                "bounding_boxes": [],
                "fields_with_bounding_boxes": {},
                "ai_extract_metadata": {},
            }

        presigned_url = url_rows[0].get("PRESIGNED_URL")

        # Download PDF to temporary file
        logger.info("Downloading PDF file")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            response = requests.get(presigned_url)
            response.raise_for_status()
            tmp_file.write(response.content)

        # Step 2: Analyze which pages need OCR vs text extraction
        logger.info("Analyzing pages to determine extraction method per page")
        doc = fitz.open(tmp_path)
        pages_needing_ocr = []
        pages_with_text = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            words = page.get_text("words")
            word_count = len(words)

            if word_count < 20:  # Page has little/no extractable text, needs OCR
                pages_needing_ocr.append(page_num)
            else:
                pages_with_text.append(page_num)

        logger.info(
            f"Pages with text extraction: {len(pages_with_text)}, Pages needing OCR: {len(pages_needing_ocr)}"
        )

        # Step 3: Extract text from pages with native text using PyMuPDF
        words_with_bboxes = []
        full_text_parts = []

        for page_num in pages_with_text:
            page = doc[page_num]
            words = page.get_text("words")

            for word_data in words:
                x0, y0, x1, y1, word_text, block_no, line_no, word_no = word_data

                words_with_bboxes.append(
                    {
                        "bbox": {
                            "x0": float(x0),
                            "x1": float(x1),
                            "y0": float(y0),
                            "y1": float(y1),
                        },
                        "page": page_num + 1,  # 1-indexed page numbers
                        "text": word_text,
                        "type": "Word",
                    }
                )

                full_text_parts.append(word_text)

        doc.close()
        logger.info(f"Extracted {len(words_with_bboxes)} words via text extraction")

        # Step 4: Extract text from scanned pages using OCR
        if pages_needing_ocr:
            logger.info(f"Converting {len(pages_needing_ocr)} pages to images for OCR")

            # Get page dimensions for coordinate normalization
            doc_for_dims = fitz.open(tmp_path)
            page_dimensions = {}
            for page_num in pages_needing_ocr:
                page = doc_for_dims[page_num]
                rect = page.rect
                page_dimensions[page_num] = {"width": rect.width, "height": rect.height}
            doc_for_dims.close()

            # Convert only the pages that need OCR
            images = convert_from_path(
                tmp_path,
                dpi=300,
                first_page=min(pages_needing_ocr) + 1,
                last_page=max(pages_needing_ocr) + 1,
            )

            for idx, page_num in enumerate(pages_needing_ocr):
                image = images[idx] if idx < len(images) else None
                if image is None:
                    continue

                logger.info(f"Running OCR on page {page_num + 1}")
                ocr_data = pytesseract.image_to_data(
                    image, output_type=pytesseract.Output.DICT
                )

                # Get dimensions for this page
                img_width, img_height = image.size
                pdf_width = page_dimensions[page_num]["width"]
                pdf_height = page_dimensions[page_num]["height"]

                # Calculate scale factors to match PDF coordinate system
                scale_x = pdf_width / img_width
                scale_y = pdf_height / img_height

                # Extract words with bounding boxes
                for i in range(len(ocr_data["text"])):
                    word_text = ocr_data["text"][i].strip()
                    conf = (
                        int(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0
                    )

                    if word_text and conf > 30:
                        x = ocr_data["left"][i]
                        y = ocr_data["top"][i]
                        w = ocr_data["width"][i]
                        h = ocr_data["height"][i]

                        # Apply scaling to convert from image pixels to PDF points
                        # DO NOT flip Y-axis - keep same orientation as image for now (testing)
                        pdf_x0 = x * scale_x
                        pdf_x1 = (x + w) * scale_x
                        pdf_y0 = y * scale_y  # No flip
                        pdf_y1 = (y + h) * scale_y  # No flip

                        words_with_bboxes.append(
                            {
                                "bbox": {
                                    "x0": float(pdf_x0),
                                    "x1": float(pdf_x1),
                                    "y0": float(pdf_y0),
                                    "y1": float(pdf_y1),
                                },
                                "page": page_num + 1,  # 1-indexed page numbers
                                "text": word_text,
                                "type": "Word",
                            }
                        )

                        full_text_parts.append(word_text)

            logger.info(f"Total words after OCR: {len(words_with_bboxes)}")

        # Clean up temporary file
        os.unlink(tmp_path)

        # Improve hybrid text quality: sort reading order and dehyphenate
        words_sorted = sort_reading_order(words_with_bboxes)
        full_text = dehyphenate_text(words_sorted)

        # Normalize text for better LLM extraction
        full_text = normalize_text(full_text)
        logger.info(
            f"Hybrid text processed: sorted, dehyphenated, normalized ({len(full_text)} chars)"
        )

        # Step 5: Use Cortex LLM to extract fields from combined text
        logger.info("Using Cortex LLM to extract fields")
        model = CortexModel()

        # Create extraction prompt
        extraction_prompt = TEXT_EXTRACT_PROMPT.format(invoice_text=full_text)

        msg = [
            SystemMessage(content="You are an invoice data extraction assistant."),
            HumanMessage(content=extraction_prompt),
        ]

        # Define the output structure for field extraction
        # Cortex requires simple string types without Optional
        class TextExtractOutput(BaseModel):
            """Output structure for text extraction"""

            model_config = {"extra": "forbid"}

            classification: str
            invoice_number: str
            snowflake_entity: str
            vendor_name: str
            invoice_date: str
            total_amount: str
            tax_amount: str
            currency: str
            purchase_order_number: str
            payment_terms: str
            due_date: str
            memo_description: str

        response = model.model.with_structured_output(TextExtractOutput).invoke(msg)
        extracted_fields = response.model_dump()

        logger.info(f"Extracted fields: {extracted_fields}")

        # Apply regex validation
        extracted_fields = validate_with_regex(extracted_fields)

        # Additional semantic validation
        if extracted_fields.get("snowflake_entity"):
            entity = extracted_fields["snowflake_entity"].lower()
            if "snowflake" not in entity and entity not in ["bonbono", "wpp"]:
                logger.warning(
                    f"Snowflake entity may be incorrect: {extracted_fields['snowflake_entity']}"
                )

        if extracted_fields.get("vendor_name"):
            vendor = extracted_fields["vendor_name"].lower()
            if "snowflake" in vendor:
                logger.warning(
                    f"Vendor contains 'Snowflake', may be swapped with customer: {extracted_fields['vendor_name']}"
                )

        # Step 6: Find bounding boxes for each extracted field with evidence validation
        logger.info("Mapping extracted fields to bounding boxes")
        fields_with_bounding_boxes = {}

        for field_name, field_value in extracted_fields.items():
            if field_value and field_value != "null":
                logger.info(
                    f"Finding bounding boxes for field '{field_name}': {field_value}"
                )
                bbox_data = find_text_bboxes(
                    field_value, words_with_bboxes, model, full_text
                )

                if bbox_data:
                    # Validate evidence: check if extracted value appears in actual PDF text
                    evidence = bbox_data.get("evidence", "")
                    value_normalized = (
                        field_value.lower()
                        .replace(" ", "")
                        .replace(",", "")
                        .replace(".", "")
                    )
                    evidence_normalized = (
                        evidence.lower()
                        .replace(" ", "")
                        .replace(",", "")
                        .replace(".", "")
                    )

                    if (
                        value_normalized
                        and evidence_normalized
                        and value_normalized not in evidence_normalized
                    ):
                        logger.warning(
                            f"Evidence mismatch for '{field_name}': extracted='{field_value}', evidence='{evidence}'"
                        )
                        bbox_data["confidence"] = max(
                            0, bbox_data.get("confidence", 100) - 20
                        )  # Reduce confidence

                    fields_with_bounding_boxes[field_name] = bbox_data
                    conf = bbox_data.get("confidence", 100)
                    logger.info(
                        f"Found bounding box for '{field_name}' on page {bbox_data['page']} (confidence: {conf})"
                    )
                else:
                    logger.warning(
                        f"No bounding box found for field '{field_name}': {field_value}"
                    )

        # Build ai_extract_metadata from ALL extracted fields (not just those with bboxes)
        # This ensures fields are saved to database even if we couldn't find their bounding boxes
        ai_extract_metadata = {}
        for field_name, field_value in extracted_fields.items():
            if field_value and field_value != "null":
                ai_extract_metadata[field_name] = field_value

        # Return bounding boxes, fields with bounding boxes, and ai_extract_metadata
        return {
            "bounding_boxes": words_with_bboxes,
            "fields_with_bounding_boxes": fields_with_bounding_boxes,
            "ai_extract_metadata": ai_extract_metadata,
        }

    except Exception as e:
        logger.error(f"Error running hybrid extractor: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "bounding_boxes": [],
            "fields_with_bounding_boxes": {},
            "ai_extract_metadata": {},
        }


def detect_extraction_method(state: State) -> State:
    """
    Detect whether PDF should use text extraction, OCR, or hybrid approach.
    Uses PyMuPDF to analyze PDF structure and text content.

    Classification logic:
    - Text-based: PDF has extractable text on most pages (>80% of pages have >50 words)
    - Scanned: PDF has little/no extractable text (<20% of pages have >10 words)
    - Hybrid: PDF has mix of text and scanned pages
    """
    stage_name = state["stage_name"]
    if not stage_name.startswith("@"):
        stage_name = "@" + stage_name
    relative_path = state["relative_path"]

    logger.info(f"Detecting extraction method for: {relative_path}")

    try:
        # Get presigned URL and download PDF
        url_query = queries.GET_PDF_FILE_QUERY
        url_rows = run_query(
            url_query, {"stage_name": stage_name, "relative_path": relative_path}
        )

        if not url_rows or len(url_rows) == 0:
            logger.warning(f"Cannot get PDF, defaulting to text extraction")
            return {"extraction_method": "text"}

        presigned_url = url_rows[0].get("PRESIGNED_URL")

        # Download PDF to temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            response = requests.get(presigned_url)
            response.raise_for_status()
            tmp_file.write(response.content)

        # Analyze PDF structure using PyMuPDF
        doc = fitz.open(tmp_path)
        total_pages = len(doc)
        pages_with_text = 0
        pages_with_little_text = 0
        total_words = 0

        for page_num in range(total_pages):
            page = doc[page_num]
            words = page.get_text("words")
            word_count = len(words)
            total_words += word_count

            if word_count > 50:  # Page has substantial text
                pages_with_text += 1
            elif word_count > 10:  # Page has some text
                pages_with_little_text += 1

        doc.close()
        os.unlink(tmp_path)

        # Calculate percentages
        text_page_ratio = pages_with_text / total_pages if total_pages > 0 else 0
        some_text_ratio = (
            (pages_with_text + pages_with_little_text) / total_pages
            if total_pages > 0
            else 0
        )
        avg_words_per_page = total_words / total_pages if total_pages > 0 else 0

        logger.info(
            f"PDF Analysis: {total_pages} pages, {avg_words_per_page:.1f} avg words/page"
        )
        logger.info(
            f"Pages with substantial text: {pages_with_text}/{total_pages} ({text_page_ratio:.1%})"
        )
        logger.info(
            f"Pages with some text: {pages_with_text + pages_with_little_text}/{total_pages} ({some_text_ratio:.1%})"
        )

        # Determine extraction method based on analysis
        if text_page_ratio >= 0.8:  # 80%+ pages have substantial text
            extraction_method = "text"
            logger.info(f"Classification: TEXT - Most pages have extractable text")
        elif some_text_ratio < 0.2:  # Less than 20% pages have any meaningful text
            extraction_method = "ocr"
            logger.info(f"Classification: OCR - PDF appears to be scanned")
        else:  # Mixed content
            extraction_method = "hybrid"
            logger.info(
                f"Classification: HYBRID - PDF has mix of text and scanned pages"
            )

        return {"extraction_method": extraction_method}

    except Exception as e:
        logger.error(f"Error detecting extraction method: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Default to text extraction on error
        return {"extraction_method": "text"}


def extraction_method_router(
    state: State,
) -> Literal["run_text_extract", "run_ocr_extract", "run_hybrid_extract"]:
    """
    Route to appropriate extraction method based on PDF type.

    Returns:
        "run_text_extract" for text-based PDFs
        "run_ocr_extract" for scanned PDFs
        "run_hybrid_extract" for hybrid PDFs
    """
    extraction_method = state.get("extraction_method", "text")

    if extraction_method == "ocr":
        return "run_ocr_extract"
    elif extraction_method == "hybrid":
        return "run_hybrid_extract"
    else:
        return "run_text_extract"


def record_to_table(state: State):
    """
    Record AI extract and invoice metadata into Snowflake target_table in state.
    """

    if state.get(
        "use_existing_ai_extract", False
    ):  # # LangGraph Studio doesn't default a value for use_existing_ai_extract
        return None

    invoice_id = state["invoice_id"]
    logger.info(f"Recording AI extract metadata for invoice_id: {invoice_id}")

    ai_extract_metadata = state["ai_extract_metadata"]
    bounding_boxes = state.get("bounding_boxes", [])
    fields_with_bounding_boxes = state.get("fields_with_bounding_boxes", {})
    target_table = state["target_table"]

    try:
        if ai_extract_metadata:
            # Clean numeric fields by removing commas and other non-numeric characters
            cleaned_metadata = ai_extract_metadata.copy()
            if "total_amount" in cleaned_metadata and cleaned_metadata["total_amount"]:
                original = cleaned_metadata["total_amount"]
                cleaned_metadata["total_amount"] = (
                    cleaned_metadata["total_amount"].replace(",", "").replace(" ", "")
                )
                logger.info(
                    f"Cleaned total_amount: {original} → {cleaned_metadata['total_amount']}"
                )
            if "tax_amount" in cleaned_metadata and cleaned_metadata["tax_amount"]:
                original = cleaned_metadata["tax_amount"]
                cleaned_metadata["tax_amount"] = (
                    cleaned_metadata["tax_amount"].replace(",", "").replace(" ", "")
                )
                logger.info(
                    f"Cleaned tax_amount: {original} → {cleaned_metadata['tax_amount']}"
                )

            # Normalize date formats to YYYY-MM-DD (Snowflake compatible)
            # This serves as a fallback in case LLM doesn't normalize the dates
            for date_field in ["invoice_date", "due_date"]:
                if date_field in cleaned_metadata and cleaned_metadata[date_field]:
                    date_val = cleaned_metadata[date_field]
                    normalized_date = normalize_date_to_snowflake_format(date_val)

                    if normalized_date:
                        if normalized_date != date_val:
                            logger.info(
                                f"Post-processing normalized {date_field}: {date_val} → {normalized_date}"
                            )
                        cleaned_metadata[date_field] = normalized_date
                    else:
                        logger.warning(f"Failed to normalize {date_field}: {date_val}")
                        # Keep original value if normalization fails
                        # Snowflake's PARSE_DATE function might still handle it

            json_string = json.dumps(cleaned_metadata)
            bounding_boxes_string = json.dumps(bounding_boxes)
            fields_with_bounding_boxes_string = json.dumps(fields_with_bounding_boxes)

            # Use string formatting for table name (identifier) but keep parameterized queries for data values
            query = queries.RECORD_METADATA_QUERY
            rows = run_query(
                query,
                {
                    "json_string": json_string,
                    "bounding_boxes_string": bounding_boxes_string,
                    "fields_with_bounding_boxes_string": fields_with_bounding_boxes_string,
                    "invoice_id": invoice_id,
                    "target_table": target_table,
                },
            )
            logger.info(
                f"Number of rows inserted with AI Extract: {rows[0].get('number of rows inserted')}"
            )
            logger.info(
                f"Saved {len(bounding_boxes)} bounding boxes and {len(fields_with_bounding_boxes)} field mappings"
            )
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
            logger.warning(
                f"No purchase order header metadata found for purchase_order_number: {purchase_order_number}"
            )
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
    logger.info(
        f"Getting purchase order line item metadata for invoice_id: {invoice_id}"
    )

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
            logger.warning(
                f"No purchase order line item metadata found for purchase_order_number: {purchase_order_number}"
            )
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
            HumanMessage(
                content=HUMAN_MESSAGE_PROMPT.format(
                    ai_extract_metadata=ai_extract_metadata,
                    purchase_order_header_metadata=purchase_order_header_metadata,
                    purchase_order_line_item_metadata=purchase_order_line_item_metadata,
                )
            ),
        ]
        response = model.model.with_structured_output(AI_Decision_Output).invoke(msg)
        logger.info(f"Model response received: {response.ai_decision}")

        return {
            "ai_decision": response.ai_decision,
            "ai_reasoning": response.ai_reasoning,
            "ai_extract_metadata": response.ai_extract_metadata.model_dump(),
        }
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
        rows = run_query(
            query,
            {
                "ai_decision": ai_decision,
                "ai_reasoning": ai_reasoning,
                "invoice_id": invoice_id,
                "target_table": target_table,
            },
        )
        logger.info(
            f"Number of rows updated with AI Decision: {rows[0].get('number of rows updated')}"
        )
        return None
    except Exception as e:
        logger.error(f"Error recording AI decision: {str(e)}")
