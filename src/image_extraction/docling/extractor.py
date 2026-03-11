from typing import List, Tuple
from pathlib import Path

from .document import MyDocument, MyItem, Label
from ..image_info import ExtractedImage


class DoclingExtractorV2:
    def __init__(self, debug: bool = False):
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
        if self.debug:
            doc.open(file_path)
        else:
            doc.open(file_path)
        doc.process_pages()
        doc.remove_unecessary_items()
        doc.crop_pictures(self.pic_dir)

        if self.debug:
            doc.draw_bbox(self.temp_dir)

        return self.process_pictures(doc, file_path._str)

    def process_pictures(self, doc: MyDocument, source_file : str) -> List[ExtractedImage]:
        output = []
        all_items: List[MyItem] = []
        for page in doc.pages:
            for item in page.item_list:
                all_items.append(item)

        all_items.sort(key=lambda item: (item.page_num, item.box[1], item.box[0]))
        picture_indices = {
            i: item for i, item in enumerate(all_items) if item.label in [Label.Picture , Label.Table] 
        }

        for pic_idx, pic_item in picture_indices.items():
            before_text = self._collect_surrounding_text(
                all_items, pic_idx, direction=-1
            )
            after_text = self._collect_surrounding_text(all_items, pic_idx, direction=1)
            caption = self._find_caption(all_items, pic_idx, pic_item.page_num)
            surrounding_text = ". ".join(before_text + after_text).strip()
            if pic_item.text:
                surrounding_text += ". " + pic_item.text

            output.append(
                ExtractedImage(
                    image_id=Path(pic_item.path).stem,
                    image_path=pic_item.path,
                    source_file=source_file,
                    page_number=pic_item.page_num,
                    bbox=pic_item.box,
                    region_type="docling",
                    surrounding_text=surrounding_text,
                    caption=caption,
                    description=f"Picture from {doc.file_name}, page {pic_item.page_num}",
                    tags=caption
                )
            )
        return output

    def _collect_surrounding_text(
        self, all_items: List[MyItem], start_idx: int, direction: int
    ) -> List[str]:
        stop_labels = {Label.Table, Label.Picture, Label.SectionHeader, Label.Title}
        texts = []
        idx = start_idx + direction
        length = 0
        while 0 <= idx < len(all_items):
            item = all_items[idx]
            if item.label in stop_labels or (
                item.label == Label.Caption and direction == -1
            ):
                break  # Stop if hit table, another picture, or header
            if item.text:  # Only add if has text
                texts.append(item.text)
                length = length + 1
                if length == 5:
                    break
            idx += direction

        if direction == -1:
            texts.reverse()  # Reverse before-text to maintain order
        return texts

    def _find_caption(self, all_items: List[MyItem], start_idx: int, page: int) -> str:
        idx = start_idx
        while idx < len(all_items):
            item = all_items[idx]
            if item.label == Label.Caption:
                return item.text
            if item.page_num != page:
                break
            idx += 1
        return "No caption"
