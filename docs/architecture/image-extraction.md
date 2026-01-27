# 🖼️ Image Extraction Architecture

## Module Overview

```
src/image_extraction/
├── __init__.py              # Factory: get_image_extractor()
├── extractor.py             # Full-page extraction (PyMuPDF)
├── docling_extractor.py     # Docling legacy
├── image_info.py            # ExtractedImage dataclass
└── docling/                 # Docling AI module
    ├── __main__.py
    ├── document.py
    ├── extractor.py
    ├── model.py
    └── processor.py
```

## Extraction Modes

| Mode | Command | Module | Description |
|------|---------|--------|-------------|
| Full-page | `-fp` | `extractor.py` | Capture toàn trang |
| Docling | `-dl` | `docling/` | AI layout detection |
| Docling Legacy | `-dl1` | `docling_extractor.py` | Phiên bản cũ |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMAGE EXTRACTION MODULE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │  get_image_      │  ◀── Factory function                                 │
│  │  extractor(mode) │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ├── mode="fp" ─────────▶ extractor.py (PyMuPDF)                   │
│           ├── mode="dl" ─────────▶ docling/extractor.py (RT-DETR)           │
│           └── mode="dl1" ────────▶ docling_extractor.py (Legacy)            │
│                                                                              │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    List[ExtractedImage]                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Full-Page Mode (`-fp`)

### Flow

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
    │   │   ├── Save as PNG/JPEG
    │   │   ├── Extract page text
    │   │   └── Auto-generate tags (regex)
    │   │
    │   └── Create ExtractedImage object
    │
    └── Return: List[ExtractedImage]
```

### Auto-Tagging

Patterns được phát hiện:
- `Figure X.Y: Description`
- `Table X: Description`
- `Fig. X - Description`
- `Hình X.Y: Mô tả` (Vietnamese)
- `Bảng X: Mô tả` (Vietnamese)

## Docling Mode (`-dl`)

### Flow

```
pdf_path
    │
    ▼
docling.get_image_extractor()
    │
    ├── Load Docling model (RT-DETR)
    │
    ├── For each page:
    │   │
    │   ├── Layout Detection
    │   │   └── Detect figures, tables, charts
    │   │
    │   ├── Region Extraction
    │   │   └── Crop detected regions
    │   │
    │   └── Context Extraction
    │       └── Get surrounding text
    │
    └── Return: List[ExtractedImage]
```

## ExtractedImage Dataclass

```python
@dataclass
class ExtractedImage:
    image_id: str           # Unique ID
    image_path: str         # Path to saved image
    source_file: str        # Original PDF path
    page_number: int        # Page number
    bbox: tuple             # (x1, y1, x2, y2)
    region_type: str        # "fullpage", "figure", "table"
    surrounding_text: str   # Context text
    caption: str            # Detected caption
    description: str        # Optional description
    tags: str               # Auto-extracted tags
```

## Tag Boosting

Khi vectorize images, tags được repeat **10 lần** để tăng semantic weight:

```python
# image_info.py
def get_vectorization_text(self) -> str:
    if self.tags:
        # 10x repeat for strong semantic boost
        tag_boost = ", ".join([self.tags] * 10)
        parts.append(f"Tags: {tag_boost}")
```

**Effect**: Query chứa tag sẽ có similarity score cao hơn đáng kể.

## Quality Filtering

Images được validate trước khi lưu:

| Check | Threshold | Purpose |
|-------|-----------|---------|
| Size | ≥ 150x150 px | Filter tiny images |
| Brightness | ≥ 30.0 | Filter black images |
| Std Deviation | ≥ 15.0 | Filter solid colors |
| Dark Ratio | ≤ 85% | Filter mostly-dark |

## Output Format

```python
ExtractedImage(
    image_id="HID_v1.1.1.pdf_p30",
    image_path="data/extracted_images/HID_v1.1.1.pdf_p30.png",
    source_file="data/documents/HID_v1.1.1.pdf",
    page_number=30,
    bbox=(0, 0, 1275, 1650),
    region_type="fullpage",
    surrounding_text="Figure 4.1: Media payload format...",
    caption="Full page 30",
    tags="Figure 4.1: Media payload format"
)
```

## Vectorization Data

```python
def get_vectorization_data(images: list[ExtractedImage]) -> list[dict]:
    return [{
        "chunk_id": img.image_id,
        "content": img.get_vectorization_text(),
        "metadata": {
            "type": "extracted_image",
            "region_type": img.region_type,
            "image_path": img.image_path,
            "source_file": img.source_file,
            "page_number": img.page_number,
            "tags": img.tags,
            "original_tags": img.tags,
            "user_tags": "",
        },
        "source_file": img.source_file,
    }]
```

## Libraries Used

| Library | Purpose |
|---------|---------|
| PyMuPDF (fitz) | PDF parsing, rendering |
| Docling | AI layout detection |
| PIL/Pillow | Image processing |
| NumPy | Quality validation |
