"""
Multi-source merging logic for combining PyMuPDF and OCR results.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def boxes_overlap(box1: dict, box2: dict, threshold: float) -> bool:
    """
    Check if two bounding boxes overlap significantly using IOU.

    Args:
        box1: First bounding box dict with x0, y0, x1, y1
        box2: Second bounding box dict with x0, y0, x1, y1
        threshold: Minimum overlap ratio to consider as overlapping

    Returns:
        True if boxes overlap above threshold
    """
    x_left = max(box1.get("x0", 0), box2.get("x0", 0))
    y_top = max(box1.get("y0", 0), box2.get("y0", 0))
    x_right = min(box1.get("x1", 0), box2.get("x1", 0))
    y_bottom = min(box1.get("y1", 0), box2.get("y1", 0))

    if x_right < x_left or y_bottom < y_top:
        return False

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = (box1.get("x1", 0) - box1.get("x0", 0)) * (box1.get("y1", 0) - box1.get("y0", 0))
    area2 = (box2.get("x1", 0) - box2.get("x0", 0)) * (box2.get("y1", 0) - box2.get("y0", 0))

    min_area = min(area1, area2)
    if min_area <= 0:
        return False

    return (intersection / min_area) > threshold


def merge_ocr_results(
    pymupdf: list[dict[str, Any]],
    ocr_300: list[dict[str, Any]],
    ocr_600: list[dict[str, Any]],
    overlap_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Merge results from PyMuPDF and OCR at different DPIs.

    Priority: PyMuPDF > OCR 600 DPI (by confidence) > OCR 300 DPI

    Args:
        pymupdf: Words/lines from PyMuPDF extraction
        ocr_300: Words/lines from OCR at 300 DPI
        ocr_600: Words/lines from OCR at 600 DPI
        overlap_threshold: IOU threshold for considering items as overlapping

    Returns:
        Merged list of words/lines
    """
    # Start with PyMuPDF
    merged = list(pymupdf) if pymupdf else []

    # Merge OCR 300 and 600, preferring higher confidence
    ocr_merged = []
    used_600 = set()

    for idx_300, word_300 in enumerate(ocr_300 or []):
        best_match = None
        for idx_600, word_600 in enumerate(ocr_600 or []):
            if idx_600 in used_600:
                continue
            if word_300.get("page") == word_600.get("page"):
                if boxes_overlap(word_300.get("bbox", {}), word_600.get("bbox", {}), overlap_threshold):
                    best_match = idx_600
                    break

        if best_match is not None:
            word_600 = ocr_600[best_match]
            if word_600.get("confidence", 0) > word_300.get("confidence", 0):
                ocr_merged.append(word_600)
            else:
                ocr_merged.append(word_300)
            used_600.add(best_match)
        else:
            ocr_merged.append(word_300)

    # Add remaining 600 DPI words
    for idx_600, word_600 in enumerate(ocr_600 or []):
        if idx_600 not in used_600:
            ocr_merged.append(word_600)

    # Add OCR words that don't overlap with PyMuPDF
    for ocr_word in ocr_merged:
        has_overlap = False
        for py_word in merged:
            if py_word.get("page") == ocr_word.get("page"):
                if boxes_overlap(py_word.get("bbox", {}), ocr_word.get("bbox", {}), overlap_threshold):
                    has_overlap = True
                    break

        if not has_overlap:
            merged.append(ocr_word)

    # Sort by page, then Y, then X
    merged.sort(key=lambda w: (
        w.get("page", 0),
        w.get("bbox", {}).get("y0", 0),
        w.get("bbox", {}).get("x0", 0),
    ))

    return merged


def merge_two_sources(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
    overlap_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Merge two extraction sources, preferring the primary source.

    Args:
        primary: Primary source (e.g., PyMuPDF)
        secondary: Secondary source (e.g., OCR)
        overlap_threshold: IOU threshold for overlap detection

    Returns:
        Merged list
    """
    if not primary:
        return secondary.copy() if secondary else []

    if not secondary:
        return primary.copy()

    merged = list(primary)

    # Add secondary items that don't overlap with primary
    for sec_item in secondary:
        has_overlap = False
        for pri_item in primary:
            if pri_item.get("page") == sec_item.get("page"):
                if boxes_overlap(pri_item.get("bbox", {}), sec_item.get("bbox", {}), overlap_threshold):
                    has_overlap = True
                    break

        if not has_overlap:
            merged.append(sec_item)

    # Sort by page, then Y, then X
    merged.sort(key=lambda w: (
        w.get("page", 0),
        w.get("bbox", {}).get("y0", 0),
        w.get("bbox", {}).get("x0", 0),
    ))

    return merged
