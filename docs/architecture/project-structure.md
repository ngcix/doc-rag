# 📁 Cấu Trúc Project

## Tổng Quan

```
SpecRAG/
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
│   └── models--Alibaba-NLP--gte-multilingual-base/
│       └── snapshots/{id}/
│           ├── model.safetensors
│           ├── tokenizer.json
│           └── config.json
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
├── docs/                        # 📖 Documentation
├── requirements.txt             # 📦 Dependencies
└── README.md                    # 📖 Main README
```

## Chi Tiết Từng Module

### config/

```
config/
├── __init__.py     # Export: settings, paths, ensure_directories()
└── settings.py     # Pydantic config classes
```

**Config Classes**:
- `ModelConfig` - Embedding model
- `ChunkingConfig` - Text splitting
- `VectorDBConfig` - Database
- `SearchConfig` - Search params
- `ImageExtractionConfig` - Image extraction
- `SequenceChartConfig` - Mermaid charts

### src/

```
src/
├── __init__.py
├── main.py                      # CLI entry point
│
├── chunking/
│   ├── __init__.py              # Export: DocumentChunker, chunk_documents
│   └── chunker.py               # LangChain text splitting
│
├── image_extraction/
│   ├── __init__.py              # Export: get_image_extractor()
│   ├── extractor.py             # Full-page extraction (PyMuPDF)
│   ├── docling_extractor.py     # Docling legacy
│   ├── image_info.py            # ExtractedImage dataclass
│   └── docling/                 # Docling AI module
│       ├── __main__.py
│       ├── document.py
│       ├── extractor.py
│       ├── model.py
│       └── processor.py
│
├── search/
│   ├── __init__.py              # Export: get_search_engine(), SearchResult
│   ├── engine.py                # Semantic search
│   └── bm25.py                  # BM25 + Hybrid search
│
├── sequence_chart/
│   ├── __init__.py              # Export: get_chart_processor()
│   └── processor.py             # Mermaid parsing
│
└── vectorization/
    ├── __init__.py              # Export: get_vectorizer(), get_vector_store()
    ├── vectorizer.py            # TextVectorizer (SentenceTransformer)
    ├── faiss_store.py           # FaissVectorStore
    └── vector_store.py          # VectorStore (ChromaDB)
```

### data/

```
data/
├── documents/                   # INPUT: Tài liệu cần xử lý
│   └── *.pdf, *.docx, *.md
│
├── extracted_images/            # OUTPUT: Hình ảnh trích xuất
│   └── {filename}_p{page}.png
│
├── faiss_index/                 # STORAGE: FAISS
│   ├── documents.index          # Binary index
│   └── documents_metadata.pkl   # Pickle: metadata, documents, embeddings
│
└── vectordb/                    # STORAGE: ChromaDB (alternative)
    └── chroma.sqlite3
```

### process/

```
process/
├── input/                       # Query logs
│   └── query_{timestamp}.json
│
└── output/                      # Result logs
    └── query_{timestamp}.json
```

**Output file format**:
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

## File Naming Conventions

| Location | Pattern | Example |
|----------|---------|---------|
| Extracted images | `{docname}_p{page}.png` | `HID_v1.1.pdf_p30.png` |
| FAISS index | `{collection}.index` | `documents.index` |
| Metadata | `{collection}_metadata.pkl` | `documents_metadata.pkl` |
| Query logs | `query_{YYYYMMDD_HHMMSS}.json` | `query_20251218_105537.json` |

## Auto-Created Directories

`ensure_directories()` tự động tạo:

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
