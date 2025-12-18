# 📦 Thư Viện và Dependencies

## 1. Tổng Quan Dependencies

```
requirements.txt
├── Core AI/ML
│   ├── torch>=2.0.0
│   ├── transformers>=4.35.0
│   └── sentence-transformers>=2.2.0
│
├── Vector Database
│   ├── chromadb>=0.4.0
│   └── faiss-cpu>=1.7.4
│
├── Document Processing
│   ├── langchain>=0.1.0
│   ├── langchain-community>=0.0.10
│   └── langchain-text-splitters>=0.0.1
│
├── File Handling
│   ├── python-docx>=0.8.11
│   ├── PyPDF2>=3.0.0
│   └── PyMuPDF>=1.23.0
│
├── Image Processing
│   ├── Pillow>=10.0.0
│   └── paddleocr>=2.6.0
│
├── Utilities
│   ├── pydantic>=2.0.0
│   ├── tqdm>=4.66.0
│   └── numpy>=1.24.0
│
└── Testing
    ├── pytest>=7.4.0
    └── pytest-asyncio>=0.21.0
```

## 2. Chi Tiết Từng Thư Viện

---

### 2.1 Core AI/ML

#### **PyTorch (`torch>=2.0.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Backend computation cho neural networks |
| **Sử dụng trong** | `sentence-transformers`, `transformers` |
| **Lợi ích** | Tensor operations, GPU acceleration |

```python
# Implicit usage via sentence-transformers
# Handles:
# - Tensor operations for embeddings
# - Model inference
# - GPU/CPU device management
```

#### **Transformers (`transformers>=4.35.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Load và run HuggingFace models |
| **Sử dụng trong** | `src/vectorization/vectorizer.py` |
| **Provider** | HuggingFace |

```python
# Used by SentenceTransformer internally
# Provides:
# - Model loading from HuggingFace Hub
# - Tokenization
# - Model architecture definitions
# - trust_remote_code support for custom models
```

**Lợi ích:**
- Hỗ trợ hàng ngàn pre-trained models
- Tự động download và cache models
- Chuẩn hóa API cho các loại models

#### **Sentence-Transformers (`sentence-transformers>=2.2.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Text-to-vector embedding |
| **Sử dụng trong** | `src/vectorization/vectorizer.py` |
| **Model** | `Alibaba-NLP/gte-multilingual-base` |

```python
# File: src/vectorization/vectorizer.py

from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "Alibaba-NLP/gte-multilingual-base",
    device="cpu",
    trust_remote_code=True
)

# Encode text to vectors
embeddings = model.encode(
    texts,
    batch_size=32,
    normalize_embeddings=True,  # For cosine similarity
    convert_to_numpy=True
)
# Returns: numpy array shape (N, 768)
```

**Lợi ích:**
- API đơn giản cho text embedding
- Batch processing
- Automatic normalization
- Progress bar (tqdm integration)

**Model được sử dụng: GTE-Multilingual-Base**
| Property | Value |
|----------|-------|
| Dimension | 768 |
| Max Tokens | 8192 |
| Languages | 100+ (including Vietnamese) |
| Size | ~560MB |
| MTEB Rank | Top-tier for multilingual |

---

### 2.2 Vector Database

#### **FAISS (`faiss-cpu>=1.7.4`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Fast similarity search |
| **Sử dụng trong** | `src/vectorization/faiss_store.py` |
| **Provider** | Facebook AI Research |

```python
# File: src/vectorization/faiss_store.py

import faiss

# Create index for cosine similarity
# IndexFlatIP = Inner Product on normalized vectors
index = faiss.IndexFlatIP(768)

# Normalize vectors
faiss.normalize_L2(vectors)

# Add vectors
index.add(vectors)

# Search
distances, indices = index.search(query_vector, top_k)
```

**Lợi ích:**
- Cực kỳ nhanh (C++ backend)
- Tối ưu memory
- Hỗ trợ nhiều index types (Flat, IVF, HNSW)
- Scale tới hàng triệu vectors

**Index Types:**
| Type | Use Case | Speed | Accuracy |
|------|----------|-------|----------|
| Flat | < 100K vectors | Fast | Exact |
| IVF | 100K - 1M | Faster | ~99% |
| HNSW | Any size | Fastest | ~95% |

#### **ChromaDB (`chromadb>=0.4.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Alternative vector store |
| **Sử dụng trong** | `src/vectorization/vector_store.py` |
| **Backend** | SQLite + HNSW |

```python
# File: src/vectorization/vector_store.py

import chromadb

client = chromadb.PersistentClient(path="data/vectordb")

collection = client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)

# Add documents
collection.add(
    ids=ids,
    embeddings=embeddings,
    documents=documents,
    metadatas=metadatas
)

# Query
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)
```

