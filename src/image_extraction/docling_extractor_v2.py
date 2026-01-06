import fitz  # PyMuPDF
import torch
import os

from tqdm import tqdm
from fitz import Pixmap
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor
from PIL import Image, ImageDraw
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

try:
    from src.image_extraction.image_info import ExtractedImage  # type: ignore
except ImportError:
    try:
        from image_info import ExtractedImage  # type: ignore
    except ImportError:
        # Fallback definition
        from dataclasses import dataclass

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

            def to_dict(self) -> Dict[str, Any]:
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


class ImageExtractor:
    def __init__(self):
        cores = int(os.cpu_count())  # type: ignore
        self.max_workers = int(cores / 2)
        self.threshold = 0.6
        self.dpi = 120
        self.current_page_image_list = []
        self.extracted_image_list = []
        self.extracted_item_list = []
        self.page_size_list = []

        self.output_dir = self._setup_directories()
        self.images_dir = os.path.join(self.output_dir, "extracted_images")
        self.temp_dir = os.path.join(self.output_dir, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.classes_map = {
            0: "Caption",
            1: "Footnote",
            2: "Formula",
            3: "List-item",
            4: "Page-footer",
            5: "Page-header",
            6: "Picture",
            7: "Section-header",
            8: "Table",
            9: "Text",
            10: "Title",
            11: "Document Index",
            12: "Code",
            13: "Checkbox-Selected",
            14: "Checkbox-Unselected",
            15: "Form",
            16: "Key-Value Region",
        }

        self.device_name = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(self.device_name)

        model_path = Path(__file__).parent.parent.parent / "models" / "docling-project--docling-layout-heron"
        self.processor = RTDetrImageProcessor.from_pretrained(model_path)
        model = RTDetrV2ForObjectDetection.from_pretrained(model_path)
        self.model = model.to(self.device)  # type: ignore
        model.eval()

        print(f"Thread use = {self.max_workers} / Cores = {cores}")

    def _setup_directories(self) -> str:
        """Setup output directories."""
        file_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        output_dir = os.path.join(file_dir, "data")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def extract_from_file(self, file_path: str, **kwargs) -> List[ExtractedImage]:
        self.extracted_item_list.clear()
        self.extracted_image_list.clear()
        self.current_page_image_list.clear()
        self.current_file = file_path
        self.doc_fitz = fitz.open(self.current_file)
        self.page_size_list.clear()
        self._convert_pages_to_images_parallel()

        if self.device_name == "cpu":
            self._process_images_parallel()
        else:
            self._process_images_gpu()

        print("Processing text extraction...")
        # must sort because of parallel process
        self.extracted_item_list.sort(key=lambda x: (x["page"], x["box"][1], x["box"][0]))
        with tqdm(total=len(self.extracted_item_list)) as progress_bar:
            for item in self.extracted_item_list:
                if item["label"] in ["Text", "Title", "Caption", "Section-header", "Table"]:
                    item["text"] = self._extract_text_from_region(page_num=item["page"], box=item["box"])
                progress_bar.update(1)

        c = 10
        for item in self.extracted_item_list:
            if c == 0:
                break
            if item.get("text"):
                print(item)

                c = c - 1

        self._draw_bbox()

        # print(self.extracted_item_list)
        input("Press Enter to continue...")
        self.doc_fitz.close()
        for p, image_file in self.current_page_image_list:
            os.remove(image_file)

        return self.extracted_image_list

    def _convert_pages_to_images_parallel(self):
        page_test = len(self.doc_fitz)
        batch_size = min(self.max_workers, page_test)

        results = []

        print("Converting pages to images...")
        with tqdm(total=page_test) as progress_bar:
            for i in range(0, page_test, batch_size):
                current_batch_nums = range(i, min(i + batch_size, page_test))

                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    futures = [executor.submit(self._convert_single_page, p_num) for p_num in current_batch_nums]

                    for future in futures:
                        results.append(future.result())
                        progress_bar.update(1)

        # must sort because of parallel process
        results.sort(key=lambda x: (x["page"]))
        self.current_page_image_list = [(res["page"], res["image"]) for res in results]
        self.page_size_list = [res["size"] for res in results]

    def _convert_single_page(self, page_num):
        page = self.doc_fitz[page_num]
        pix = page.get_pixmap(dpi=self.dpi)
        pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore
        image_file = os.path.join(self.temp_dir, f"{self.current_file}_p{page_num + 1}.png")
        pil_image.save(image_file, "PNG")
        return {"page": page_num + 1, "image": image_file, "size": pil_image.size}
        # self.current_page_image_list.append((page_num + 1, image_file))
        # self.page_size_list.append(pil_image.size)

    def _process_images_parallel(self):
        batch_size = min(self.max_workers, len(self.current_page_image_list))

        print("Processing image detection...")
        with tqdm(total=len(self.current_page_image_list)) as progress_bar:
            for i in range(0, len(self.current_page_image_list), batch_size):
                batch = self.current_page_image_list[i : i + batch_size]

                with ThreadPoolExecutor(max_workers=batch_size) as executor:
                    futures = []
                    for page_num, image_path in batch:
                        future = executor.submit(self._process_single_page, page_num, image_path)
                        futures.append(future)

                    for future in futures:
                        try:
                            extracted = future.result(timeout=30)  # 30s timeout per image
                            self.extracted_item_list.extend(extracted)
                            progress_bar.update(1)
                        except Exception as e:
                            print(f"\tError processing image: {e}")

    def _process_images_gpu(self):
        """When using GPU, process one by one is faster"""
        with tqdm(total=len(self.current_page_image_list)) as progress_bar:
            for page_num, image_path in self.current_page_image_list:
                self.extracted_item_list.extend(self._process_single_page(page_num, image_path))
                progress_bar.update(1)

    def _process_single_page(self, page_num, image_path):
        pil_image = Image.open(image_path)
        detections = self._detect_page_layout(page_num, pil_image)
        # for detection in detections:
        #     pass
        return detections

    def _detect_page_layout(self, page_num, image: Image.Image) -> List[Dict[str, Any]]:
        inputs = self.processor(images=[image], return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Post-process
        results = self.processor.post_process_object_detection(
            outputs,
            target_sizes=[(image.size[1], image.size[0])],
            threshold=self.threshold,
        )
        detections = []
        for result in results:
            for score, label_id, box in zip(result["scores"], result["labels"], result["boxes"]):
                score = round(score.item(), 2)
                label = self.classes_map[label_id.item()]
                box_coords = [round(i, 2) for i in box.tolist()]

                detections.append({"page": page_num, "label": label, "score": score, "box": box_coords})

        return detections

    def _extract_text_from_region(self, page_num: int, box: List[float]) -> Dict[str, str]:
        try:
            page = self.doc_fitz[page_num - 1]
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height

            img_width, img_height = self.page_size_list[page_num - 1]
            scale_x = page_width / img_width
            scale_y = page_height / img_height

            x1, y1, x2, y2 = box
            pdf_x1 = x1 * scale_x
            pdf_y1 = y1 * scale_y
            pdf_x2 = x2 * scale_x
            pdf_y2 = y2 * scale_y

            text_rect = fitz.Rect(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
            text = page.get_text(clip=text_rect).strip()
            context_rect = fitz.Rect(max(0, pdf_x1 - 50), max(0, pdf_y1 - 30), min(page_width, pdf_x2 + 50), min(page_height, pdf_y2 + 30))
            context = page.get_text(clip=context_rect).strip()

            return {"text": text, "context": context}

        except Exception as e:
            print(f"Error extract text from page {page_num}:\n\t{e}")
            return {"text": "", "context": ""}

    def _draw_bbox(self):
        current_page_idx = -1
        page_image = None
        draw = None

        for item in self.extracted_item_list:
            page_num = item["page"]
            page_idx = page_num - 1

            if page_idx != current_page_idx:
                if page_image:
                    self._save_debug_image(page_image, current_page_idx + 1)

                current_page_idx = page_idx
                img_path = self.current_page_image_list[page_idx][1]
                page_image = Image.open(img_path).convert("RGB")
                draw = ImageDraw.Draw(page_image)

            # page = self.doc_fitz[page_idx]
            # pdf_w = page.rect.width
            # pdf_h = page.rect.height
            img_w, img_h = self.page_size_list[page_idx]
            # draw_scale_x = pdf_w / img_w
            # draw_scale_y = pdf_h / img_h

            if "box" in item:
                x1, y1, x2, y2 = item["box"]
                pixel_box = [x1, y1, x2, y2]
                color = "red" if item.get("label") == "picture" else "blue"
                draw.rectangle(pixel_box, outline=color, width=3)
                draw.text((pixel_box[0], pixel_box[1] - 12), f"{item.get('label')}", fill=color)

        if page_image:
            self._save_debug_image(page_image, current_page_idx + 1)

    def _save_debug_image(self, image, page_num):
        """Hàm phụ trợ để lưu ảnh debug"""
        debug_dir = os.path.join(self.temp_dir, "debug_bboxes")
        os.makedirs(debug_dir, exist_ok=True)
        save_path = os.path.join(debug_dir, f"debug_p{page_num}.png")
        image.save(save_path)


_extractor = None


def get_image_extractor() -> ImageExtractor:
    """Get or create the global image extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ImageExtractor()
    return _extractor


if __name__ == "__main__":
    get_image_extractor().extract_from_file(os.path.join(os.getcwd(), "data/documents/A2DP_v1.4.1.pdf"))
    # get_image_extractor().extract_from_file(os.path.join(os.getcwd(), "data/documents/80211-2024._pdf"))
