"""Image Extraction module using PyMuPDF and PaddleOCR PP-Structure."""
from .extractor import (
    ImageExtractor,
    ExtractedImage,
    get_image_extractor,
)

# Import config from settings
from config.settings import ImageExtractionConfig

__all__ = [
    # Image extraction
    "ImageExtractor",
    "ExtractedImage",
    "ImageExtractionConfig",
    "get_image_extractor",
]
