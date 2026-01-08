from pathlib import Path
from .extractor import DoclingExtractorV2

if __name__ == "__main__":
    e = DoclingExtractorV2(debug=True)
    file_dir = Path(__file__).resolve().parents[3]
    # test_file = file_dir / "data/documents/HID_v1.1.1._pdf"
    test_file = file_dir / "data/documents/A2DP_v1.4.1.pdf"
    output = e.extract_from_file(test_file)
    # for item in output:
    #     print("_" * 100)
    #     print(item)
