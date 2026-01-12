"""Image Extraction module using PyMuPDF and PaddleOCR PP-Structure."""
# from .extractor import (
#     ImageExtractor,
#     ExtractedImage,
#     get_image_extractor,
# )

# Import config from settings
from config.settings import ImageExtractionConfig
from src.image_extraction.image_info import ExtractedImage
import src.image_extraction.extractor as paddle
import src.image_extraction.docling as docling
import src.image_extraction.docling_extractor as doclingv1
import src.image_extraction.pymu_extractor as pymu

__all__ = [
    # Image extraction
    "ImageExtractor",
    "ExtractedImage",
    "ImageExtractionConfig",
    "get_image_extractor",
]

def get_image_extractor(mode, force_new: bool = False, image_format: str = None):
    if mode == "fp":
        return paddle.get_image_extractor(force_new=force_new, image_format=image_format)
    if mode == "dl":
        return docling.get_image_extractor()
    if mode == "dl1":
        return doclingv1.get_image_extractor()
    if mode == "pymu":
        return pymu.get_image_extractor()
    return None  # Should not happen

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
                },
                "source_file": img.source_file,
            }
        )
    return data

