# 🖼️ Luồng Trích Xuất Ảnh (Image Extraction Flow)

## 1. Tổng Quan

Module `src/image_extraction/extractor.py` cung cấp 2 chế độ trích xuất:

| Chế độ | Command | Mô tả |
|--------|---------|-------|
| **Full-page** | `-fp` | Capture toàn bộ trang chứa hình |
| **PyMuPDF** | `-pymu` | Trích xuất từng ảnh riêng lẻ |

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMAGE EXTRACTION MODULE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │  ImageExtractor  │  ◀── Main class                                       │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ├── extract_from_file(pdf_path, fullpage_mode)                    │
│           │           │                                                      │
│           │   ┌───────┴───────────────────────────────────┐                 │
│           │   │                                           │                 │
│           │   ▼                                           ▼                 │
│   ┌───────────────────────┐               ┌───────────────────────────┐     │
│   │  FULL-PAGE MODE       │               │  PYMUPDF MODE             │     │
│   │  _extract_fullpage_   │               │  extract_from_pdf()       │     │
│   │  from_pdf()           │               │                           │     │
│   └───────────────────────┘               └───────────────────────────┘     │
│           │                                           │                     │
│           │                               ┌───────────┴───────────┐         │
│           │                               │                       │         │
│           │                               ▼                       ▼         │
│           │               ┌─────────────────────┐   ┌─────────────────────┐ │
│           │               │ _extract_pdf_with_  │   │ _extract_drawings_  │ │
│           │               │ pymupdf()           │   │ with_pymupdf()      │ │
│           │               └─────────────────────┘   └─────────────────────┘ │
│           │                               │                       │         │
│           │                               ▼                       │         │
│           │               ┌─────────────────────┐                 │         │
│           │               │ _analyze_pdf_layout │ ◀── Optional    │         │
│           │               │ _with_ppstructure() │     enrichment  │         │
│           │               └─────────────────────┘                 │         │
│           │                                                       │         │
│           └───────────────────────────────────────────────────────┘         │
│                                           │                                  │
│                                           ▼                                  │
│                              ┌─────────────────────┐                        │
│                              │  List[ExtractedImage]│                        │
│                              └─────────────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Full-Page Mode Flow (`-fp`)

### 3.1 Tổng quan

```
pdf_path
    │
    ▼
_extract_fullpage_from_pdf(pdf_path)
    │
    ├── For each page in PDF:
    │   │
    │   ├── Check if page has images/drawings
    │   │   ├── page.get_images() → embedded images
    │   │   └── page.get_drawings() → vector drawings
    │   │
    │   ├── If has content:
    │   │   ├── Render page at 150 DPI
    │   │   ├── Save as PNG
    │   │   ├── Extract page text
    │   │   └── Auto-generate tags
    │   │
    │   └── Create ExtractedImage object
    │
    └── Return: List[ExtractedImage]
```

### 3.2 Chi tiết code

```python
# File: src/image_extraction/extractor.py

def _extract_fullpage_from_pdf(self, pdf_path: Path) -> list[ExtractedImage]:
    import fitz  # PyMuPDF
    
    extracted_images = []
    doc = fitz.open(str(pdf_path))
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. CHECK FOR IMAGES
        has_images = False
        image_list = page.get_images(full=True)
        for img in image_list:
            xref = img[0]
            pix_check = fitz.Pixmap(doc, xref)
            if pix_check.width >= self.min_width and pix_check.height >= self.min_height:
                has_images = True
                break
        
        # 2. CHECK FOR DRAWINGS (if no images)
        if not has_images and self.extract_figures:
            drawings = page.get_drawings()
            for d in drawings:
                rect = d["rect"]
                if rect.width > self.min_drawing_size:
                    has_images = True
                    break
        
        if not has_images:
            continue  # Skip pages without visual content
        
        # 3. RENDER FULL PAGE
        pix = page.get_pixmap(dpi=150)
        
        # 4. GENERATE DETERMINISTIC ID
        image_id = f"{pdf_path.name}_p{page_num + 1}"
        image_path = self.output_dir / f"{image_id}.png"
        pix.save(str(image_path))
        
        # 5. EXTRACT TEXT
        text = page.get_text()
        
        # 6. AUTO-GENERATE TAGS
        extracted_tags = self._extract_tags_from_text(text)
        
        # 7. CREATE RESULT
        extracted_images.append(ExtractedImage(
            image_id=image_id,
            image_path=str(image_path),
            source_file=str(pdf_path),
            page_number=page_num + 1,
            bbox=(0, 0, pix.width, pix.height),
            region_type="fullpage",
            surrounding_text=text[:10000],
            caption=f"Full page {page_num + 1}",
            tags=extracted_tags
        ))
    
    doc.close()
    return extracted_images
```

