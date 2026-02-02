"""
Document Parser - Standalone content parsing with OCR and bounding boxes.

Usage:
    from document_parser import parse_document

    result = parse_document("invoice.pdf")
    print(result.full_text)
    print(result.words)  # List of words with bounding boxes
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from .parser import parse_document, parse_document_dict
from .schemas import DocumentContent, Word, Line, BoundingBox, PageDimensions

__all__ = [
    "parse_document",
    "parse_document_dict",
    "DocumentContent",
    "Word",
    "Line",
    "BoundingBox",
    "PageDimensions",
]

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False, show_path=False)],
    )


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="document-parser",
        description="Extract text and bounding boxes from PDF documents",
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the PDF file to parse",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output JSON file path (default: stdout)",
    )
    parser.add_argument(
        "--dpi",
        type=str,
        default="300,600",
        help="Comma-separated DPI values for OCR (default: 300,600)",
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Skip OCR and use only PyMuPDF extraction",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Output only the extracted text (no JSON)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    # Validate input
    if not args.pdf_path.exists():
        console.print(f"[red]Error:[/red] File not found: {args.pdf_path}")
        return 1

    if not args.pdf_path.suffix.lower() == ".pdf":
        console.print(f"[yellow]Warning:[/yellow] File may not be a PDF: {args.pdf_path}")

    # Parse DPI values
    try:
        dpi_levels = [int(d.strip()) for d in args.dpi.split(",")]
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid DPI values: {args.dpi}")
        return 1

    # Parse document
    try:
        console.print(f"[blue]Parsing:[/blue] {args.pdf_path}")
        result = parse_document(
            args.pdf_path,
            dpi_levels=dpi_levels,
            skip_ocr=args.skip_ocr,
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if args.verbose:
            console.print_exception()
        return 1

    # Output results
    if args.text_only:
        output = result.full_text
    else:
        output = json.dumps(result.model_dump(), indent=2, default=str)

    if args.output:
        args.output.write_text(output)
        console.print(f"[green]Output written to:[/green] {args.output}")
    else:
        print(output)

    # Print summary
    if not args.text_only:
        console.print(
            f"\n[green]Summary:[/green] {result.page_count} pages, "
            f"{len(result.words)} words, {len(result.lines)} lines"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
