"""
Helper functions for invoice processing.

This module contains utility functions for text processing, PDF extraction,
bounding box matching, and field validation.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import fitz  # PyMuPDF

from langchain_core.messages import SystemMessage, HumanMessage
from app.model import CortexModel

logger = logging.getLogger(__name__)


def normalize_date_to_snowflake_format(date_string: str) -> Optional[str]:
    """
    Normalize date string to YYYY-MM-DD format for Snowflake compatibility.

    Handles a comprehensive list of date formats commonly found in invoices worldwide:
    - ISO formats: YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD
    - European formats: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
    - US formats: MM/DD/YYYY, MM-DD-YYYY
    - Text formats: "October 14, 2025", "14 Oct 2025", "4 Dec 2025", "Dec 4, 2025"
    - Mixed formats: "14-Oct-2025", "2025-Oct-14"

    Args:
        date_string: Date string in various formats

    Returns:
        Normalized date string in YYYY-MM-DD format, or None if parsing fails
    """
    if not date_string or date_string == "null" or not isinstance(date_string, str):
        return None

    date_string = date_string.strip()

    # If already in correct format, return as-is
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_string):
        try:
            # Validate it's a real date
            datetime.strptime(date_string, "%Y-%m-%d")
            return date_string
        except ValueError:
            pass

    # Define comprehensive date format patterns
    # Order matters: try most specific formats first
    date_formats = [
        # ISO formats
        (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),  # 2025/10/08
        (r"^\d{4}\d{2}\d{2}$", "%Y%m%d"),  # 20251008
        # European formats (DD first)
        (r"^\d{2}\.\d{2}\.\d{4}$", "%d.%m.%Y"),  # 08.10.2025
        (r"^\d{2}-\d{2}-\d{4}$", "%d-%m-%Y"),  # 08-10-2025
        (r"^\d{2}/\d{2}/\d{4}$", "%d/%m/%Y"),  # 08/10/2025 (try European first)
        # Single digit day/month variations
        (r"^\d{1,2}\.\d{1,2}\.\d{4}$", "%d.%m.%Y"),  # 8.10.2025
        (r"^\d{1,2}-\d{1,2}-\d{4}$", "%d-%m-%Y"),  # 8-10-2025
        (r"^\d{1,2}/\d{1,2}/\d{4}$", "%d/%m/%Y"),  # 8/10/2025
        # Year with 2 digits
        (r"^\d{2}\.\d{2}\.\d{2}$", "%d.%m.%y"),  # 08.10.25
        (r"^\d{2}/\d{2}/\d{2}$", "%d/%m/%y"),  # 08/10/25
        (r"^\d{2}-\d{2}-\d{2}$", "%d-%m-%y"),  # 08-10-25
        # Text-based formats with full month names
        (
            r"^\w+ \d{1,2},?\s+\d{4}$",
            "%B %d, %Y",
        ),  # October 14, 2025 or October 14 2025
        (r"^\d{1,2}\s+\w+\s+\d{4}$", "%d %B %Y"),  # 14 October 2025
        # Text-based formats with abbreviated month names
        (r"^\w{3} \d{1,2},?\s+\d{4}$", "%b %d, %Y"),  # Oct 14, 2025 or Oct 14 2025
        (r"^\d{1,2}\s+\w{3}\s+\d{4}$", "%d %b %Y"),  # 14 Oct 2025
        (r"^\d{1,2}-\w{3}-\d{4}$", "%d-%b-%Y"),  # 14-Oct-2025
        (r"^\w{3}-\d{1,2}-\d{4}$", "%b-%d-%Y"),  # Oct-14-2025
        # Reverse formats
        (r"^\d{4}-\w{3}-\d{1,2}$", "%Y-%b-%d"),  # 2025-Oct-14
        (r"^\d{4}\s+\w{3}\s+\d{1,2}$", "%Y %b %d"),  # 2025 Oct 14
        # Edge cases
        (r"^\w{3}\s+\d{4}$", "%b %Y"),  # Oct 2025 (assume day 1)
        (r"^\w+\s+\d{4}$", "%B %Y"),  # October 2025 (assume day 1)
    ]

    normalized_date = None

    # Try each format pattern
    for pattern, date_format in date_formats:
        if re.match(pattern, date_string, re.IGNORECASE):
            try:
                parsed_date = datetime.strptime(date_string, date_format)
                normalized_date = parsed_date.strftime("%Y-%m-%d")
                logger.info(
                    f"Normalized date: {date_string} → {normalized_date} (format: {date_format})"
                )
                return normalized_date
            except ValueError:
                # If European format fails, try US format for ambiguous cases
                if date_format in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]:
                    us_format = (
                        date_format.replace("%d/", "%m/")
                        .replace("%d-", "%m-")
                        .replace("%d.", "%m.")
                    )
                    us_format = (
                        us_format.replace("/%Y", "/%Y")
                        .replace("-%Y", "-%Y")
                        .replace(".%Y", ".%Y")
                    )
                    us_format = us_format.replace("%m/", "%m/").replace("%m.", "%m.")
                    # Convert DD/MM/YYYY to MM/DD/YYYY
                    if "/" in date_format or "-" in date_format or "." in date_format:
                        separator = (
                            "/"
                            if "/" in date_format
                            else ("-" if "-" in date_format else ".")
                        )
                        us_format = f"%m{separator}%d{separator}%Y"
                        try:
                            parsed_date = datetime.strptime(date_string, us_format)
                            normalized_date = parsed_date.strftime("%Y-%m-%d")
                            logger.info(
                                f"Normalized date (US format): {date_string} → {normalized_date}"
                            )
                            return normalized_date
                        except ValueError:
                            pass
                logger.debug(
                    f"Failed to parse date with format {date_format}: {date_string}"
                )
                continue

    # If no format matched, try using dateutil parser as last resort
    try:
        from dateutil import parser as dateutil_parser

        parsed_date = dateutil_parser.parse(date_string, fuzzy=True)
        normalized_date = parsed_date.strftime("%Y-%m-%d")
        logger.info(
            f"Normalized date (dateutil fallback): {date_string} → {normalized_date}"
        )
        return normalized_date
    except (ImportError, ValueError, TypeError) as e:
        logger.warning(f"Failed to normalize date '{date_string}': {str(e)}")
        return None


def normalize_text(text: str) -> str:
    """
    Normalize text for better LLM extraction.
    - Fixes unicode ligatures (ﬁ→fi, ﬂ→fl)
    - Normalizes special characters
    - Preserves formatting important for parsing
    """
    # Unicode ligature mapping
    ligatures = {
        "\ufb01": "fi",  # ﬁ
        "\ufb02": "fl",  # ﬂ
        "\ufb03": "ffi",  # ﬃ
        "\ufb04": "ffl",  # ﬄ
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u00a0": " ",  # non-breaking space
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
    }

    for old, new in ligatures.items():
        text = text.replace(old, new)

    # Remove zero-width characters
    zero_width_chars = ["\u200b", "\u200c", "\u200d", "\ufeff"]
    for char in zero_width_chars:
        text = text.replace(char, "")

    return text


def normalize_number_variations(text: str) -> List[str]:
    """
    Generate variations of a number for better matching.
    Handles different number formats: 1,234.56 vs 1.234,56 vs 1234.56
    Also handles currency symbols: $1,234.56
    """
    variations = [text]

    # Strip currency symbols for better matching
    text_no_currency = (
        text.replace("$", "").replace("€", "").replace("£", "").replace("¥", "").strip()
    )
    if text_no_currency != text:
        variations.append(text_no_currency)

    # Remove all separators
    no_sep = text_no_currency.replace(",", "").replace(".", "").replace(" ", "")
    if no_sep.isdigit() or (no_sep.replace(".", "").isdigit()):
        variations.append(no_sep)
        variations.append(text_no_currency.replace(",", ""))
        variations.append(text_no_currency.replace(".", ""))

        # Add currency symbol versions
        for currency in ["$", "€", "£"]:
            variations.append(f"{currency}{text_no_currency}")
            variations.append(f"{currency}{text_no_currency.replace(',', '')}")

    # EU format (1.234,56) → US format (1234.56)
    if "," in text_no_currency and "." in text_no_currency:
        last_comma = text_no_currency.rindex(",")
        last_period = text_no_currency.rindex(".")
        if last_comma > last_period:  # EU format
            us_format = text_no_currency.replace(".", "").replace(",", ".")
            variations.append(us_format)
            variations.append(f"${us_format}")

    return list(set(variations))


def sort_reading_order(words_with_bboxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort words in natural reading order: top-to-bottom, left-to-right.
    Groups words into lines with Y-tolerance.
    """
    LINE_TOLERANCE = 5  # Group words within 5 points vertically as same line

    sorted_words = sorted(
        words_with_bboxes,
        key=lambda w: (
            w["page"],
            round(w["bbox"]["y1"] / LINE_TOLERANCE)
            * LINE_TOLERANCE,  # Group by line (using y1 top edge)
            w["bbox"]["x0"],  # Then left-to-right
        ),
        reverse=True,
    )  # Reverse because PDF y increases upward (start from top)

    return sorted_words


