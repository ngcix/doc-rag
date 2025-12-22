"""Image Extraction module using PyMuPDF and PaddleOCR PP-Structure."""
# from .extractor import (
#     ImageExtractor,
#     ExtractedImage,
#     get_image_extractor,
# )

# Import config from settings
from config.settings import ImageExtractionConfig
import extractor
import extractor_docling

__all__ = [
    # Image extraction
    "ImageExtractor",
    "ExtractedImage",
    "ImageExtractionConfig",
    "get_image_extractor",
]

def get_image_extractor(mode):
    if mode == "fp":
        return extractor.get_image_extractor()
    if mode == "dl":
        return extractor_docling.get_image_extractor()
    return None # Should not happen
