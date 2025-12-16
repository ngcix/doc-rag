# Simple RAG System

A production-ready Retrieval-Augmented Generation (RAG) system with document chunking, vectorization, semantic search, and intelligent image extraction from PDFs.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Document Chunking** | Split TXT, MD, PDF, DOCX into optimized chunks using LangChain |
| **Vectorization** | Convert text to embeddings using `Alibaba-NLP/gte-multilingual-base` (768-dim) |
| **Semantic Search** | Fast similarity search with cosine distance |
| **Dual Backend** | Choose between FAISS (fast) or ChromaDB (full-featured) |
| **Image Extraction** | Extract embedded images and vector drawings from PDFs using **PyMuPDF** |
| **Layout Analysis** | Detect document regions (figure, table, text) using **PaddleOCR PP-Structure** |
| **Sequence Charts** | Parse Mermaid diagrams, export images, and vectorize descriptions |

## 📁 Directory Structure

```
simple-rag/
├── config/                     # Configuration (settings.py)
│   └── settings.py             # All configurable parameters
├── data/
│   ├── documents/              # 📥 Place source documents here (PDF, TXT, MD, DOCX)
│   ├── extracted_images/       # 📤 Extracted images output
│   ├── vectordb/               # ChromaDB storage
│   └── faiss_index/            # FAISS index storage
├── models/                     # Downloaded ML models cache (~1.5GB)
├── process/
│   ├── input/                  # Search queries log
│   └── output/                 # Search results log
├── src/
│   ├── chunking/               # Document chunking module
│   ├── vectorization/          # Text vectorization & vector stores
│   ├── search/                 # Search engine
│   ├── sequence_chart/         # Mermaid sequence diagram processing
│   └── image_extraction/       # PDF image extraction with PyMuPDF
└── tests/                      # Unit tests
```

## 🚀 Quick Start

### Installation

```bash
# Install base requirements
pip install -r requirements.txt

# For GPU support (optional)
pip install paddlepaddle-gpu  # Instead of paddlepaddle
```

### 1. Initialize folders

```bash
python -m src.main init
```

### 2. Add documents

Place your documents (PDF, TXT, MD, DOCX) in `data/documents/`

### 3. Process documents (text + images)

```bash
# Process everything: text chunks + images from PDFs
python -m src.main process

# Skip image extraction (text only)
python -m src.main process --no-images

# Skip chart processing
python -m src.main process --no-charts
```

Extracted images are saved to: `data/extracted_images/`

### 5. Search

```bash
# Semantic search
python -m src.main search "authentication flow"

# With custom result count
python -m src.main search "user login" --top-k 10
```

### 6. View statistics

```bash
python -m src.main stats
```

### 7. Clean data

```bash
# Clean vectordb and logs (with confirmation)
python -m src.main clean

# Clean without confirmation
python -m src.main clean -y

# Clean everything including models (~1.5GB)
python -m src.main clean --all -y
```

## ⚙️ Configuration

All settings are in `config/settings.py`:

### Model Configuration

```python
class ModelConfig:
    model_name: str = "Alibaba-NLP/gte-multilingual-base"
    max_seq_length: int = 8192
    device: str = "cpu"  # or "cuda" for GPU
    normalize_embeddings: bool = True
```

### Chunking Configuration

```python
class ChunkingConfig:
    chunk_size: int = 512        # Characters per chunk
    chunk_overlap: int = 50      # Overlap between chunks
    separators: list = ["\n\n", "\n", ". ", " ", ""]
```

### Vector Store Configuration

```python
class VectorDBConfig:
    backend: str = "faiss"       # "faiss" or "chromadb"
    faiss_index_type: str = "Flat"  # "Flat", "IVF", "HNSW"
    distance_metric: str = "cosine"
```

### Image Extraction Configuration

Located in `config/settings.py`:

```python
class ImageExtractionConfig(BaseModel):
    # Size filters
    min_width: int = 50          # Minimum image width
    min_height: int = 50         # Minimum image height
    
    # Quality filters (avoid black/empty images)
    min_brightness: float = 30.0  # Filter dark images
    min_std_dev: float = 15.0    # Filter solid color images
    max_dark_pixel_ratio: float = 0.85  # Filter mostly black images
    
    # Extraction options
    extract_tables: bool = True   # Extract table regions
    extract_figures: bool = True  # Extract figure/image regions
    context_chars: int = 500      # Characters to extract around image
    
    # PP-Structure settings (AI-based layout analysis)
    use_ppstructure: bool = True  # Enable PP-Structure
    ppstructure_max_pages: int = 20  # Max pages for analysis
    
    # PyMuPDF vector drawings clustering
    cluster_merge_distance: int = 50  # Merge nearby drawings
    min_diagram_size: int = 100  # Min size for diagrams
    
    # GPU settings
    use_gpu: bool = False  # Use GPU for PP-Structure
```