### 3.3 Auto-Tagging Logic

```python
def _extract_tags_from_text(self, text: str) -> str:
    """
    Extract tags using regex patterns.
    """
    tags = []
    patterns = [
        r"(Figure\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        r"(Table\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        r"(Fig\.\s*\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        # Vietnamese support
        r"(Hình\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)",
        r"(Bảng\s+\d+(\.\d+)?\s*[:.-]\s*.*?)(?=\n|\.)"
    ]
    
    for p in patterns:
        matches = re.finditer(p, text, re.IGNORECASE)
        for m in matches:
            tag = m.group(1).strip()
            if 5 < len(tag) < 100:
                tags.append(tag)
    
    return ",".join(list(set(tags)))
```

**Ví dụ:**
```
Input text: "Figure 4.1: Media payload format\nThis diagram shows..."
Output tags: "Figure 4.1: Media payload format"
```

### 3.4 Full-page Output Structure

```python
ExtractedImage(
    image_id="HID_v1.1.1.pdf_p30",
    image_path="data/extracted_images/HID_v1.1.1.pdf_p30.png",
    source_file="data/documents/HID_v1.1.1.pdf",
    page_number=30,
    bbox=(0, 0, 1275, 1650),  # Full page dimensions
    region_type="fullpage",
    surrounding_text="Figure 4.1: Media payload format...",  # Up to 10000 chars
    caption="Full page 30 of HID_v1.1.1.pdf",
    tags="Figure 4.1: Media payload format"
)
```

## 4. PyMuPDF Mode Flow (`-pymu`)

### 4.1 Tổng quan

```
pdf_path
    │
    ▼
extract_from_pdf(pdf_path)
    │
    ├── 1. Extract Embedded Images
    │   └── _extract_pdf_with_pymupdf()
    │       ├── page.get_images() → List of image refs
    │       ├── fitz.Pixmap(doc, xref) → Extract image data
    │       ├── Validate quality (_is_valid_pixmap)
    │       └── Find caption (_find_caption_near_image)
    │
    ├── 2. Extract Vector Drawings
    │   └── _extract_drawings_with_pymupdf()
    │       ├── page.get_drawings() → List of drawing paths
    │       ├── Cluster nearby drawings
    │       ├── Render clustered regions
    │       └── Validate and save
    │
    └── 3. Enrich with PP-Structure (optional)
        └── _analyze_pdf_layout_with_ppstructure()
            ├── Render pages as temp images
            ├── Run PP-StructureV3 detection
            └── Extract text regions for context
```

### 4.2 Extract Embedded Images

```python
def _extract_pdf_with_pymupdf(self, pdf_path: Path) -> list[ExtractedImage]:
    import fitz
    
    doc = fitz.open(str(pdf_path))
    extracted_images = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            
            # Extract image data
            pix = fitz.Pixmap(doc, xref)
            
            # Size filter
            if pix.width < self.min_width or pix.height < self.min_height:
                continue
            
            # Color space handling
            if pix.n - pix.alpha < 3:  # Grayscale/CMYK
                pix = fitz.Pixmap(fitz.csRGB, pix)
            
            # Quality validation
            is_valid, reason, stats = self._is_valid_pixmap(pix)
            if not is_valid:
                continue
            
            # Save image
            image_data = pix.tobytes("png")
            image_id = hashlib.md5(image_data).hexdigest()[:8]
            image_filename = f"{pdf_path.stem}_p{page_num + 1}_img{img_index}_{image_id}.png"
            image_path = self.output_dir / image_filename
            pix.save(str(image_path))
            
            # Find caption near image
            image_bbox = self._get_image_position(page, xref)
            caption = self._find_caption_near_image(page, image_bbox)
            
            # Get surrounding text
            text = page.get_text()
            
            extracted_images.append(ExtractedImage(
                image_id=image_id,
                image_path=str(image_path),
                source_file=str(pdf_path),
                page_number=page_num + 1,
                bbox=image_bbox,
                region_type="figure",
                surrounding_text=text[:self.context_chars],
                caption=caption
            ))
    
    return extracted_images
```

