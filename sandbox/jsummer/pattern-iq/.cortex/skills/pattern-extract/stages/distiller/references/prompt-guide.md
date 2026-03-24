# Pattern Extraction Guide

## What is a "Recipe"?

A Recipe is not a single function — it is the **interaction pattern** showing how 3-4 components work together to solve a specific problem. Think of it as a reusable playbook.

## Bad Extraction Examples

### Example 1: Too Granular
> **Name**: `get_oauth_token`
> **Description**: Function `get_oauth_token` from `auth.py`.

**Why it's bad**: Describes a single function with no context about the problem it solves or how it fits into a larger pattern.

### Example 2: No Abstraction
> **Name**: `AcmeCorp Invoice Processor`
> **Description**: Processes invoices for AcmeCorp using their custom table schema ACME_DB.INVOICES.

**Why it's bad**: Customer-specific names and schemas make it non-reusable.

### Example 3: Too Vague
> **Name**: `Data Pipeline`
> **Description**: A data pipeline that moves data.

**Why it's bad**: No specificity about what problem it solves or what makes this pattern unique.

## Good Extraction Examples

### Example 1: Orchestration Recipe
> **Name**: OAuth Token Refresh with Retry Pattern
> **Description**: Shows how a token manager, retry decorator, and session pool interact to maintain authenticated connections to external APIs. Solves the problem of token expiration during long-running batch jobs. Use in any service that needs resilient authenticated HTTP calls.
> **Abstracted Code**: Generic template with `<AUTH_ENDPOINT>`, `<TOKEN_CACHE>` placeholders
> **Complexity**: 3

### Example 2: Multi-Component Integration
> **Name**: PDF Table Extraction with Validation Pipeline
> **Description**: Combines PDF page iteration, table boundary detection, cell merging logic, and schema validation into a complete extraction workflow. Solves the problem of extracting structured data from inconsistent PDF layouts. Use when building document processing pipelines that need reliable table extraction.
> **Abstracted Code**: Generic template with `<PDF_SOURCE>`, `<OUTPUT_TABLE>`, `<VALIDATION_SCHEMA>` placeholders
> **Complexity**: 4

### Example 3: State Management Pattern
> **Name**: LangGraph Stateful Agent with Tool Routing
> **Description**: Demonstrates how a state graph, tool registry, and routing node work together to build a multi-tool agent. Solves the problem of dynamically selecting and executing tools based on conversation context. Use when building Cortex Agents or LangGraph workflows that need flexible tool dispatch.
> **Abstracted Code**: Generic template with `<TOOL_REGISTRY>`, `<STATE_SCHEMA>`, `<ROUTING_LOGIC>` placeholders
> **Complexity**: 4

## Abstraction Rules

When creating the "clean room" abstracted code:
- Replace specific table names with `<TABLE_NAME>` or `<SOURCE_TABLE>`
- Replace specific model names with `<MODEL_NAME>`
- Replace specific API endpoints with `<API_ENDPOINT>`
- Replace specific column names with descriptive placeholders like `<KEY_COLUMN>`, `<VALUE_COLUMN>`
- Replace specific credentials/secrets with `<CREDENTIALS>`
- Keep structural logic intact — the flow, error handling, and orchestration patterns must be preserved
- Include inline markers like `# --- CUSTOMIZE: description ---` at key integration points
