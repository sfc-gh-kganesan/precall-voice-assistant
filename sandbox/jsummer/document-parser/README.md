# Document Parser

Standalone document content parsing utility with OCR and bounding boxes.

> **Attribution:** This project extracts and adapts the content parsing layer from [invoice-extractor](../brlee/invoice-extractor/) by Brian Lee. The original project uses LangGraph and Snowflake Cortex AI for invoice field extraction; this utility isolates the document parsing components for general-purpose use without AI dependencies.

## Features

- **PyMuPDF** native text extraction with word/line bounding boxes
- **Tesseract OCR** at multiple DPI levels (300/600) for scanned documents
- **Multi-language support** with automatic script detection (10+ languages)
- **IOU-based merging** combines PyMuPDF and OCR results
- **Structured output** via Pydantic models (JSON-serializable)

## Installation

```bash
# System dependencies (macOS)
brew install tesseract poppler tesseract-lang

# System dependencies (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-all poppler-utils

# Python dependencies
uv sync
```

## Usage

### CLI

```bash
# Parse and output JSON
document-parser invoice.pdf

# Output to file
document-parser invoice.pdf -o result.json

# Text only (no JSON structure)
document-parser invoice.pdf --text-only

# Fast mode (skip OCR, PyMuPDF only)
document-parser invoice.pdf --skip-ocr

# Custom DPI
document-parser invoice.pdf --dpi 300
```

### Python API

```python
from document_parser import parse_document

result = parse_document("document.pdf")

# Full extracted text
print(result.full_text)

# Words with bounding boxes
for word in result.words:
    print(f"{word.text} @ page {word.page}: {word.bbox}")

# Lines with bounding boxes
for line in result.lines:
    print(f"{line.text} @ page {line.page}")

# Page dimensions
print(result.page_dimensions)
```

### Output Schema

```python
DocumentContent:
  words: list[Word]           # Words with bbox, page, source, confidence
  lines: list[Line]           # Lines with bbox, page, source
  full_text: str              # Reconstructed document text
  page_count: int
  page_dimensions: dict[int, PageDimensions]
```

## Makefile Commands

```bash
make install      # Install dependencies
make parse PDF=file.pdf              # Parse document
make parse PDF=file.pdf OUTPUT=out.json
make parse-text PDF=file.pdf         # Text only output
make parse-fast PDF=file.pdf         # Skip OCR
```
