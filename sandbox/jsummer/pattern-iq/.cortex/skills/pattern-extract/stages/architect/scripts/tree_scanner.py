#!/usr/bin/env python3
"""
tree_scanner.py -- Scan a repository's file structure and project metadata.

Usage:
    python tree_scanner.py <repo_path> [--project-root <path>] [--output <path>] [--summary]
"""

import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist",
    ".tox", ".mypy_cache", ".ruff_cache", "egg-info", ".pytest_cache",
}

SCAN_EXTS = {
    ".py", ".sql", ".yml", ".yaml", ".toml", ".json", ".md",
    ".tsx", ".ts", ".jsx", ".js",
    ".jinja",
}

SCAN_FILENAMES = {
    "Dockerfile",
}


def read_lines(path, max_lines=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if max_lines:
                return [f.readline() for _ in range(max_lines)]
            return f.readlines()
    except Exception:
        return []


def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def extract_head(path, ext):
    if ext == ".py":
        lines = read_lines(path, max_lines=10)
        return "".join(lines).strip()
    lines = read_lines(path, max_lines=5)
    return "".join(lines).strip()


def parse_requirements_txt(path):
    deps = []
    for line in read_lines(path):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            name = re.split(r"[>=<!\[;]", line)[0].strip()
            if name:
                deps.append(name)
    return deps


def parse_pyproject_toml(path):
    deps = []
    content = "".join(read_lines(path))
    match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if match:
        for item in re.findall(r'"([^"]+)"', match.group(1)):
            name = re.split(r"[>=<!\[;]", item)[0].strip()
            if name:
                deps.append(name)
    return deps


def parse_package_json(path):
    deps = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in ("dependencies", "devDependencies"):
            if key in data and isinstance(data[key], dict):
                deps.extend(data[key].keys())
    except Exception:
        pass
    return deps


def read_readme(repo_path, max_chars=500):
    for name in ("README.md", "readme.md", "README.rst", "README.txt"):
        p = os.path.join(repo_path, name)
        if os.path.isfile(p):
            content = "".join(read_lines(p))
            return content[:max_chars]
    return ""


def collect_dependencies(repo_path):
    deps = []
    req = os.path.join(repo_path, "requirements.txt")
    if os.path.isfile(req):
        deps.extend(parse_requirements_txt(req))
    pyproj = os.path.join(repo_path, "pyproject.toml")
    if os.path.isfile(pyproj):
        deps.extend(parse_pyproject_toml(pyproj))
    pkgjson = os.path.join(repo_path, "package.json")
    if os.path.isfile(pkgjson):
        deps.extend(parse_package_json(pkgjson))
    return sorted(set(deps))


def scan_tree(repo_path, project_root=None):
    abs_root = os.path.abspath(repo_path)
    abs_project_root = os.path.abspath(project_root) if project_root else abs_root

    files = []
    for dirpath, dirnames, filenames in os.walk(abs_root):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.endswith(".egg-info")
        ]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SCAN_EXTS and fname not in SCAN_FILENAMES:
                continue
            fullpath = os.path.join(dirpath, fname)
            relpath = os.path.relpath(fullpath, abs_project_root)
            files.append({
                "path": relpath,
                "ext": ext,
                "line_count": count_lines(fullpath),
                "head": extract_head(fullpath, ext),
            })

    dependencies = collect_dependencies(abs_root)
    readme = read_readme(abs_root)

    return {"files": files, "dependencies": dependencies, "readme": readme}


def summarize(result):
    return {
        "files": [
            {"path": f["path"], "ext": f["ext"], "line_count": f["line_count"]}
            for f in result["files"]
        ],
        "dependencies": result["dependencies"],
        "readme": result["readme"],
    }


def main():
    parser = argparse.ArgumentParser(description="Scan repository file structure and metadata")
    parser.add_argument("repo_path", help="Path to the repository to scan")
    parser.add_argument("--project-root", help="Git repo root for relative paths")
    parser.add_argument("--output", metavar="PATH", help="Write full JSON to file")
    parser.add_argument("--summary", action="store_true", help="Print compact JSON (no head) to stdout")
    args = parser.parse_args()

    if not os.path.isdir(args.repo_path):
        print(f"Error: {args.repo_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = scan_tree(args.repo_path, project_root=args.project_root)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")

    if args.summary:
        json.dump(summarize(result), sys.stdout, indent=2)
        print()
    elif not args.output:
        json.dump(result, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
