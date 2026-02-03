"""
Utility functions for document extraction.
"""

from pathlib import Path
import json


def extract_content_from_file(file_path: Path) -> str:
    """
    Extract content from a file.

    Args:
        file_path: Path to the file to extract.

    Returns:
        The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a .txt or .json file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() not in [".txt", ".json" ]:
        raise ValueError(f"Expected a .txt, .json file, got: {file_path.suffix}")

    if file_path.suffix.lower() == ".txt":
        return file_path.read_text(encoding="utf-8")
    elif file_path.suffix.lower() == ".json":
        with open(file_path, "r") as f:
            return json.load(f)
