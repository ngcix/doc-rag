import hashlib
import io
import os
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
from docling_core.types.doc.document import PictureItem, DoclingDocument

from src.image_extraction.image_info import ExtractedImage


def get_image_hash(pil_image) -> str:
    """Generate MD5 hash from PIL Image."""
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()
    return hashlib.md5(img_bytes).hexdigest()[:8]


class ImageExtractor:
    """Extracts images from PDF documents using Docling."""

    def __init__(self):
        if hasattr(sys, '_MEIPASS'):
            res_path = os.path.join(sys._MEIPASS, "docling_parse", "pdf_resources_v2")
            os.environ["DOCLING_PDF_RESOURCES_DIR"] = res_path
        self.converter = self._create_converter()
        self.output_dir = self._setup_directories()
        self.pic_dir = os.path.join(self.output_dir, "extracted_images")
        os.makedirs(self.pic_dir, exist_ok=True)
        os.environ["HF_HUB_OFFLINE"] = "1"

    def _create_converter(self) -> DocumentConverter:
        """Create and configure document converter."""
        pipeline_options = PdfPipelineOptions()
        if hasattr(sys, '_MEIPASS'):
            pipeline_options.artifacts_path = os.path.join(sys._MEIPASS, "models")
        else:
            pipeline_options.artifacts_path = os.path.join(os.getcwd(), "models")
        pipeline_options.images_scale = 4.0
        pipeline_options.generate_picture_images = True
        pipeline_options.generate_table_images = True
        pipeline_options.generate_page_images = True
        pipeline_options.do_ocr = False

        return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)})

    def _setup_directories(self) -> str:
        """Setup output directories."""
        file_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        output_dir = os.path.join(file_dir, "data")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def extract_from_file(self, file_path: str, **kwargs) -> list[ExtractedImage]:
        """Extract images from PDF file."""
        result = self.converter.convert(file_path)
        doc_filename = os.path.basename(file_path)

        result.document.save_as_json(f"{self.output_dir}/documents/{doc_filename}.json")

        text_dict = {text.self_ref: text.text for text in result.document.texts}
        images = []

        for idx, picture in enumerate(result.document.pictures, 1):
            image_path = self._save_picture_image(picture, result.document, doc_filename, idx)
            page_num, bbox = self._extract_position_info(picture)
            surrounding_text = self._extract_surrounding_text(picture, result.document, text_dict)
            caption = self._extract_caption(picture, text_dict)

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
            print(extracted_image.to_dict())

        return images

    def _save_picture_image(self, picture: PictureItem, document: DoclingDocument, doc_filename: str, idx: int) -> Path:
        """Save picture image to file."""
        image_path = Path(self.pic_dir) / f"{doc_filename}-picture-{idx}.png"
        with image_path.open("wb") as fp:
            picture.get_image(document).save(fp, "PNG")
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
                        bbox_coords = (prov.bbox.l, prov.bbox.t, prov.bbox.r, prov.bbox.b)
                    break

        return page_num, bbox_coords

    def _extract_caption(self, picture: PictureItem, text_dict: dict) -> str:
        """Extract caption from picture."""
        if not hasattr(picture, "captions") or not picture.captions:
            return ""

        caption_texts = [text_dict[cap.cref] for cap in picture.captions]
        return " ".join(caption_texts).strip()

    def _extract_surrounding_text(self, picture: PictureItem, document: DoclingDocument, text_dict: dict) -> str:
        """Extract surrounding text from picture context."""
        surrounding_texts = []

        # Get text from inside picture
        for child in picture.children:
            surrounding_texts.append(text_dict[child.cref])

        # Find adjacent text elements
        item_list = document.body.children
        text_ref = ["text"]

        for idx, element in enumerate(item_list):
            if "pictures" not in element.cref:
                continue

            # Find next text element
            for i in range(idx, len(item_list)):
                if any(word in item_list[i].cref for word in text_ref):
                    surrounding_texts.append(text_dict[item_list[i].cref])
                    break

            # Find previous text element
            for i in range(idx - 1, -1, -1):
                if any(word in item_list[i].cref for word in text_ref):
                    surrounding_texts.append(text_dict[item_list[i].cref])
                    break

        return "\n".join(surrounding_texts)


_extractor = None


def get_image_extractor() -> ImageExtractor:
    """Get or create the global image extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ImageExtractor()
    return _extractor
