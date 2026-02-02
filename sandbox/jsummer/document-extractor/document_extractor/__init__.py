"""
Document Extractor - Extract structured data from documents using BAML.

Usage:
    from document_extractor import extract_text_from_file, extract_metadata

    content = extract_text_from_file("document.txt")
    metadata = extract_metadata(content)
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

import os
os.environ["BAML_LOG"] = "error" # To suppress BAML logs

from .run import extract_metadata
from .utility import extract_text_from_file

__all__ = [
    "extract_text_from_file",
    "extract_metadata",
]

console = Console()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="document-extractor",
        description="Extract structured data from text documents",
    )
    parser.add_argument(
        "txt_path",
        type=Path,
        help="Path to the .txt file to extract",
    )

    args = parser.parse_args()

    # Read content from file
    console.print(f"[blue]Reading:[/blue] {args.txt_path}")
    content = extract_text_from_file(args.txt_path)

    # Extract metadata using BAML
    console.print("[blue]Extracting metadata...[/blue]")
    metadata = extract_metadata(content)

    # Output results
    print(metadata.model_dump_json(indent=2))


if __name__ == "__main__":
    sys.exit(main())