## 🔧 Architecture

### Processing Pipeline

```
Document → Chunking → Vectorization → Vector Store → Search
    │           │           │              │            │
    ▼           ▼           ▼              ▼            ▼
PDF/TXT/MD  LangChain   GTE-Base       FAISS      Cosine Similarity
DOCX        Splitter    (768-dim)    or ChromaDB    Top-K Results
```

### Image Extraction Pipeline (Integrated)

```
PDF File
    │
    ├── Step 1: PyMuPDF ──────────────────────────────────────────┐
    │       ├── page.get_images() → Embedded bitmaps              │
    │       └── page.get_drawings() → Vector diagrams → Cluster   │
    │                                                              │
    ├── Step 2: PP-Structure (Layout Analysis) ───────────────────┤
    │       ├── Render page to image (150 DPI)                    │
    │       ├── Detect regions: text, figure, table, title        │
    │       └── Extract text content from each region             │
    │                                                              │
    └── Step 3: Context Enrichment ───────────────────────────────┤
            ├── Match images with PP-Structure layout             │
            ├── Add surrounding text context                      │
            └── Detect captions (Figure X, Hình X, etc.)          │
                                                                   │
                                                                   ▼
                                             Validation → Save PNG
                                             + Vectorize for search
```

## 🖼️ Image Extraction Technologies

Dự án sử dụng **hai công nghệ chính** để trích xuất hình ảnh từ documents:

### 1. PyMuPDF (fitz) - Phương pháp chính

**PyMuPDF** là thư viện Python binding cho MuPDF, được sử dụng làm phương pháp **chính** để trích xuất hình ảnh từ PDF.

| Tính năng | Mô tả |
|-----------|-------|
| **Embedded Images** | Trích xuất trực tiếp các hình ảnh nhúng (PNG, JPEG) trong PDF |
| **Vector Drawings** | Phát hiện và render các đường vẽ vector (diagrams, flowcharts) |
| **Clustering** | Gom nhóm các đường vẽ gần nhau thành 1 diagram hoàn chỉnh |
| **Alpha Handling** | Xử lý transparency, composite lên nền trắng |

**Cách hoạt động:**

```python
import fitz  # PyMuPDF

doc = fitz.open("document.pdf")
for page_num in range(len(doc)):
    page = doc[page_num]
    
    # 1. Trích xuất embedded images
    image_list = page.get_images(full=True)
    for img in image_list:
        xref = img[0]
        pix = fitz.Pixmap(doc, xref)  # Chuyển thành Pixmap
        pix.save("output.png")
    
    # 2. Trích xuất vector drawings  
    drawings = page.get_drawings()  # Lấy tất cả vector paths
    # Cluster nearby paths thành diagram
    # Render với page.get_pixmap(clip=region, dpi=150)
```

**Ưu điểm:**
- ⚡ **Rất nhanh** - không cần render toàn trang
- 🎯 **Chính xác** - lấy đúng ảnh gốc từ PDF
- 📐 **Vector support** - capture cả diagrams, flowcharts
- 💻 **Không cần GPU**

---

### 2. PaddleOCR PP-Structure - Layout Analysis

**PP-Structure V3** là module thuộc [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR), sử dụng deep learning để phân tích layout tài liệu.

| Tính năng | Mô tả |
|-----------|-------|
| **Layout Detection** | Phát hiện vùng: figure, table, text, title, chart |
| **Region Classification** | Phân loại loại nội dung trong từng vùng |
| **Text Context** | Trích xuất text xung quanh hình ảnh |
| **OCR Integration** | Có thể OCR text trong hình nếu cần |

**Khi nào PP-Structure được sử dụng:**
- Xử lý file **ảnh** (PNG, JPG) - không phải PDF
- Làm **fallback** khi PyMuPDF gặp lỗi
- Khi cần phân tích **layout phức tạp**

**Cách hoạt động:**

