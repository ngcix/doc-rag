import fitz

from PIL import Image, ImageDraw
from tqdm import tqdm
from enum import Enum
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor

from .model import get_model
from .processor import get_processor


class Label(Enum):
    Caption = 0
    Footnote = 1
    Formula = 2
    ListItem = 3
    PageFooter = 4
    PageHeader = 5
    Picture = 6
    SectionHeader = 7
    Table = 8
    Text = 9
    Title = 10
    DocumentIndex = 11
    Code = 12
    CheckboxSelected = 13
    CheckboxUnselected = 14
    Form = 15
    KeyValueRegion = 16
    Icon = 17


class MyItem:
    page_num: int
    label: Label
    text: str
    box: Tuple[int, int, int, int]
    score: float
    path: str  # for pictures save

    def __init__(self, page_num=0, label=Label.Text, box=(0, 0, 0, 0), score=0.0):
        self.page_num = page_num
        self.label = label
        self.text = ""
        self.box = box
        self.score = score
        self.path = ""

    def gap_y(self, item) -> bool:
        _, y1, _, y2 = self.box
        _, _y1, _, _y2 = item.box
        return (
            (y1 <= _y1 <= y2)
            or (y1 <= _y2 <= y2)
            or (_y1 <= y1 <= _y2)
            or (_y1 <= y2 <= _y2)
        )


class MyPage:
    fitz_page: fitz.Page
    page_num: int
    image_path: str
    item_list: List[MyItem]
    picture_list: List[MyItem]

    def __init__(self, fitz_page=None, page_num=0):
        self.fitz_page = fitz_page
        self.page_num = page_num
        self.item_list = []
        self.picture_list = []

    def predict_items(self):
        model = get_model()
        pix = self.fitz_page.get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore
        for result in model.predict(image):
            for score, label_id, box in zip(
                result["scores"], result["labels"], result["boxes"]
            ):
                score = round(score.item(), 2)
                box_coords = [round(i, 2) for i in box.tolist()]
                self.item_list.append(
                    MyItem(
                        page_num=self.page_num,
                        label=Label(label_id.item()),
                        box=box_coords,
                        score=score,
                    )
                )
        # self.resolve_gap_items()
        for item in self.item_list:
            if item.label in [
                Label.Text,
                Label.SectionHeader,
                Label.ListItem,
                Label.Title,
                Label.Picture,
                Label.Table,
                Label.Caption,
            ]:
                self._extract_text_from_page_region(item)
            if item.label in [Label.Picture, Label.Table]:
                self.picture_list.append(item)

    def _extract_text_from_page_region(self, item: MyItem):
        try:
            x1, y1, x2, y2 = item.box

            text_rect = fitz.Rect(x1, y1, x2, y2)
            item.text = self.fitz_page.get_text(clip=text_rect).strip()
            if item.label not in [Label.Picture, Label.Table]:
                item.text = item.text.replace("\n", "").strip()
            else:
                item.text = item.text.replace("\n", ".").strip()

        except Exception as e:
            print(f"Error extract text from page {self.page_num}:\n\t{e}")

    def crop_pictures(self, output_dir: Path, file_name: str, dpi: int = 160):
        pix = self.fitz_page.get_pixmap(dpi=dpi)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore
        for i, pic in enumerate(self.picture_list):
            x1, y1, x2, y2 = self._get_scaled_box(pic, image.size)
            pic.image = image.crop((x1 - 2, y1 - 2, x2 + 2, y2 + 2))
            image_path = output_dir / f"{file_name}_p{self.page_num}_{i}.png"
            pic.path = image_path.__str__()
            pic.image.save(image_path, "PNG")

    def draw_bboxes(self, output_dir: Path, file_name: str):
        pix = self.fitz_page.get_pixmap(dpi=160)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore
        draw = ImageDraw.Draw(image)

        for item in self.item_list:
            x1, y1, x2, y2 = self._get_scaled_box(item, image.size)
            color = "red" if item.label in [Label.Picture, Label.Table] else "blue"
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            draw.text((x1, y1 - 12), f"{item.label.name} {item.score}", fill=color)

        output_path = output_dir / f"{file_name}_p{self.page_num}.png"
        image.save(output_path)

    def _get_scaled_box(self, item: MyItem, image_size: tuple):
        x1, y1, x2, y2 = item.box

        img_width, img_height = image_size
        page_rect = self.fitz_page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        scale_x = img_width / page_width
        scale_y = img_height / page_height
        x1 = x1 * scale_x
        y1 = y1 * scale_y
        x2 = x2 * scale_x
        y2 = y2 * scale_y

        return x1, y1, x2, y2

    def is_icon_image(self, item: MyItem):
        """We need the scale, so this function must be put here"""
        x1, y1, x2, y2 = item.box
        size_x = x2 - x1
        size_y = y2 - y1

        # loc_x = x1 * 100 / self.page_width
        # loc_y = y1 * 100 / self.page_height
        # print(f"size=({size_x} x {size_y}) \t loc=({loc_x, loc_y})")

        for it in self.item_list:
            if it.label in [Label.PageFooter, Label.PageHeader] and item.gap_y(it):
                return True

        return size_x <= 5 and size_y <= 5

    def resolve_gap_items(self):
        # print(f"Page {self.page_num}:")
        for item in self.item_list:
            _x1, _y1, _x2, _y2 = item.box
            # print(f"({_y1} {_x1})")
            pass

    def delete_image(self):
        image_file = Path(self.image_path)
        try:
            image_file.unlink()
        except FileNotFoundError:
            pass
        except PermissionError:
            pass


class MyDocument:
    page_count: int
    file_name: str
    fitz_doc: fitz.Document
    pages: List[MyPage]

    def __init__(self):
        pass

    def open(self, file_path: Path, max_page=2**32):
        self.file_name = file_path.stem
        self.fitz_doc = fitz.open(file_path)
        self.pages = []
        for i in range(len(self.fitz_doc)):
            self.pages.append(MyPage(fitz_page=self.fitz_doc[i], page_num=i + 1))
        self.page_count = min(len(self.pages), max_page)

    def close(self):
        for page in self.pages:
            page.delete_image()
        self.pages = []
        self.fitz_doc.close()

    def process_pages(self):
        desc = "Predicting pages"
        model = get_model()
        if model.device_name == "cpu":
            get_processor().run_parallel(
                desc, lambda p: self.pages[p].predict_items(), self.page_count
            )
        else:
            get_processor().run_sequential(
                desc, lambda p: self.pages[p].predict_items(), self.page_count
            )

    def crop_pictures(self, output_dir: Path):
        get_processor().run_sequential(
            "Cropping",
            lambda p: self.pages[p].crop_pictures(output_dir, self.file_name),
            self.page_count,
        )

    def draw_bbox(self, output_dir: Path):
        get_processor().run_sequential(
            "Drawing bbox",
            lambda p: self.pages[p].draw_bboxes(output_dir, self.file_name),
            self.page_count,
        )

    def remove_unecessary_items(self):
        """Remove if icon repeat in many page or too small or in the same location"""
        self.pictures = []
        for i in range(self.page_count):
            page = self.pages[i]
            page.resolve_gap_items()
            icons = []
            for p in page.picture_list:
                if page.is_icon_image(p):
                    icons.append(p)
            for ic in icons:
                page.picture_list.remove(ic)
                page.item_list.remove(ic)

            self.pictures.extend(page.picture_list)
