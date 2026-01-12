# Jupyter Notebooks

This directory contains analysis and development notebooks for the Knowledge Builder project.

## Notebooks

| Notebook | Description |
|----------|-------------|
| `KNOWLEDGE_BUILDER_SETUP.ipynb` | Complete knowledge base setup workflow: database table creation, knowledge article ingestion, HTML text cleaning, document chunking, Cortex Search Service creation, and search testing examples |

## Running Notebooks

```bash
# Install development dependencies including Jupyter
uv sync --group dev

# Start Jupyter
uv run jupyter notebook notebooks/
```

Notebooks use the main project dependencies plus Jupyter from the `dev` dependency group.
