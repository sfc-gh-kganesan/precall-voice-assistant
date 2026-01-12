# Jupyter notebooks

This directory contains analysis and development notebooks.

## Files

- `setup.ipynb` - Complete knowledge base setup workflow:
  - Database table creation (SEARCH_QUERIES, SEARCH_FEEDBACK)
  - Knowledge article ingestion from CSV
  - HTML text cleaning and document chunking
  - Cortex Search Service creation and configuration
  - Search testing and feedback collection examples

## Setup

To run the notebooks:

```bash
# Install development dependencies including Jupyter
uv sync --group dev

# Start Jupyter
uv run jupyter notebook notebooks/
```

## Dependencies

Notebooks use the main project dependencies plus Jupyter from the `dev` dependency group.