#!/usr/bin/env python3
"""
file_reader.py -- Read high-utility files grouped by domain from an architect manifest.

Usage:
    python file_reader.py --manifest <path> --repo-root <path> [--threshold high] [--output <path>]
"""

import argparse
import json
import os
import sys

CONTEXT_BUDGET = 60000

UTILITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def passes_threshold(score, threshold):
    if threshold == "all":
        return True
    if threshold == "medium":
        return score in ("high", "medium")
    return score == "high"


def read_file_content(repo_root, relpath):
    fullpath = os.path.join(repo_root, relpath)
    try:
        with open(fullpath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def process_domain(domain, repo_root, threshold):
    files = [f for f in domain.get("files", []) if passes_threshold(f.get("utility_score", "low"), threshold)]
    files.sort(key=lambda f: UTILITY_ORDER.get(f.get("utility_score", "low"), 2))

    result_files = []
    budget_remaining = CONTEXT_BUDGET
    truncated_count = 0

    for f in files:
        if budget_remaining <= 0:
            result_files.append({
                "path": f["path"],
                "content": None,
                "utility_score": f.get("utility_score", "low"),
                "line_count": f.get("line_count", 0),
                "truncated": True,
            })
            truncated_count += 1
            continue

        content = read_file_content(repo_root, f["path"])
        if content is None:
            continue

        if len(content) > budget_remaining:
            content = content[:budget_remaining]
            budget_remaining = 0
        else:
            budget_remaining -= len(content)

        result_files.append({
            "path": f["path"],
            "content": content,
            "utility_score": f.get("utility_score", "low"),
            "line_count": f.get("line_count", 0),
            "truncated": False,
        })

    return {
        "name": domain.get("name", "unknown"),
        "files": result_files,
        "truncated_count": truncated_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Read high-utility files grouped by domain")
    parser.add_argument("--manifest", required=True, help="Path to architect manifest JSON")
    parser.add_argument("--repo-root", required=True, help="Root directory to resolve file paths")
    parser.add_argument("--threshold", default="high", choices=["high", "medium", "all"], help="Minimum utility score")
    parser.add_argument("--output", metavar="PATH", help="Write output JSON to file")
    args = parser.parse_args()

    if not os.path.isfile(args.manifest):
        print(f"Error: {args.manifest} not found", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.repo_root):
        print(f"Error: {args.repo_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(args.manifest)
    domains = manifest.get("domains", [])

    result = {
        "domains": [process_domain(d, args.repo_root, args.threshold) for d in domains]
    }

    result["domains"] = [d for d in result["domains"] if d["files"]]

    output_json = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
            f.write("\n")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
