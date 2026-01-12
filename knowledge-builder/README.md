# Knowledge Builder

Knowledge Builder Service - A Snowflake-native application for building, testing, and analyzing knowledge bases with Cortex Search.

## Overview

This project provides tools for:
- **Knowledge Base Management**: Process and chunk HTML documents for search
- **Search Testing**: Baseline testing with golden pairs and ad-hoc search playground
- **Feedback Collection**: User feedback on search quality and relevance
- **Exploratory Data Analysis**: Analyze knowledge base quality, outbound links, and image sources

## Features

### Streamlit Application
The main Streamlit app (`app/streamlit_app.py`) provides four key interfaces:

1. **Stats**: Metrics on search performance (queries, responses, similarity scores)
2. **Feedback**: Review and rate search results from baseline tests and ad-hoc queries
3. **Playground**: Interactive search interface with AI-powered responses
4. **EDA**: Knowledge base analysis including numeric/categorical profiling and link analysis

### Backend Services
- **Python Services** (`src/services/`): FastAPI service for knowledge processing
- **Rust Jobs** (`src/jobs/example_job/`): Rate-limited batch job processor for API requests
- Snowpark-based data operations
- Integration with Cortex Search and Cortex LLM services

## Prerequisites

- Python 3.13.9
- Rust toolchain (for optional job services)
- Snowflake account with access to:
  - Cortex Search Service
  - Cortex Complete (LLM)
  - Required tables: `KB_KNOWLEDGE`, `SEARCH_QUERIES`, `SEARCH_FEEDBACK`, `ORIGINAL_GOLDEN_PAIRS`
- Snowflake CLI (`snow`) installed

## Installation

Install dependencies using `uv`:

```bash
# Install core dependencies
uv sync

# Install with EDA capabilities (for streamlit app)
uv sync --group eda

# Install with dev tools (Jupyter, linters)
uv sync --group dev
```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=KNOWLEDGE_BUILDER
SNOWFLAKE_SCHEMA=PUBLIC
```

### Snowflake Configuration
The `snowflake.yml` file defines the Streamlit app deployment configuration:
- **Entity name**: `feedback_app`
- **Main file**: `streamlit_app.py`
- **Query warehouse**: `COMPUTE_WH`

## Usage

### Running Locally

```bash
# Run the Streamlit app locally
uv run streamlit run app/streamlit_app.py

# Run Jupyter notebooks
uv run jupyter notebook notebooks/

# Build Rust job (optional)
cargo build --release
```

### Deploying to Snowflake

Deploy the Streamlit app to your Snowflake account:

```bash
snow streamlit deploy
```

This will:
1. Upload the app files from the `app/` directory to the configured Snowflake stage
2. Create/update the Streamlit app in Snowsight (entity: `feedback_app`)
3. Make the app accessible at: `https://<account>.snowflakecomputing.com/streamlit/KNOWLEDGE_BUILDER/PUBLIC/FEEDBACK_APP`

**Note**: Ensure your `snowflake.yml` configuration matches your target database/schema and that all required tables and Cortex services exist.

## Project Structure

```
knowledge-builder/
├── app/                       # Streamlit application
│   ├── streamlit_app.py       # Main entry point
│   ├── data_operations.py     # Snowflake data operations
│   └── ui_components.py       # UI components and page logic
├── src/
│   ├── services/              # Backend services (Python)
│   │   └── kb_builder_svc.py  # FastAPI service for knowledge processing
│   ├── jobs/                  # Job processors
│   │   └── example_job/       # Rust batch job for rate-limited API requests
│   │       └── main.rs        # Rust job entry point
│   ├── utils/                 # Python utility functions
│   └── demos/                 # Demo scripts and examples
├── database/                  # Snowflake database artifacts
│   ├── schema/                # Database and table definitions
│   ├── functions/             # SQL UDFs (analyze_image_links, html_utils)
│   ├── infrastructure/        # Compute pools, network rules, services
│   └── jobs/                  # SQL job definitions
├── notebooks/                 # Jupyter notebooks for analysis and setup
│   └── KNOWLEDGE_BUILDER_SETUP.ipynb  # Complete knowledge base setup workflow
├── docs/                      # Additional documentation
├── pyproject.toml             # Python dependencies and project metadata
├── Cargo.toml                 # Rust dependencies for job services
├── snowflake.yml              # Snowflake deployment configuration
└── config.py                  # Application configuration
```

## Database Schema

Required tables:
- `KB_KNOWLEDGE`: Source knowledge articles and content
- `SEARCH_QUERIES`: Logged search queries and responses
- `SEARCH_FEEDBACK`: User feedback on search results
- `ORIGINAL_GOLDEN_PAIRS`: Baseline test query/answer pairs
- `EVALUATION_RESULTS`: Evaluation metrics and test results

Required Cortex services:
- `KB_SEARCH`: Cortex Search Service (created by KNOWLEDGE_BUILDER_SETUP.ipynb)

SQL artifacts are organized in the `database/` directory:
- **Schema**: Database and table setup scripts
- **Functions**: SQL UDFs for HTML processing, image analysis, and KB operations
- **Infrastructure**: Compute pools, network rules, and service definitions
- **Jobs**: SQL-based job definitions and schedulers

## Development

### Code Quality

```bash
# Format and lint
uv run ruff check .
uv run ruff format .
```

### Testing

Run Jupyter notebooks for end-to-end testing:

```bash
uv run jupyter notebook notebooks/KNOWLEDGE_BUILDER_SETUP.ipynb
```

## Dependencies

### Core
- `snowflake-snowpark-python`: Snowflake data operations
- `fastapi`: REST API framework
- `pandas`: Data manipulation
- `pydantic`: Data validation

### Streamlit App (eda group)
- `streamlit`: Web application framework
- `altair`: Data visualization
- `ydata-profiling`: Automated EDA reports

### Development (dev group)
- `jupyter`: Interactive notebooks
- `ruff`: Linting and formatting

## License

Internal project for Snowflake AI FDE team.