### 4.3 Quality Validation

```python
def _is_valid_pixmap(self, pix) -> tuple[bool, str, dict]:
    """
    Validate image quality to filter out:
    - Black/empty images
    - Solid color images
    - Mostly dark images
    """
    import numpy as np
    
    # Get raw samples as numpy array
    samples = np.frombuffer(pix.samples, dtype=np.uint8)
    pixels = samples.reshape((pix.height, pix.width, pix.n))
    
    # Extract RGB only (exclude alpha)
    if pix.alpha:
        rgb = pixels[:, :, :3]
    else:
        rgb = pixels[:, :, :min(3, pix.n)]
    
    # Calculate grayscale (luminance formula)
    gray = 0.299 * rgb[:,:,0] + 0.587 * rgb[:,:,1] + 0.114 * rgb[:,:,2]
    
    # Statistics
    mean_val = np.mean(gray)
    std_val = np.std(gray)
    dark_ratio = np.sum(gray < 30) / gray.size
    
    # Validation checks
    if mean_val < self.min_brightness:  # 30.0
        return False, "Too dark", {}
    if std_val < self.min_std_dev:  # 15.0
        return False, "Low variance (solid color)", {}
    if dark_ratio > self.max_dark_pixel_ratio:  # 0.85
        return False, "Too many dark pixels", {}
    
    return True, "OK", {"brightness": mean_val, "std_dev": std_val}
```

**Validation Flow:**

```
Image Data
    │
    ▼
Calculate Statistics
    ├── Mean brightness (0-255)
    ├── Standard deviation
    └── Dark pixel ratio
    │
    ▼
┌───────────────────────────────────────┐
│  Check 1: Brightness >= 30?           │
│  ├── No → Reject (too dark)           │
│  └── Yes → Continue                   │
├───────────────────────────────────────┤
│  Check 2: Std Dev >= 15?              │
│  ├── No → Reject (solid color)        │
│  └── Yes → Continue                   │
├───────────────────────────────────────┤
│  Check 3: Dark ratio <= 85%?          │
│  ├── No → Reject (mostly black)       │
│  └── Yes → ACCEPT                     │
└───────────────────────────────────────┘
```

### 4.4 Extract Vector Drawings

```python
def _extract_drawings_with_pymupdf(self, pdf_path: Path) -> list[ExtractedImage]:
    import fitz
    
    doc = fitz.open(str(pdf_path))
    extracted_drawings = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        drawings = page.get_drawings()
        
        if not drawings:
            continue
        
        # 1. FILTER SMALL DRAWINGS
        valid_rects = []
        for d in drawings:
            rect = d["rect"]
            if rect.width > 20 or rect.height > 20:
                valid_rects.append(rect)
        
        # 2. CLUSTER NEARBY DRAWINGS
        valid_rects.sort(key=lambda r: (r.y0, r.x0))
        clusters = []
        current_cluster = fitz.Rect(valid_rects[0])
        
        for rect in valid_rects[1:]:
            # Expand for proximity check
            expanded = fitz.Rect(current_cluster)
            expanded.x0 -= self.cluster_merge_distance  # 50px
            expanded.y0 -= self.cluster_merge_distance
            expanded.x1 += self.cluster_merge_distance
            expanded.y1 += self.cluster_merge_distance
            
            if rect.intersects(expanded):
                current_cluster.include_rect(rect)  # Merge
            else:
                clusters.append(current_cluster)
                current_cluster = fitz.Rect(rect)
        
        clusters.append(current_cluster)
        
        # 3. RENDER AND SAVE CLUSTERS
        for i, rect in enumerate(clusters):
            if rect.width < self.min_diagram_size:  # 100px
                continue
            
            pix = page.get_pixmap(clip=rect, dpi=150)
            
            is_valid, _, _ = self._is_valid_pixmap(pix)
            if not is_valid:
                continue
            
            # Save drawing region
            image_id = hashlib.md5(pix.tobytes()).hexdigest()[:8]
            image_filename = f"{pdf_path.stem}_p{page_num + 1}_drawing{i}_{image_id}.png"
            pix.save(str(self.output_dir / image_filename))
            
            # Get text within drawing
            text = page.get_text(clip=rect)
            caption = self._find_caption_near_image(page, rect)
            
            extracted_drawings.append(ExtractedImage(
                image_id=image_id,
                image_path=str(self.output_dir / image_filename),
                region_type="drawing",
                surrounding_text=text[:self.context_chars],
                caption=caption
            ))
    
    return extracted_drawings
```

