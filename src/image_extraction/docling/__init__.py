from .document import MyDocument
from .extractor import DoclingExtractorV2

__all__ = ["MyDocument", "DoclingExtractorV2"]


_extractor = None


def get_image_extractor():
    global _extractor
    if _extractor is None:
        _extractor = DoclingExtractorV2()
    return _extractor
