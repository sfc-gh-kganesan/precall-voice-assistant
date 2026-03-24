#!/usr/bin/env python3
"""
reconcile_patterns.py -- Query existing patterns for a repo and produce a reconciliation manifest.

The Librarian SKILL.md uses this manifest to ask the LLM to semantically match
fresh pattern cards against existing ones, determining which to insert, update,
or delete.

Usage:
    python reconcile_patterns.py --input <fresh-cards.json> --connection <name> --output <manifest.json>
"""

import argparse
import json
import os
import sys

import snowflake.connector


def load_fresh_cards(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_existing_patterns(conn, repo_name):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT PATTERN_ID, PATTERN_NAME, DESCRIPTION "
        "FROM PATTERN_IQ.PUBLIC.REUSABLE_PATTERNS "
        "WHERE REPO_NAME = %s",
        (repo_name,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [
        {
            "pattern_id": row[0],
            "pattern_name": row[1],
            "description": row[2] or "",
        }
        for row in rows
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Query existing patterns and produce a reconciliation manifest"
    )
    parser.add_argument("--input", required=True, help="Path to fresh pattern cards JSON")
    parser.add_argument("--connection", required=True, help="Snowflake connection name")
    parser.add_argument("--output", required=True, help="Path to write reconciliation manifest")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    fresh_cards = load_fresh_cards(args.input)
    if not fresh_cards:
        print("No fresh pattern cards to reconcile.", file=sys.stderr)
        sys.exit(0)

    repo_name = fresh_cards[0].get("repo_name", "")
    if not repo_name:
        print("Error: fresh cards missing repo_name", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to Snowflake (connection={args.connection})...", file=sys.stderr)
    conn = snowflake.connector.connect(connection_name=args.connection)

    try:
        existing = fetch_existing_patterns(conn, repo_name)
        print(
            f"Found {len(existing)} existing patterns for repo '{repo_name}'.",
            file=sys.stderr,
        )
    finally:
        conn.close()

    manifest = {
        "repo_name": repo_name,
        "existing_patterns": existing,
        "fresh_cards_count": len(fresh_cards),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"Reconciliation manifest written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
