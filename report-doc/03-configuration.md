# ⚙️ Cấu Hình Hệ Thống

## 1. Tổng Quan

Tất cả cấu hình được định nghĩa tập trung trong `config/settings.py` sử dụng **Pydantic** để validation và type safety.

```python
# Sử dụng cấu hình
from config import settings

# Access nested configs
model_name = settings.model.model_name
chunk_size = settings.chunking.chunk_size
backend = settings.vectordb.backend
```

## 2. Các Path Cơ Bản

```python
# File: config/settings.py

from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent          # simple-rag/
DATA_DIR = BASE_DIR / "data"                      # simple-rag/data/

# Input/Output paths
DOCUMENTS_DIR = DATA_DIR / "documents"            # Đặt tài liệu input
EXTRACTED_IMAGES_DIR = DATA_DIR / "extracted_images"  # Hình ảnh output

# Storage paths
VECTORDB_DIR = DATA_DIR / "vectordb"              # ChromaDB storage
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"        # FAISS storage
MODELS_DIR = BASE_DIR / "models"                  # Local models

# Process logs
PROCESS_DIR = BASE_DIR / "process"
PROCESS_INPUT_DIR = PROCESS_DIR / "input"         # Query inputs
PROCESS_OUTPUT_DIR = PROCESS_DIR / "output"       # Search results
```

## 3. ModelConfig - Cấu Hình Embedding Model

```python
class ModelConfig(BaseModel):
    """Configuration for the embedding model."""
    
    # Model path (local hoặc HuggingFace)
    model_name: str = str(MODELS_DIR / "models--Alibaba-NLP--gte-multilingual-base" / "snapshots" / MODEL_SNAPSHOT_ID)
    
    # Cache directory cho models
    model_cache_dir: Path = MODELS_DIR
    
    # Maximum sequence length (số tokens tối đa)
    max_seq_length: int = 8192
    
    # Device: "cpu" hoặc "cuda"
    device: str = "cpu"
    
    # Normalize vectors cho cosine similarity
    normalize_embeddings: bool = True
```

### Giải thích các tham số:

| Parameter | Giá trị | Mô tả |
|-----------|---------|-------|
| `model_name` | Local path | Path tới model đã download |
| `max_seq_length` | 8192 | GTE model hỗ trợ context dài |
| `device` | "cpu" | Chạy trên CPU (đổi "cuda" cho GPU) |
| `normalize_embeddings` | True | Cần thiết cho cosine similarity |

### Lợi ích của model GTE-multilingual:
- **768 dimensions**: Cân bằng giữa quality và speed
- **8192 max tokens**: Context dài, tốt cho full-page extraction
- **Multilingual**: Hỗ trợ tiếng Việt và nhiều ngôn ngữ
- **State-of-the-art**: Top performance trên MTEB benchmark

## 4. ChunkingConfig - Cấu Hình Chia Chunk

```python
class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""
    
    # Số ký tự mỗi chunk
    chunk_size: int = 512
    
    # Số ký tự overlap giữa các chunks
    chunk_overlap: int = 50
    
    # Thứ tự ưu tiên split
    separators: list[str] = ["\n\n", "\n", ". ", " ", ""]
    
    # Hàm đo độ dài
    length_function: str = "len"  # hoặc "tiktoken"
```

### Giải thích chiến lược chunking:

```
Original Text:
┌─────────────────────────────────────────────────────────┐
│ Paragraph 1 about topic A.                              │
│                                                         │
│ Paragraph 2 continues with more details about topic A. │
│ This extends the discussion.                           │
│                                                         │
│ Paragraph 3 introduces topic B.                        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼ RecursiveCharacterTextSplitter
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ Chunk 1 (512 chars) │ │ Chunk 2 (512 chars) │ │ Chunk 3 (512 chars) │
│ Paragraph 1 +       │ │ ...details about    │ │ Paragraph 3...      │
│ start of Para 2     │ │ Para 2 + start...   │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
       │                        │                        │
       └────────────────────────┴────────────────────────┘
                            │
                50 chars OVERLAP (context continuity)
```

### Separators Priority:
1. `"\n\n"` - Ưu tiên split theo paragraph
2. `"\n"` - Fallback split theo dòng
3. `". "` - Fallback split theo câu
4. `" "` - Fallback split theo từ
5. `""` - Cuối cùng, split từng ký tự

## 5. VectorDBConfig - Cấu Hình Vector Database

```python
class VectorDBConfig(BaseModel):
    """Configuration for vector database."""
    
    # Backend: "faiss" hoặc "chromadb"
    backend: str = "faiss"
    
    # Tên collection trong database
    collection_name: str = "documents"
    
    # Thư mục lưu ChromaDB
    persist_directory: Path = VECTORDB_DIR
    
    # Thư mục lưu FAISS
    faiss_index_dir: Path = FAISS_INDEX_DIR
    
    # Distance metric: cosine, l2, ip
    distance_metric: str = "cosine"
    
    # FAISS index type: Flat, IVF, HNSW
    faiss_index_type: str = "Flat"
```

### So sánh FAISS vs ChromaDB:

