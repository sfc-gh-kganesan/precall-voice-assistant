# Document Extractor

Extract structured contract metadata from documents using BAML and Snowflake Cortex AI.

## Features

- **BAML-powered extraction** with structured output schemas
- **Contract metadata extraction** including parties, dates, and terms
- **Snowflake Cortex AI** integration for LLM-based analysis
- **Bounding box support** for citation tracking
- **Structured output** via Pydantic models (JSON-serializable)

## Installation

```bash
# Python dependencies
uv sync

# To use the document-extractor CLI directly
uv pip install -e .
```

## Configuration

Create a `.env` file with your API credentials:

```bash
CORTEX_BASE_URL=<your-cortex-endpoint>
CORTEX_API_KEY=<your-api-key>
```

## Usage

### CLI

First, activate the virtual environment:

```bash
source .venv/bin/activate
```

Then run the CLI:

```bash
# Extract metadata from a text file
document-extractor contract.txt

# Extract from parsed JSON (includes bounding boxes)
document-extractor parsed_document.json
```

### Python API

```python
from document_extractor import extract_content_from_file, content_blocks_extract

# Load content from file
content = extract_content_from_file("parsed_document.json")

# Extract contract metadata
metadata = content_blocks_extract(content)

# Access extracted fields
print(metadata.document_title)
print(metadata.effective_start)
print(metadata.effective_end)

# Parties and their roles
for party in metadata.parties:
    print(f"{party.name}: {party.role}")

# Contract terms with citations
for term in metadata.terms:
    print(f"{term.title} ({term.category}): {term.summary}")
```

### Output Schema

```python
ContractMetadata:
  document_id: str           # Unique document identifier
  document_title: str        # Document title
  document_date: Date?       # Document date if available
  effective_start: Date      # Contract start date
  effective_end: Date        # Contract end date
  parties: list[Party]       # Parties with name, role, signature date
  terms: list[ContractTerm]  # Terms with title, summary, category, citation
```

## Makefile Commands

```bash
make install                 # Install dependencies
make extract FILE=doc.json   # Extract metadata from file
make extract FILE=doc.txt    # Extract from text file
make clean                   # Remove build artifacts
```
