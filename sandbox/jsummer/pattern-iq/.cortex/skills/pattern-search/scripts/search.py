#!/usr/bin/env python3
"""
search.py -- Query the Pattern-IQ Cortex Search service for reusable patterns.

Usage:
    python search.py --query "authentication token" [--category auth] [--limit 5]
"""

import argparse
import json
import os
import sys

from snowflake.connector import connect
from snowflake.core import Root


def build_filter(category=None, language=None, framework=None, repo_name=None):
    conditions = []
    if category:
        conditions.append({"@eq": {"category": category}})
    if language:
        conditions.append({"@eq": {"language": language}})
    if framework:
        conditions.append({"@eq": {"framework": framework}})
    if repo_name:
        conditions.append({"@eq": {"repo_name": repo_name}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"@and": conditions}


def main():
    parser = argparse.ArgumentParser(description="Search the pattern catalog")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--language", help="Filter by language")
    parser.add_argument("--framework", help="Filter by framework")
    parser.add_argument("--repo-name", help="Filter by repo name")
    parser.add_argument("--max-complexity", type=int, help="Maximum complexity score (1-5)")
    parser.add_argument("--limit", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--connection", default=None, help="Snowflake connection name")
    args = parser.parse_args()

    conn_name = args.connection or os.getenv("SNOWFLAKE_CONNECTION_NAME") or "default"

    conn = connect(connection_name=conn_name)
    try:
        root = Root(conn)
        svc = (
            root
            .databases["PATTERN_IQ"]
            .schemas["PUBLIC"]
            .cortex_search_services["PATTERN_SEARCH_SVC"]
        )

        columns = [
            "pattern_id", "pattern_name", "category", "description",
            "abstracted_code", "source_repo_link", "repo_name",
            "complexity_score", "dependencies", "dependency_graph",
            "synthetic_queries", "usage_notes", "tags",
            "language", "framework",
        ]

        search_filter = build_filter(
            category=args.category,
            language=args.language,
            framework=args.framework,
            repo_name=args.repo_name,
        )

        kwargs = {
            "query": args.query,
            "columns": columns,
            "limit": args.limit,
        }
        if search_filter:
            kwargs["filter"] = search_filter

        resp = svc.search(**kwargs)
        results = json.loads(resp.to_json())

        if args.max_complexity and "results" in results:
            results["results"] = [
                r for r in results["results"]
                if r.get("complexity_score") is None or r.get("complexity_score") <= args.max_complexity
            ]

        print(json.dumps(results, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
