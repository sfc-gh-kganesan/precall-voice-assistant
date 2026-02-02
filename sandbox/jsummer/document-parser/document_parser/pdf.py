"""
PDF text extraction using PyMuPDF.
"""

import logging
from typing import Any

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_text_and_lines_with_bboxes(pdf_path: str) -> dict[str, Any]:
    """
    Extract text by both words AND lines with bounding boxes from PDF using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing:
        - 'words': List of word dicts with bbox, page, text
        - 'lines': List of line dicts with bbox, page, text
        - 'page_dimensions': Dict mapping page_num to {width, height}
        - 'page_count': Number of pages
    """
    words_with_bboxes = []
    lines_with_bboxes = []
    page_dimensions = {}

    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)

        for page_num, page in enumerate(doc):
            # Get page dimensions
            rect = page.rect
            page_dimensions[page_num] = {"width": rect.width, "height": rect.height}

            # Get the full dict structure which includes blocks -> lines -> spans
            page_dict = page.get_text("dict")

            # Process blocks to extract lines
            for block in page_dict.get("blocks", []):
                # Skip image blocks (type 1)
                if block.get("type", 0) != 0:
                    continue

                block_no = block.get("number", 0)

                for line_idx, line in enumerate(block.get("lines", [])):
                    # Get line bounding box
                    line_bbox = line.get("bbox", (0, 0, 0, 0))
                    x0, y0, x1, y1 = line_bbox

                    # Build line text from spans
                    line_text_parts = []
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if span_text:
                            line_text_parts.append(span_text)

                    line_text = "".join(line_text_parts).strip()

                    if line_text:
                        lines_with_bboxes.append({
                            "bbox": {
                                "x0": float(x0),
                                "x1": float(x1),
                                "y0": float(y0),
                                "y1": float(y1),
                            },
                            "page": page_num + 1,  # 1-indexed page numbers
                            "text": line_text,
                            "source": "pymupdf",
                            "block_no": block_no,
                            "line_no": line_idx,
                            "confidence": 100,
                        })

            # Get words with their bounding boxes
            words = page.get_text("words")

            for word_data in words:
                x0, y0, x1, y1, word_text, block_no, line_no, word_no = word_data

                words_with_bboxes.append({
                    "bbox": {
                        "x0": float(x0),
                        "x1": float(x1),
                        "y0": float(y0),
                        "y1": float(y1),
                    },
                    "page": page_num + 1,
                    "text": word_text,
                    "source": "pymupdf",
                    "block_no": block_no,
                    "line_no": line_no,
                    "confidence": 100,
                })

        doc.close()

        return {
            "words": words_with_bboxes,
            "lines": lines_with_bboxes,
            "page_dimensions": page_dimensions,
            "page_count": page_count,
        }

    except Exception as e:
        logger.error(f"Error extracting text and lines with bboxes: {str(e)}")
        return {"words": [], "lines": [], "page_dimensions": {}, "page_count": 0}
