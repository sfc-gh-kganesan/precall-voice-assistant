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

from dotenv import load_dotenv
from rich.console import Console

import os
load_dotenv()
os.environ["BAML_LOG"] = "error" # To suppress BAML logs

from .run import content_blocks_extract
from .utility import extract_content_from_file

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
        "file_path",
        type=Path,
        help="Path to the file to extract",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )

    args = parser.parse_args()

    # Read content from file
    console.print(f"[blue]Reading:[/blue] {args.file_path}")
    content = extract_content_from_file(args.file_path)

    # Extract metadata using BAML
    console.print("[blue]Extracting metadata...[/blue]")
    metadata = content_blocks_extract(content)

    # Output results
    if args.output:
        args.output.write_text(metadata.model_dump_json(indent=2))
        console.print(f"[green]Output written to:[/green] {args.output}")
    else:
        print(metadata.model_dump_json(indent=2))


if __name__ == "__main__":
    sys.exit(main())
