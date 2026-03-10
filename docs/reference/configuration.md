# ⚙️ Configuration Reference

## Tổng Quan

Cấu hình được định nghĩa trong `config/settings.py` sử dụng **Pydantic**.

SpecRAG hỗ trợ override bằng file ngoài code `config/setting.json` (phù hợp cho release):

```json
{
    "paths": {
        "database_dir": "./data"
    }
}
```

`database_dir` có thể là đường dẫn tương đối (so với thư mục chạy ứng dụng) hoặc tuyệt đối.

```python
from config import settings

# Access config
model_name = settings.model.model_name
chunk_size = settings.chunking.chunk_size
backend = settings.vectordb.backend
```

## Paths

| Path | Mô tả |
|------|-------|
| `DOCUMENTS_DIR` | `data/documents/` - Input documents |
| `EXTRACTED_IMAGES_DIR` | `data/extracted_images/` - Output images |
| `FAISS_INDEX_DIR` | `data/faiss_index/` - FAISS storage |
| `VECTORDB_DIR` | `data/vectordb/` - ChromaDB storage |
| `MODELS_DIR` | `models/` - Local models |
| `PROCESS_INPUT_DIR` | `process/input/` - Query logs |
| `PROCESS_OUTPUT_DIR` | `process/output/` - Result logs |

### Path Override trong `setting.json`

Bạn có thể cấu hình đường dẫn qua section `paths`:

```json
{
    "paths": {
        "database_dir": "./data",
        "documents_dir": "./data/documents",
        "extracted_images_dir": "./data/extracted_images",
        "vectordb_dir": "./data/vectordb",
        "faiss_index_dir": "./data/faiss_index",
        "models_dir": "./models",
        "process_dir": "./process"
    }
}
```

Nếu chỉ cần đổi nơi lưu data, cấu hình tối thiểu là `paths.database_dir`.

---

## ModelConfig

Cấu hình embedding model.

```python
class ModelConfig(BaseModel):
    model_name: str = "models/.../gte-multilingual-base"
    model_cache_dir: Path = MODELS_DIR
    max_seq_length: int = 8192
    device: str = "cpu"  # hoặc "cuda"
    normalize_embeddings: bool = True
```

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `model_name` | Local path | Path tới model |
| `max_seq_length` | 8192 | Max tokens |
| `device` | "cpu" | "cpu" hoặc "cuda" |
| `normalize_embeddings` | True | Cần cho cosine similarity |

---

## ChunkingConfig

Cấu hình text chunking.

```python
class ChunkingConfig(BaseModel):
    chunk_size: int = 512
    chunk_overlap: int = 150
    separators: list[str] = ["\n\n", "\n", ". ", " ", ""]
    length_function: str = "len"
```

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `chunk_size` | 512 | Số ký tự mỗi chunk |
| `chunk_overlap` | 150 | Overlap giữa chunks |
| `separators` | [...] | Thứ tự ưu tiên split |

**Separators Priority**:
1. `"\n\n"` - Paragraph breaks
2. `"\n"` - Line breaks
3. `". "` - Sentences
4. `" "` - Words
5. `""` - Characters

---

## VectorDBConfig

Cấu hình vector database.

```python
class VectorDBConfig(BaseModel):
    backend: str = "faiss"  # hoặc "chromadb"
    collection_name: str = "documents"
    persist_directory: Path = VECTORDB_DIR
    faiss_index_dir: Path = FAISS_INDEX_DIR
    distance_metric: str = "cosine"
    faiss_index_type: str = "Flat"
```

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `backend` | "faiss" | "faiss" hoặc "chromadb" |
| `distance_metric` | "cosine" | cosine, l2, ip |
| `faiss_index_type` | "Flat" | Flat, IVF, HNSW |

**FAISS vs ChromaDB**:

| Feature | FAISS | ChromaDB |
|---------|-------|----------|
| Speed | ⚡⚡⚡ | ⚡⚡ |
| Filtering | ❌ | ✅ Rich |
| Scale | Millions | Thousands |

---

## SearchConfig

Cấu hình search.

```python
class SearchConfig(BaseModel):
    top_k: int = 5
    score_threshold: float = 0.7
    include_metadata: bool = True
```

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `top_k` | 5 | Số kết quả |
| `score_threshold` | 0.7 | Ngưỡng similarity (0.0-1.0) |

---

## ImageExtractionConfig

Cấu hình image extraction.

```python
class ImageExtractionConfig(BaseModel):
    output_dir: Path = EXTRACTED_IMAGES_DIR
    image_format: str = "png"
    min_width: int = 150
    min_height: int = 150
    min_brightness: float = 30.0
    min_std_dev: float = 15.0
    max_dark_pixel_ratio: float = 0.85
    context_chars: int = 2000
    cluster_merge_distance: int = 50
    min_diagram_size: int = 100
    use_gpu: bool = False
```

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `min_width/height` | 150 | Filter ảnh nhỏ |
| `min_brightness` | 30.0 | Filter ảnh tối |
| `context_chars` | 2000 | Chars context xung quanh |

---

## SequenceChartConfig

Cấu hình Mermaid charts.

```python
class SequenceChartConfig(BaseModel):
    export_format: str = "png"
    export_quality: int = 150
    include_description: bool = True
```

---

## Thay Đổi Cấu Hình

### Cách 1: Sửa settings.py

```python
# config/settings.py
class ChunkingConfig(BaseModel):
    chunk_size: int = 1024  # Đổi từ 512
```

### Cách 2: Runtime Override

```python
from config import settings

settings.chunking.chunk_size = 1024
settings.vectordb.backend = "chromadb"
```

### Cách 3: Environment Variables (Suggested)

```python
import os

class ModelConfig(BaseModel):
    device: str = os.getenv("RAG_DEVICE", "cpu")
```

```bash
export RAG_DEVICE=cuda
specrag process -fp
```

---

## Global Settings Instance

```python
# config/settings.py
class Settings(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sequence_chart: SequenceChartConfig = Field(default_factory=SequenceChartConfig)
    image_extraction: ImageExtractionConfig = Field(default_factory=ImageExtractionConfig)

# Singleton
settings = Settings()
```
