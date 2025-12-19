# 🤖 Simple RAG System

A **production-ready** Retrieval-Augmented Generation (RAG) system engineered for high-performance document processing.

It handles **End-to-End** flow: from raw documents (PDF, DOCX, MD) to intelligent chunking, vectorization, and accurate semantic search.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **🧠 Intelligent Chunking** | Optimized recursive splitting for text (TXT, MD, PDF, DOCX) to preserve context. |
| **⚡ High-Perf Vectorization** | Uses `gte-multilingual-base` (384-dim) for SOTA multilingual embedding quality. |
| **🔍 Hybrid Search** | **Semantic Search** (Vector) + **Keyword Boosting** (Tags) for maximum accuracy. |
| **🖼️ Smart Image Extraction** | Extracts full PDF pages or individual images, auto-tags (e.g., `Figure 4.1`, `Table 2`). |
| **🤖 Agent Integration** | Designed for **ClineSR / GaussO MM** multimodal agent with vision capability. |
| **📈 Self-Improving** | Feedback loop with **Tag Boosting** (3x repeat) for automatic re-embedding. |

---

## 📊 Technical Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Embedding Model** | `gte-multilingual-base` | Alibaba-NLP, multilingual support |
| **Vector Dimensions** | 384 | Optimized for speed & quality |
| **Vector Database** | FAISS | IndexFlatIP (Inner Product) |
| **Chunk Size** | ~500 tokens | Configurable via settings |
| **Chunk Overlap** | 50 tokens | Preserves context boundaries |
| **Image Extraction** | PyMuPDF (fitz) | Full-page or individual mode |
| **OCR Engine** | PP-Structure (Optional) | Layout analysis & enrichment |

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repo
git clone <your-repo-url>
cd simple-rag

# Create virtual env
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install pymupdf paddlepaddle  # Core engines
```

### 2. Prepare Data

Put your documents in the data folder:

```text
data/documents/
  ├── internal_report.pdf
  ├── api_specs.md
  └── research_paper.docx
```

### 3. Process Documents (MUST specify extraction mode)

```bash
# [RECOMMENDED] Full-Page Mode (-fp)
# Captures entire page context + images. Best for RAG with diagrams.
python -m src.main process -fp

# [ALTERNATIVE] PyMuPDF Mode (-pymu)
# Extracts individual embedded images. Precision focus.
python -m src.main process -pymu
```

> ⚠️ **Note**: You MUST specify either `-fp` or `-pymu`. The system will error if neither is provided.

### 4. Search

```bash
# General question
python -m src.main search "what is the system architecture?"

# Specific target (High precision due to auto-tagging)
python -m src.main search "Figure 4.1"

# With top-k parameter
python -m src.main search "OAuth flow" --top-k 10
```

---

## 🏃 Workflow Example

A typical "Basic Cycle" for a new user:

```bash
# 1. Process documents (MUST choose -fp or -pymu)
python -m src.main process -fp

# 2. Search for something
python -m src.main search "system architecture"

# 3. Check tags of an image found (e.g., A2DP_v1.4.pdf_p18)
python -m src.main listtag A2DP_v1.4.pdf_p18

# 4. Add a manual tag (system automatically re-embeds!)
python -m src.main addtag A2DP_v1.4.pdf_p18 "security-diagram"

# 5. Search again with the new tag
python -m src.main search "security diagram"
```

---

## 🛠️ CLI Command Reference

| Command | Action | Example |
|---------|--------|---------|
| **`process -fp`** | Full-page image extraction | `python -m src.main process -fp` |
| **`process -pymu`** | Individual image extraction | `python -m src.main process -pymu` |
| **`search`** | Query the database | `python -m src.main search "query"` |
| **`list`** | Show all indexed Docs | `python -m src.main list` |
| **`listtag`** | View tags for a doc | `python -m src.main listtag doc_id` |
| **`addtag`** | Add tag & **Re-embed** | `python -m src.main addtag doc_id "new-tag"` |
| **`stats`** | View DB size/status | `python -m src.main stats` |
| **`clean`** | Reset database | `python -m src.main clean --yes` |
| **`init`** | Setup folder structure | `python -m src.main init` |

---

## 🤖 ClineSR / GaussO MM Integration

This RAG system is designed to work with multimodal AI agents:

### Architecture Flow

```
User (Text + Image Query)
         ↓
    ClineSR / GaussO MM
    ├── 👁️ Vision Processing
    └── 📝 Text Processing
         ↓
    🧠 Embedding (gte-multilingual-base)
         ↓
    💾 FAISS Search
         ↓
    📑 Top-K Context (text + image paths)
         ↓
    🧠 Reasoning & Generation
         ↓
    💬 Response (Text + Images)