**Lợi ích:**
- Tích hợp metadata filtering
- Built-in persistence
- Easy setup (no server needed)
- Document storage included

**So sánh FAISS vs ChromaDB:**
| Feature | FAISS | ChromaDB |
|---------|-------|----------|
| Speed | ⚡⚡⚡ | ⚡⚡ |
| Filtering | ❌ | ✅ Rich |
| Setup | 📦 Library | 📦 Library |
| Scale | Millions | Thousands |
| Memory | Very efficient | Moderate |

---

### 2.3 Document Processing

#### **LangChain (`langchain>=0.1.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Text chunking framework |
| **Sử dụng trong** | `src/chunking/chunker.py` |

```python
# File: src/chunking/chunker.py

from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len
)

chunks = splitter.split_text(text)
```

**Lợi ích:**
- Recursive splitting giữ context
- Configurable separators
- Overlap để không mất thông tin

**Splitting Strategy:**
```
Priority order:
1. "\n\n" (paragraph breaks) - Best for semantic units
2. "\n" (line breaks) - Fallback
3. ". " (sentences) - Smaller units
4. " " (words) - Last resort
5. "" (characters) - Emergency
```

#### **LangChain Community/Text Splitters**

```python
# langchain-community: Community integrations
# langchain-text-splitters: Dedicated text splitting

# Import with fallback for compatibility
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
```

---

### 2.4 File Handling

#### **PyMuPDF (`PyMuPDF>=1.23.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | PDF processing |
| **Sử dụng trong** | `src/image_extraction/extractor.py`, `src/chunking/chunker.py` |
| **Import as** | `fitz` |

```python
# File: src/image_extraction/extractor.py

import fitz  # PyMuPDF

doc = fitz.open("document.pdf")

for page_num in range(len(doc)):
    page = doc[page_num]
    
    # Extract text
    text = page.get_text()
    
    # Get embedded images
    images = page.get_images(full=True)
    
    # Get vector drawings
    drawings = page.get_drawings()
    
    # Render page to image
    pix = page.get_pixmap(dpi=150)
    pix.save("page.png")

doc.close()
```

**Lợi ích:**
- Rất nhanh (C-based)
- Full PDF features: text, images, drawings, annotations
- High-quality rendering
- Image extraction with metadata

**Capabilities:**
| Feature | Support |
|---------|---------|
| Text extraction | ✅ |
| Image extraction | ✅ |
| Vector drawings | ✅ |
| Page rendering | ✅ |
| Annotations | ✅ |
| Forms | ✅ |

#### **python-docx (`python-docx>=0.8.11`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | DOCX file reading |
| **Sử dụng trong** | `src/chunking/chunker.py` |

```python
# File: src/chunking/chunker.py

from docx import Document

doc = Document("document.docx")
paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
text = "\n\n".join(paragraphs)
```

#### **PyPDF2 (`PyPDF2>=3.0.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Fallback PDF reader |
| **Status** | Available but PyMuPDF preferred |

---

### 2.5 Image Processing

#### **Pillow (`Pillow>=10.0.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Image manipulation |
| **Sử dụng trong** | `src/image_extraction/extractor.py`, `src/sequence_chart/processor.py` |

```python
# File: src/image_extraction/extractor.py

from PIL import Image

# Open and analyze image
img = Image.open("image.png")

# Convert to grayscale
gray = img.convert('L')

# Crop region
cropped = img.crop((x1, y1, x2, y2))

# Save
cropped.save("output.png")
```

**Lợi ích:**
- Đơn giản, mạnh mẽ
- Hỗ trợ nhiều formats
- Image analysis (histogram, stats)

#### **PaddleOCR (`paddleocr>=2.6.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Layout analysis (PP-Structure) |
| **Sử dụng trong** | `src/image_extraction/extractor.py` |
| **Optional** | Chỉ dùng khi `use_ppstructure=True` |

```python
# File: src/image_extraction/extractor.py

from paddleocr import PPStructureV3

engine = PPStructureV3(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)

results = engine.predict(input="page.png")

# Results contain:
# - text_regions
# - figure_regions
# - table_regions
# - title_regions
```

**Lợi ích:**
- AI-based layout detection
- Identifies figures, tables, titles
- Text region extraction
- Chinese/English OCR included

**Installation (Optional):**
```bash
# CPU version
pip install paddlepaddle
pip install paddleocr

# GPU version
pip install paddlepaddle-gpu
pip install paddleocr
```

---

### 2.6 Utilities

#### **Pydantic (`pydantic>=2.0.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Configuration validation |
| **Sử dụng trong** | `config/settings.py` |

```python
# File: config/settings.py

from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    model_name: str = "gte-multilingual-base"
    max_seq_length: int = 8192
    device: str = "cpu"
    normalize_embeddings: bool = True

class Settings(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    # ...

settings = Settings()
```

