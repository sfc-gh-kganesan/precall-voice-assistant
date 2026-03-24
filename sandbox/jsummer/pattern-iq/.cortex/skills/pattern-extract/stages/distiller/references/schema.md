# Pattern-IQ Table Schema

## PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS

| Column | Type | Notes |
|---|---|---|
| PATTERN_ID | VARCHAR | UUID primary key |
| PATTERN_NAME | VARCHAR NOT NULL | Descriptive name (e.g., "OAuth Token Refresh with Retry Pattern") |
| CATEGORY | VARCHAR | From taxonomy (see categories.md) |
| DESCRIPTION | VARCHAR | 2-3 sentences: what it does, what problem it solves, when to reuse |
| ABSTRACTED_CODE | VARCHAR(16M) | Clean-room generic template with `<PLACEHOLDER>`s |
| SOURCE_REPO_LINK | VARCHAR | HTTPS GitHub URL to source repo |
| REPO_NAME | VARCHAR | Git repository name |
| COMPLEXITY_SCORE | NUMBER | 1 (drop-in) to 5 (multi-service integration) |
| DEPENDENCIES | VARIANT | JSON array of external library names |
| DEPENDENCY_GRAPH | VARIANT | JSON object: `{internal: [...], external: [...]}` |
| SYNTHETIC_QUERIES | VARIANT | JSON array of intent-matching questions engineers might ask |
| USAGE_NOTES | VARCHAR | How to port, prerequisites, gotchas |
| TAGS | ARRAY | 3-5 freeform domain-specific tags |
| LANGUAGE | VARCHAR | Primary language: python, sql, yaml |
| FRAMEWORK | VARCHAR | From taxonomy (see frameworks.md), or empty for pure stdlib |
| CREATED_AT | TIMESTAMP_NTZ | Auto-set |
| CREATED_BY | VARCHAR | Who extracted |
| SEARCH_CONTENT | VARCHAR(16M) | pattern_name + description + usage_notes + synthetic_queries (for Cortex Search) |
