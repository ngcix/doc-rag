# 🏗️ Kiến Trúc Tổng Quan

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SPECRAG SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │ Documents  │───▶│   Chunking   │───▶│ Vectorization│───▶│ Vector DB   │ │
│  │ (PDF/DOCX) │    │  (LangChain) │    │   (GTE 768d) │    │ (FAISS)     │ │
│  └────────────┘    └──────────────┘    └──────────────┘    └─────────────┘ │
│                                                                    │        │
│  ┌────────────┐    ┌──────────────┐                               ▼        │
│  │    PDF     │───▶│   Image      │──────────────────────▶ ┌─────────────┐ │
│  │  (Images)  │    │  Extraction  │                        │   Search    │ │
│  └────────────┘    └──────────────┘                        │   Engine    │ │
│                                                             └─────────────┘ │
│  ┌────────────┐    ┌──────────────┐                               │        │
│  │  Markdown  │───▶│  Sequence    │──────────────────────────────▶│        │
│  │  (Mermaid) │    │   Charts     │                               ▼        │
│  └────────────┘    └──────────────┘                        ┌─────────────┐ │
│                                                             │   Results   │ │
│                                                             └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Document Chunking (`src/chunking/`)

- **Tool**: LangChain `RecursiveCharacterTextSplitter`
- **Chunk size**: 512 characters
- **Overlap**: 150 characters
- **Supports**: TXT, MD, PDF, DOCX

### 2. Image Extraction (`src/image_extraction/`)

- **Tool**: PyMuPDF (fitz) full-page rendering
- **Mode**: Full-page (`-fp`) capture toàn trang
- **Features**: Auto-tagging, tag boosting 10x

### 3. Vectorization (`src/vectorization/`)

- **Model**: `Alibaba-NLP/gte-multilingual-base`
- **Dimension**: 768
- **Max tokens**: 8192
- **Backend**: FAISS (default) hoặc ChromaDB

### 4. Search Engine (`src/search/`)

- **Semantic Search**: Cosine similarity trên FAISS
- **Hybrid Search**: BM25 + Vector (RRF fusion)
- **Multi-query**: Multiple queries + RRF merge

### 5. Sequence Charts (`src/sequence_chart/`)

- **Format**: Mermaid diagrams
- **Processing**: Parse, render, vectorize

## Data Flow

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

## Key Features

| Feature | Mô tả |
|---------|-------|
| **Intelligent Chunking** | Recursive splitting bảo toàn context |
| **High-Perf Vectorization** | GTE model 768-dim, multilingual |
| **Hybrid Search** | Semantic + BM25 exact match |
| **Smart Image Extraction** | Full-page + auto-tagging |
| **Tag Boosting** | 10x repeat để tăng semantic weight |
| **Knowledge Management** | Thêm description vào documents |
| **Self-Improving** | Feedback loop qua addtag/addknowledge |

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Embedding** | Alibaba-NLP/gte-multilingual-base (768-dim) |
| **Vector DB** | FAISS (IndexFlatIP, cosine similarity) |
| **Search** | Semantic + BM25 Hybrid + Multi-Query RRF |
| **PDF Processing** | PyMuPDF (fitz) |
| **Image Extraction** | PyMuPDF full-page rendering |
| **Text Splitting** | LangChain RecursiveCharacterTextSplitter |
| **Config** | Pydantic v2 |

## Processing Pipeline

```
┌──────┐    ┌─────────┐    ┌────────────┐    ┌───────────┐    ┌────────────┐
│ CLI  │    │ Chunker │    │ Extractor  │    │ Vectorizer│    │VectorStore │
└──┬───┘    └────┬────┘    └─────┬──────┘    └─────┬─────┘    └─────┬──────┘
   │             │               │                 │                │
   │ process()   │               │                 │                │
   │─────────────│               │                 │                │
   │             │               │                 │                │
   │ chunk_dir() │               │                 │                │
   │────────────>│               │                 │                │
   │             │               │                 │                │
   │  chunks[]   │               │                 │                │
   │<────────────│               │                 │                │
   │             │               │                 │                │
   │ extract()   │               │                 │                │
   │─────────────│──────────────>│                 │                │
   │             │               │                 │                │
   │  images[]   │               │                 │                │
   │<────────────│───────────────│                 │                │
   │             │               │                 │                │
   │ vectorize(all_texts)        │                 │                │
   │─────────────│───────────────│────────────────>│                │
   │             │               │                 │                │
   │  embeddings[]               │                 │                │
   │<────────────│───────────────│─────────────────│                │
   │             │               │                 │                │
   │ add_chunks()│               │                 │                │
   │─────────────│───────────────│─────────────────│───────────────>│
   │             │               │                 │                │
   │             │               │                 │    rebuild()   │
   │             │               │                 │    save()      │
   │             │               │                 │                │
   │   "Done!"   │               │                 │                │
   │<────────────│───────────────│─────────────────│────────────────│
```

---

**Xem thêm**: 
- [Project Structure →](./project-structure.md)
- [Image Extraction →](./image-extraction.md)
- [Search Engine →](./search-engine.md)