def dehyphenate_text(words_with_bboxes: List[Dict[str, Any]]) -> str:
    """
    Merge words split across line breaks with hyphens.
    Only merges if words are on adjacent lines and both are alphabetic.
    """
    text_parts = []
    i = 0

    while i < len(words_with_bboxes):
        word = words_with_bboxes[i]
        text = word["text"]

        # Check if word ends with hyphen and next word exists
        if text.endswith("-") and i + 1 < len(words_with_bboxes):
            next_word = words_with_bboxes[i + 1]

            # Check if words are on different lines (y-position change > 5)
            # and both are alphabetic (not numbers or special chars)
            y_diff = abs(word["bbox"]["y1"] - next_word["bbox"]["y1"])
            if y_diff > 5 and text[:-1].isalpha() and next_word["text"].isalpha():
                # Merge without hyphen
                merged = text[:-1] + next_word["text"]
                text_parts.append(merged)
                logger.debug(f"Dehyphenated: {text} + {next_word['text']} → {merged}")
                i += 2
                continue

        text_parts.append(text)
        i += 1

    return " ".join(text_parts)


def validate_with_regex(extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply regex validation to catch formatting errors.
    Returns validated fields with warnings logged.
    """
    # Invoice number patterns
    if extracted_fields.get("invoice_number"):
        inv_num = extracted_fields["invoice_number"]
        if inv_num and not re.match(r"^[A-Z0-9\-#\s]{2,30}$", inv_num, re.IGNORECASE):
            logger.warning(f"Invoice number format unusual: {inv_num}")

    # PO number patterns
    if extracted_fields.get("purchase_order_number"):
        po = extracted_fields["purchase_order_number"]
        if po and not re.match(r"^[A-Z0-9\-\s]{2,30}$", po, re.IGNORECASE):
            logger.warning(f"PO number format unusual: {po}")

    # Amount patterns
    for field in ["total_amount", "tax_amount"]:
        if extracted_fields.get(field):
            amt = extracted_fields[field]
            # Should be number with optional commas/periods/spaces
            if amt and not re.match(r"^[\d,.\s]+$", str(amt)):
                logger.warning(f"{field} format unusual: {amt}")

    # Date patterns
    for field in ["invoice_date", "due_date"]:
        if extracted_fields.get(field):
            date = extracted_fields[field]
            date_patterns = [
                r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
                r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
                r"\d{1,2}\.\d{1,2}\.\d{4}",  # DD.MM.YYYY
                r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}",  # October 14, 2025
                r"\d{1,2}\s+[A-Za-z]+\s+\d{4}",  # 14 Oct 2025
            ]
            if date and not any(re.search(p, str(date)) for p in date_patterns):
                logger.warning(f"{field} format unusual: {date}")

    # Currency patterns
    if extracted_fields.get("currency"):
        curr = extracted_fields["currency"]
        valid_currencies = [
            "USD",
            "EUR",
            "GBP",
            "CAD",
            "COP",
            "CRC",
            "AUD",
            "JPY",
            "CHF",
            "$",
            "€",
            "£",
        ]
        if curr and not any(c in curr.upper() for c in valid_currencies):
            logger.warning(f"Currency unusual: {curr}")

    return extracted_fields


def extract_text_with_bboxes(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text by words with bounding boxes from PDF using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dictionaries containing word text and bounding box coordinates
    """
    words_with_bboxes = []

    try:
        doc = fitz.open(pdf_path)

        for page_num, page in enumerate(doc):
            # Get words with their bounding boxes
            words = page.get_text(
                "words"
            )  # Returns list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)

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

        doc.close()
        return words_with_bboxes

    except Exception as e:
        logger.error(f"Error extracting text with bboxes: {str(e)}")
        return []


def find_text_bboxes(
    extracted_value: str,
    words_with_bboxes: List[Dict[str, Any]],
    model: CortexModel,
    full_text: str,
) -> Optional[Dict[str, Any]]:
    """
    Find bounding box for extracted text using deterministic algorithm and LLM assistance.

    Args:
        extracted_value: The extracted field value to find
        words_with_bboxes: List of words with their bounding boxes
        model: Cortex model for LLM assistance
        full_text: Full text of the document for context

    Returns:
        Dictionary with bbox, confidence, page, value, and evidence, or None if not found
    """
    if not extracted_value or extracted_value == "null" or extracted_value is None:
        return None

    matching_bboxes = []
    was_deterministic = False
    extracted_value_lower = str(extracted_value).lower().strip()

    # Generate number variations for better matching
    search_variations = [extracted_value_lower]
    if any(c.isdigit() for c in extracted_value):
        search_variations.extend(
            [v.lower() for v in normalize_number_variations(extracted_value)]
        )

    # First, try deterministic exact match with all variations
    for search_term in search_variations:
        for i, word_data in enumerate(words_with_bboxes):
            word_text_lower = word_data["text"].lower().strip()

            # Also check without currency symbols
            word_text_no_currency = (
                word_text_lower.replace("$", "")
                .replace("€", "")
                .replace("£", "")
                .replace("¥", "")
                .strip()
            )

            # Check for exact word match (with or without currency)
            if word_text_lower == search_term or word_text_no_currency == search_term:
                matching_bboxes.append(word_data)
                was_deterministic = True
                break

            # Check for multi-word match
            if search_term.startswith(word_text_lower) or search_term.startswith(
                word_text_no_currency
            ):
                # Build potential multi-word match
                combined_text = word_text_lower
                combined_text_no_currency = word_text_no_currency
                temp_bboxes = [word_data]

                for j in range(
                    i + 1, min(i + 20, len(words_with_bboxes))
                ):  # Look ahead up to 20 words
                    next_word = words_with_bboxes[j]
                    next_word_lower = next_word["text"].lower().strip()
                    next_word_no_currency = (
                        next_word_lower.replace("$", "")
                        .replace("€", "")
                        .replace("£", "")
                        .replace("¥", "")
                        .strip()
                    )

                    combined_text += " " + next_word_lower
                    combined_text_no_currency += " " + next_word_no_currency
                    temp_bboxes.append(next_word)

                    # Remove spaces for number matching (handles "$388,401.38" vs "388401.38")
                    combined_no_space = combined_text_no_currency.replace(
                        " ", ""
                    ).replace(",", "")
                    search_no_space = search_term.replace(" ", "").replace(",", "")

                    if (
                        combined_text == search_term
                        or combined_text_no_currency == search_term
                        or combined_no_space == search_no_space
                    ):
                        matching_bboxes.extend(temp_bboxes)
                        was_deterministic = True
                        break
                    elif not (
                        search_term.startswith(combined_text)
                        or search_term.startswith(combined_text_no_currency)
                        or search_no_space.startswith(combined_no_space)
                    ):
                        break

                if matching_bboxes:
                    break

        if matching_bboxes:
            break

    # If no deterministic match found, use LLM to help locate the text
    if not matching_bboxes:
        logger.info(
            f"No deterministic match found for '{extracted_value}', using LLM assistance"
        )

        try:
            # Use the existing model for bbox matching (plain text response)
            llm_prompt = f"""Given the following invoice text, find the exact substring that contains: "{extracted_value}"

Invoice Text:
{full_text}

Respond with the exact substring from the invoice that matches or contains this value. 
If the value is not found, respond with "NOT_FOUND"."""

            msg = [
                SystemMessage(content="You are a text extraction assistant."),
                HumanMessage(content=llm_prompt),
            ]
            response = model.model.invoke(msg)
            llm_match = response.content.strip()

            if llm_match != "NOT_FOUND":
                # Try to find the LLM-suggested text in our words
                llm_match_lower = llm_match.lower().strip()
                for i, word_data in enumerate(words_with_bboxes):
                    if llm_match_lower.startswith(word_data["text"].lower().strip()):
                        combined_text = word_data["text"].lower().strip()
                        temp_bboxes = [word_data]

                        for j in range(i + 1, min(i + 20, len(words_with_bboxes))):
                            next_word = words_with_bboxes[j]
                            combined_text += " " + next_word["text"].lower().strip()
                            temp_bboxes.append(next_word)

                            if (
                                combined_text == llm_match_lower
                                or llm_match_lower in combined_text
                            ):
                                matching_bboxes.extend(temp_bboxes)
                                break

                        if matching_bboxes:
                            break

        except Exception as e:
            logger.error(f"Error using LLM for bbox matching: {str(e)}")

    # If we found matching bboxes, create a combined bounding box
    if matching_bboxes:
        # Calculate the combined bounding box
        x0 = min(bbox["bbox"]["x0"] for bbox in matching_bboxes)
        y0 = min(bbox["bbox"]["y0"] for bbox in matching_bboxes)
        x1 = max(bbox["bbox"]["x1"] for bbox in matching_bboxes)
        y1 = max(bbox["bbox"]["y1"] for bbox in matching_bboxes)
        page = matching_bboxes[0]["page"]

        # Calculate confidence score
        if was_deterministic:
            confidence = 100  # Exact match found
        else:
            confidence = 80  # LLM-assisted match

        # Get evidence text (actual text from PDF)
        evidence_text = " ".join([bbox["text"] for bbox in matching_bboxes])

        return {
            "bbox": {"x0": x0, "x1": x1, "y0": y0, "y1": y1},
            "confidence": confidence,
            "page": page,
            "value": extracted_value,
            "evidence": evidence_text,  # Actual text from PDF
        }

    return None
