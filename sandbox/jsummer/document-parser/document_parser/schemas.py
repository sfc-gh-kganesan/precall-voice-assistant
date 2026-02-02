"""
Pydantic models for document parsing output.
"""

from typing import Optional
from pydantic import BaseModel


class BoundingBox(BaseModel):
    """Bounding box coordinates in PDF points."""

    x0: float
    y0: float
    x1: float
    y1: float


class Word(BaseModel):
    """A word extracted from the document with its bounding box."""

    text: str
    bbox: BoundingBox
    page: int
    source: str  # "pymupdf" | "ocr_300" | "ocr_600"
    confidence: int
    block_no: Optional[int] = None
    line_no: Optional[int] = None


class Line(BaseModel):
    """A line of text extracted from the document with its bounding box."""

    text: str
    bbox: BoundingBox
    page: int
    source: str
    block_no: Optional[int] = None
    line_no: Optional[int] = None


class Block(BaseModel):
    """A block of text (paragraph/section) with combined bounding box."""

    text: str
    bbox: BoundingBox
    page: int
    block_no: Optional[int]  # None for ungrouped words
    word_count: int


class PageDimensions(BaseModel):
    """Dimensions of a PDF page in points."""

    width: float
    height: float


class DocumentContent(BaseModel):
    """Complete extracted content from a document."""

    words: list[Word]
    lines: list[Line]
    blocks: list[Block]
    full_text: str
    page_count: int
    page_dimensions: dict[int, PageDimensions]
