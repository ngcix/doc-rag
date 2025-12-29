"""
PyMuPDF Smart Image Extraction Module

This module provides smart image extraction from PDF documents using PyMuPDF.
Based on the solution from simple-notebook repository.

Features:
- Detects embedded bitmap images
- Clusters vector drawings into diagram regions
- Merges overlapping/nearby elements
- Captures surrounding text as context
"""
from typing import Optional
from pathlib import Path
import hashlib
import re

from config import settings, ensure_directories, EXTRACTED_IMAGES_DIR
from src.image_extraction.image_info import ExtractedImage

try:
    import fitz
except ImportError:
    fitz = None



class UnionFind:
    """Helper class for Union-Find algorithm."""
    def __init__(self, size):
        self.parent = list(range(size))
    
    def find(self, i):
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]
    
    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j
            return True
        return False


class PyMuImageExtractor:
    """
    Extracts image regions from PDF documents using PyMuPDF smart cropping.

    Features:
    - Detects embedded bitmap images
    - Clusters vector drawings into diagrams
    - Merges nearby elements
    - Captures surrounding text as context
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        min_width: int = 50,
        min_height: int = 50,
        cluster_merge_distance: int = 50,
        min_drawing_size: int = 20,
        min_diagram_size: int = 100,
        context_chars: int = 5000,
    ):
        """
        Initialize the PyMuPDF Image Extractor.

        Args:
            output_dir: Directory to save extracted images.
            min_width: Minimum width to consider as valid image.
            min_height: Minimum height to consider as valid image.
            cluster_merge_distance: Pixels to merge nearby drawings.
            min_drawing_size: Minimum size for a drawing path.
            min_diagram_size: Minimum size for a clustered diagram.
            context_chars: Maximum characters for surrounding text.
        """
        self.output_dir = output_dir or EXTRACTED_IMAGES_DIR
        self.min_width = min_width
        self.min_height = min_height
        self.cluster_merge_distance = cluster_merge_distance
        self.min_drawing_size = min_drawing_size
        self.min_diagram_size = min_diagram_size
        self.context_chars = context_chars

        ensure_directories()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if fitz is None:
            print("Warning: PyMuPDF (fitz) is not installed. Image extraction will not work.")
            print("Install with: pip install pymupdf")

    def _extract_tags_from_text(self, text: str) -> str:
        """
        Extract tags from text using regex patterns.
        Looks for 'Figure X.Y: ...' or 'Table X.Y: ...'
        """
        tags = []
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
                tag = m.group(1).strip()
                if 5 < len(tag) < 100:
                    tags.append(tag)

        return ",".join(list(set(tags)))

    def extract_from_file(
        self, 
        file_path: Path, 
        fullpage_mode: bool = False
    ) -> list[ExtractedImage]:
        """
        Extract images from a file.

        Args:
            file_path: Path to the file.
            fullpage_mode: Ignored for PyMuPDF mode (always smart crop).

        Returns:
            List of ExtractedImage objects.
        """
        file_path = Path(file_path)

        if file_path.suffix.lower() == '.pdf':
            return self.extract_from_pdf(file_path)
        else:
            print(f"  Unsupported file type: {file_path.suffix}")
            return []

    def extract_from_pdf(self, pdf_path: Path) -> list[ExtractedImage]:
        """
        Extract images from a PDF file using smart cropping.

        Detects and extracts:
        - Embedded bitmap images
        - Vector drawings and diagrams
        - Figures and charts

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of ExtractedImage objects.
        """
        if fitz is None:
            print("  PyMuPDF not available. Install with: pip install pymupdf")
            return []

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        print(f"  Using PyMuPDF smart cropping...")
        return self._extract_smart_crops(pdf_path)

    def _extract_smart_crops(self, pdf_path: Path) -> list[ExtractedImage]:
        """
        Smartly detect and crop figures/diagrams from PDF pages using PyMuPDF.
        """
        try:
            doc = fitz.open(str(pdf_path))
            extracted_images = []

            print(f"  Smart scanning {len(doc)} pages...")

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_images = []

                # A. Get Bitmaps (Embedded Images)
                img_infos = page.get_image_info(xrefs=True)
                for img in img_infos:
                    bbox = fitz.Rect(img['bbox'])
                    if bbox.width >= self.min_width and bbox.height >= self.min_height:
                        page_images.append(bbox)

                # B. Get Vector Drawings (Clustered)
                drawing_clusters = self._cluster_drawings(page)
                page_images.extend(drawing_clusters)

                # C. Merge Overlapping/Nearby Regions
                merged_regions = self._merge_nearby_blocks(page_images)

                # D. Render and Save
                for i, rect in enumerate(merged_regions):
                    try:
                        # Render region
                        pix = page.get_pixmap(clip=rect, dpi=150)

                        # Validate size
                        if pix.width < self.min_width or pix.height < self.min_height:
                            continue

                        image_data = pix.tobytes("png")
                        # Use readable ID instead of hash for easier tagging
                        # Format: filename_p{page}_crop_{number}
                        image_id = f"{pdf_path.stem}_p{page_num + 1}_crop_{i + 1}"
                        image_filename = f"{image_id}.png"
                        image_path = self.output_dir / image_filename

                        pix.save(str(image_path))

                        # Get context text (caption/surrounding) - EXPANDED WINDOW
                        context_rect = fitz.Rect(rect)
                        context_rect.y1 += 150  # Look 150px below for caption
                        context_rect.y0 -= 80   # Look 80px above for title
                        context_rect.x0 -= 20   # Expand horizontally
                        context_rect.x1 += 20
                        text = page.get_text(clip=context_rect)

                        # Truncate context text
                        text = text[:self.context_chars] if text else ""

                        # Auto-extract tags from context text
                        extracted_tags = self._extract_tags_from_text(text)

                        extracted_images.append(ExtractedImage(
                            image_id=image_id,
                            image_path=str(image_path),
                            source_file=str(pdf_path),
                            page_number=page_num + 1,
                            bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                            region_type="smart_crop",
                            surrounding_text=text,
                            caption="",
                            description=f"Smart crop from {pdf_path.name}, page {page_num + 1}",
                            tags=extracted_tags,
                        ))

                        print(f"    Page {page_num + 1}: crop {i + 1} ({int(rect.width)}x{int(rect.height)})")

                    except Exception as e:
                        print(f"    Error saving crop {i} on page {page_num + 1}: {e}")

            doc.close()
            print(f"  Extracted {len(extracted_images)} smart crops from {pdf_path.name}")
            return extracted_images

        except Exception as e:
            print(f"  Error in smart cropping: {e}")
            return []

    def _cluster_drawings(self, page) -> list:
        """
        Cluster vector drawings into diagram regions using Grid-based Union-Find.
        O(N) complexity for sparse grids.
        """
        drawings = page.get_drawings()
        if not drawings:
            return []

        # 1. Filter valid rects
        valid_rects = []
        for d in drawings:
            rect = d["rect"]
            if rect.width > 5 or rect.height > 5:
                valid_rects.append(rect)
        
        n = len(valid_rects)
        if n == 0:
            return []
        if n == 1:
            return valid_rects
        
        # 2. Setup Union-Find and Grid
        uf = UnionFind(n)
        
        # Grid cell size = merge distance. 
        cell_size = self.cluster_merge_distance
        grid = {}
        
        for i, rect in enumerate(valid_rects):
            start_x = int(rect.x0 // cell_size)
            end_x = int(rect.x1 // cell_size)
            start_y = int(rect.y0 // cell_size)
            end_y = int(rect.y1 // cell_size)
            
            for gx in range(start_x, end_x + 1):
                for gy in range(start_y, end_y + 1):
                    key = (gx, gy)
                    if key not in grid:
                        grid[key] = []
                    grid[key].append(i)
        
        # 3. Check adjacencies within grid cells
        dist = self.cluster_merge_distance
        
        for key, indices in grid.items():
            if len(indices) < 2:
                continue
                
            for i_idx in range(len(indices)):
                idx_a = indices[i_idx]
                rect_a = valid_rects[idx_a]
                
                # Expand A
                expanded_a = fitz.Rect(rect_a)
                expanded_a.x0 -= dist; expanded_a.y0 -= dist
                expanded_a.x1 += dist; expanded_a.y1 += dist
                
                for j_idx in range(i_idx + 1, len(indices)):
                    idx_b = indices[j_idx]
                    
                    if uf.find(idx_a) == uf.find(idx_b):
                        continue
                    
                    rect_b = valid_rects[idx_b]
                    if rect_b.intersects(expanded_a):
                        uf.union(idx_a, idx_b)

        # 4. Group by root
        groups = {}
        for i in range(n):
            root = uf.find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(valid_rects[i])
            
        # 5. Create final rects
        final_clusters = []
        for root, rects in groups.items():
            cluster_rect = fitz.Rect(rects[0])
            for r in rects[1:]:
                cluster_rect.include_rect(r)
                
            if cluster_rect.width >= self.min_diagram_size and cluster_rect.height >= self.min_diagram_size:
                final_clusters.append(cluster_rect)
                
        return final_clusters

    def _merge_nearby_blocks(self, rects: list) -> list:
        """Merge overlapping or nearby bounding boxes."""
        if not rects:
            return []

        merged = []
        sorted_rects = sorted(rects, key=lambda r: (r.y0, r.x0))

        current = fitz.Rect(sorted_rects[0])

        for rect in sorted_rects[1:]:
            # Check if close enough to merge
            expanded = fitz.Rect(current)
            dist = self.cluster_merge_distance
            expanded.x0 -= dist
            expanded.y0 -= dist
            expanded.x1 += dist
            expanded.y1 += dist

            if rect.intersects(expanded):
                current.include_rect(rect)
            else:
                merged.append(current)
                current = fitz.Rect(rect)

        merged.append(current)
        return merged

    def extract_from_directory(
        self,
        directory: Path,
        recursive: bool = True
    ) -> list[ExtractedImage]:
        """
        Extract images from all PDFs in a directory.

        Args:
            directory: Directory containing PDF files.
            recursive: Whether to search recursively.

        Returns:
            List of all extracted images.
        """
        directory = Path(directory)
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(directory.glob(pattern))

        all_images = []
        for pdf_file in pdf_files:
            images = self.extract_from_pdf(pdf_file)
            all_images.extend(images)

        return all_images

    def get_vectorization_data(self, images: list[ExtractedImage]) -> list[dict]:
        """
        Prepare extracted images for vectorization.

        Args:
            images: List of ExtractedImage objects.

        Returns:
            List of dicts ready for vectorization.
        """
        data = []
        for img in images:
            data.append({
                "chunk_id": f"img_{img.image_id}",
                "content": img.get_vectorization_text(),
                "metadata": {
                    "type": "extracted_image",
                    "region_type": img.region_type,
                    "image_path": img.image_path,
                    "source_file": img.source_file,
                    "page_number": img.page_number,
                    "bbox": str(img.bbox),
                    "tags": img.tags,
                },
                "source_file": img.source_file
            })
        return data


# Global extractor instance
_extractor: Optional[PyMuImageExtractor] = None


def get_image_extractor() -> PyMuImageExtractor:
    """Get or create the global PyMuPDF image extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = PyMuImageExtractor()
    return _extractor
