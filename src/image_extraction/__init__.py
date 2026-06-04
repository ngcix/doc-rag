"""Image Extraction module using PyMuPDF full-page extraction."""
from typing import Optional

# Import config from settings
from src.config.settings import ImageExtractionConfig
from src.image_extraction.image_info import ExtractedImage
import src.image_extraction.extractor as pymupdf_fullpage

__all__ = [
    # Image extraction
    "ExtractedImage",
    "ImageExtractionConfig",
    "get_image_extractor",
]

def get_image_extractor(force_new: bool = False, image_format: Optional[str] = None):
    return pymupdf_fullpage.get_image_extractor(force_new=force_new, image_format=image_format)

def get_vectorization_data(images: list[ExtractedImage]) -> list[dict]:
    """
    Prepare extracted images for vectorization.

    Args:
        images: List of ExtractedImage objects.

    Returns:
        List of dicts ready for vectorization.
    """
    data = []
    for img in images:
        data.append(
            {
                "chunk_id": img.image_id,
                "content": img.get_vectorization_text(),
                "metadata": {
                    "type": "extracted_image",
                    "region_type": img.region_type,
                    "image_path": img.image_path,
                    "source_file": img.source_file,
                    "page_number": img.page_number,
                    "bbox": str(img.bbox),
                    "tags": img.tags,
                    # Store original tags separately for reset capability
                    "original_tags": img.tags,
                    # User-added tags (initially empty)
                    "user_tags": "",
                },
                "source_file": img.source_file,
            }
        )
    return data