```

### 8-Step Data Flow

| Step | Component | Action |
|------|-----------|--------|
| **①** | Chunker & ImgExt | Extract content from documents |
| **②** | Embedding Model | Vectorize text + images (OCR) |
| **③** | FAISS | Index vectors (N+M embeddings) |
| **④** | User | Send multimodal query (text + image) |
| **⑤** | Agent → Embed | Encode query → Vector |
| **⑥** | FAISS | Similarity search → Top-K results |
| **⑦** | Agent | Generate response with vision |
| **⑧** | Feedback | Tag + Re-embed to improve search |

### Feedback Loop (Tag Boosting)

When adding a tag:

```python
# Original content
content = "Image showing authentication flow..."

# After tag boost (3x repeat for semantic weight)
boosted = content + "\nTags: oauth, oauth, oauth, auth-flow, auth-flow, auth-flow"

# Re-embed and update FAISS
new_vector = embed(boosted)  # Higher similarity to "oauth" queries
```

> 📖 **Detailed Report**: [report-doc/11-report-clineSR-withRAG.md](report-doc/11-report-clineSR-withRAG.md)

---

## 🏗️ Architecture

### Data Processing Pipeline

```mermaid
graph LR
    A[Documents] --> B{Type Check};
    B -->|Text/MD/DOCX| C[Text Chunker];
    B -->|PDF| D[Image Extractor];
    D -->|Full Page| E[Auto-Tagging];
    C --> F[Batch Collector];
    E --> F;
    F --> G[Vectorization];
    G --> H[(FAISS DB)];
```

### Image Extraction Strategies

| Strategy | Flag | Description | Best For |
|----------|------|-------------|----------|
| **Full-Page** | `-fp` | Render entire page as image (DPI 150) | Diagrams, flowcharts, complex layouts |
| **PyMuPDF** | `-pymu` | Extract individual embedded images | Product images, charts, screenshots |

### Auto-Tagging

The system scans page text for patterns:

- `Figure X.Y`, `Diagram X`, `Chart X`
- `Table X.Y`, `Hình X.Y` (Vietnamese)
- Custom regex patterns in settings

Tags are repeated 3x in embedding content for **boosted retrieval priority**.

---

## ⚙️ Configuration

Customize in `config/settings.py`:

| Setting | Default | Options |
|---------|---------|---------|
| `EMBEDDING_MODEL` | `gte-multilingual-base` | Any SentenceTransformer model |
| `VECTOR_DIMENSION` | `384` | Model-dependent |
| `CHUNK_SIZE` | `500` | Tokens per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `CONTEXT_SIZE` | `10000` | Characters for image context |
| `TOP_K` | `5` | Default search results |

---

## 📁 Project Structure

```text
simple-rag/
├── config/                 # Settings & Global configs
├── data/                   # Your Data (Docs, DBs, Images)
│   ├── documents/          # Input documents
│   ├── embeddings/         # FAISS index files
│   └── images/             # Extracted images
├── src/
│   ├── chunking/           # Text splitters (LangChain based)
│   ├── image_extraction/   # PDF/Image processing (PyMuPDF)
│   ├── search/             # Search Algo & Ranking
│   ├── vectorization/      # Embedding Engines
│   └── main.py             # CLI Entry point
├── report-doc/             # Architecture & Integration docs
└── tests/                  # Pytest suite
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [04-flow-process.md](report-doc/04-flow-process.md) | Detailed processing flow |
| [05-flow-image-extraction.md](report-doc/05-flow-image-extraction.md) | Image extraction guide |
| [10-debuit-clineSR.md](report-doc/10-debuit-clineSR.md) | ClineSR integration (detailed) |
| [11-report-clineSR-withRAG.md](report-doc/11-report-clineSR-withRAG.md) | Summary report with diagrams |

---

## 📄 License

MIT License. Created by Phung Duc Vu.
