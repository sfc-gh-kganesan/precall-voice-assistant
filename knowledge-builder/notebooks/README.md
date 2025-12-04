# Jupyter Notebooks

This directory contains analysis and development notebooks.

## Files

- `knowledge_processing_chunking.ipynb` - Knowledge processing, HTML chunking, and batch processing workflow

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