| Feature | FAISS | ChromaDB |
|---------|-------|----------|
| **Speed** | ⚡ Rất nhanh | 🔄 Nhanh |
| **Memory** | 💾 Efficient | 📊 Higher |
| **Filtering** | ❌ Limited | ✅ Rich |
| **Persistence** | 📁 Custom | 📁 Built-in |
| **Scalability** | 🚀 Millions | 📈 Thousands |
| **Use case** | Production | Development |

### FAISS Index Types:

| Type | Mô tả | Use Case |
|------|-------|----------|
| `Flat` | Exact search, brute force | < 100K vectors |
| `IVF` | Inverted file, approximate | 100K - 1M vectors |
| `HNSW` | Graph-based, approximate | Fast retrieval |

## 6. SearchConfig - Cấu Hình Search

```python
class SearchConfig(BaseModel):
    """Configuration for search."""
    
    # Số kết quả trả về
    top_k: int = 5
    
    # Ngưỡng similarity tối thiểu (0.0 - 1.0)
    score_threshold: float = 0.5
    
    # Có include metadata không
    include_metadata: bool = True
```

### Giải thích Score Threshold:

```
Similarity Score Scale (Cosine):
┌────────────────────────────────────────────────────────┐
│ 0.0        0.5        0.7        0.85       1.0       │
│ ├──────────┼──────────┼──────────┼──────────┤         │
│ Unrelated  Threshold  Related    Similar    Identical │
└────────────────────────────────────────────────────────┘
                 ▲
                 │
        Default threshold = 0.5
        (chỉ trả về kết quả có score >= 0.5)
```

## 7. ImageExtractionConfig - Cấu Hình Trích Xuất Ảnh

```python
class ImageExtractionConfig(BaseModel):
    """Configuration for image extraction."""
    
    # Output settings
    output_dir: Path = EXTRACTED_IMAGES_DIR
    image_format: str = "png"
    
    # Size filters
    min_width: int = 150          # Bỏ qua ảnh nhỏ hơn 150px
    min_height: int = 150
    
    # Quality filters (tránh ảnh đen/rỗng)
    min_brightness: float = 30.0  # Mean brightness tối thiểu
    min_std_dev: float = 15.0     # Standard deviation tối thiểu
    max_dark_pixel_ratio: float = 0.85  # Tỉ lệ pixel tối đa
    
    # Extraction options
    extract_tables: bool = True   # Trích xuất vùng table
    extract_figures: bool = True  # Trích xuất vùng figure
    context_chars: int = 2000     # Số ký tự context xung quanh
    
    # PP-Structure settings
    use_ppstructure: bool = False # Enable layout analysis
    ppstructure_max_pages: int = 20
    
    # PyMuPDF vector drawings
    cluster_merge_distance: int = 50  # Merge drawings gần nhau
    min_drawing_size: int = 20
    min_diagram_size: int = 100
    
    # GPU settings
    use_gpu: bool = False
```

### Quality Filtering Logic:

```python
def _is_valid_pixmap(self, pix):
    """
    Kiểm tra ảnh có hợp lệ không:
    1. Brightness >= 30 (không quá tối)
    2. Std Dev >= 15 (không solid color)
    3. Dark pixel ratio <= 85%
    """
    # Calculate grayscale
    gray = 0.299 * R + 0.587 * G + 0.114 * B
    
    # Check conditions
    if mean(gray) < min_brightness: return False
    if std(gray) < min_std_dev: return False
    if dark_ratio > max_dark_pixel_ratio: return False
    
    return True
```

## 8. SequenceChartConfig - Cấu Hình Sequence Charts

```python
class SequenceChartConfig(BaseModel):
    """Configuration for sequence chart processing."""
    
    # Export format: png, svg, pdf
    export_format: str = "png"
    
    # DPI quality
    export_quality: int = 150
    
    # Include description in vectorization
    include_description: bool = True
```

## 9. Global Settings Instance

```python
# File: config/settings.py

class Settings(BaseModel):
    """Main settings class combining all configurations."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sequence_chart: SequenceChartConfig = Field(default_factory=SequenceChartConfig)
    image_extraction: ImageExtractionConfig = Field(default_factory=ImageExtractionConfig)

# Global singleton
settings = Settings()
```

## 10. Thay Đổi Cấu Hình

### Cách 1: Sửa trực tiếp `settings.py`
```python
# config/settings.py
class ChunkingConfig(BaseModel):
    chunk_size: int = 1024  # Đổi từ 512 -> 1024
```

### Cách 2: Override runtime
```python
from config import settings

# Override specific value
settings.chunking.chunk_size = 1024
settings.vectordb.backend = "chromadb"
```

### Cách 3: Create custom config
```python
from config import ChunkingConfig, ModelConfig

custom_chunking = ChunkingConfig(
    chunk_size=1024,
    chunk_overlap=100
)

custom_model = ModelConfig(
    device="cuda",
    model_name="Alibaba-NLP/gte-multilingual-base"  # Online
)
```

## 11. Environment Variables (Suggested)

Để production, có thể mở rộng với env vars:

```python
import os

class ModelConfig(BaseModel):
    device: str = os.getenv("RAG_DEVICE", "cpu")
    
class VectorDBConfig(BaseModel):
    backend: str = os.getenv("RAG_BACKEND", "faiss")
```

```bash
# Usage
export RAG_DEVICE=cuda
export RAG_BACKEND=chromadb
python -m src.main process -fp
```

