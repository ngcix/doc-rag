"""
Image Extraction Module using pdf_oxide

This module provides functionality to extract image regions from documents
using pdf-oxide, a fast Rust-based PDF processing library.

Strategy:
- Detection phase: Uses pdf_oxide (Rust) to quickly scan all pages for visual content
  (embedded images, vector paths/rects, figure/table captions)
- Render phase: Uses PyMuPDF (fitz) to render only the detected pages as full-page images
- This hybrid approach combines Rust-speed detection with proven PyMuPDF rendering
"""
from typing import Optional, List
from pathlib import Path
import hashlib
import re
import sys

# Import config from settings
from src.config.settings import settings, EXTRACTED_IMAGES_DIR, BASE_DIR
from src.image_extraction.image_info import ExtractedImage
import pdf_oxide


def _get_relative_path(absolute_path: Path, base_dir: Path) -> str:
    """Convert absolute path to relative path from base directory."""
    try:
        rel_path = absolute_path.relative_to(base_dir)
        return str(rel_path).replace('\\', '/')
    except ValueError:
        return str(absolute_path)


class PdfOxideExtractor:
    """
    PDF image extractor using pdf_oxide for fast detection + PyMuPDF for rendering.
    
    Detection logic mirrors the PyMuPDF fullpage extractor:
    1. Check for embedded images (≥5% page area)
    2. Check for vector drawings/paths (combined area ≥2% page)
    3. Check for Figure/Table caption patterns in text
    4. Check for table structure (many rects/paths > 50)
    
    Only pages that pass detection are rendered as full-page images.
    """

    def __init__(self, image_format_override: str = None):
        self._config = settings.image_extraction
        self._image_format_override = image_format_override
        
        self.output_dir = Path(getattr(self._config, "output_dir", EXTRACTED_IMAGES_DIR))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    @property
    def image_format(self):
        if self._image_format_override:
            return self._image_format_override
        return getattr(self._config, "image_format", "png")

    @property
    def min_width(self):
        return getattr(self._config, "min_width", 150)

    @property
    def min_height(self):
        return getattr(self._config, "min_height", 150)

    @property
    def min_drawing_size(self):
        return getattr(self._config, "min_drawing_size", 20)

    @property
    def context_chars(self):
        return getattr(self._config, "context_chars", 2000)

    # ── Caption detection patterns (same as PyMuPDF extractor) ──
    FIGURE_PATTERNS = [
        r'figure\s+\d+',       # Figure 1, Figure 12
        r'fig\.\s*\d+',        # Fig. 1, Fig.12
        r'table\s+\d+',        # Table 1
        r'hình\s+\d+',         # Vietnamese: Hình 1
        r'bảng\s+\d+',         # Vietnamese: Bảng 1
        r'error\s+id',         # Error ID column
        r'0x[0-9a-f]{2}',      # Hex error codes
        r'signaling\s+command', # Column header in spec tables
    ]

    def _extract_tags_from_text(self, text: str) -> list[str]:
        """Extract tags from text using regex patterns."""
        tags = []
        patterns = [
            (r'(Figure\s+\d+[\.\-]?\d*)', 'figure'),
            (r'(Fig\.\s*\d+[\.\-]?\d*)', 'figure'),
            (r'(Table\s+\d+[\.\-]?\d*)', 'table'),
            (r'(Hình\s+\d+[\.\-]?\d*)', 'figure'),
            (r'(Bảng\s+\d+[\.\-]?\d*)', 'table'),
        ]
        for pattern, tag_type in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                tag = f"{tag_type}:{match.strip()}"
                if tag not in tags:
                    tags.append(tag)
        return tags

    def extract_from_file(
        self, file_path: Path, fullpage_mode: bool = False
    ) -> List[ExtractedImage]:
        """Extract images from a file (PDF only)."""
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return self.extract_from_pdf(file_path, fullpage_mode)
        else:
            print(f"Unsupported file type for pdf_oxide: {suffix}")
            return []

    def _detect_visual_content(self, doc, page_num: int, page_area: float) -> bool:
        """
        Detect if a page contains significant visual content using pdf_oxide.
        
        Uses 4-level detection (mirrors PyMuPDF fullpage logic):
        1. Embedded images (≥5% page area)
        2. Vector paths/drawings (combined area ≥2% page)
        3. Figure/Table caption patterns
        4. Table structure (many rects/paths)
        
        Returns True if visual content detected.
        """
        min_image_area = page_area * 0.05   # 5% of page
        max_drawing_area = page_area * 0.50  # Skip full-page frames

        # ── Step 1: Check embedded images ──
        try:
            images = doc.extract_images(page_num)
            for img_info in images:
                w = img_info.get("width", 0)
                h = img_info.get("height", 0)
                img_area = w * h
                if w >= self.min_width and h >= self.min_height and img_area >= min_image_area:
                    return True
        except Exception:
            pass

        # ── Step 2: Check vector drawings (paths + rects) ──
        try:
            total_content_area = 0
            
            # Check paths
            paths = doc.extract_paths(page_num)
            for path in paths:
                bbox = path.get("bbox", (0, 0, 0, 0))
                # bbox format: (x, y, width, height)
                pw, ph = bbox[2], bbox[3]
                drawing_area = pw * ph
                
                # Skip full-page frames
                if drawing_area > max_drawing_area:
                    continue
                # Skip trivially small
                if pw < self.min_drawing_size or ph < self.min_drawing_size:
                    continue
                # Skip light-colored fills (background boxes)
                fill = path.get("fill_color")
                if fill and path.get("operations_count", 0) <= 2:
                    brightness = sum(fill) / len(fill) if fill else 0
                    if brightness > 0.85:
                        continue
                        
                total_content_area += drawing_area

            # Check rects
            rects = doc.extract_rects(page_num)
            for rect in rects:
                bbox = rect.get("bbox", (0, 0, 0, 0))
                rw, rh = bbox[2], bbox[3]
                rect_area = rw * rh
                
                if rect_area > max_drawing_area:
                    continue
                if rw < self.min_drawing_size or rh < self.min_drawing_size:
                    continue
                    
                fill = rect.get("fill_color")
                if fill and rect.get("operations_count", 0) <= 2:
                    brightness = sum(fill) / len(fill) if fill else 0
                    if brightness > 0.85:
                        continue
                        
                total_content_area += rect_area

            if total_content_area >= page_area * 0.02:
                return True
        except Exception:
            pass

        # ── Step 3: Check caption patterns in text ──
        try:
            text = doc.extract_text(page_num)
            if text:
                text_lower = text.lower()
                for pattern in self.FIGURE_PATTERNS:
                    if re.search(pattern, text_lower):
                        return True
        except Exception:
            pass

        # ── Step 4: Check table structure (many rects/paths) ──
        try:
            paths_count = len(doc.extract_paths(page_num))
            rects_count = len(doc.extract_rects(page_num))
            if (paths_count + rects_count) > 50:
                return True
        except Exception:
            pass

        return False

    def extract_from_pdf(self, pdf_path: Path, fullpage_mode: bool = False) -> List[ExtractedImage]:
        """
        Extract images from a PDF file using hybrid pdf_oxide + PyMuPDF approach.
        
        Phase 1 (pdf_oxide / Rust): Scan all pages, detect which ones contain visual content
        Phase 2 (PyMuPDF): Render only the detected pages as full-page images
        """
        extracted_images = []
        
        # ── Phase 1: Detection with pdf_oxide (fast) ──
        try:
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            po_doc = pdf_oxide.PdfDocument.from_bytes(pdf_data)
        except Exception as e:
            print(f"pdf_oxide error loading {pdf_path}: {e}")
            return []

        print(f"Scanning pages with pdf_oxide: {pdf_path.name}")
        page_count = po_doc.page_count()
        
        pages_with_visual = []
        page_texts = {}
        
        for page_num in range(page_count):
            try:
                # Get page dimensions
                media_box = po_doc.page_media_box(page_num)
                # media_box = (x_min, y_min, width, height)
                page_width = media_box[2]
                page_height = media_box[3]
                page_area = page_width * page_height
                
                if self._detect_visual_content(po_doc, page_num, page_area):
                    pages_with_visual.append(page_num)
                    # Pre-extract text for context (fast in pdf_oxide)
                    try:
                        page_texts[page_num] = po_doc.extract_text(page_num)
                    except Exception:
                        page_texts[page_num] = ""
            except Exception as e:
                print(f"  Error scanning page {page_num + 1}: {e}")

        print(f"  Detected {len(pages_with_visual)}/{page_count} pages with visual content")

        if not pages_with_visual:
            return []

        # ── Phase 2: Render detected pages with PyMuPDF ──
        try:
            import fitz
            fitz_doc = fitz.open(str(pdf_path))
        except ImportError:
            print("PyMuPDF (fitz) is required for rendering. Install with: pip install pymupdf")
            return []
        except Exception as e:
            print(f"PyMuPDF error loading {pdf_path}: {e}")
            return []

        image_format = self.image_format.lower()
        
        for page_num in pages_with_visual:
            try:
                page = fitz_doc[page_num]
                
                # Render full page at 150 DPI
                pix = page.get_pixmap(dpi=150)
                
                # Generate ID and save
                image_id = f"{pdf_path.name}_p{page_num + 1}"
                image_filename = f"{image_id}.{image_format}"
                image_path = self.output_dir / image_filename

                if image_format in ("jpg", "jpeg"):
                    from PIL import Image
                    import io
                    img_data = pix.tobytes("ppm")
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_img.save(str(image_path), "JPEG", quality=90)
                else:
                    pix.save(str(image_path))

                # Get text context (pre-extracted by pdf_oxide)
                text = page_texts.get(page_num, "")
                
                # Auto-generate tags
                extracted_tags = self._extract_tags_from_text(text)

                extracted_images.append(
                    ExtractedImage(
                        image_id=image_id,
                        image_path=_get_relative_path(image_path, BASE_DIR),
                        source_file=str(pdf_path),
                        page_number=page_num + 1,
                        bbox=(0, 0, pix.width, pix.height),
                        region_type="fullpage",
                        surrounding_text=text[:10000],
                        caption=f"Full page {page_num + 1} of {pdf_path.name}",
                        description=f"Full page capture of {pdf_path.name}, page {page_num + 1}",
                        tags=", ".join(extracted_tags) if extracted_tags else "",
                    )
                )
                print(f"  Captured full page {page_num + 1}")
            except Exception as e:
                print(f"  Error rendering page {page_num + 1}: {e}")

        fitz_doc.close()
        print(f"  Total: {len(extracted_images)} pages captured from {pdf_path.name}")
        return extracted_images


# Global extractor instance
_extractor: Optional[PdfOxideExtractor] = None

def get_image_extractor(force_new: bool = False, image_format: str = None) -> PdfOxideExtractor:
    global _extractor
    if _extractor is None or force_new:
        _extractor = PdfOxideExtractor(image_format_override=image_format)
    return _extractor