```python
from paddleocr import PPStructureV3

# Khởi tạo engine (lazy loading)
engine = PPStructureV3(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)

# Phân tích layout
results = engine.predict(input="page_image.png")

for result in results:
    layout = result.layout_parsing_result
    for box in layout.get('boxes', []):
        region_type = box.get('type')  # 'figure', 'table', 'text'
        bbox = box.get('bbox')  # (x1, y1, x2, y2)
        # Crop vùng và lưu...
```

**Ưu điểm:**
- 🧠 **AI-powered** - deep learning model
- 📊 **Multi-region** - phân biệt được nhiều loại vùng
- 📖 **Context aware** - lấy được text context
- 🌐 **Works on any image** - không giới hạn PDF

---

### 3. So sánh hai phương pháp

| Tiêu chí | PyMuPDF | PP-Structure |
|----------|---------|--------------|
| **Vai trò** | Phương pháp chính | Bổ sung / Fallback |
| **Input** | Chỉ PDF | Mọi định dạng ảnh |
| **Tốc độ** | ⚡ Rất nhanh | 🐢 Chậm hơn (AI) |
| **GPU** | Không cần | Optional (tăng tốc) |
| **Output** | Raw images | Classified regions |

### 4. Luồng xử lý thực tế

```
Input File
    │
    ├── PDF ──────────────────────────────────────┐
    │       │                                      │
    │       ├── PyMuPDF: get_images()             │
    │       │       → Embedded bitmaps            │
    │       │                                      │
    │       └── PyMuPDF: get_drawings()           │
    │               → Vector diagrams              │
    │               → Cluster & render             │
    │                                              │
    │   (On error) ──── Fallback ────────────────►│
    │                                              │
    └── Image (PNG/JPG) ──► PP-Structure ─────────┤
                                │                  │
                                ├─ Detect regions  │
                                ├─ Classify        │
                                └─ Crop & save     │
                                                   │
                                                   ▼
                              Validation Filter
                              (brightness, std_dev, dark_ratio)
                                                   │
                                                   ▼
                              ✅ Save valid images
                              + Extract text context
                              + Vectorize for search
```

### 5. Image Validation

Trước khi lưu, mỗi hình ảnh được kiểm tra:

| Check | Threshold | Mục đích |
|-------|-----------|----------|
| `min_width` | ≥ 50px | Loại bỏ ảnh quá nhỏ |
| `min_height` | ≥ 50px | Loại bỏ ảnh quá nhỏ |
| `min_brightness` | ≥ 30 | Loại bỏ ảnh đen |
| `min_std_dev` | ≥ 15 | Loại bỏ ảnh solid color |
| `max_dark_pixel_ratio` | ≤ 85% | Loại bỏ ảnh mostly black |

## 📊 Vector Store Backends

| Backend | Best For | Features |
|---------|----------|----------|
| **FAISS** (default) | Speed, large datasets | Fast similarity search, multiple index types |
| **ChromaDB** | Metadata filtering | Persistent, full-featured, easy debugging |

### FAISS Index Types

| Type | Use Case | Speed | Accuracy |
|------|----------|-------|----------|
| `Flat` | < 100k vectors | ⭐⭐ | ⭐⭐⭐ (exact) |
| `IVF` | Large datasets | ⭐⭐⭐ | ⭐⭐ (approximate) |
| `HNSW` | Balanced | ⭐⭐⭐ | ⭐⭐⭐ |

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_chunking.py -v
```

## 📝 CLI Reference

| Command | Description |
|---------|-------------|
| `python -m src.main init` | Initialize directory structure |
| `python -m src.main process` | Process documents: text + images + charts |
| `python -m src.main search "<query>"` | Semantic search |
| `python -m src.main stats` | Show database statistics |
| `python -m src.main clean` | Clean extracted data |

### Command Options

```bash
# Process with options
python -m src.main process --input /path/to/docs
python -m src.main process --no-images    # Skip image extraction
python -m src.main process --no-charts    # Skip chart processing

# Search with options
python -m src.main search "query" --top-k 10 --no-save

# Clean all including models
python -m src.main clean --all -y
```

## 🔍 Known Limitations

1. **PDF Text Extraction**: Uses PyPDF2 which may not handle complex layouts perfectly
2. **Image Extraction**: Only supports PDF files currently
3. **FAISS Deletion**: Deleting vectors requires index rebuild (expensive)
4. **Memory**: Large models require ~2GB RAM

## 📄 License

MIT License