**Clustering Logic:**

```
Original drawings (scattered):
┌─────────────────────────────────────┐
│  ┌───┐                              │
│  │ A │    ┌───────┐                 │
│  └───┘    │   B   │   ┌───┐         │
│           └───────┘   │ C │         │
│  ┌───────────────┐    └───┘         │
│  │      D        │                  │
│  └───────────────┘                  │
└─────────────────────────────────────┘

After clustering (merge distance = 50px):
┌─────────────────────────────────────┐
│  ┌─────────────────────┐            │
│  │     Cluster 1       │  ┌───┐     │
│  │   (A + B merged)    │  │ C │     │  ← C too far
│  └─────────────────────┘  └───┘     │
│  ┌───────────────┐                  │
│  │   Cluster 2   │                  │
│  │      (D)      │                  │
│  └───────────────┘                  │
└─────────────────────────────────────┘
```

### 4.5 Caption Detection

```python
def _find_caption_near_image(self, page, image_bbox: tuple, search_distance: int = 100) -> str:
    """
    Find caption text near an image.
    Searches below and above the image for patterns like:
    - "Figure X.Y: Description"
    - "Table X: Description"
    """
    import re
    import fitz
    
    caption_patterns = [
        r"(?i)^fig(?:ure)?\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–]?\s*.+",
        r"(?i)^table\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–]?\s*.+",
        r"(?i)^diagram\.?\s*\d+[\.\-\:]?\s*\d*\s*[:\-–]?\s*.+",
    ]
    
    # Get text blocks with positions
    blocks = page.get_text("dict")["blocks"]
    x0, y0, x1, y1 = image_bbox
    
    candidates = []
    
    for block in blocks:
        if block.get("type") != 0:  # Skip non-text
            continue
        
        bx0, by0, bx1, by1 = block.get("bbox")
        
        # Check if text is BELOW image
        if by0 >= y1 and by0 <= y1 + search_distance:
            # Check horizontal overlap
            if not (bx1 < x0 or bx0 > x1):
                text = self._extract_block_text(block)
                candidates.append({
                    "text": text,
                    "distance": by0 - y1,
                    "position": "below"
                })
        
        # Check if text is ABOVE image
        if by1 <= y0 and by1 >= y0 - search_distance:
            if not (bx1 < x0 or bx0 > x1):
                text = self._extract_block_text(block)
                candidates.append({
                    "text": text,
                    "distance": y0 - by1,
                    "position": "above"
                })
    
    # Sort: prefer below, then by distance
    candidates.sort(key=lambda c: (c["position"] != "below", c["distance"]))
    
    # Match patterns
    for candidate in candidates:
        for pattern in caption_patterns:
            if re.match(pattern, candidate["text"]):
                return candidate["text"][:300]
    
    return ""
```

## 5. PP-Structure Enrichment (Optional)

### 5.1 Flow

```
_analyze_pdf_layout_with_ppstructure(pdf_path, pages_to_analyze)
    │
    ├── 1. Render pages to temp PNG images
    │
    ├── 2. Run PP-StructureV3.predict(images)
    │   └── Returns layout detection results:
    │       - text_regions
    │       - figure_regions
    │       - table_regions
    │       - title_regions
    │
    └── 3. Merge layout info with extracted images
```

### 5.2 PP-Structure Integration

