from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractedImage:
    """Represents an extracted image region from a document."""

    image_id: str
    image_path: str
    source_file: str
    page_number: int
    bbox: tuple  # (x1, y1, x2, y2)
    region_type: str  # "figure", "table", "chart", etc.
    surrounding_text: str = ""
    caption: str = ""
    description: str = ""
    tags: str = ""  # Keywords extracted from context

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "image_path": self.image_path,
            "source_file": self.source_file,
            "page_number": self.page_number,
            "bbox": self.bbox,
            "region_type": self.region_type,
            "surrounding_text": self.surrounding_text,
            "caption": self.caption,
            "description": self.description,
        }

    def get_vectorization_text(self) -> str:
        """Generate text for vectorization."""
        parts = []
        if self.caption:
            parts.append(f"Caption: {self.caption}")
        if self.tags:
            # Repeat tags many times to strongly boost importance in vector
            # This helps exact-match tags rank higher than semantic-only matches
            tag_boost = ", ".join([self.tags] * 10)
            parts.append(f"Tags: {tag_boost}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.surrounding_text:
            parts.append(f"Context: {self.surrounding_text}")
        parts.append(f"Type: {self.region_type}")
        parts.append(f"Source: {Path(self.source_file).name}, Page {self.page_number}")
        return "\n".join(parts)
