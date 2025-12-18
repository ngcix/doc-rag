# 📁 Cấu Trúc Thư Mục Dự Án

## 1. Tổng Quan Cấu Trúc

```
simple-rag/
├── config/                      # ⚙️ Cấu hình hệ thống
│   ├── __init__.py              # Export settings, paths
│   └── settings.py              # Định nghĩa tất cả cấu hình
│
├── data/                        # 📂 Dữ liệu (input/output)
│   ├── documents/               # 📄 Input documents (PDF, DOCX, MD)
│   ├── extracted_images/        # 🖼️ Hình ảnh đã trích xuất
│   ├── faiss_index/             # 🔍 FAISS index files
│   │   ├── documents.index      # Binary FAISS index
│   │   └── documents_metadata.pkl # Metadata + embeddings
│   └── vectordb/                # 📊 ChromaDB data (alternative)
│
├── models/                      # 🤖 Local models
│   └── Alibaba-NLP_gte-multilingual-base/  # Embedding model
│       ├── model.safetensors    # Model weights
│       ├── tokenizer.json       # Tokenizer
│       └── config.json          # Model config
│
├── process/                     # 📝 Process logs
│   ├── input/                   # Query inputs (JSON)
│   └── output/                  # Search results (JSON)
│
├── src/                         # 💻 Source code
│   ├── __init__.py
│   ├── main.py                  # 🚀 CLI Entry point
│   ├── chunking/                # ✂️ Document chunking
│   ├── image_extraction/        # 🖼️ Image extraction
│   ├── search/                  # 🔍 Search engine
│   ├── sequence_chart/          # 📊 Mermaid processing
│   └── vectorization/           # 🧮 Vectorization
│
├── tests/                       # 🧪 Unit tests
│   ├── test_chunking.py
│   └── test_sequence_chart.py
│
├── requirements.txt             # 📦 Dependencies
├── pyproject.toml               # 🔧 Project metadata
└── README.md                    # 📖 Documentation
```

## 2. Chi Tiết Từng Module

### 2.1 `config/` - Cấu Hình

```
config/
├── __init__.py                  # Export tất cả settings và paths
└── settings.py                  # Định nghĩa cấu hình chi tiết
```

**`__init__.py` exports**:
- `settings` - Global settings instance
- `ensure_directories()` - Tạo thư mục cần thiết
- Tất cả paths: `DOCUMENTS_DIR`, `EXTRACTED_IMAGES_DIR`, `FAISS_INDEX_DIR`...
- Tất cả config classes: `ModelConfig`, `ChunkingConfig`, `VectorDBConfig`...

**`settings.py` classes**:
| Class | Mục đích |
|-------|----------|
| `ModelConfig` | Cấu hình embedding model |
| `ChunkingConfig` | Cấu hình chia chunk |
| `VectorDBConfig` | Cấu hình vector database |
| `SearchConfig` | Cấu hình search |
| `SequenceChartConfig` | Cấu hình sequence charts |
| `ImageExtractionConfig` | Cấu hình trích xuất ảnh |
| `Settings` | Tổng hợp tất cả configs |

### 2.2 `data/` - Dữ Liệu

```
data/
├── documents/                   # INPUT: Đặt tài liệu cần xử lý
│   └── *.pdf, *.docx, *.md
│
├── extracted_images/            # OUTPUT: Hình ảnh được trích xuất
│   └── {filename}_p{page}.png   # Pattern: docname_p{pagenum}.png
│
├── faiss_index/                 # STORAGE: FAISS vector index
│   ├── documents.index          # FAISS binary index
│   └── documents_metadata.pkl   # Pickle file chứa:
│       ├── metadata             # Dict[doc_id, metadata]
│       ├── documents            # Dict[doc_id, content]
│       ├── embeddings           # Dict[doc_id, vector]
│       └── dimension            # Embedding dimension (768)
│
└── vectordb/                    # STORAGE: ChromaDB (alternative)
    └── chroma.sqlite3           # SQLite database
```

### 2.3 `src/` - Source Code

