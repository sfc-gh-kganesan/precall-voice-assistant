"""
Helper utilities for PDF processing, OCR, and text extraction.
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import cv2

logger = logging.getLogger(__name__)


# ============================================================================
# Amount Normalization
# ============================================================================

def normalize_amount(amount_str: str, return_string: bool = False) -> float | str:
    """
    Normalize amount string to float, handling US and EU/LATAM formats.

    US format:  3,371.58 (comma=thousands, period=decimal)
    EU format:  3.371,58 (period=thousands, comma=decimal)

    Args:
        amount_str: Raw amount string from invoice
        return_string: If True, return formatted string instead of float

    Returns:
        Normalized float value, or formatted string if return_string=True
    """
    if not amount_str:
        return "" if return_string else 0.0

    # Convert to string and clean up
    cleaned = str(amount_str).strip()

    # Handle negative amounts: (100.00) or -100.00
    is_negative = (
        cleaned.startswith("(") and cleaned.endswith(")")
    ) or cleaned.startswith("-")

    # Remove currency symbols, parentheses, minus signs, whitespace
    cleaned = cleaned.lstrip("($€£¥R₹-").rstrip(")").strip()

    # Remove any remaining currency codes (USD, EUR, etc.)
    cleaned = re.sub(r"^[A-Z]{3}\s*", "", cleaned)  # Remove leading currency codes
    cleaned = re.sub(r"\s*[A-Z]{3}$", "", cleaned)  # Remove trailing currency codes
    cleaned = cleaned.strip()

    if not cleaned:
        return "" if return_string else 0.0

    # Find last occurrence of . and ,
    last_period = cleaned.rfind(".")
    last_comma = cleaned.rfind(",")

    try:
        if last_period == -1 and last_comma == -1:
            # No separators - integer
            result = float(cleaned.replace(" ", ""))
        elif last_period == -1:
            # Only commas - could be thousands OR decimal
            digits_after_comma = len(cleaned) - last_comma - 1
            if digits_after_comma <= 2:
                # Comma is decimal (EU format: 3371,58)
                result = float(cleaned.replace(",", "."))
            else:
                # Comma is thousands (US format: 3,371)
                result = float(cleaned.replace(",", ""))
        elif last_comma == -1:
            # Only periods - could be thousands OR decimal
            digits_after_period = len(cleaned) - last_period - 1
            if digits_after_period <= 2:
                # Period is decimal (US format: 3371.58)
                result = float(cleaned)
            else:
                # Period is thousands (EU format: 3.371)
                result = float(cleaned.replace(".", ""))
        elif last_period > last_comma:
            # Period is decimal (US: 3,371.58)
            result = float(cleaned.replace(",", ""))
        else:
            # Comma is decimal (EU: 3.371,58)
            result = float(cleaned.replace(".", "").replace(",", "."))

        if is_negative:
            result = -result

        if return_string:
            return f"{result:.2f}"
        return result

    except ValueError:
        return "" if return_string else 0.0


# ============================================================================
# PDF Text Extraction (PyMuPDF)
# ============================================================================

def extract_text_and_lines_with_bboxes(pdf_path: str) -> Dict[str, Any]:
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
    token_id = 0
    line_id = 0

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
                            "line_id": line_id,
                            "bbox": {
                                "x0": float(x0),
                                "x1": float(x1),
                                "y0": float(y0),
                                "y1": float(y1),
                            },
                            "page": page_num + 1,  # 1-indexed page numbers
                            "text": line_text,
                            "type": "Line",
                            "block_no": block_no,
                            "line_no": line_idx,
                            "source": "pymupdf",
                            "confidence": 100,
                        })
                        line_id += 1

            # Get words with their bounding boxes
            words = page.get_text("words")

            for word_data in words:
                x0, y0, x1, y1, word_text, block_no, line_no, word_no = word_data

                words_with_bboxes.append({
                    "token_id": token_id,
                    "bbox": {
                        "x0": float(x0),
                        "x1": float(x1),
                        "y0": float(y0),
                        "y1": float(y1),
                    },
                    "page": page_num + 1,
                    "text": word_text,
                    "type": "Word",
                    "block_no": block_no,
                    "line_no": line_no,
                    "source": "pymupdf",
                    "confidence": 100,
                })
                token_id += 1

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


# ============================================================================
# OCR Processing (Tesseract)
# ============================================================================

def preprocess_image_for_ocr(pil_image: Image.Image, dpi: int = 300) -> Image.Image:
    """
    Preprocess image for better OCR results.
    
    Args:
        pil_image: PIL Image to preprocess
        dpi: Target DPI (higher = better quality but slower)
    
    Returns:
        Preprocessed PIL Image
    """
    # Convert to numpy array
    img_array = np.array(pil_image)
    
    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Apply adaptive thresholding for better text contrast
    # This helps with scanned documents and varying lighting
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
    
    return Image.fromarray(denoised)


def detect_languages_from_image(pil_image: Image.Image) -> str:
    """
    Detect languages present in an image using quick OCR pass.
    
    Args:
        pil_image: PIL Image to analyze
    
    Returns:
        Tesseract language string, e.g., "eng+kor" or "eng+jpn"
    """
    # Quick OCR pass with major world scripts
    detection_langs = "eng+kor+jpn+chi_sim+chi_tra+ara+heb+rus+deu+fra+spa+tha+vie+hin"
    
    try:
        raw_text = pytesseract.image_to_string(
            pil_image, lang=detection_langs, config="--oem 3 --psm 3"
        )
    except Exception as e:
        logger.warning(f"Quick OCR for language detection failed: {e}")
        return "eng"  # Fallback to English only
    
    # Analyze Unicode ranges to detect scripts
    detected_scripts = detect_scripts_from_text(raw_text)
    
    # Map scripts to Tesseract language codes
    lang_codes = map_scripts_to_tesseract_langs(detected_scripts)
    
    # Always include English as base
    if "eng" not in lang_codes:
        lang_codes.insert(0, "eng")
    
    # Build language string (limit to avoid slowdown)
    lang_string = "+".join(lang_codes[:5])
    
    logger.info(f"Detected languages for OCR: {lang_string}")
    return lang_string


def detect_scripts_from_text(text: str) -> List[str]:
    """Detect writing scripts present in text using Unicode character ranges."""
    scripts = set()
    
    for char in text:
        code = ord(char)
        
        # Latin (covers most European languages including Spanish, Portuguese, French, German, etc.)
        if 0x0041 <= code <= 0x024F:
            scripts.add("latin")
        # Korean Hangul
        elif 0xAC00 <= code <= 0xD7AF or 0x1100 <= code <= 0x11FF:
            scripts.add("korean")
        # Japanese (Hiragana and Katakana)
        elif 0x3040 <= code <= 0x30FF or 0x31F0 <= code <= 0x31FF:
            scripts.add("japanese")
        # CJK (Chinese characters, also used in Japanese/Korean)
        elif 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            scripts.add("cjk")
        # Arabic
        elif 0x0600 <= code <= 0x06FF:
            scripts.add("arabic")
        # Hebrew
        elif 0x0590 <= code <= 0x05FF:
            scripts.add("hebrew")
        # Cyrillic (Russian, Ukrainian, etc.)
        elif 0x0400 <= code <= 0x04FF:
            scripts.add("cyrillic")
        # Thai
        elif 0x0E00 <= code <= 0x0E7F:
            scripts.add("thai")
        # Vietnamese (Latin with diacritics - often caught by Latin range)
        elif 0x1E00 <= code <= 0x1EFF:
            scripts.add("vietnamese")
        # Devanagari (Hindi, Sanskrit)
        elif 0x0900 <= code <= 0x097F:
            scripts.add("devanagari")
    
    return list(scripts)


def map_scripts_to_tesseract_langs(scripts: List[str]) -> List[str]:
    """Map detected scripts to Tesseract language codes."""
    script_to_lang = {
        "latin": "eng",
        "korean": "kor",
        "japanese": "jpn",
        "cjk": "chi_sim",
        "arabic": "ara",
        "hebrew": "heb",
        "cyrillic": "rus",
        "thai": "tha",
        "vietnamese": "vie",
        "devanagari": "hin",
    }
    
    return [script_to_lang.get(script, "eng") for script in scripts if script in script_to_lang]


def run_ocr_on_pdf(
    pdf_path: str,
    dpi: int = 300,
    preprocess: bool = True,
) -> Dict[str, Any]:
    """
    Run OCR on a PDF file and return words with bounding boxes.
    
    Args:
        pdf_path: Path to the PDF file
        dpi: DPI for PDF to image conversion
        preprocess: Whether to preprocess images for better OCR
    
    Returns:
        Dictionary containing:
        - 'words': List of word dicts with bbox, page, text, confidence
        - 'lines': List of line dicts with bbox, page, text
        - 'page_dimensions': Dict mapping page_num to {width, height}
    """
    ocr_words = []
    ocr_lines = []
    page_dimensions = {}
    
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)
        
        # Get PDF dimensions for coordinate mapping
        doc = fitz.open(pdf_path)
        
        for page_num, (pil_image, page) in enumerate(zip(images, doc)):
            # Get page dimensions
            pdf_rect = page.rect
            pdf_width = pdf_rect.width
            pdf_height = pdf_rect.height
            page_dimensions[page_num] = {"width": pdf_width, "height": pdf_height}
            
            # Get image dimensions
            img_width, img_height = pil_image.size
            
            # Calculate scale factors
            scale_x = pdf_width / img_width
            scale_y = pdf_height / img_height
            
            # Preprocess image if requested
            if preprocess:
                processed_image = preprocess_image_for_ocr(pil_image, dpi)
            else:
                processed_image = pil_image
            
            # Detect languages
            detected_langs = detect_languages_from_image(pil_image)
            
            # Run Tesseract with word-level output
            ocr_data = pytesseract.image_to_data(
                processed_image,
                output_type=pytesseract.Output.DICT,
                lang=detected_langs,
            )
            
            # Process OCR results
            current_line_key = None
            line_words = []
            line_bbox = None
            
            for i in range(len(ocr_data["text"])):
                word_text = ocr_data["text"][i].strip()
                conf = int(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0
                block_num = ocr_data["block_num"][i]
                par_num = ocr_data["par_num"][i]
                line_num = ocr_data["line_num"][i]
                
                line_key = (block_num, par_num, line_num)
                
                if word_text and conf > 20:  # Confidence threshold
                    x = ocr_data["left"][i]
                    y = ocr_data["top"][i]
                    w = ocr_data["width"][i]
                    h = ocr_data["height"][i]
                    
                    # Convert to PDF coordinates
                    pdf_x0 = x * scale_x
                    pdf_y0 = y * scale_y
                    pdf_x1 = (x + w) * scale_x
                    pdf_y1 = (y + h) * scale_y
                    
                    word_dict = {
                        "token_id": len(ocr_words),
                        "bbox": {
                            "x0": pdf_x0,
                            "x1": pdf_x1,
                            "y0": pdf_y0,
                            "y1": pdf_y1,
                        },
                        "page": page_num + 1,
                        "text": word_text,
                        "type": "Word",
                        "source": "ocr",
                        "confidence": conf,
                    }
                    ocr_words.append(word_dict)
                    
                    # Track line grouping
                    if line_key != current_line_key:
                        # Save previous line
                        if line_words and line_bbox:
                            ocr_lines.append({
                                "line_id": len(ocr_lines),
                                "bbox": line_bbox,
                                "page": page_num + 1,
                                "text": " ".join(line_words),
                                "type": "Line",
                                "source": "ocr",
                            })
                        # Start new line
                        current_line_key = line_key
                        line_words = [word_text]
                        line_bbox = {
                            "x0": pdf_x0,
                            "x1": pdf_x1,
                            "y0": pdf_y0,
                            "y1": pdf_y1,
                        }
                    else:
                        # Extend current line
                        line_words.append(word_text)
                        if line_bbox:
                            line_bbox["x1"] = max(line_bbox["x1"], pdf_x1)
                            line_bbox["y1"] = max(line_bbox["y1"], pdf_y1)
            
            # Save last line
            if line_words and line_bbox:
                ocr_lines.append({
                    "line_id": len(ocr_lines),
                    "bbox": line_bbox,
                    "page": page_num + 1,
                    "text": " ".join(line_words),
                    "type": "Line",
                    "source": "ocr",
                })
        
        doc.close()
        
        return {
            "words": ocr_words,
            "lines": ocr_lines,
            "page_dimensions": page_dimensions,
        }
    
    except Exception as e:
        logger.error(f"Error running OCR on PDF: {str(e)}")
        return {"words": [], "lines": [], "page_dimensions": {}}


# ============================================================================
# Text Merging (PyMuPDF + OCR)
# ============================================================================

def merge_words(
    pymupdf_words: List[Dict[str, Any]],
    ocr_words: List[Dict[str, Any]],
    overlap_threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Merge PyMuPDF words and OCR words, preferring PyMuPDF for overlapping regions.
    
    Args:
        pymupdf_words: Words from PyMuPDF extraction
        ocr_words: Words from OCR extraction
        overlap_threshold: IoU threshold for considering words as overlapping
    
    Returns:
        List of merged words
    """
    if not pymupdf_words:
        return ocr_words.copy() if ocr_words else []
    
    if not ocr_words:
        return pymupdf_words.copy()
    
    def boxes_overlap(box1: Dict, box2: Dict, threshold: float) -> bool:
        """Check if two bounding boxes overlap significantly."""
        x_left = max(box1["x0"], box2["x0"])
        y_top = max(box1["y0"], box2["y0"])
        x_right = min(box1["x1"], box2["x1"])
        y_bottom = min(box1["y1"], box2["y1"])
        
        if x_right < x_left or y_bottom < y_top:
            return False
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = (box1["x1"] - box1["x0"]) * (box1["y1"] - box1["y0"])
        area2 = (box2["x1"] - box2["x0"]) * (box2["y1"] - box2["y0"])
        
        if area1 == 0 or area2 == 0:
            return False
        
        iou = intersection / min(area1, area2)
        return iou > threshold
    
    merged = pymupdf_words.copy()
    
    # Add OCR words that don't overlap with PyMuPDF words
    for ocr_word in ocr_words:
        ocr_page = ocr_word.get("page", 0)
        ocr_bbox = ocr_word.get("bbox", {})
        
        has_overlap = False
        for pymupdf_word in pymupdf_words:
            if pymupdf_word.get("page", 0) == ocr_page:
                pymupdf_bbox = pymupdf_word.get("bbox", {})
                if boxes_overlap(ocr_bbox, pymupdf_bbox, overlap_threshold):
                    has_overlap = True
                    break
        
        if not has_overlap:
            merged.append(ocr_word)
    
    # Sort by page, then Y, then X
    merged.sort(key=lambda w: (
        w.get("page", 0),
        w.get("bbox", {}).get("y0", 0),
        w.get("bbox", {}).get("x0", 0)
    ))
    
    return merged


