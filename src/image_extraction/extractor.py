"""
Image Extraction Module using PaddleOCR PP-Structure

This module provides functionality to extract image regions from documents
using PaddleOCR's PP-Structure for layout analysis.
"""

from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
import hashlib
import os
import sys
import re
from src.image_extraction.image_info import ExtractedImage

# LangChain compatibility shim for PaddleOCR
# PaddleOCR uses old langchain imports that no longer exist in langchain >= 1.0
# This shim re-maps old module paths to their new locations
try:
    import langchain.docstore
except ModuleNotFoundError:
    import types
    import langchain

    # Create a fake docstore module
    docstore_module = types.ModuleType("langchain.docstore")
    document_module = types.ModuleType("langchain.docstore.document")

    # Import Document from new location
    try:
        from langchain_core.documents import Document
    except ImportError:
        from langchain.schema import Document

    document_module.Document = Document
    docstore_module.document = document_module

    # Register in sys.modules
    sys.modules["langchain.docstore"] = docstore_module
    sys.modules["langchain.docstore.document"] = document_module
    langchain.docstore = docstore_module

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import settings, ensure_directories, EXTRACTED_IMAGES_DIR
from PIL import Image, ImageOps
import io
import numpy as np


# Import config from settings (use this instead of local dataclass)
# This allows centralized configuration management
def _get_image_extraction_config():
    """Get image extraction config from global settings."""
    try:
        from config.settings import settings

        return settings.image_extraction
    except ImportError:
        # Fallback to default values if settings not available
        return None


