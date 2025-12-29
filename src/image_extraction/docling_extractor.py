import hashlib
import io
import os
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
from docling_core.types.doc.document import (
    PictureItem,
    DoclingDocument,
    GroupItem,
)

try:
    from src.image_extraction.image_info import ExtractedImage
except:
    pass
try:
    from image_info import ExtractedImage
except:
    pass


def get_image_hash(pil_image) -> str:
    """Generate MD5 hash from PIL Image."""
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()
    return hashlib.md5(img_bytes).hexdigest()[:8]


class ImageExtractor:
    """Extracts images from PDF documents using Docling."""

    def __init__(self):
        if hasattr(sys, "_MEIPASS"):
            res_dir = os.path.join(sys._MEIPASS, "docling_parse", "pdf_resources_v2")
            os.environ["DOCLING_PDF_RESOURCES_DIR"] = res_dir
            print(f"Docling Resources set to: {res_dir}")
        self.converter = self._create_converter()
        self.output_dir = self._setup_directories()
        self.pic_dir = os.path.join(self.output_dir, "extracted_images")
        os.makedirs(self.pic_dir, exist_ok=True)
        os.environ["HF_HUB_OFFLINE"] = "1"

    def _create_converter(self) -> DocumentConverter:
        """Create and configure document converter."""
        pipeline_options = PdfPipelineOptions()
        if hasattr(sys, "_MEIPASS"):
            pipeline_options.artifacts_path = os.path.join(sys._MEIPASS, "models")
        else:
            pipeline_options.artifacts_path = os.path.join(os.getcwd(), "models")
        pipeline_options.images_scale = 4.0
        pipeline_options.generate_picture_images = True
        pipeline_options.generate_table_images = True
        pipeline_options.generate_page_images = True
        pipeline_options.do_ocr = False

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def _setup_directories(self) -> str:
        """Setup output directories."""
        file_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        )
        output_dir = os.path.join(file_dir, "data")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def extract_from_json(self, file_path: str):
        doc = DoclingDocument.load_from_json(file_path)
        self._document_processing(file_path, doc)

    def extract_from_file(self, file_path: str, **kwargs) -> list[ExtractedImage]:
        """Extract images from PDF file."""
        result = self.converter.convert(file_path)
        doc_filename = os.path.basename(file_path)

        result.document.save_as_json(f"{self.output_dir}/documents/{doc_filename}.json")
        return self._document_processing(file_path, result.document)

    def _document_processing(
        self, file_path: str, document: DoclingDocument
    ) -> list[ExtractedImage]:
        doc_filename = os.path.basename(file_path)

        self.document = document
        self.item_list = document.body.children
        self.item_dict = {}
        self.item_dict.update({item.self_ref: item for item in document.texts})
        self.item_dict.update({item.self_ref: item for item in document.groups})
        self.item_dict.update({item.self_ref: item for item in document.tables})
        self.item_dict.update({item.self_ref: item for item in document.pictures})
        self.indices = {item.cref: i for i, item in enumerate(document.body.children)}
        images = []

        # preprocess to remove logo, etc...
        for idx, picture in enumerate(document.pictures, 1):
            caption = self._extract_caption(picture)
            if caption == "":
                self.item_dict.pop(picture.self_ref)

        for idx, picture in enumerate(document.pictures, 1):
            caption = self._extract_caption(picture)
            if caption == "":  # may not an image, this is a logo, etc...
                continue
            surrounding_text = self._extract_surrounding_text(picture)
            image_path = self._save_picture_image(picture, doc_filename, idx)
            page_num, bbox = self._extract_position_info(picture)

            extracted_image = ExtractedImage(
                image_id=get_image_hash(picture.image.pil_image),
                image_path=str(image_path),
                source_file=str(file_path),
                page_number=page_num,
                bbox=bbox,
                region_type="picture",
                surrounding_text=surrounding_text,
                caption=caption,
                description=f"Picture from {doc_filename}, page {page_num}",
            )

            images.append(extracted_image)

            print(picture.self_ref)
            print(extracted_image.to_dict())
            print(
                "========================================================================"
            )

        return images

    def _save_picture_image(
        self,
        picture: PictureItem,
        doc_filename: str,
        idx: int,
    ) -> Path:
        """Save picture image to file."""
        image_path = Path(self.pic_dir) / f"{doc_filename}-picture-{idx}.png"
        with image_path.open("wb") as fp:
            picture.get_image(self.document).save(fp, "PNG")
        return image_path

    def _extract_position_info(self, picture: PictureItem) -> tuple[int, tuple]:
        """Extract page number and bounding box from picture."""
        page_num = 0
        bbox_coords = (0, 0, 0, 0)

        if hasattr(picture, "prov") and picture.prov:
            for prov in picture.prov:
                if prov.page_no is not None:
                    page_num = prov.page_no
                    if prov.bbox:
                        bbox_coords = (
                            prov.bbox.l,
                            prov.bbox.t,
                            prov.bbox.r,
                            prov.bbox.b,
                        )
                    break

        return page_num, bbox_coords

    def _extract_caption(
        self,
        picture: PictureItem,
    ) -> str:
        """Extract caption from picture."""
        if not hasattr(picture, "captions") or not picture.captions:
            pic_index = self.indices[picture.self_ref]
            if pic_index + 1 >= len(self.item_list):
                return ""
            item = self.item_dict.get(self.item_list[pic_index + 1].cref)
            if item is None:
                return ""
            if "caption" in item.label:
                return item.text
            return ""

        caption_texts = [self.item_dict[cap.cref].text for cap in picture.captions]
        return " ".join(caption_texts).strip()

    def _extract_surrounding_text(self, picture: PictureItem) -> str:
        """Extract surrounding text from picture context."""
        surrounding_ref = []

        # Get text from inside picture
        for child in picture.children:
            surrounding_ref.append(child.cref)

        # Find adjacent text elements
        pic_index = self.indices[picture.self_ref]

        # TODO: What to do with "formula"
        # Find text element in next section
        for i in range(pic_index + 1, len(self.item_list)):
            item = self.item_dict.get(self.item_list[i].cref)
            if item is None or any(
                word in item.label for word in ["caption", "page_footer", "page_header"]
            ):
                continue

            if any(word in item.label for word in ["header", "picture", "table"]):
                break
            if "text" in item.label:
                surrounding_ref.append(item.self_ref)
                continue
            if "group" in item.self_ref:
                surrounding_ref = surrounding_ref + self._get_text_ref_from_group(item)
                continue

        # Find text element in previous section
        for i in range(pic_index - 1, -1, -1):
            item = self.item_dict.get(self.item_list[i].cref)
            if item is None or any(
                word in item.label for word in ["page_footer", "page_header"]
            ):
                continue

            if any(
                word in item.label for word in ["header", "picture", "table", "caption"]
            ):
                break
            if "text" in item.label:
                surrounding_ref.insert(0, item.self_ref)
                continue
            if "group" in item.self_ref:
                surrounding_ref = surrounding_ref + self._get_text_ref_from_group(item)
                continue

        surrounding_texts = []
        for cref in surrounding_ref:
            item = self.item_dict.get(cref)
            if item is None:
                continue
            surrounding_texts.append(item.text)

        return "\n".join(surrounding_texts)

    def _get_text_ref_from_group(self, group_item: GroupItem) -> list[str]:
        text_list = []
        for children in group_item.children:
            item = self.item_dict.get(children.cref)
            if item is None:
                continue
            if "text" in children.cref:
                text_list.append(item.self_ref)
            if "group" in children.cref:
                item = self.item_dict.get(children.cref)
                if item is None:
                    continue
                text_list.append(self._get_text_ref_from_group(item))
        return text_list


_extractor = None


def get_image_extractor() -> ImageExtractor:
    """Get or create the global image extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ImageExtractor()
    return _extractor


if __name__ == "__main__":
    get_image_extractor().extract_from_json(
        os.path.join(os.getcwd(), "data/documents/A2DP_v1.4.1.pdf.json")
    )
