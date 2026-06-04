# 🖼️ Image Extraction Architecture

## Module Overview

```
src/image_extraction/
├── __init__.py              # Factory: get_image_extractor()
├── extractor.py             # Full-page extraction (PyMuPDF)
└── image_info.py            # ExtractedImage dataclass
```

## Extraction Modes

| Mode | Command | Module | Description |
|------|---------|--------|-------------|
| Full-page | `-fp` | `extractor.py` | Capture trang có visual content |

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
│           └── extractor.py (PyMuPDF)                                        │
│                                                                              │
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
    │   ├── Check if page has visual content
    │   │   ├── page.get_images() → embedded images
    │   │   └── page.get_drawings() → vector drawings
    │   │   └── page.get_text() → figure/table markers
    │   │
    │   ├── If has content:
    │   │   ├── Render page at 150 DPI
    │   │   ├── Save as PNG/JPEG
    │   │   ├── Extract page text
    │   │   └── Auto-generate tags
    │   │
    │   └── Create ExtractedImage object
    │
    └── Return: List[ExtractedImage]
```

`-fp` bỏ qua các trang không có dấu hiệu visual content để giảm số ảnh, disk usage và thời gian vectorization.

### Auto-Tagging

Patterns được phát hiện:
- `Figure X.Y: Description`
- `Table X: Description`
- `Fig. X - Description`
- `Hình X.Y: Mô tả` (Vietnamese)
- `Bảng X: Mô tả` (Vietnamese)

## ExtractedImage Dataclass

```python
@dataclass
class ExtractedImage:
    image_id: str           # Unique ID
    image_path: str         # Path to saved image
    source_file: str        # Original PDF path
    page_number: int        # Page number
    bbox: tuple             # (x1, y1, x2, y2)
    region_type: str        # "fullpage"
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
        tag_boost = ", ".join([self.tags] * 10)
        parts.append(f"Tags: {tag_boost}")
```

**Effect**: Query chứa tag sẽ có similarity score cao hơn đáng kể.

## Page Selection

`-fp` capture một trang nếu có ít nhất một dấu hiệu:

| Check | Purpose |
|-------|---------|
| Embedded image đủ lớn | Bắt các trang có ảnh bitmap |
| Vector drawing đủ lớn | Bắt diagrams/figures vẽ bằng vector |
| Figure/table caption | Bắt trang có caption hoặc marker đặc thù |
| Nhiều line/rectangle | Bắt các bảng nhiều đường kẻ |

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
| PIL/Pillow | JPEG output |
