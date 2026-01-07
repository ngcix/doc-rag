import fitz

from PIL import Image, ImageDraw
from tqdm import tqdm
from enum import Enum
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor

from .model import MyModel


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


class MyPage:
    fitz_page: fitz.Page
    page_num: int
    image_path: str
    image_size: tuple
    item_list: List[MyItem]
    picture_list: List[MyItem]

    def __init__(self, fitz_page=None, page_num=0):
        self.fitz_page = fitz_page
        self.page_num = page_num
        self.item_list = []
        self.picture_list = []

    def save_to_image(self, path: Path, base_name, dpi):
        """Do not store the pil_image in the object because memory is not enough"""
        pix = self.fitz_page.get_pixmap(dpi=dpi)
        pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore
        self.image_path = path / f"{base_name}_p{self.page_num}.png"
        pil_image.save(self.image_path, "PNG")
        self.image_size = pil_image.size

    def predict_items(self, model: MyModel):
        image = Image.open(self.image_path)
        for result in model.predict(image):
            for score, label_id, box in zip(result["scores"], result["labels"], result["boxes"]):
                score = round(score.item(), 2)
                box_coords = [round(i, 2) for i in box.tolist()]
                self.item_list.append(MyItem(page_num=self.page_num, label=Label(label_id.item()), box=box_coords, score=score))

        for item in self.item_list:
            if item.label in [Label.Text, Label.SectionHeader, Label.ListItem, Label.Title, Label.Picture, Label.Table, Label.Caption]:
                self._extract_text_from_page_region(item)
            if item.label == Label.Picture:
                self.picture_list.append(item)

    def _extract_text_from_page_region(self, item: MyItem):
        try:
            page_rect = self.fitz_page.rect
            page_width = page_rect.width
            page_height = page_rect.height

            img_width, img_height = self.image_size
            scale_x = page_width / img_width
            scale_y = page_height / img_height

            x1, y1, x2, y2 = item.box
            pdf_x1 = x1 * scale_x
            pdf_y1 = y1 * scale_y
            pdf_x2 = x2 * scale_x
            pdf_y2 = y2 * scale_y

            text_rect = fitz.Rect(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
            item.text = self.fitz_page.get_text(clip=text_rect).strip()

        except Exception as e:
            print(f"Error extract text from page {self.page_num}:\n\t{e}")

    def crop_pictures(self, output_dir: Path, file_name: str):
        image = Image.open(self.image_path)
        for i, pic in enumerate(self.picture_list):
            cropped = image.crop(pic.box)
            image_path = output_dir / f"{file_name}_p{self.page_num}_{i}"
            pic.path = image_path.__str__()
            cropped.save(image_path, "PNG")

    def draw_bboxes(self, output_dir: Path, file_name: str):
        image = Image.open(self.image_path).convert("RGB")
        draw = ImageDraw.Draw(image)

        for item in self.item_list:
            x1, y1, x2, y2 = item.box
            color = "red" if item.label == Label.Picture else "blue"
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            draw.text((x1, y1 - 12), item.label.name, fill=color)

        output_path = output_dir / f"{file_name}_p{self.page_num}.png"
        image.save(output_path)


class MyDocument:
    page_count: int
    file_name: str
    fitz_doc: fitz.Document
    pages: List[MyPage]

    def __init__(self):
        pass

    def open(self, file_path: Path):
        self.file_name = file_path.stem
        self.fitz_doc = fitz.open(file_path)
        self.pages = []
        for i in range(len(self.fitz_doc)):
            self.pages.append(MyPage(fitz_page=self.fitz_doc[i], page_num=i + 1))
        self.page_count = len(self.pages)

    def close(self):
        self.pages = []
        self.fitz_doc.close()

    def convert_pages_to_images_parallel(self, path, model: MyModel):
        batch_size = min(model.max_workers, self.page_count)

        with tqdm(total=self.page_count, desc="Converting pages") as pbar:
            for i in range(0, self.page_count, batch_size):
                current_batch_nums = range(i, min(i + batch_size, self.page_count))

                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    futures = [executor.submit(self.pages[p].save_to_image, path, self.file_name, model.dpi) for p in current_batch_nums]

                    for future in futures:
                        future.result()
                        pbar.update(1)

    def process_pages(self, model: MyModel):
        if model.device_name == "cpu":
            self._predict_pages_parallel(model)
        else:
            self._predict_pages_gpu(model)

    def _predict_pages_parallel(self, model: MyModel):
        batch_size = min(model.max_workers, self.page_count)

        with tqdm(total=self.page_count, desc="Predicting pages") as pbar:
            for i in range(0, self.page_count, batch_size):
                current_batch_nums = range(i, min(i + batch_size, self.page_count))

                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    futures = [executor.submit(self.pages[p].predict_items, model) for p in current_batch_nums]

                    for future in futures:
                        future.result()
                        pbar.update(1)

    def _predict_pages_gpu(self, model: MyModel):
        with tqdm(total=self.page_count, desc="Processing layouts") as pbar:
            for page in self.pages:
                page.predict_items(model)
                pbar.update(1)

    def crop_pictures(self, output_dir: Path):
        with tqdm(total=self.page_count, desc="Processing layouts") as pbar:
            for page in self.pages:
                page.crop_pictures(output_dir, self.file_name)
                pbar.update(1)

    def draw_bbox(self, output_dir: Path):
        with tqdm(total=self.page_count, desc="Drawing bbox") as pbar:
            for page in self.pages:
                page.draw_bboxes(output_dir, self.file_name)
                pbar.update(1)
