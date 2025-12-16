# Simple RAG System

A production-ready Retrieval-Augmented Generation (RAG) system with document chunking, vectorization, semantic search, and intelligent image extraction from PDFs.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Document Chunking** | Split TXT, MD, PDF, DOCX into optimized chunks using LangChain |
| **Vectorization** | Convert text to embeddings using `Alibaba-NLP/gte-multilingual-base` (768-dim) |
| **Semantic Search** | Fast similarity search with cosine distance |
| **Dual Backend** | Choose between FAISS (fast) or ChromaDB (full-featured) |
| **Image Extraction** | Extract embedded images and vector drawings from PDFs using PyMuPDF |
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

Located in `src/image_extraction/extractor.py`:

```python
class ImageExtractionConfig:
    min_width: int = 50          # Minimum image width
    min_height: int = 50         # Minimum image height
    min_brightness: float = 30.0  # Filter dark images
    min_std_dev: float = 15.0    # Filter solid color images
    max_dark_pixel_ratio: float = 0.85  # Filter mostly black images
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

### Image Extraction Pipeline

```
PDF → PyMuPDF → Bitmap Extraction → Validation → Save PNG
          │          │                   │
          ▼          ▼                   ▼
    Vector Drawing → Clustering → Filter Black/Invalid
      Detection     (Merge nearby)    Images
```

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
