import os
from src.image_extraction import get_image_extractor


def test_extractor_creation():
    extractor = get_image_extractor("dl")
    assert extractor is not None

def _test_extraction_pdf():
    extractor = get_image_extractor("dl")
    test_file = os.path.join(os.getcwd(), "data/documents/test.pdf")
    extractor.extract_from_file(test_file)
    assert True is True

def test_surround_text_extraction():
    extractor = get_image_extractor("dl")
    test_file = os.path.join(os.getcwd(), "data/documents/A2DP_v1.4.1.pdf.json")
    extractor.extract_from_json(test_file)
