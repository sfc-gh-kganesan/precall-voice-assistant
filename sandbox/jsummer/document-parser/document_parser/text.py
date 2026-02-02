"""
Text reconstruction utilities for building readable text from bounding boxes.
"""

import re
from typing import Any, Optional


def sort_reading_order(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort words in reading order (top-to-bottom, left-to-right).

    Args:
        words: List of word dicts with bbox and page

    Returns:
        Sorted list of words
    """
    return sorted(words, key=lambda w: (
        w.get("page", 0),
        w.get("bbox", {}).get("y0", 0),
        w.get("bbox", {}).get("x0", 0),
    ))


def reconstruct_text_from_words(
    words: list[dict[str, Any]],
    page_num: Optional[int] = None,
) -> str:
    """
    Reconstruct readable text from word bounding boxes.

    Args:
        words: List of word dicts with bbox, page, text
        page_num: Optional page number to filter by (1-indexed)

    Returns:
        Reconstructed text string
    """
    if page_num:
        words = [w for w in words if w.get("page") == page_num]

    if not words:
        return ""

    # Sort by page, Y position, then X position
    sorted_words = sorted(words, key=lambda w: (
        w.get("page", 0),
        w.get("bbox", {}).get("y0", 0),
        w.get("bbox", {}).get("x0", 0)
    ))

    lines = []
    current_line = []
    last_y = None
    y_threshold = 10  # Pixels threshold for same line

    for word in sorted_words:
        bbox = word.get("bbox", {})
        y = bbox.get("y0", 0)
        text = word.get("text", "")

        if last_y is None or abs(y - last_y) < y_threshold:
            current_line.append(text)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [text]

        last_y = y

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)


def reconstruct_layout_from_bboxes(words: list[dict[str, Any]]) -> str:
    """
    Reconstruct text with layout preservation from bounding boxes.

    Groups words into lines based on Y-coordinate, then sorts by X within each line.

    Args:
        words: List of word dicts with bbox and text

    Returns:
        Layout-preserved text string
    """
    if not words:
        return ""

    # Group by Y-coordinate (with tolerance)
    y_tolerance = 5.0
    lines_dict: dict[float, list[dict]] = {}

    for word in words:
        y = word.get("bbox", {}).get("y0", 0)

        # Find matching line
        matched_y = None
        for existing_y in lines_dict:
            if abs(y - existing_y) < y_tolerance:
                matched_y = existing_y
                break

        if matched_y is not None:
            lines_dict[matched_y].append(word)
        else:
            lines_dict[y] = [word]

    # Sort lines by Y and words within lines by X
    result_lines = []
    for y in sorted(lines_dict.keys()):
        line_words = sorted(lines_dict[y], key=lambda w: w.get("bbox", {}).get("x0", 0))
        line_text = " ".join(w.get("text", "") for w in line_words)
        result_lines.append(line_text)

    return "\n".join(result_lines)


def dehyphenate_text(words: list[dict[str, Any]]) -> str:
    """
    Reconstruct text from words, removing hyphens at line breaks.

    Args:
        words: List of word dicts (should be pre-sorted)

    Returns:
        Dehyphenated text string
    """
    if not words:
        return ""

    text_parts = []
    prev_text = ""

    for word in words:
        text = word.get("text", "")

        # Handle hyphenation at line ends
        if prev_text.endswith("-"):
            text_parts[-1] = prev_text[:-1] + text
        else:
            text_parts.append(text)

        prev_text = text

    return " ".join(text_parts)


def normalize_text(text: str) -> str:
    """
    Normalize whitespace and remove extra spaces.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()


def get_page_text(
    words: list[dict[str, Any]],
    page_num: int,
) -> str:
    """
    Get text for a specific page from words.

    Args:
        words: List of word dicts
        page_num: Page number (1-indexed)

    Returns:
        Text for that page
    """
    return reconstruct_text_from_words(words, page_num)


def build_full_text(words: list[dict[str, Any]]) -> str:
    """
    Build full document text from words with proper formatting.

    Args:
        words: List of word dicts

    Returns:
        Full document text
    """
    sorted_words = sort_reading_order(words)
    text = dehyphenate_text(sorted_words)
    return normalize_text(text)