# ============================================================================
# Text Reconstruction
# ============================================================================

def reconstruct_text_from_words(
    words: List[Dict[str, Any]],
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


def get_page_text(
    words: List[Dict[str, Any]],
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


# ============================================================================
# Field Bounding Box Matching
# ============================================================================

def find_field_bbox(
    field_value: str,
    words: List[Dict[str, Any]],
    fuzzy_threshold: float = 0.8,
) -> Optional[Dict[str, Any]]:
    """
    Find bounding box for a field value in the extracted words.
    
    Args:
        field_value: The field value to search for
        words: List of word dicts with bbox
        fuzzy_threshold: Threshold for fuzzy matching (0-1)
    
    Returns:
        Dict with bbox and matched text, or None if not found
    """
    if not field_value or not words:
        return None
    
    field_value = str(field_value).strip()
    field_lower = field_value.lower()
    field_words = field_value.split()
    
    # Try exact match first
    for word in words:
        word_text = word.get("text", "").strip()
        if word_text.lower() == field_lower:
            return {
                "bbox": word.get("bbox"),
                "page": word.get("page"),
                "matched_text": word_text,
                "confidence": 1.0,
            }
    
    # Try multi-word sequence match
    if len(field_words) > 1:
        for i in range(len(words) - len(field_words) + 1):
            # Check if words are on the same page and close together
            candidate_words = words[i:i + len(field_words)]
            
            if len(set(w.get("page", 0) for w in candidate_words)) > 1:
                continue  # Words on different pages
            
            candidate_text = " ".join(w.get("text", "") for w in candidate_words)
            
            if candidate_text.lower() == field_lower:
                # Merge bounding boxes
                merged_bbox = {
                    "x0": min(w.get("bbox", {}).get("x0", 0) for w in candidate_words),
                    "y0": min(w.get("bbox", {}).get("y0", 0) for w in candidate_words),
                    "x1": max(w.get("bbox", {}).get("x1", 0) for w in candidate_words),
                    "y1": max(w.get("bbox", {}).get("y1", 0) for w in candidate_words),
                }
                return {
                    "bbox": merged_bbox,
                    "page": candidate_words[0].get("page"),
                    "matched_text": candidate_text,
                    "confidence": 1.0,
                }
    
    # Try partial/fuzzy match
    for word in words:
        word_text = word.get("text", "").strip()
        if field_lower in word_text.lower() or word_text.lower() in field_lower:
            return {
                "bbox": word.get("bbox"),
                "page": word.get("page"),
                "matched_text": word_text,
                "confidence": 0.8,
            }
    
    return None


# ============================================================================
# Confidence Calculation
# ============================================================================

def calculate_extraction_confidence(
    extracted_fields: Dict[str, Any],
    fields_with_bboxes: Dict[str, Any],
    full_text: str,
) -> Dict[str, Any]:
    """
    Calculate confidence score for the extraction.
    
    Args:
        extracted_fields: Dict of extracted field values
        fields_with_bboxes: Dict of fields that have bounding boxes
        full_text: Full text of the document
    
    Returns:
        Dict with score (0-1) and reasoning
    """
    score = 0.0
    reasons = []
    
    # Check required fields
    required_fields = ["invoice_number", "vendor_name", "total_amount"]
    found_required = sum(1 for f in required_fields if extracted_fields.get(f))
    score += (found_required / len(required_fields)) * 0.4
    
    if found_required == len(required_fields):
        reasons.append("All required fields found")
    else:
        missing = [f for f in required_fields if not extracted_fields.get(f)]
        reasons.append(f"Missing required fields: {', '.join(missing)}")
    
    # Check bounding box coverage
    total_fields = len([v for v in extracted_fields.values() if v])
    fields_with_bboxes_count = len(fields_with_bboxes)
    
    if total_fields > 0:
        bbox_coverage = fields_with_bboxes_count / total_fields
        score += bbox_coverage * 0.3
        
        if bbox_coverage > 0.7:
            reasons.append(f"High bbox coverage ({fields_with_bboxes_count}/{total_fields})")
        else:
            reasons.append(f"Low bbox coverage ({fields_with_bboxes_count}/{total_fields})")
    
    # Check text quality
    if full_text:
        # Check for common OCR errors or garbled text
        alpha_ratio = sum(1 for c in full_text if c.isalpha()) / max(len(full_text), 1)
        
        if alpha_ratio > 0.3:
            score += 0.3
            reasons.append("Good text quality")
        else:
            reasons.append("Poor text quality (possibly scanned/OCR issues)")
    
    return {
        "score": round(score, 2),
        "reasoning": "; ".join(reasons),
    }


# ============================================================================
# OCR Helper Functions (for nodes.py)
# ============================================================================

def run_tesseract_ocr(
    pdf_path: str,
    page_dimensions: Dict[int, Dict[str, float]],
    dpi: int = 300,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run Tesseract OCR on PDF and return words and lines with bboxes.
    
    Args:
        pdf_path: Path to PDF file
        page_dimensions: Dict mapping page_num to {width, height}
        dpi: DPI for conversion
    
    Returns:
        Tuple of (words, lines) lists
    """
    words = []
    lines = []
    
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
        
        for page_num, pil_image in enumerate(images):
            # Get dimensions
            img_width, img_height = pil_image.size
            pdf_dims = page_dimensions.get(page_num, {"width": img_width, "height": img_height})
            pdf_width = pdf_dims.get("width", img_width)
            pdf_height = pdf_dims.get("height", img_height)
            
            scale_x = pdf_width / img_width
            scale_y = pdf_height / img_height
            
            # Preprocess and detect language
            processed = preprocess_image_for_ocr(pil_image, dpi)
            langs = detect_languages_from_image(pil_image)
            
            # Run OCR
            ocr_data = pytesseract.image_to_data(
                processed,
                output_type=pytesseract.Output.DICT,
                lang=langs,
            )
            
            # Process results
            current_line_key = None
            line_words_list = []
            line_bbox = None
            
            for i in range(len(ocr_data["text"])):
                word_text = ocr_data["text"][i].strip()
                conf = int(ocr_data["conf"][i]) if str(ocr_data["conf"][i]) != "-1" else 0
                
                if word_text and conf > 20:
                    x = ocr_data["left"][i]
                    y = ocr_data["top"][i]
                    w = ocr_data["width"][i]
                    h = ocr_data["height"][i]
                    
                    bbox = {
                        "x0": x * scale_x,
                        "y0": y * scale_y,
                        "x1": (x + w) * scale_x,
                        "y1": (y + h) * scale_y,
                    }
                    
                    words.append({
                        "bbox": bbox,
                        "page": page_num + 1,
                        "text": word_text,
                        "type": "Word",
                        "source": f"ocr_{dpi}",
                        "confidence": conf,
                    })
                    
                    # Track lines
                    block_num = ocr_data["block_num"][i]
                    par_num = ocr_data["par_num"][i]
                    line_num = ocr_data["line_num"][i]
                    line_key = (block_num, par_num, line_num)
                    
                    if line_key != current_line_key:
                        if line_words_list and line_bbox:
                            lines.append({
                                "bbox": line_bbox,
                                "page": page_num + 1,
                                "text": " ".join(line_words_list),
                                "type": "Line",
                                "source": f"ocr_{dpi}",
                            })
                        current_line_key = line_key
                        line_words_list = [word_text]
                        line_bbox = bbox.copy()
                    else:
                        line_words_list.append(word_text)
                        if line_bbox:
                            line_bbox["x1"] = max(line_bbox["x1"], bbox["x1"])
                            line_bbox["y1"] = max(line_bbox["y1"], bbox["y1"])
            
            # Save last line
            if line_words_list and line_bbox:
                lines.append({
                    "bbox": line_bbox,
                    "page": page_num + 1,
                    "text": " ".join(line_words_list),
                    "type": "Line",
                    "source": f"ocr_{dpi}",
                })
        
        return words, lines
        
    except Exception as e:
        logger.error(f"Error in run_tesseract_ocr: {e}")
        return [], []


def merge_ocr_results(
    pymupdf: List[Dict[str, Any]],
    ocr_300: List[Dict[str, Any]],
    ocr_600: List[Dict[str, Any]],
    overlap_threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Merge results from PyMuPDF and OCR at different DPIs.
    
    Priority: PyMuPDF > OCR 600 DPI (by confidence) > OCR 300 DPI
    """
    def boxes_overlap(box1: Dict, box2: Dict, threshold: float) -> bool:
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


def reconstruct_layout_from_bboxes(words: List[Dict[str, Any]]) -> str:
    """
    Reconstruct text with layout preservation from bounding boxes.
    
    Groups words into lines based on Y-coordinate, then sorts by X within each line.
    """
    if not words:
        return ""
    
    # Group by Y-coordinate (with tolerance)
    y_tolerance = 5.0
    lines_dict: Dict[float, List[Dict]] = {}
    
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


def sort_reading_order(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort words in reading order (top-to-bottom, left-to-right)."""
    return sorted(words, key=lambda w: (
        w.get("page", 0),
        w.get("bbox", {}).get("y0", 0),
        w.get("bbox", {}).get("x0", 0),
    ))


def dehyphenate_text(words: List[Dict[str, Any]]) -> str:
    """
    Reconstruct text from words, removing hyphens at line breaks.
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
    """Normalize whitespace and remove extra spaces."""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()


# ============================================================================
# Field Validation
# ============================================================================

def validate_with_regex(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean extracted fields using regex patterns.
    """
    result = fields.copy()
    
    # Clean PO number
    if result.get("purchase_order_number"):
        po = str(result["purchase_order_number"]).strip()
        # Normalize to PO-XXXXXX format
        po = re.sub(r'^P\.?O\.?\s*#?\s*', 'PO-', po, flags=re.IGNORECASE)
        po = re.sub(r'^PO\s+', 'PO-', po)
        # Remove trailing descriptions
        po = re.sub(r'-\s*[a-zA-Z].*$', '', po)
        po = po.rstrip('-.,;:')
        result["purchase_order_number"] = po
    
    # Clean invoice number
    if result.get("invoice_number"):
        inv = str(result["invoice_number"]).strip()
        inv = inv.rstrip('.,;:')
        result["invoice_number"] = inv
    
    # Ensure currency is 3-letter code
    if result.get("currency"):
        curr = str(result["currency"]).upper().strip()
        # Extract 3-letter code if present
        match = re.search(r'[A-Z]{3}', curr)
        if match:
            result["currency"] = match.group(0)
        elif curr in ['$', '＄']:
            result["currency"] = 'USD'
        elif curr in ['€']:
            result["currency"] = 'EUR'
        elif curr in ['£']:
            result["currency"] = 'GBP'
        elif curr in ['¥', '円']:
            result["currency"] = 'JPY'
    
    # Normalize date format (should be YYYY-MM-DD)
    if result.get("invoice_date"):
        date_str = str(result["invoice_date"]).strip()
        # Try to parse and reformat
        result["invoice_date"] = normalize_date_format(date_str)
    
    return result


def normalize_date_format(date_str: str) -> str:
    """Normalize date string to YYYY-MM-DD format."""
    from datetime import datetime
    
    if not date_str:
        return ""
    
    date_str = date_str.strip()
    
    # Already in correct format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Common formats
    formats = [
        "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%m-%d-%Y", "%d-%m-%Y",
        "%m.%d.%Y", "%d.%m.%Y",
        "%B %d, %Y", "%b %d, %Y",
        "%d %B %Y", "%d %b %Y",
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
    
    return date_str


def find_and_verify_field_bbox(
    field_name: str,
    field_value: str,
    words_with_bboxes: List[Dict[str, Any]],
    model: Any,
    full_text: str,
    invoice_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Find and verify bounding box for a field value.
    """
    bbox_result = find_field_bbox(field_value, words_with_bboxes)
    
    if bbox_result:
        return {
            "value": field_value,
            "bbox": bbox_result.get("bbox"),
            "page": bbox_result.get("page"),
            "matched_text": bbox_result.get("matched_text"),
            "confidence": bbox_result.get("confidence", 0.8),
        }
    
    return None


# ============================================================================
# Line Item Filtering
# ============================================================================

def filter_line_items_with_confidence(
    line_items: List[Dict[str, Any]],
    model: Any,
    invoice_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Filter line items, removing non-items and normalizing fields.
    """
    filtered = []
    
    # Skip patterns
    skip_patterns = [
        r'^\s*(sub)?total\s*$',
        r'^\s*grand\s*total\s*$',
        r'^\s*total\s*(due|amount)?\s*$',
        r'^\s*tax\s*$',
        r'^\s*vat\s*$',
        r'^\s*shipping\s*$',
        r'^\s*discount\s*$',
    ]
    skip_regex = re.compile('|'.join(skip_patterns), re.IGNORECASE)
    
    for item in line_items:
        description = item.get("description", "").strip()
        
        # Skip empty descriptions
        if not description:
            continue
        
        # Skip totals/subtotals
        if skip_regex.match(description):
            continue
        
        # Ensure type is set
        if not item.get("type"):
            item["type"] = "Service"
        
        # Normalize service dates (use invoice date as fallback for services)
        if item.get("type") == "Service":
            if not item.get("service_start_date") and invoice_date:
                item["service_start_date"] = invoice_date
            if not item.get("service_end_date") and item.get("service_start_date"):
                item["service_end_date"] = item.get("service_start_date")
        
        filtered.append(item)
    
    return filtered

