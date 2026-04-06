#!/usr/bin/env python3
"""
merge_batches.py -- Merge batch result files into a single pattern-cards JSON file.

Usage:
    python merge_batches.py --batch-dir /tmp --output /tmp/pattern-cards.json

Reads all files matching /tmp/distiller-batch-*-result.json, validates each is
a JSON array of pattern cards, deduplicates by pattern_name, and writes the
merged output.
"""

import argparse
import glob
import json
import sys


def load_batch_files(batch_dir):
    """Find and load all batch result files."""
    pattern = f"{batch_dir}/distiller-batch-*-result.json"
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"ERROR: No batch result files found matching {pattern}", file=sys.stderr)
        sys.exit(1)

    all_cards = []
    for path in files:
        print(f"Reading {path}...")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"WARNING: {path} is not a JSON array, skipping", file=sys.stderr)
            continue
        print(f"  {len(data)} cards")
        all_cards.extend(data)

    return all_cards, files


def deduplicate(cards):
    """Deduplicate by pattern_name, keeping the first occurrence."""
    seen = set()
    unique = []
    dupes = 0
    for card in cards:
        name = card.get("pattern_name", "")
        if name in seen:
            dupes += 1
            continue
        seen.add(name)
        unique.append(card)
    if dupes:
        print(f"Removed {dupes} duplicate(s) by pattern_name")
    return unique


def validate_cards(cards):
    """Basic validation of required fields."""
    required = ["pattern_name", "category", "description", "abstracted_code"]
    issues = 0
    for i, card in enumerate(cards):
        missing = [f for f in required if not card.get(f)]
        if missing:
            name = card.get("pattern_name", f"card[{i}]")
            print(f"WARNING: {name} missing fields: {missing}", file=sys.stderr)
            issues += 1
    return issues


def main():
    parser = argparse.ArgumentParser(description="Merge batch pattern extraction results")
    parser.add_argument("--batch-dir", required=True, help="Directory containing batch result files")
    parser.add_argument("--output", required=True, help="Output path for merged pattern cards")
    args = parser.parse_args()

    cards, files = load_batch_files(args.batch_dir)
    print(f"\nLoaded {len(cards)} total cards from {len(files)} batch file(s)")

    cards = deduplicate(cards)
    issues = validate_cards(cards)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2)

    print(f"\nWrote {len(cards)} cards to {args.output}")
    if issues:
        print(f"  ({issues} card(s) with validation warnings)")


if __name__ == "__main__":
    main()