**Lợi ích:**
- Type validation at runtime
- Default values
- Nested configurations
- Easy serialization

#### **tqdm (`tqdm>=4.66.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Progress bars |
| **Sử dụng trong** | Vectorization, processing |

```python
# Integrated via sentence-transformers
embeddings = model.encode(
    texts,
    show_progress_bar=True  # Uses tqdm
)

# Output:
# Batches: 100%|██████████| 9/9 [00:12<00:00,  1.35s/it]
```

#### **NumPy (`numpy>=1.24.0`)**

| Aspect | Details |
|--------|---------|
| **Mục đích** | Array operations |
| **Sử dụng trong** | Everywhere |

```python
import numpy as np

# Embedding operations
embeddings = np.array(embedding_list, dtype=np.float32)

# Image analysis
pixels = np.frombuffer(image.samples, dtype=np.uint8)
mean_brightness = np.mean(pixels)
std_dev = np.std(pixels)

# Similarity calculation
similarity = np.dot(vec1, vec2)  # Cosine for normalized vectors
```

---

### 2.7 Testing

#### **pytest (`pytest>=7.4.0`)**

```bash
# Run tests
pytest tests/

# Verbose
pytest tests/ -v

# Specific file
pytest tests/test_chunking.py
```

#### **pytest-asyncio (`pytest-asyncio>=0.21.0`)**

Cho async tests (nếu cần).

---

## 3. Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEPENDENCY GRAPH                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          ┌──────────────────┐                               │
│                          │     PyTorch      │                               │
│                          │   (torch>=2.0)   │                               │
│                          └────────┬─────────┘                               │
│                                   │                                          │
│                    ┌──────────────┴──────────────┐                          │
│                    │                             │                          │
│                    ▼                             ▼                          │
│           ┌─────────────────┐          ┌─────────────────┐                  │
│           │  Transformers   │          │     NumPy       │                  │
│           │   (>=4.35.0)    │          │   (>=1.24.0)    │                  │
│           └────────┬────────┘          └────────┬────────┘                  │
│                    │                            │                           │
│                    ▼                            │                           │
│           ┌─────────────────┐                   │                           │
│           │   Sentence-     │                   │                           │
│           │  Transformers   │◀──────────────────┘                           │
│           │   (>=2.2.0)     │                                               │
│           └────────┬────────┘                                               │
│                    │                                                        │
│                    ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Simple RAG Core                              │   │
│  │                                                                      │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │   │
│  │  │   Chunking    │  │  Vectorizer   │  │    Search     │            │   │
│  │  │               │  │               │  │               │            │   │
│  │  │  - LangChain  │  │  - Sentence-  │  │  - FAISS      │            │   │
│  │  │  - PyMuPDF    │  │    Trans-     │  │  - ChromaDB   │            │   │
│  │  │  - python-docx│  │    formers    │  │               │            │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘            │   │
│  │                                                                      │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │   │
│  │  │    Image      │  │   Sequence    │  │    Config     │            │   │
│  │  │  Extraction   │  │    Charts     │  │               │            │   │
│  │  │               │  │               │  │               │            │   │
│  │  │  - PyMuPDF    │  │  - PIL        │  │  - Pydantic   │            │   │
│  │  │  - PIL        │  │  - re         │  │               │            │   │
│  │  │  - PaddleOCR* │  │               │  │               │            │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘            │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  * Optional dependency                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 4. Installation Guide

### 4.1 Basic Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install all dependencies
pip install -r requirements.txt
```

### 4.2 Install PyMuPDF and PaddlePaddle Separately

```bash
# Core PDF processing
pip install pymupdf

# Optional: PaddleOCR for layout analysis
pip install paddlepaddle paddleocr
```

### 4.3 GPU Support

```bash
# PyTorch with CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118

# FAISS GPU
pip install faiss-gpu

# PaddlePaddle GPU
pip install paddlepaddle-gpu
```

### 4.4 Minimal Installation

Chỉ cần thiết cho basic functionality:

```bash
pip install torch transformers sentence-transformers
pip install faiss-cpu
pip install langchain langchain-text-splitters
pip install pymupdf
pip install pydantic numpy tqdm
```

## 5. Version Compatibility Matrix

| Package | Min Version | Tested Version | Notes |
|---------|-------------|----------------|-------|
| Python | 3.10 | 3.10, 3.11 | 3.12 untested |
| torch | 2.0.0 | 2.1.0 | CUDA 11.8+ for GPU |
| transformers | 4.35.0 | 4.36.0 | For GTE model |
| sentence-transformers | 2.2.0 | 2.3.0 | |
| faiss-cpu | 1.7.4 | 1.7.4 | |
| chromadb | 0.4.0 | 0.4.15 | |
| PyMuPDF | 1.23.0 | 1.23.8 | |
| pydantic | 2.0.0 | 2.5.0 | V2 required |

