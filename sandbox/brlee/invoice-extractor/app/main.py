"""
CLI entry point for invoice extraction.

Usage:
    python -m app.main extract invoice.pdf [--output results/output.json]
    python -m app.main extract invoice.pdf --no-tables
    python -m app.main batch invoices/ --output results/
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from app.graph import extract_invoice_sync, extract_invoice

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_single(
    pdf_path: str,
    output_path: str = None,
    use_tables: bool = True,
) -> dict:
    """
    Extract data from a single PDF invoice.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Optional path to save JSON output
        use_tables: Whether to use table detection
    
    Returns:
        Extraction result as dict
    """
    logger.info(f"Extracting from: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return {"error": f"File not found: {pdf_path}"}
    
    try:
        result = extract_invoice_sync(
            pdf_path=pdf_path,
            use_table_detection=use_tables,
        )
        
        # Add metadata
        result["_metadata"] = {
            "pdf_path": os.path.abspath(pdf_path),
            "extracted_at": datetime.now().isoformat(),
            "table_detection": use_tables,
        }
        
        # Save to file if output path specified
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to: {output_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


async def extract_batch_async(
    pdf_paths: List[str],
    output_dir: str,
    use_tables: bool = True,
) -> List[dict]:
    """
    Extract data from multiple PDFs concurrently.
    
    Args:
        pdf_paths: List of PDF file paths
        output_dir: Directory to save JSON outputs
        use_tables: Whether to use table detection
    
    Returns:
        List of extraction results
    """
    os.makedirs(output_dir, exist_ok=True)
    
    async def process_one(pdf_path: str) -> dict:
        invoice_id = Path(pdf_path).stem
        try:
            result = await extract_invoice(
                pdf_path=pdf_path,
                invoice_id=invoice_id,
                use_table_detection=use_tables,
            )
            result["_metadata"] = {
                "pdf_path": os.path.abspath(pdf_path),
                "extracted_at": datetime.now().isoformat(),
            }
            
            # Save to file
            output_path = os.path.join(output_dir, f"{invoice_id}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✓ {invoice_id}")
            return result
            
        except Exception as e:
            logger.error(f"✗ {invoice_id}: {e}")
            return {"error": str(e), "pdf_path": pdf_path}
    
    # Process concurrently (but limit concurrency to avoid memory issues)
    results = []
    batch_size = 4
    
    for i in range(0, len(pdf_paths), batch_size):
        batch = pdf_paths[i:i + batch_size]
        batch_results = await asyncio.gather(*[process_one(p) for p in batch])
        results.extend(batch_results)
    
    return results


def extract_batch(
    input_dir: str,
    output_dir: str,
    use_tables: bool = True,
) -> List[dict]:
    """
    Extract data from all PDFs in a directory.
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory to save JSON outputs
        use_tables: Whether to use table detection
    
    Returns:
        List of extraction results
    """
    # Find all PDFs
    pdf_paths = []
    for ext in ["*.pdf", "*.PDF"]:
        pdf_paths.extend(Path(input_dir).glob(ext))
    
    pdf_paths = [str(p) for p in pdf_paths]
    
    if not pdf_paths:
        logger.error(f"No PDF files found in: {input_dir}")
        return []
    
    logger.info(f"Found {len(pdf_paths)} PDF files")
    
    return asyncio.run(extract_batch_async(pdf_paths, output_dir, use_tables))


def main():
    parser = argparse.ArgumentParser(
        description="Invoice data extraction tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract single invoice
  python -m app.main extract invoice.pdf
  
  # Extract with custom output path
  python -m app.main extract invoice.pdf --output results/invoice.json
  
  # Extract without table detection (pure LLM)
  python -m app.main extract invoice.pdf --no-tables
  
  # Batch extract all PDFs in a directory
  python -m app.main batch invoices/ --output results/
""",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract single PDF
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract data from a single PDF invoice",
    )
    extract_parser.add_argument(
        "pdf_path",
        help="Path to the PDF file",
    )
    extract_parser.add_argument(
        "--output", "-o",
        help="Output JSON file path",
    )
    extract_parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Disable table detection (use pure LLM extraction)",
    )
    
    # Batch extract
    batch_parser = subparsers.add_parser(
        "batch",
        help="Extract data from all PDFs in a directory",
    )
    batch_parser.add_argument(
        "input_dir",
        help="Directory containing PDF files",
    )
    batch_parser.add_argument(
        "--output", "-o",
        default="results",
        help="Output directory for JSON files (default: results/)",
    )
    batch_parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Disable table detection (use pure LLM extraction)",
    )
    
    args = parser.parse_args()
    
    if args.command == "extract":
        result = extract_single(
            pdf_path=args.pdf_path,
            output_path=args.output,
            use_tables=not args.no_tables,
        )
        
        # Print summary
        if "error" not in result:
            fields = result.get("fields", {})
            line_items = result.get("line_items", [])
            
            print("\n" + "=" * 60)
            print("EXTRACTION SUMMARY")
            print("=" * 60)
            print(f"Invoice Number: {fields.get('invoice_number', 'N/A')}")
            print(f"Vendor Name:    {fields.get('vendor_name', 'N/A')}")
            print(f"Invoice Date:   {fields.get('invoice_date', 'N/A')}")
            print(f"Total Amount:   {fields.get('total_amount', 'N/A')} {fields.get('currency', '')}")
            print(f"PO Number:      {fields.get('purchase_order_number', 'N/A')}")
            print(f"Line Items:     {len(line_items)}")
            
            confidence = result.get("extraction_confidence", {})
            print(f"Confidence:     {confidence.get('score', 0):.0%}")
            print("=" * 60)
            
            if not args.output:
                print("\nFull output:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\nError: {result.get('error')}")
            sys.exit(1)
    
    elif args.command == "batch":
        results = extract_batch(
            input_dir=args.input_dir,
            output_dir=args.output,
            use_tables=not args.no_tables,
        )
        
        # Print summary
        successful = sum(1 for r in results if "error" not in r)
        failed = len(results) - successful
        
        print("\n" + "=" * 60)
        print("BATCH EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Total:      {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed:     {failed}")
        print(f"Output:     {os.path.abspath(args.output)}")
        print("=" * 60)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