```python
def _init_structure_engine(self):
    """Initialize PP-Structure engine."""
    from paddleocr import PPStructureV3
    
    engine = PPStructureV3(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
    )
    return engine

def _analyze_pdf_layout_with_ppstructure(self, pdf_path, pages_to_analyze):
    import fitz
    
    doc = fitz.open(str(pdf_path))
    temp_paths = []
    
    # 1. Render pages
    for page_num in pages_to_analyze:
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=150)
        temp_path = self.output_dir / f"_temp_page_{page_num}.png"
        pix.save(str(temp_path))
        temp_paths.append(temp_path)
    
    # 2. Batch process with PP-Structure
    image_paths = [str(p) for p in temp_paths]
    results = self.structure_engine.predict(input=image_paths)
    
    # 3. Parse results
    layout_info = {}
    for idx, result in enumerate(results):
        page_layout = {
            "text_regions": [],
            "figure_regions": [],
            "table_regions": [],
            "title_regions": [],
        }
        
        layout_result = result.layout_parsing_result
        for box in layout_result.get('boxes', []):
            region_type = box.get('type').lower()
            region_data = {
                "bbox": box.get('bbox'),
                "text": box.get('text'),
                "type": region_type,
            }
            
            if region_type in ['text', 'paragraph']:
                page_layout["text_regions"].append(region_data)
            elif region_type in ['figure', 'image', 'chart']:
                page_layout["figure_regions"].append(region_data)
            # ... etc
        
        layout_info[pages_to_analyze[idx]] = page_layout
    
    # 4. Cleanup temp files
    for temp_path in temp_paths:
        temp_path.unlink()
    
    return layout_info
```

## 6. Vectorization Data Preparation

```python
def get_vectorization_data(self, images: list[ExtractedImage]) -> list[dict]:
    """Prepare data for vectorization."""
    data = []
    for img in images:
        data.append({
            "chunk_id": img.image_id,
            "content": img.get_vectorization_text(),  # ← Key method
            "metadata": {
                "type": "extracted_image",
                "region_type": img.region_type,
                "image_path": img.image_path,
                "source_file": img.source_file,
                "page_number": img.page_number,
                "tags": img.tags
            },
            "source_file": img.source_file
        })
    return data

# ExtractedImage.get_vectorization_text()
def get_vectorization_text(self) -> str:
    parts = []
    if self.caption:
        parts.append(f"Caption: {self.caption}")
    if self.tags:
        # BOOST TAGS - repeat 3 times!
        parts.append(f"Tags: {self.tags}, {self.tags}, {self.tags}")
    if self.description:
        parts.append(f"Description: {self.description}")
    if self.surrounding_text:
        parts.append(f"Context: {self.surrounding_text}")
    parts.append(f"Type: {self.region_type}")
    parts.append(f"Source: {Path(self.source_file).name}, Page {self.page_number}")
    return "\n".join(parts)
```

**Ví dụ output:**
```
Tags: Figure 4.1: Media payload format, Figure 4.1: Media payload format, Figure 4.1: Media payload format
Caption: Figure 4.1: Media payload format
Context: The media payload format consists of...
Type: fullpage
Source: HID_v1.1.1.pdf, Page 30
```

## 7. So Sánh 2 Chế Độ

| Aspect | Full-page (`-fp`) | PyMuPDF (`-pymu`) |
|--------|-------------------|-------------------|
| **Output** | Toàn trang | Từng ảnh riêng |
| **Context** | Full page text (10K chars) | Limited (2K chars) |
| **Tags** | Auto-generated | From caption |
| **Quality** | Consistent 150 DPI | Original resolution |
| **Use case** | RAG, context search | Asset extraction |
| **File size** | Larger | Smaller |
| **Processing** | Faster | Slower (more ops) |

## 8. Thư Viện Sử Dụng

| Thư viện | Chức năng |
|----------|-----------|
| **PyMuPDF (fitz)** | PDF parsing, rendering, image extraction |
| **PaddleOCR** | Layout analysis (PP-Structure) |
| **PIL/Pillow** | Image processing |
| **NumPy** | Image validation statistics |
| **hashlib** | Generate image IDs |

