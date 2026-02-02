"""
OCR processing using Tesseract.
"""

import logging
from typing import Any

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)


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


def detect_scripts_from_text(text: str) -> list[str]:
    """Detect writing scripts present in text using Unicode character ranges."""
    scripts = set()

    for char in text:
        code = ord(char)

        # Latin (covers most European languages)
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
        # Vietnamese (Latin with diacritics)
        elif 0x1E00 <= code <= 0x1EFF:
            scripts.add("vietnamese")
        # Devanagari (Hindi, Sanskrit)
        elif 0x0900 <= code <= 0x097F:
            scripts.add("devanagari")

    return list(scripts)


def map_scripts_to_tesseract_langs(scripts: list[str]) -> list[str]:
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


def run_tesseract_ocr(
    pdf_path: str,
    page_dimensions: dict[int, dict[str, float]],
    dpi: int = 300,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
                    "source": f"ocr_{dpi}",
                })

        return words, lines

    except Exception as e:
        logger.error(f"Error in run_tesseract_ocr: {e}")
        return [], []
