import os
from src.image_extraction import get_image_extractor

def test_extractor_creation():
    extractor = get_image_extractor("dl")
    assert extractor is not None

def test_extraction_pdf():
    extractor = get_image_extractor("dl")
    test_file = os.path.join(os.getcwd(), "data/test.pdf")
    extractor.extract_from_file(test_file)
    assert True is True