class ImageExtractor:
    """
    Extracts image regions from documents using PyMuPDF and PP-Structure.

    Extraction methods:
    - PyMuPDF (fitz): Fast extraction of embedded images and vector drawings
    - PP-Structure: AI-based layout analysis for context enrichment

    Configuration is loaded from config/settings.py
    """

    def __init__(self, config=None):
        """
        Initialize the ImageExtractor.

        Args:
            config: Image extraction configuration. If None, loads from settings.
        """
        # Load config from settings if not provided
        if config is None:
            config = _get_image_extraction_config()

        # Store config (may be pydantic model or None)
        self._config = config
        self._structure_engine = None
        ensure_directories()

        # Ensure output directory exists
        output_dir = self._get_config_value("output_dir", EXTRACTED_IMAGES_DIR)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def _get_config_value(self, key: str, default):
        """Get config value with fallback to default."""
        if self._config is None:
            return default
        return getattr(self._config, key, default)

    # Property shortcuts for config values (backward compatible)
    @property
    def output_dir(self):
        return self._get_config_value("output_dir", EXTRACTED_IMAGES_DIR)

    @property
    def image_format(self):
        return self._get_config_value("image_format", "png")

    @property
    def min_width(self):
        return self._get_config_value("min_width", 50)

    @property
    def min_height(self):
        return self._get_config_value("min_height", 50)

    @property
    def min_brightness(self):
        return self._get_config_value("min_brightness", 30.0)

    @property
    def min_std_dev(self):
        return self._get_config_value("min_std_dev", 15.0)

    @property
    def max_dark_pixel_ratio(self):
        return self._get_config_value("max_dark_pixel_ratio", 0.85)

    @property
    def extract_tables(self):
        return self._get_config_value("extract_tables", True)

    @property
    def extract_figures(self):
        return self._get_config_value("extract_figures", True)

    @property
    def context_chars(self):
        return self._get_config_value("context_chars", 500)

    @property
    def use_ppstructure(self):
        return self._get_config_value("use_ppstructure", True)

    @property
    def ppstructure_max_pages(self):
        return self._get_config_value("ppstructure_max_pages", 20)

    @property
    def cluster_merge_distance(self):
        return self._get_config_value("cluster_merge_distance", 50)

    @property
    def min_drawing_size(self):
        return self._get_config_value("min_drawing_size", 20)

    @property
    def min_diagram_size(self):
        return self._get_config_value("min_diagram_size", 100)

    @property
    def use_gpu(self):
        return self._get_config_value("use_gpu", False)

    @property
    def structure_engine(self):
        """Lazy loading of PP-Structure engine."""
        if self._structure_engine is None:
            self._structure_engine = self._init_structure_engine()
        return self._structure_engine

    def _init_structure_engine(self):
        """Initialize the PP-Structure engine."""
        try:
            from paddleocr import PPStructureV3

            print("Initializing PP-StructureV3 engine...")
            engine = PPStructureV3(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
            )
            print("PP-StructureV3 engine initialized successfully")
            return engine
        except ImportError:
            raise ImportError(
                "PaddleOCR is required for image extraction. Install with: pip install paddleocr[all]"
            )

    def extract_from_file(
        self, file_path: Path, fullpage_mode: bool = False
    ) -> list[ExtractedImage]:
        """
        Extract images from a file (PDF or Image).

        Args:
            file_path: Path to the file.
            fullpage_mode: If True, extract full page as image instead of cropping.

        Returns:
            List of ExtractedImage objects.
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            if fullpage_mode:
                return self._extract_fullpage_from_pdf(file_path)
            else:
                return self.extract_from_pdf(file_path)
        elif suffix in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            return self._extract_from_image(file_path, str(file_path))
        else:
            print(f"Unsupported file type: {suffix}")
            return []

    def _extract_tags_from_text(self, text: str) -> str:
        """
        Extract tags from text using regex patterns.
        Looks for 'Figure X.Y: ...' or 'Table X.Y: ...'
        """
        tags = []
        # Pattern: Figure/Table/Fig. followed by number and some text up to newline or period
        # Example: "Figure 4.2: Media payload format"
        patterns = [
            r"(Figure\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
            r"(Table\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
            r"(Fig\.\s*\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
            r"(Hình\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
            r"(Bảng\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        ]

        for p in patterns:
            matches = re.finditer(p, text, re.IGNORECASE)
            for m in matches:
                # Clean up the tag
                tag = m.group(1).strip()
                # Limit length to avoid grabbing whole paragraphs
                if len(tag) > 5 and len(tag) < 100:
                    tags.append(tag)

        # Unique tags
        return ",".join(list(set(tags)))

    def _extract_fullpage_from_pdf(self, pdf_path: Path) -> list[ExtractedImage]:
        """
        Extract full pages as images from PDF.
        """
        extracted_images = []
        try:
            import fitz

            doc = fitz.open(str(pdf_path))

            print(f"Extracting full pages from: {pdf_path.name}")

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Check if page has images
                has_images = False
                headers_detected = False

                # Check for embedded images
                image_list = page.get_images(full=True)
                for img in image_list:
                    try:
                        xref = img[0]
                        pix_check = fitz.Pixmap(doc, xref)
                        if (
                            pix_check.width >= self.min_width
                            and pix_check.height >= self.min_height
                        ):
                            has_images = True
                            pix_check = None
                            break
                        pix_check = None
                    except:
                        continue

                # If no embedded images, check for drawings if configured
                if not has_images and self.extract_figures:
                    drawings = page.get_drawings()
                    for d in drawings:
                        rect = d["rect"]
                        if (
                            rect.width > self.min_drawing_size
                            and rect.height > self.min_drawing_size
                        ):
                            has_images = True
                            break

                if not has_images:
                    continue

                # Render full page
                pix = page.get_pixmap(dpi=150)
                image_data = pix.tobytes("png")

                # Generate ID
                # Use deterministic ID based on filename and page: docname_p{pagenum}
                image_id = f"{pdf_path.name}_p{page_num + 1}"
                image_filename = f"{image_id}.png"
                image_path = self.output_dir / image_filename

                # Save image
                pix.save(str(image_path))

                # Get text content as context
                text = page.get_text()

                # Auto-generate tags from text
                extracted_tags = self._extract_tags_from_text(text)

                extracted_images.append(
                    ExtractedImage(
                        image_id=image_id,
                        image_path=str(image_path),
                        source_file=str(pdf_path),
                        page_number=page_num + 1,
                        bbox=(0, 0, pix.width, pix.height),
                        region_type="fullpage",
                        # For fullpage mode, we use the entire page text as context
                        # The vectorizer (GTE) handles long context (8192 tokens), strict truncation is less critical
                        # but we still guard against massive dumps if needed.
                        surrounding_text=text[:10000],
                        caption=f"Full page {page_num + 1} of {pdf_path.name}",
                        description=f"Full page capture of {pdf_path.name}, page {page_num + 1}",
                        tags=extracted_tags,
                    )
                )
                print(f"  Captured full page {page_num + 1}")

            doc.close()
            return extracted_images

        except Exception as e:
            print(f"Error extracting full pages: {e}")
            return []

    def extract_from_pdf(self, pdf_path: Path) -> list[ExtractedImage]:
        """
        Extract images from a PDF file.

        Uses PyMuPDF (fitz) as primary method for image extraction,
        and PP-Structure for layout analysis and context enrichment.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of ExtractedImage objects.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        print(f"Extracting images from: {pdf_path.name}")

        # 1. Extract embedded images (bitmaps) with PyMuPDF
        extracted_images = self._extract_pdf_with_pymupdf(pdf_path)

        # 2. Extract vector drawings (diagrams) with PyMuPDF
        if self.extract_figures:
            drawings = self._extract_drawings_with_pymupdf(pdf_path)
            extracted_images.extend(drawings)

        # 3. Run PP-Structure for layout analysis and context enrichment
        if self.use_ppstructure and extracted_images:
            try:
                # Only analyze pages that have extracted images
                pages_with_images = list(
                    set(img.page_number for img in extracted_images)
                )
                pages_with_images.sort()

                layout_info = self._analyze_pdf_layout_with_ppstructure(
                    pdf_path, pages_to_analyze=pages_with_images
                )
                if layout_info:
                    extracted_images = self._enrich_images_with_layout_context(
                        extracted_images, layout_info
                    )
                    print(
                        f"  Enriched {len(extracted_images)} images with PP-Structure context"
                    )
            except Exception as e:
                print(f"  PP-Structure analysis skipped: {e}")

        print(
            f"  Extracted {len(extracted_images)} images/drawings from {pdf_path.name}"
        )
        return extracted_images

    def _analyze_pdf_layout_with_ppstructure(
        self, pdf_path: Path, pages_to_analyze: list[int] = None, max_pages: int = 20
    ) -> dict:
        """
        Analyze PDF layout using PP-Structure.

        Renders pages and runs PP-Structure to detect:
        - Text regions with content
        - Figure/image regions
        - Table regions
        - Title/caption regions

        Args:
            pdf_path: Path to PDF file
            pages_to_analyze: Specific page numbers (1-indexed) to analyze.
                            If None, analyzes first max_pages.
            max_pages: Maximum number of pages to analyze (default 20)

        Returns:
            Dict mapping page_number to layout analysis results.
        """
        import fitz

        layout_info = {}
        temp_paths = []

        try:
            doc = fitz.open(str(pdf_path))
            num_pages = len(doc)

            # Determine which pages to analyze
            if pages_to_analyze:
                pages = [
                    p - 1 for p in pages_to_analyze if 1 <= p <= num_pages
                ]  # Convert to 0-indexed
            else:
                pages = list(range(min(num_pages, max_pages)))

            if not pages:
                doc.close()
                return layout_info

            print(f"  Running PP-Structure layout analysis on {len(pages)} pages...")

            # Step 1: Render pages to temp images
            for page_num in pages:
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                temp_path = self.output_dir / f"_temp_page_{page_num}.png"
                pix.save(str(temp_path))
                temp_paths.append((page_num, temp_path))
                pix = None

            doc.close()

            # Step 2: Process with PP-Structure using batch input
            # Create list of all temp image paths
            image_paths = [str(tp[1]) for tp in temp_paths]

            try:
                # Call PP-Structure with batch of images
                results = self.structure_engine.predict(input=image_paths)

                # Process results - one result per image
                for idx, result in enumerate(results):
                    if idx >= len(temp_paths):
                        break

                    page_num = temp_paths[idx][0]

                    page_layout = {
                        "text_regions": [],
                        "figure_regions": [],
                        "table_regions": [],
                        "title_regions": [],
                    }

                    # Get layout parsing result
                    if hasattr(result, "layout_parsing_result"):
                        layout_result = result.layout_parsing_result
                    elif isinstance(result, dict) and "layout_parsing_result" in result:
                        layout_result = result["layout_parsing_result"]
                    else:
                        continue

                    if isinstance(layout_result, dict):
                        boxes = layout_result.get("boxes", [])
                        for box in boxes:
                            region_type = box.get("type", "unknown").lower()
                            bbox = box.get("bbox", box.get("coordinate", []))
                            text = box.get("text", "")

                            region_data = {
                                "bbox": bbox,
                                "text": text,
                                "type": region_type,
                            }

                            if region_type in ["text", "paragraph"]:
                                page_layout["text_regions"].append(region_data)
                            elif region_type in ["figure", "image", "chart", "picture"]:
                                page_layout["figure_regions"].append(region_data)
                            elif region_type == "table":
                                page_layout["table_regions"].append(region_data)
                            elif region_type in ["title", "caption"]:
                                page_layout["title_regions"].append(region_data)

                    layout_info[page_num + 1] = page_layout
                    print(
                        f"    Page {page_num + 1}: {len(page_layout['text_regions'])} text, "
                        f"{len(page_layout['figure_regions'])} figures, "
                        f"{len(page_layout['table_regions'])} tables"
                    )

            except Exception as e:
                print(f"  PP-Structure batch processing failed: {e}")

        except ImportError:
            print("  PP-Structure not available, skipping layout analysis")
        except Exception as e:
            print(f"  Layout analysis error: {e}")
        finally:
            # Clean up all temp files
            for _, temp_path in temp_paths:
                try:
                    temp_path.unlink(missing_ok=True)
                except:
                    pass

        return layout_info

    def _enrich_images_with_layout_context(
        self, images: list[ExtractedImage], layout_info: dict
    ) -> list[ExtractedImage]:
        """
        Enrich extracted images with context from PP-Structure layout analysis.

        For each image, finds nearby text regions and captions from the layout.
        """
        for img in images:
            page_num = img.page_number
            if page_num not in layout_info:
                continue

            page_layout = layout_info[page_num]

            # Collect all text from the page for context
            all_text_parts = []

            # Add title/caption regions (highest priority)
            for region in page_layout.get("title_regions", []):
                if region.get("text"):
                    all_text_parts.append(f"[Title] {region['text']}")

            # Add nearby text regions
            for region in page_layout.get("text_regions", []):
                if region.get("text"):
                    all_text_parts.append(region["text"])

            # Combine and update image context
            if all_text_parts:
                enriched_text = "\n".join(all_text_parts)
                # Combine with existing surrounding_text
                if img.surrounding_text:
                    img.surrounding_text = (
                        f"{enriched_text}\n---\n{img.surrounding_text}"
                    )
                else:
                    img.surrounding_text = enriched_text

                # Truncate to config limit
                img.surrounding_text = img.surrounding_text[: self.context_chars]

            # Try to find caption for the image
            for region in page_layout.get("title_regions", []):
                text = region.get("text", "").lower()
                if any(
                    keyword in text
                    for keyword in ["figure", "fig.", "hình", "diagram", "chart"]
                ):
                    img.caption = region.get("text", "")[:200]
                    break

        return images

    def _find_caption_near_image(
        self, page, image_bbox: tuple, search_distance: int = 100
    ) -> str:
        """
        Find caption text near an image by searching for keywords.

        Looks for patterns like:
        - "Figure X.Y: Description"
        - "Table X: Description"
        - "Fig. X - Description"
        - "Hình X.Y: Mô tả"

        Args:
            page: PyMuPDF page object
            image_bbox: Bounding box of the image (x0, y0, x1, y1)
            search_distance: Max distance in pixels to search for caption

        Returns:
            Caption text if found, empty string otherwise.
        """
        import re
        import fitz

        # Keywords to detect captions (case-insensitive)
        caption_patterns = [
            r"(?i)^fig(?:ure)?\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–—]?\s*.+",
            r"(?i)^table\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–—]?\s*.+",
            r"(?i)^picture\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–—]?\s*.+",
            r"(?i)^diagram\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–—]?\s*.+",
            r"(?i)^chart\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–—]?\s*.+",
            r"(?i)^hình\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–—]?\s*.+",
            r"(?i)^bảng\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–—]?\s*.+",
        ]

        try:
            # Get text blocks with positions
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)[
                "blocks"
            ]

            x0, y0, x1, y1 = image_bbox

            # Collect candidate caption texts with their distance from image
            candidates = []

            for block in blocks:
                if block.get("type") != 0:  # Skip non-text blocks
                    continue

                block_bbox = block.get("bbox", (0, 0, 0, 0))
                bx0, by0, bx1, by1 = block_bbox

                # Check if text block is near the image (below or above)
                # Below image
                if by0 >= y1 and by0 <= y1 + search_distance:
                    distance = by0 - y1
                    # Check horizontal overlap
                    if not (bx1 < x0 or bx0 > x1):
                        text = ""
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text += span.get("text", "")
                            text += " "
                        text = text.strip()
                        if text:
                            candidates.append(
                                {
                                    "text": text,
                                    "distance": distance,
                                    "position": "below",
                                }
                            )

                # Above image (less common but possible)
                if by1 <= y0 and by1 >= y0 - search_distance:
                    distance = y0 - by1
                    if not (bx1 < x0 or bx0 > x1):
                        text = ""
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text += span.get("text", "")
                            text += " "
                        text = text.strip()
                        if text:
                            candidates.append(
                                {
                                    "text": text,
                                    "distance": distance,
                                    "position": "above",
                                }
                            )

            # Sort by distance (closest first), prefer below
            candidates.sort(key=lambda c: (c["position"] != "below", c["distance"]))

            # Check each candidate for caption patterns
            for candidate in candidates:
                text = candidate["text"]
                for pattern in caption_patterns:
                    if re.match(pattern, text):
                        # Clean up and return
                        caption = text.strip()
                        # Limit length
                        if len(caption) > 300:
                            caption = caption[:300] + "..."
                        return caption

            # If no pattern matched, check for simple keyword presence in closest text
            if candidates:
                closest_text = candidates[0]["text"].lower()
                keywords = [
                    "figure",
                    "fig.",
                    "fig ",
                    "table",
                    "picture",
                    "diagram",
                    "chart",
                    "hình",
                    "bảng",
                    "biểu đồ",
                ]
                for kw in keywords:
                    if kw in closest_text:
                        caption = candidates[0]["text"].strip()
                        if len(caption) > 300:
                            caption = caption[:300] + "..."
                        return caption

            return ""

        except Exception as e:
            # Silently fail - caption detection is optional
            return ""

    def _extract_pdf_with_pymupdf(self, pdf_path: Path) -> list[ExtractedImage]:
        """Extract images using PyMuPDF (fitz) - primary method."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            extracted_images = []

            print(f"  Using PyMuPDF, {len(doc)} pages")

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get images directly from PDF
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]

                        # Use Pixmap to handle color spaces and masks correctly
                        pix = fitz.Pixmap(doc, xref)

                        # Check image size
                        if pix.width < self.min_width or pix.height < self.min_height:
                            pix = None
                            continue

                        # Handle alpha channel and color space properly
                        # First, convert non-RGB color spaces to RGB
                        if pix.n - pix.alpha < 3:  # Grayscale or CMYK
                            pix = fitz.Pixmap(fitz.csRGB, pix)

                        # Saving as PNG handles alpha transparency correctly, so we just keep it.
                        width = pix.width
                        height = pix.height

                        # Validate image content (check for black/empty images)
                        is_valid, reason, _ = self._is_valid_pixmap(pix)

                        if not is_valid:
                            pix = None
                            continue

                        image_data = pix.tobytes("png")
                        image_id = hashlib.md5(image_data).hexdigest()[:8]
                        image_filename = f"{pdf_path.stem}_p{page_num + 1}_img{img_index}_{image_id}.png"
                        image_path = self.output_dir / image_filename

                        # Save image
                        pix.save(str(image_path))
                        pix = None  # Free memory

                        # Get image position on page for caption detection
                        image_bbox = (0, 0, width, height)  # Default
                        try:
                            # Try to find where this image appears on the page
                            img_rects = page.get_image_rects(xref)
                            if img_rects:
                                rect = img_rects[0]  # Take first occurrence
                                image_bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                        except:
                            pass

                        # Find caption near image
                        caption = self._find_caption_near_image(page, image_bbox)

                        # Get surrounding text
                        text = page.get_text()

                        extracted_images.append(
                            ExtractedImage(
                                image_id=image_id,
                                image_path=str(image_path),
                                source_file=str(pdf_path),
                                page_number=page_num + 1,
                                bbox=image_bbox,
                                region_type="figure",
                                surrounding_text=text[: self.context_chars],
                                caption=caption,
                                description=f"Image from {pdf_path.name}, page {page_num + 1}",
                            )
                        )

                        print(
                            f"    Found image on page {page_num + 1}: {width}x{height}"
                        )
                    except Exception as e:
                        print(
                            f"    Error extracting image {img_index} on page {page_num + 1}: {e}"
                        )

            doc.close()
            return extracted_images

        except ImportError:
            print("  PyMuPDF not available")
            return []
        except Exception as e:
            print(f"  Error with PyMuPDF: {e}")
            return []

    def _extract_drawings_with_pymupdf(self, pdf_path: Path) -> list[ExtractedImage]:
        """Extract vector drawings (diagrams) by rendering drawing paths."""
        extracted_drawings = []
        try:
            import fitz

            doc = fitz.open(str(pdf_path))

            print(f"  Scanning for vector drawings...")

            for page_num in range(len(doc)):
                page = doc[page_num]
                drawings = page.get_drawings()

                if not drawings:
                    continue

                # Filter small drawings and group them
                valid_rects = []
                for d in drawings:
                    rect = d["rect"]
                    # Filter out very small paths (e.g. bullets, table lines)
                    if rect.width > 20 or rect.height > 20:
                        valid_rects.append(rect)

                if not valid_rects:
                    continue

                # Cluster rects to find diagram regions
                # Optimized approach: Sort by position and single-pass merge

                # 1. Sort by Y then X
                valid_rects.sort(key=lambda r: (r.y0, r.x0))

                clusters = []
                if valid_rects:
                    current_cluster = fitz.Rect(valid_rects[0])

                    for rect in valid_rects[1:]:
                        # Check if rect is close to current cluster
                        # Expand current cluster by merge distance for check
                        expanded = fitz.Rect(current_cluster)
                        expanded.x0 -= self.cluster_merge_distance
                        expanded.y0 -= self.cluster_merge_distance
                        expanded.x1 += self.cluster_merge_distance
                        expanded.y1 += self.cluster_merge_distance

                        if rect.intersects(expanded):
                            current_cluster.include_rect(rect)
                        else:
                            # Finish current cluster and start new one
                            clusters.append(current_cluster)
                            current_cluster = fitz.Rect(rect)

                    # Append the last cluster
                    clusters.append(current_cluster)

                # Process clusters
                for i, rect in enumerate(clusters):
                    # Check if cluster is big enough to be a diagram
                    if (
                        rect.width < self.min_diagram_size
                        or rect.height < self.min_diagram_size
                    ):
                        continue

                    # Render the region
                    # Use higher DPI for better quality
                    try:
                        pix = page.get_pixmap(clip=rect, dpi=150)

                        # Check validity using optimized check
                        is_valid, _, _ = self._is_valid_pixmap(pix)

                        if not is_valid:
                            pix = None
                            continue

                        image_data = pix.tobytes("png")
                        # Save
                        image_id = hashlib.md5(image_data).hexdigest()[:8]
                        image_filename = (
                            f"{pdf_path.stem}_p{page_num + 1}_drawing{i}_{image_id}.png"
                        )
                        image_path = self.output_dir / image_filename

                        pix.save(str(image_path))

                        # Get text within drawing region
                        text = page.get_text(clip=rect)

                        # Find caption near the drawing
                        drawing_bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                        caption = self._find_caption_near_image(page, drawing_bbox)

                        extracted_drawings.append(
                            ExtractedImage(
                                image_id=image_id,
                                image_path=str(image_path),
                                source_file=str(pdf_path),
                                page_number=page_num + 1,
                                bbox=drawing_bbox,
                                region_type="drawing",
                                surrounding_text=text[: self.context_chars],
                                caption=caption,
                                description=f"Drawing from {pdf_path.name}, page {page_num + 1}",
                            )
                        )
                        pix = None

                    except Exception as e:
                        print(
                            f"    Error rendering drawing on page {page_num + 1}: {e}"
                        )

            doc.close()
        except Exception as e:
            print(f"Error extracting drawings: {e}")

        return extracted_drawings

    def _extract_pdf_with_pdf2image(self, pdf_path: Path) -> list[ExtractedImage]:
        """Extract images using pdf2image and PP-Structure."""
        try:
            from pdf2image import convert_from_path

            extracted_images = []
            pages = convert_from_path(str(pdf_path), dpi=150)

            for page_num, page_image in enumerate(pages, start=1):
                print(f"  Processing page {page_num}/{len(pages)}...")

                # Save page as temporary image
                temp_path = self.output_dir / f"_temp_page_{page_num}.png"
                page_image.save(str(temp_path))

                # Extract images from this page
                page_images = self._extract_from_image(
                    temp_path, source_file=str(pdf_path), page_number=page_num
                )
                extracted_images.extend(page_images)

                # Clean up temp file
                temp_path.unlink(missing_ok=True)

            return extracted_images

        except ImportError:
            print("  pdf2image not available. Install poppler and pdf2image.")
            return []
        except Exception as e:
            print(f"  pdf2image error: {e}")
            return []

    def _extract_from_image(
        self, image_path: Path, source_file: str, page_number: int = 1
    ) -> list[ExtractedImage]:
        """
        Extract image regions from a single image using PP-Structure.

        Args:
            image_path: Path to the image.
            source_file: Original source file path.
            page_number: Page number in the source document.

        Returns:
            List of ExtractedImage objects.
        """
        extracted_images = []

        try:
            from PIL import Image
            import numpy as np

            # Run PP-Structure analysis
            results = self.structure_engine.predict(input=str(image_path))

            # Load original image for cropping
            original_image = Image.open(image_path)

            # Process results
            for result in results:
                # Get layout parsing result
                if hasattr(result, "layout_parsing_result"):
                    layout_result = result.layout_parsing_result
                elif isinstance(result, dict) and "layout_parsing_result" in result:
                    layout_result = result["layout_parsing_result"]
                else:
                    continue

                # Extract text content for context
                all_text = self._extract_text_from_result(result)

                # Process each detected region
                if isinstance(layout_result, dict):
                    boxes = layout_result.get("boxes", [])
                    for box_idx, box in enumerate(boxes):
                        region_type = box.get("type", "unknown")
                        bbox = box.get("bbox", box.get("coordinate", []))

                        # Filter by region type
                        if region_type in ["figure", "image", "chart", "picture"]:
                            if not self.extract_figures:
                                continue
                        elif region_type == "table":
                            if not self.extract_tables:
                                continue
                        else:
                            continue  # Skip text regions

                        if len(bbox) >= 4:
                            # Crop and save the image region
                            cropped = self._crop_region(original_image, bbox)

                            if cropped and self._is_valid_size(cropped):
                                image_id = hashlib.md5(
                                    f"{source_file}_{page_number}_{box_idx}".encode()
                                ).hexdigest()[:8]

                                image_filename = f"{Path(source_file).stem}_p{page_number}_{region_type}_{image_id}.{self.image_format}"
                                save_path = self.output_dir / image_filename
                                cropped.save(str(save_path))

                                # Get nearby text as context
                                nearby_text = self._get_nearby_text(box, layout_result)

                                extracted_images.append(
                                    ExtractedImage(
                                        image_id=image_id,
                                        image_path=str(save_path),
                                        source_file=source_file,
                                        page_number=page_number,
                                        bbox=tuple(bbox[:4]),
                                        region_type=region_type,
                                        surrounding_text=nearby_text
                                        or all_text[: self.context_chars],
                                        caption=box.get("caption", ""),
                                        description=f"{region_type} from page {page_number}",
                                    )
                                )

        except Exception as e:
            print(f"Error extracting from image: {e}")

        return extracted_images

    def _crop_region(self, image, bbox) -> Optional["Image.Image"]:
        """Crop a region from an image."""
        try:
            from PIL import Image

            # Handle different bbox formats
            if len(bbox) == 4:
                x1, y1, x2, y2 = bbox
            elif len(bbox) == 8:  # Polygon format
                x1 = min(bbox[0], bbox[2], bbox[4], bbox[6])
                y1 = min(bbox[1], bbox[3], bbox[5], bbox[7])
                x2 = max(bbox[0], bbox[2], bbox[4], bbox[6])
                y2 = max(bbox[1], bbox[3], bbox[5], bbox[7])
            else:
                return None

            # Ensure valid coordinates
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(image.width, int(x2)), min(image.height, int(y2))

            if x2 > x1 and y2 > y1:
                return image.crop((x1, y1, x2, y2))
            return None

        except Exception:
            return None

    def _is_valid_size(self, image) -> bool:
        """Check if image meets minimum size requirements."""
        return image.width >= self.min_width and image.height >= self.min_height

    def _extract_text_from_result(self, result) -> str:
        """Extract all text content from PP-Structure result."""
        texts = []

        try:
            if hasattr(result, "layout_parsing_result"):
                layout = result.layout_parsing_result
            elif isinstance(result, dict):
                layout = result.get("layout_parsing_result", {})
            else:
                return ""

            if isinstance(layout, dict):
                boxes = layout.get("boxes", [])
                for box in boxes:
                    if box.get("type") in ["text", "title", "paragraph"]:
                        texts.append(box.get("text", ""))
        except Exception:
            pass

        return " ".join(texts)

    def _get_nearby_text(self, target_box: dict, layout_result: dict) -> str:
        """Get text from regions near the target box."""
        if not isinstance(layout_result, dict):
            return ""

        target_bbox = target_box.get("bbox", target_box.get("coordinate", []))
        if len(target_bbox) < 4:
            return ""

        target_center_y = (target_bbox[1] + target_bbox[3]) / 2

        nearby_texts = []
        boxes = layout_result.get("boxes", [])

        for box in boxes:
            if box.get("type") in ["text", "title", "paragraph", "caption"]:
                box_bbox = box.get("bbox", box.get("coordinate", []))
                if len(box_bbox) >= 4:
                    box_center_y = (box_bbox[1] + box_bbox[3]) / 2

                    # Check if text is near (within 100 pixels vertically)
                    if abs(box_center_y - target_center_y) < 200:
                        text = box.get("text", "")
                        if text:
                            nearby_texts.append(text)

        return " ".join(nearby_texts[:3])  # Limit to 3 nearby text blocks

    def extract_from_directory(
        self, directory: Path, recursive: bool = True
    ) -> list[ExtractedImage]:
        """
        Extract images from all documents in a directory.

        Args:
            directory: Path to the directory.
            recursive: Whether to process subdirectories.

        Returns:
            List of all ExtractedImage objects.
        """
        directory = Path(directory)
        all_images = []

        pattern = "**/*" if recursive else "*"
        extensions = [".pdf", ".png", ".jpg", ".jpeg"]

        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                try:
                    images = self.extract_from_file(file_path)
                    all_images.extend(images)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

        return all_images

    def _is_valid_pixmap(self, pix) -> tuple[bool, str, dict]:
        """
        Check if pixmap is valid using direct buffer access (faster than PIL).
        Properly handles RGB/RGBA by excluding alpha channel from calculations.
        """
        stats = {"brightness": 0, "std_dev": 0, "dark_ratio": 0}
        try:
            # Get raw samples as numpy array
            samples = np.frombuffer(pix.samples, dtype=np.uint8)

            # Reshape to (H, W, C) for proper channel handling
            n_channels = pix.n
            height = pix.height
            width = pix.width

            # Reshape the samples
            pixels = samples.reshape((height, width, n_channels))

            # Extract only RGB channels (exclude alpha if present)
            if pix.alpha and n_channels >= 4:
                # RGBA - take only RGB
                rgb = pixels[:, :, :3]
            else:
                # RGB or grayscale
                rgb = pixels[:, :, : min(3, n_channels)]

            # Calculate grayscale using standard luminance formula
            # Y = 0.299*R + 0.587*G + 0.114*B
            if rgb.shape[2] == 3:
                gray = (
                    0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
                )
            else:
                gray = rgb[:, :, 0].astype(float)  # Already grayscale

            # Calculate statistics
            mean_val = np.mean(gray)
            std_val = np.std(gray)

            # Calculate dark pixel ratio (pixels with brightness < 30)
            dark_threshold = 30
            dark_pixels = np.sum(gray < dark_threshold)
            total_pixels = gray.size
            dark_ratio = dark_pixels / total_pixels if total_pixels > 0 else 0

            stats["brightness"] = mean_val
            stats["std_dev"] = std_val
            stats["dark_ratio"] = dark_ratio

            # Check brightness (avoid black images)
            if mean_val < self.min_brightness:
                return False, f"Too dark (mean={mean_val:.2f})", stats

            # Check variance (avoid solid color images)
            if std_val < self.min_std_dev:
                return False, f"Low variance (std={std_val:.2f})", stats

            # Check dark pixel ratio (avoid mostly black images)
            if dark_ratio > self.max_dark_pixel_ratio:
                return False, f"Too many dark pixels ({dark_ratio:.1%})", stats

            return True, "OK", stats

        except Exception as e:
            # Fallback to PIL method if something fails
            print(f"Error in fast validation: {e}")
            return self._is_valid_image(pix.tobytes("png"))

    def _is_valid_image(self, image_data: bytes) -> tuple[bool, str, dict]:
        """
        Check if image is valid (not too dark, not solid color).

        Args:
            image_data: Image data in bytes (PNG format).

        Returns:
            Tuple (is_valid, reason, stats_dict)
        """
        stats = {"brightness": 0, "std_dev": 0}
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # Convert to grayscale for analysis
                gray = img.convert("L")
                np_img = np.array(gray)

                # Calculate statistics
                mean_brightness = np.mean(np_img)
                std_dev = np.std(np_img)

                stats["brightness"] = mean_brightness
                stats["std_dev"] = std_dev

                # Check brightness (avoid black images)
                if mean_brightness < self.min_brightness:
                    return (
                        False,
                        f"Too dark (brightness={mean_brightness:.2f} < {self.min_brightness})",
                        stats,
                    )

                # Check variance (avoid solid color images)
                if std_dev < self.min_std_dev:
                    return (
                        False,
                        f"Low variance (std_dev={std_dev:.2f} < {self.min_std_dev})",
                        stats,
                    )

                return True, "OK", stats
        except Exception as e:
            return False, f"Error: {e}", stats

# Global extractor instance
_extractor: Optional[ImageExtractor] = None


def get_image_extractor() -> ImageExtractor:
    """Get or create the global image extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = ImageExtractor()
    return _extractor
