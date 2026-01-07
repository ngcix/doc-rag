from typing import List
from pathlib import Path
from dataclasses import dataclass

from .document import MyDocument
from .model import MyModel


@dataclass
class ExtractedImage:
    image_id: str
    image_path: str
    source_file: str
    page_number: int
    bbox: tuple
    region_type: str
    surrounding_text: str = ""
    caption: str = ""
    description: str = ""
    tags: str = ""

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
            "tags": self.tags,
        }


class DoclingExtractorV2:
    def __init__(self, threshold: float = 0.6, dpi: int = 120, max_workers: int = None, debug: bool = False):
        self.model = MyModel(threshold=threshold, dpi=dpi, max_workers=max_workers)
        self.debug = debug

        file_dir = Path(__file__).resolve().parents[3]
        self.output_dir = file_dir / "data"
        self.temp_dir = self.output_dir / "temp"
        self.pic_dir = self.output_dir / "extracted_images"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.pic_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_file(self, file_path: Path, **kwargs) -> List[ExtractedImage]:
        doc = MyDocument()
        doc.open(file_path)
        doc.convert_pages_to_images_parallel(self.temp_dir, self.model)
        doc.process_pages(self.model)
        doc.crop_pictures(self.pic_dir)

        if self.debug:
            doc.draw_bbox(self.temp_dir)

        return self.process_pictures(doc)

    def process_pictures(self, doc: MyDocument) -> List[ExtractedImage]:
        # TODO: process images context here
        return []
