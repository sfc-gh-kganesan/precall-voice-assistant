"""
Utility functions for document extraction.
"""

from pathlib import Path


def extract_text_from_file(file_path: Path) -> str:
    """
    Extract text content from a .txt file.

    Args:
        file_path: Path to the text file to extract.

    Returns:
        The text content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a .txt file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() != ".txt":
        raise ValueError(f"Expected a .txt file, got: {file_path.suffix}")

    return file_path.read_text(encoding="utf-8")
