"""Full-page PDF image extraction using PyMuPDF."""

from pathlib import Path
from typing import Optional
import io
import re

from PIL import Image

from src.config import BASE_DIR, EXTRACTED_IMAGES_DIR, ensure_directories
from src.image_extraction.image_info import ExtractedImage


def _get_relative_path(absolute_path: Path, base_dir: Path) -> str:
    """Convert an absolute path to a stable project-relative path when possible."""
    try:
        return str(absolute_path.relative_to(base_dir)).replace("\\", "/")
    except ValueError:
        return str(absolute_path)


def _get_image_extraction_config():
    """Get image extraction config from global settings."""
    try:
        from src.config import settings

        return settings.image_extraction
    except ImportError:
        return None


class ImageExtractor:
    """Extract full-page PDF images for RAG indexing."""

    _caption_patterns = [
        r"(Figure\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        r"(Table\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        r"(Fig\.\s*\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        r"(Hình\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        r"(Bảng\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
    ]

    _visual_text_patterns = [
        r"figure\s+\d+",
        r"fig\.\s*\d+",
        r"table\s+\d+",
        r"hình\s+\d+",
        r"bảng\s+\d+",
        r"error\s+id",
        r"0x[0-9a-f]{2}",
        r"signaling\s+command",
    ]

    def __init__(self, config=None, image_format_override: str = None):
        self._config = config or _get_image_extraction_config()
        self._image_format_override = image_format_override

        ensure_directories()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_config_value(self, key: str, default):
        if self._config is None:
            return default
        return getattr(self._config, key, default)

    @property
    def output_dir(self) -> Path:
        return Path(self._get_config_value("output_dir", EXTRACTED_IMAGES_DIR))

    @property
    def image_format(self) -> str:
        image_format = self._image_format_override or self._get_config_value("image_format", "png")
        return image_format.lower()

    @property
    def min_width(self) -> int:
        return self._get_config_value("min_width", 150)

    @property
    def min_height(self) -> int:
        return self._get_config_value("min_height", 150)

    @property
    def extract_tables(self) -> bool:
        return self._get_config_value("extract_tables", True)

    @property
    def extract_figures(self) -> bool:
        return self._get_config_value("extract_figures", True)

    @property
    def context_chars(self) -> int:
        return self._get_config_value("context_chars", 10000)

    @property
    def min_drawing_size(self) -> int:
        return self._get_config_value("min_drawing_size", 20)

    def extract_from_file(
        self,
        file_path: Path,
    ) -> list[ExtractedImage]:
        """Extract full-page images from a PDF file."""
        file_path = Path(file_path)
        if file_path.suffix.lower() != ".pdf":
            print(f"Unsupported file type: {file_path.suffix.lower()}")
            return []

        return self._extract_fullpage_from_pdf(file_path)

    def _extract_fullpage_from_pdf(self, pdf_path: Path) -> list[ExtractedImage]:
        """Render selected PDF pages as full-page images."""
        extracted_images = []
        try:
            import fitz

            doc = fitz.open(str(pdf_path))
            print(f"Extracting full pages from: {pdf_path.name}")

            for page_num in range(len(doc)):
                page = doc[page_num]

                if not self._page_has_visual_content(doc, page):
                    continue

                pix = page.get_pixmap(dpi=150)
                image_id = f"{pdf_path.name}_p{page_num + 1}"
                image_path = self.output_dir / f"{image_id}.{self.image_format}"
                self._save_pixmap(pix, image_path)

                text = page.get_text()
                extracted_images.append(
                    ExtractedImage(
                        image_id=image_id,
                        image_path=_get_relative_path(image_path, BASE_DIR),
                        source_file=str(pdf_path),
                        page_number=page_num + 1,
                        bbox=(0, 0, pix.width, pix.height),
                        region_type="fullpage",
                        surrounding_text=text[: self.context_chars],
                        caption=f"Full page {page_num + 1} of {pdf_path.name}",
                        description=f"Full page capture of {pdf_path.name}, page {page_num + 1}",
                        tags=self._extract_tags_from_text(text),
                    )
                )
                print(f"  Captured full page {page_num + 1}")

            doc.close()
            return extracted_images
        except Exception as e:
            print(f"Error extracting full pages: {e}")
            return []

    def _save_pixmap(self, pix, image_path: Path) -> None:
        if self.image_format in ("jpg", "jpeg"):
            with Image.open(io.BytesIO(pix.tobytes("ppm"))) as image:
                image.save(str(image_path), "JPEG", quality=90)
            return

        pix.save(str(image_path))

    def _page_has_visual_content(self, doc, page) -> bool:
        page_area = page.rect.width * page.rect.height

        if self._has_embedded_image(doc, page, page_area):
            return True

        drawings = page.get_drawings()
        if self.extract_figures and self._has_meaningful_drawings(drawings, page_area):
            return True

        text = page.get_text().lower()
        if self._has_visual_text_marker(text):
            return True

        return self.extract_tables and self._has_table_lines(drawings)

    def _has_embedded_image(self, doc, page, page_area: float) -> bool:
        min_image_area = page_area * 0.05
        for img in page.get_images(full=True):
            try:
                pix = doc.extract_image(img[0])
                width = pix.get("width", 0)
                height = pix.get("height", 0)
                if width >= self.min_width and height >= self.min_height and width * height >= min_image_area:
                    return True
            except Exception:
                continue
        return False

    def _has_meaningful_drawings(self, drawings: list, page_area: float) -> bool:
        max_drawing_area = page_area * 0.50
        total_content_area = 0

        for drawing in drawings:
            rect = drawing["rect"]
            drawing_area = rect.width * rect.height

            fill = drawing.get("fill")
            if fill and len(drawing.get("items", [])) == 1:
                item_type = drawing.get("items", [[""]])[0][0]
                if item_type == "re":
                    brightness = sum(fill) / len(fill) if fill else 0
                    if brightness > 0.85:
                        continue

            if rect.width < self.min_drawing_size or rect.height < self.min_drawing_size:
                continue
            if drawing_area > max_drawing_area:
                continue

            total_content_area += drawing_area

        return total_content_area >= page_area * 0.02

    def _has_visual_text_marker(self, text: str) -> bool:
        return any(re.search(pattern, text) for pattern in self._visual_text_patterns)

    def _has_table_lines(self, drawings: list) -> bool:
        line_count = 0
        for drawing in drawings:
            for item in drawing.get("items", []):
                if item[0] in ("l", "re"):
                    line_count += 1
        return line_count > 50

    def _extract_tags_from_text(self, text: str) -> str:
        tags = []
        for pattern in self._caption_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                tag = match.group(1).strip()
                if 5 < len(tag) < 100:
                    tags.append(tag)
        return ",".join(sorted(set(tags)))


_extractor: Optional[ImageExtractor] = None


def get_image_extractor(force_new: bool = False, image_format: str = None) -> ImageExtractor:
    """Get or create the global image extractor instance."""
    global _extractor
    if _extractor is None or force_new:
        _extractor = ImageExtractor(image_format_override=image_format)
    return _extractor