```
src/
├── __init__.py
├── main.py                      # CLI entry point (argparse)
│
├── chunking/
│   ├── __init__.py              # Export: DocumentChunker, DocumentChunk
│   └── chunker.py               # Text splitting logic
│
├── image_extraction/
│   ├── __init__.py              # Export: ImageExtractor, ExtractedImage
│   └── extractor.py             # PDF image extraction logic
│
├── search/
│   ├── __init__.py              # Export: SearchEngine, SearchResult
│   └── engine.py                # Semantic search implementation
│
├── sequence_chart/
│   ├── __init__.py              # Export: SequenceChartProcessor
│   └── processor.py             # Mermaid parsing logic
│
└── vectorization/
    ├── __init__.py              # Export: get_vector_store() factory
    ├── vectorizer.py            # TextVectorizer class
    ├── faiss_store.py           # FaissVectorStore class
    └── vector_store.py          # VectorStore class (ChromaDB)
```

### 2.4 `process/` - Logs

```
process/
├── input/                       # Search query inputs
│   └── query_{timestamp}.json   # {query_id, query, timestamp, parameters}
│
└── output/                      # Search results
    └── query_{timestamp}.json   # {query_id, results: [...]}
```

**Ví dụ output file**:
```json
{
  "query_id": "query_20251218_105537",
  "query": "Figure 4.1",
  "timestamp": "2025-12-18T10:55:37",
  "result_count": 5,
  "results": [
    {
      "rank": 1,
      "document": "Tags: Figure 4.1...",
      "similarity": 0.8542,
      "metadata": {"source_file": "HID.pdf", "page_number": 30},
      "chunk_id": "HID.pdf_p30"
    }
  ]
}
```

### 2.5 `models/` - Local Models

```
models/
└── models--Alibaba-NLP--gte-multilingual-base/
    └── snapshots/
        └── {snapshot_id}/
            ├── model.safetensors    # Model weights (~1GB)
            ├── tokenizer.json       # Tokenizer vocabulary
            ├── config.json          # Model architecture config
            ├── modules.json         # SentenceTransformer modules
            └── sentence_bert_config.json
```

**Lợi ích local model**:
- Offline usage
- Faster loading
- No network dependency
- Consistent versioning

## 3. Data Flow Qua Thư Mục

```
┌──────────────────┐
│ data/documents/  │  ◀── INPUT: User đặt tài liệu
│   *.pdf          │
│   *.docx         │
└────────┬─────────┘
         │
         ▼ process -fp
┌──────────────────────────────┐
│ data/extracted_images/       │  ◀── OUTPUT: Hình ảnh
│   {doc}_p{page}.png          │
└────────┬─────────────────────┘
         │
         ▼ vectorization
┌──────────────────────────────┐
│ data/faiss_index/            │  ◀── STORAGE: Vectors
│   documents.index            │
│   documents_metadata.pkl     │
└────────┬─────────────────────┘
         │
         ▼ search
┌──────────────────────────────┐
│ process/output/              │  ◀── LOGS: Results
│   query_{ts}.json            │
└──────────────────────────────┘
```

## 4. File Naming Conventions

| Location | Pattern | Example |
|----------|---------|---------|
| Extracted images | `{docname}_p{page}.png` | `HID_v1.1.1.pdf_p30.png` |
| FAISS index | `{collection}.index` | `documents.index` |
| Metadata | `{collection}_metadata.pkl` | `documents_metadata.pkl` |
| Query logs | `query_{YYYYMMDD_HHMMSS}.json` | `query_20251218_105537.json` |

## 5. Các Thư Mục Được Tự Động Tạo

Hàm `ensure_directories()` trong `config/settings.py` tự động tạo:

```python
directories = [
    DOCUMENTS_DIR,        # data/documents/
    EXTRACTED_IMAGES_DIR, # data/extracted_images/
    VECTORDB_DIR,         # data/vectordb/
    FAISS_INDEX_DIR,      # data/faiss_index/
    MODELS_DIR,           # models/
    PROCESS_INPUT_DIR,    # process/input/
    PROCESS_OUTPUT_DIR,   # process/output/
]
```

