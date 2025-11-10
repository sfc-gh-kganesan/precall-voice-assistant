#!/usr/bin/env python3
"""Schema initialization script for Support Data Agent."""

import argparse
import sys

from app.services.schema_manager import (
    SchemaManager,
    clean_schema,
    initialize_schema,
    reset_schema,
)


def main():
    parser = argparse.ArgumentParser(description="Initialize Support Data Agent schema")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--clean", action="store_true", help="Clean schema (no sample data)")
    group.add_argument("--with-samples", action="store_true", help="Schema with sample data")
    group.add_argument("--reset", action="store_true", help="Drop and recreate schema")
    group.add_argument("--status", action="store_true", help="Check schema status")

    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")

    args = parser.parse_args()

    try:
        if args.status:
            print("Checking schema status...")
            manager = SchemaManager()
            status = manager.get_schema_status()

            print("\nSchema Status:")
            print("-" * 40)
            for table, info in status.items():
                status_icon = "✓" if info["exists"] else "✗"
                print(f"{status_icon} {table:<20} {info['row_count']:>8} rows")

            return

        if args.reset:
            if not args.force:
                confirm = input("This will DROP ALL TABLES. Are you sure? (y/N): ")
                if confirm.lower() != "y":
                    print("Operation cancelled.")
                    return

            print("Resetting schema...")
            include_samples = input("Include sample data? (y/N): ").lower() == "y" if not args.force else False
            result = reset_schema(include_sample_data=include_samples)

        elif args.clean:
            print("Creating clean schema...")
            result = clean_schema()

        elif args.with_samples:
            print("Creating schema with sample data...")
            result = initialize_schema(include_sample_data=True)

        if result.get("success"):
            print("Schema operation completed successfully!")

            manager = SchemaManager()
            status = manager.get_schema_status()
            total_rows = sum(info["row_count"] for info in status.values())
            print(f"Total rows: {total_rows}")

        else:
            print("Schema operation failed!")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
