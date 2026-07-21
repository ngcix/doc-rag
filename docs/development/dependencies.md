# 📦 Dependencies

## Overview

```
requirements.txt
├── Core AI/ML
│   ├── torch>=2.0.0
│   ├── transformers>=4.35.0
│   └── sentence-transformers>=2.2.0
│
├── Vector Database
│   ├── faiss-cpu>=1.7.4
│   └── chromadb>=0.4.0
│
├── Document Processing
│   ├── langchain>=0.1.0
│   ├── langchain-text-splitters>=0.0.1
│   └── PyMuPDF>=1.23.0
│
├── Image Processing
│   └── Pillow>=10.0.0
│
├── Utilities
│   ├── pydantic>=2.0.0
│   ├── tqdm>=4.66.0
│   └── numpy>=1.24.0
│
├── HTTP API
│   ├── fastapi>=0.115.0
│   └── uvicorn[standard]>=0.30.0
│
└── Testing
    └── pytest>=7.4.0
```

## Core AI/ML

### PyTorch (`torch>=2.0.0`)

- Backend cho neural networks
- Tensor operations, GPU acceleration

### Transformers (`transformers>=4.35.0`)

- HuggingFace models
- Tokenization

### Sentence-Transformers (`sentence-transformers>=2.2.0`)

- Text-to-vector embedding
- Model: `Alibaba-NLP/gte-multilingual-base`

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("gte-multilingual-base")
embeddings = model.encode(texts, normalize_embeddings=True)
```

## Vector Database

### FAISS (`faiss-cpu>=1.7.4`)

- Fast similarity search
- Facebook AI Research

```python
import faiss

index = faiss.IndexFlatIP(768)  # Inner Product
index.add(vectors)
distances, indices = index.search(query, top_k)
```

### ChromaDB (`chromadb>=0.4.0`)

- Alternative vector store
- Rich filtering

## Document Processing

### LangChain (`langchain>=0.1.0`)

- Text chunking

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=150)
chunks = splitter.split_text(text)
```

### PyMuPDF (`PyMuPDF>=1.23.0`)

- PDF processing
- Import as `fitz`

```python
import fitz

doc = fitz.open("document.pdf")
page = doc[0]
text = page.get_text()
pix = page.get_pixmap(dpi=150)
```

## Image Processing

### Pillow (`Pillow>=10.0.0`)

- Image manipulation

## Utilities

### Pydantic (`pydantic>=2.0.0`)

- Configuration validation

### tqdm (`tqdm>=4.66.0`)

- Progress bars

### NumPy (`numpy>=1.24.0`)

- Array operations

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEPENDENCY GRAPH                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                          ┌──────────────────┐                               │
│                          │     PyTorch      │                               │
│                          └────────┬─────────┘                               │
│                                   │                                          │
│                    ┌──────────────┴──────────────┐                          │
│                    │                             │                          │
│                    ▼                             ▼                          │
│           ┌─────────────────┐          ┌─────────────────┐                  │
│           │  Transformers   │          │     NumPy       │                  │
│           └────────┬────────┘          └────────┬────────┘                  │
│                    │                            │                           │
│                    ▼                            │                           │
│           ┌─────────────────┐                   │                           │
│           │   Sentence-     │◀──────────────────┘                           │
│           │  Transformers   │                                               │
│           └────────┬────────┘                                               │
│                    │                                                        │
│                    ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SpecRAG Core                                 │   │
│  │                                                                      │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │   │
│  │  │   Chunking    │  │  Vectorizer   │  │    Search     │            │   │
│  │  │  - LangChain  │  │  - Sentence-  │  │  - FAISS      │            │   │
│  │  │  - PyMuPDF    │  │    Trans.     │  │  - ChromaDB   │            │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘            │   │
│  │                                                                      │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │   │
│  │  │    Image      │  │   Sequence    │  │    Config     │            │   │
│  │  │  Extraction   │  │    Charts     │  │               │            │   │
│  │  │  - PyMuPDF    │  │  - PIL        │  │  - Pydantic   │            │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘            │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Installation

### Basic

```bash
pip install -r requirements.txt
```

### GPU Support

```bash
# PyTorch với CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118

# FAISS GPU
pip install faiss-gpu
```

### Minimal

```bash
pip install torch transformers sentence-transformers
pip install faiss-cpu
pip install langchain langchain-text-splitters
pip install pymupdf
pip install pydantic numpy tqdm
```

## Version Compatibility

| Package | Min Version | Notes |
|---------|-------------|-------|
| Python | 3.10 | 3.11 tested |
| torch | 2.0.0 | CUDA 11.8+ for GPU |
| transformers | 4.35.0 | For GTE model |
| sentence-transformers | 2.2.0 | |
| faiss-cpu | 1.7.4 | |
| PyMuPDF | 1.23.0 | |
| pydantic | 2.0.0 | V2 required |
