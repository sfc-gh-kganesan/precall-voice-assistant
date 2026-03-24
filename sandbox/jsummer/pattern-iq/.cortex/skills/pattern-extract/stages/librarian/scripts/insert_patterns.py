#!/usr/bin/env python3
"""
insert_patterns.py -- Sync pattern cards to REUSABLE_PATTERNS (insert, update, delete).

Each entry in the input JSON must have an "action" field:
  - "insert": create a new row (pattern_id must be a pre-assigned UUID)
  - "update": update an existing row by pattern_id (preserves CREATED_AT)
  - "delete": remove a stale row by pattern_id

If no "action" field is present, falls back to the legacy insert-with-skip
behaviour (skip if REPO_NAME + PATTERN_NAME already exists).

Usage:
    python insert_patterns.py --input <path> --connection <name>
"""

import argparse
import json
import os
import sys
import uuid

import snowflake.connector


def build_search_content(p):
    parts = [
        p.get("pattern_name", ""),
        p.get("description", ""),
        p.get("usage_notes", ""),
        " ".join(p.get("synthetic_queries", [])),
    ]
    return " ".join(part for part in parts if part)


def load_patterns(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _insert_row(cursor, p):
    """Insert a single pattern row."""
    pattern_id = p.get("pattern_id", str(uuid.uuid4()))
    search_content = build_search_content(p)

    cursor.execute(
        """INSERT INTO PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS (
            PATTERN_ID, PATTERN_NAME, CATEGORY, DESCRIPTION, ABSTRACTED_CODE,
            SOURCE_REPO_LINK, REPO_NAME, COMPLEXITY_SCORE,
            DEPENDENCIES, DEPENDENCY_GRAPH, SYNTHETIC_QUERIES,
            USAGE_NOTES, TAGS, LANGUAGE, FRAMEWORK,
            CREATED_BY, SEARCH_CONTENT
        ) SELECT
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s),
            %s, PARSE_JSON(%s), %s, %s,
            CURRENT_USER(), %s
        """,
        (
            pattern_id,
            p.get("pattern_name", ""),
            p.get("category", ""),
            p.get("description", ""),
            p.get("abstracted_code", ""),
            p.get("source_repo_link", ""),
            p.get("repo_name", ""),
            p.get("complexity_score", 0),
            json.dumps(p.get("dependencies", [])),
            json.dumps(p.get("dependency_graph", {})),
            json.dumps(p.get("synthetic_queries", [])),
            p.get("usage_notes", ""),
            json.dumps(p.get("tags", [])),
            p.get("language", ""),
            p.get("framework", ""),
            search_content,
        ),
    )


def _update_row(cursor, p):
    """Update an existing pattern row by PATTERN_ID."""
    search_content = build_search_content(p)

    cursor.execute(
        """UPDATE PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS SET
            PATTERN_NAME = %s,
            CATEGORY = %s,
            DESCRIPTION = %s,
            ABSTRACTED_CODE = %s,
            SOURCE_REPO_LINK = %s,
            REPO_NAME = %s,
            COMPLEXITY_SCORE = %s,
            DEPENDENCIES = PARSE_JSON(%s),
            DEPENDENCY_GRAPH = PARSE_JSON(%s),
            SYNTHETIC_QUERIES = PARSE_JSON(%s),
            USAGE_NOTES = %s,
            TAGS = PARSE_JSON(%s),
            LANGUAGE = %s,
            FRAMEWORK = %s,
            SEARCH_CONTENT = %s,
            UPDATED_AT = CURRENT_TIMESTAMP()
        WHERE PATTERN_ID = %s
        """,
        (
            p.get("pattern_name", ""),
            p.get("category", ""),
            p.get("description", ""),
            p.get("abstracted_code", ""),
            p.get("source_repo_link", ""),
            p.get("repo_name", ""),
            p.get("complexity_score", 0),
            json.dumps(p.get("dependencies", [])),
            json.dumps(p.get("dependency_graph", {})),
            json.dumps(p.get("synthetic_queries", [])),
            p.get("usage_notes", ""),
            json.dumps(p.get("tags", [])),
            p.get("language", ""),
            p.get("framework", ""),
            search_content,
            p["pattern_id"],
        ),
    )


def _delete_row(cursor, p):
    """Delete a stale pattern row by PATTERN_ID."""
    cursor.execute(
        "DELETE FROM PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS WHERE PATTERN_ID = %s",
        (p["pattern_id"],),
    )


def sync_patterns(conn, patterns):
    """Process patterns with explicit action fields (insert/update/delete)."""
    cursor = conn.cursor()
    inserted = 0
    updated = 0
    deleted = 0
    total = len(patterns)

    for i, p in enumerate(patterns, 1):
        action = p.get("action", "insert")
        name = p.get("pattern_name", p.get("pattern_id", "unknown"))

        if action == "delete":
            _delete_row(cursor, p)
            deleted += 1
            print(f"  Deleted {i}/{total}: {name}", file=sys.stderr)
        elif action == "update":
            _update_row(cursor, p)
            updated += 1
            print(f"  Updated {i}/{total}: {name}", file=sys.stderr)
        else:
            _insert_row(cursor, p)
            inserted += 1
            print(f"  Inserted {i}/{total}: {name}", file=sys.stderr)

    cursor.close()
    return inserted, updated, deleted


def insert_patterns_legacy(conn, patterns):
    """Legacy mode: insert with skip-on-duplicate by (REPO_NAME, PATTERN_NAME)."""
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    total = len(patterns)

    for i, p in enumerate(patterns, 1):
        repo_name = p.get("repo_name", "")
        pattern_name = p.get("pattern_name", "")

        cursor.execute(
            "SELECT PATTERN_ID FROM PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS WHERE REPO_NAME = %s AND PATTERN_NAME = %s",
            (repo_name, pattern_name),
        )
        if cursor.fetchone():
            skipped += 1
            print(f"  Skipped {i}/{total}: {pattern_name} (duplicate)", file=sys.stderr)
            continue

        _insert_row(cursor, p)
        inserted += 1
        if inserted % 10 == 0 or i == total:
            print(f"  Inserted {inserted}/{total} (skipped {skipped})...", file=sys.stderr)

    cursor.close()
    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description="Sync pattern cards to Snowflake")
    parser.add_argument("--input", required=True, help="Path to the patterns JSON file")
    parser.add_argument("--connection", required=True, help="Snowflake connection name")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    patterns = load_patterns(args.input)
    if not patterns:
        print("No patterns to process.", file=sys.stderr)
        sys.exit(0)

    # Detect mode: if any entry has an "action" field, use sync mode.
    has_actions = any("action" in p for p in patterns)

    print(f"Connecting to Snowflake (connection={args.connection})...", file=sys.stderr)
    conn = snowflake.connector.connect(connection_name=args.connection)

    try:
        if has_actions:
            inserted, updated, deleted = sync_patterns(conn, patterns)
            print(
                f"\nDone. Inserted {inserted}, updated {updated}, deleted {deleted}.",
                file=sys.stderr,
            )
        else:
            inserted, skipped = insert_patterns_legacy(conn, patterns)
            print(
                f"\nDone. Inserted {inserted}, skipped {skipped} (duplicates).",
                file=sys.stderr,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
