"""
Main document parsing API.
"""

import logging
from pathlib import Path
from itertools import groupby
from typing import Any

from .pdf import extract_text_and_lines_with_bboxes
from .ocr import run_tesseract_ocr
from .merge import merge_ocr_results
from .text import build_full_text
from .schemas import (
    DocumentContent,
    Word,
    Line,
    Block,
    BoundingBox,
    PageDimensions,
)

logger = logging.getLogger(__name__)


def aggregate_blocks(words: list[Word]) -> list[Block]:
    """
    Aggregate words into blocks based on page and block_no.

    Args:
        words: List of Word objects

    Returns:
        List of Block objects with combined bounding boxes
    """
    # Sort words by page, block_no, y0, x0 for proper grouping and reading order
    sorted_words = sorted(
        words,
        key=lambda w: (
            w.page,
            w.block_no if w.block_no is not None else float('inf'),
            w.bbox.y0,
            w.bbox.x0,
        ),
    )

    blocks = []
    for (page, block_no), group in groupby(
        sorted_words, key=lambda w: (w.page, w.block_no)
    ):
        group_words = list(group)

        # Compute combined bounding box
        combined_bbox = BoundingBox(
            x0=min(w.bbox.x0 for w in group_words),
            y0=min(w.bbox.y0 for w in group_words),
            x1=max(w.bbox.x1 for w in group_words),
            y1=max(w.bbox.y1 for w in group_words),
        )

        # Concatenate text in reading order (already sorted)
        text = " ".join(w.text for w in group_words)

        blocks.append(
            Block(
                text=text,
                bbox=combined_bbox,
                page=page,
                block_no=block_no,
                word_count=len(group_words),
            )
        )

    return blocks


def parse_document(
    pdf_path: str | Path,
    dpi_levels: list[int] | None = None,
    skip_ocr: bool = False,
) -> DocumentContent:
    """
    Extract all content from a PDF document with bounding boxes.

    This function combines PyMuPDF native text extraction with Tesseract OCR
    at multiple DPI levels to maximize text recovery from both digital and
    scanned documents.

    Args:
        pdf_path: Path to the PDF file
        dpi_levels: List of DPI values for OCR (default: [300, 600])
        skip_ocr: If True, skip OCR and only use PyMuPDF extraction

    Returns:
        DocumentContent with words, lines, full_text, and page_dimensions
    """
    pdf_path = str(pdf_path)
    dpi_levels = dpi_levels or [300, 600]

    logger.info(f"Parsing document: {pdf_path}")

    # Step 1: PyMuPDF native extraction
    logger.info("Extracting text with PyMuPDF")
    pymupdf_result = extract_text_and_lines_with_bboxes(pdf_path)
    pymupdf_words = pymupdf_result["words"]
    pymupdf_lines = pymupdf_result["lines"]
    page_dimensions = pymupdf_result["page_dimensions"]
    page_count = pymupdf_result["page_count"]

    logger.info(f"PyMuPDF extracted {len(pymupdf_words)} words, {len(pymupdf_lines)} lines")

    if skip_ocr:
        # Use PyMuPDF results only
        merged_words = pymupdf_words
        merged_lines = pymupdf_lines
    else:
        # Step 2: Run OCR at each DPI level
        ocr_words_by_dpi = {}
        ocr_lines_by_dpi = {}

        for dpi in dpi_levels:
            logger.info(f"Running OCR at {dpi} DPI")
            words, lines = run_tesseract_ocr(pdf_path, page_dimensions, dpi=dpi)
            ocr_words_by_dpi[dpi] = words
            ocr_lines_by_dpi[dpi] = lines
            logger.info(f"OCR at {dpi} DPI: {len(words)} words, {len(lines)} lines")

        # Step 3: Merge results
        logger.info("Merging extraction results")

        # Get OCR results (default to empty lists if DPI not in list)
        ocr_words_300 = ocr_words_by_dpi.get(300, [])
        ocr_words_600 = ocr_words_by_dpi.get(600, [])
        ocr_lines_300 = ocr_lines_by_dpi.get(300, [])
        ocr_lines_600 = ocr_lines_by_dpi.get(600, [])

        # Handle case where only one DPI level is provided
        if len(dpi_levels) == 1:
            dpi = dpi_levels[0]
            ocr_words_300 = ocr_words_by_dpi.get(dpi, [])
            ocr_words_600 = []
            ocr_lines_300 = ocr_lines_by_dpi.get(dpi, [])
            ocr_lines_600 = []

        merged_words = merge_ocr_results(pymupdf_words, ocr_words_300, ocr_words_600)
        merged_lines = merge_ocr_results(pymupdf_lines, ocr_lines_300, ocr_lines_600)

    logger.info(f"Merged: {len(merged_words)} words, {len(merged_lines)} lines")

    # Step 4: Build full text
    full_text = build_full_text(merged_words)

    # Step 5: Convert to Pydantic models
    words = [
        Word(
            text=w["text"],
            bbox=BoundingBox(**w["bbox"]),
            page=w["page"],
            source=w["source"],
            confidence=w.get("confidence", 0),
            block_no=w.get("block_no"),
            line_no=w.get("line_no"),
        )
        for w in merged_words
    ]

    lines = [
        Line(
            text=ln["text"],
            bbox=BoundingBox(**ln["bbox"]),
            page=ln["page"],
            source=ln["source"],
            block_no=ln.get("block_no"),
            line_no=ln.get("line_no"),
        )
        for ln in merged_lines
    ]

    page_dims = {
        k: PageDimensions(width=v["width"], height=v["height"])
        for k, v in page_dimensions.items()
    }

    # Step 6: Aggregate words into blocks
    blocks = aggregate_blocks(words)

    logger.info(f"Parsing complete: {page_count} pages, {len(words)} words, {len(blocks)} blocks")

    return DocumentContent(
        words=words,
        lines=lines,
        blocks=blocks,
        full_text=full_text,
        page_count=page_count,
        page_dimensions=page_dims,
    )


def parse_document_dict(
    pdf_path: str | Path,
    dpi_levels: list[int] | None = None,
    skip_ocr: bool = False,
) -> dict[str, Any]:
    """
    Parse document and return as dictionary (for JSON serialization).

    Args:
        pdf_path: Path to the PDF file
        dpi_levels: List of DPI values for OCR
        skip_ocr: If True, skip OCR

    Returns:
        Dictionary representation of DocumentContent
    """
    result = parse_document(pdf_path, dpi_levels, skip_ocr)
    return result.model_dump()
