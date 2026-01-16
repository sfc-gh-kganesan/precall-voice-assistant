# Invoice Extractor

Standalone invoice data extraction module extracted from the InvoiceIQ project.

## Features

- **PDF Processing**: Extracts text from PDFs using PyMuPDF with Tesseract OCR fallback
- **Field Extraction**: Extracts 9 header fields (invoice number, vendor, date, amounts, PO, etc.)
- **Line Item Extraction**: Extracts line items with descriptions, amounts, quantities, dates
- **Table Detection**: Uses pdfplumber for bordered tables, falls back to LLM for freeform
- **Multi-language Support**: Detects and OCRs documents in 10+ languages
- **Bounding Boxes**: Returns field locations for UI highlighting

## Installation

### Prerequisites

- Python 3.11+
- Tesseract OCR installed on your system
- Poppler (for pdf2image)

**macOS:**
```bash
brew install tesseract poppler
# Install language packs for better OCR
brew install tesseract-lang
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-all poppler-utils
```

### Python Dependencies

```bash
cd invoice-extractor
pip install -e .
# or with uv:
uv pip install -e .
```

## Configuration

### Snowflake Cortex (Recommended)

This extractor uses Snowflake Cortex LLM via the OpenAI-compatible API. You need:

1. **SNOWFLAKE_PAT**: Personal Access Token for authentication
2. **SNOWFLAKE_ACCOUNT**: Your Snowflake account identifier

Create a `.env` file in the `invoice-extractor` directory:

```bash
SNOWFLAKE_ACCOUNT=your-account       # e.g., pm-fde
SNOWFLAKE_PAT=your-personal-access-token
```

### Example .env file

Copy the example file and fill in your values:

```bash
cp example.env .env
```

See `example.env` for all available options.

## Usage

### Quick Start (Makefile)

```bash
# See all available commands
make help

# Extract a PDF (saves to results/)
make extract PDF=invoice.pdf

# Batch extract all PDFs in a folder
make batch DIR=invoices/

# Clean results
make clean
```

### Command Line

```bash
# Extract single invoice
python -m app.main extract invoice.pdf

# Extract and save to file
python -m app.main extract invoice.pdf --output results/output.json

# Batch extract
python -m app.main batch invoices/ --output results/

# Without table detection (pure LLM)
python -m app.main extract invoice.pdf --no-tables
```

### Python API

```python
from app.graph import extract_invoice_sync

# Synchronous extraction
result = extract_invoice_sync("invoice.pdf")
print(result["fields"]["invoice_number"])
print(len(result["line_items"]))

# Async extraction
import asyncio
from app.graph import extract_invoice

result = asyncio.run(extract_invoice("invoice.pdf"))
```

### Output Format

```json
{
  "fields": {
    "invoice_number": "INV-12345",
    "vendor_name": "Acme Corp",
    "invoice_date": "2024-01-15",
    "total_amount": "1,234.56",
    "tax_amount": "123.45",
    "currency": "USD",
    "purchase_order_number": "PO-789012",
    "snowflake_entity": "Customer Inc",
    "memo_description": "Services invoice"
  },
  "line_items": [
    {
      "line_number": 1,
      "description": "Consulting Services - January 2024",
      "type": "Service",
      "amount": "1,000.00",
      "quantity": null,
      "unit_price": null,
      "service_start_date": "2024-01-01",
      "service_end_date": "2024-01-31"
    }
  ],
  "extraction_confidence": {
    "score": 0.85,
    "reasoning": "All required fields found; High bbox coverage (7/8)"
  },
  "fields_with_bounding_boxes": {
    "invoice_number": {
      "value": "INV-12345",
      "bbox": {"x0": 100, "y0": 50, "x1": 200, "y1": 65},
      "page": 1
    }
  }
}
```

## Architecture

```
app/
├── main.py           # CLI entry point
├── graph.py          # LangGraph workflow
├── nodes.py          # Extraction nodes
├── model.py          # Snowflake Cortex LLM wrapper
├── prompts.py        # Extraction prompts
├── helpers.py        # PDF/OCR utilities
├── table_detection.py # Table detection and parsing
├── schemas.py        # Output data structures
└── line_item_keywords.py # Goods/Service classification keywords
```

## Extraction Pipeline

1. **Bounding Box Extraction** (`extract_bounding_boxes`)
   - PyMuPDF extracts native PDF text
   - Tesseract OCR at 300/600 DPI for scanned pages
   - Results merged for best coverage

2. **Field Extraction** (`run_unified_extractor`)
   - Text reconstructed from bounding boxes
   - LLM extracts 9 header fields
   - Fields mapped back to bounding boxes

3. **Line Item Extraction** (`extract_line_items_with_tables`)
   - pdfplumber detects bordered tables
   - LLM classifies rows (line item vs subtotal/header)
   - Falls back to page-by-page LLM extraction

4. **Output Collection** (`collect_extraction_output`)
   - Normalizes amounts (US/EU formats)
   - Assigns line numbers
   - Builds final output

## Supported Fields

| Field | Description |
|-------|-------------|
| `invoice_number` | Invoice ID/number |
| `vendor_name` | Company issuing the invoice |
| `snowflake_entity` | Customer being billed |
| `invoice_date` | Invoice date (YYYY-MM-DD) |
| `total_amount` | Total amount due |
| `tax_amount` | Tax/VAT amount |
| `currency` | 3-letter currency code |
| `purchase_order_number` | PO reference (PO-XXXXXX) |
| `memo_description` | "Goods invoice" / "Services invoice" |

## Line Item Types

- **Goods**: Physical products with quantity/unit_price
- **Service**: Intangible services with optional service dates

## License

MIT

