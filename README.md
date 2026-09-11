# 🚀 SpecRAG

**High-performance RAG for Technical Specifications**

> Turn your PDF specs into a searchable knowledge base that AI agents can query instantly.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![FAISS](https://img.shields.io/badge/Vector_DB-FAISS-orange)

---

## ✨ Why SpecRAG?

| Feature | Description |
|---------|-------------|
| 🎯 **Spec-Optimized** | Auto-detects `Figure X.Y`, `Table X.Y` captions in technical docs |
| 🖼️ **Full-Page Context** | Captures entire page + 10,000 chars of text context |
| 🔀 **Hybrid Search** | Semantic + BM25 exact match with RRF fusion |
| 👁️ **Vision-Ready** | Returns image paths for AI agents to analyze diagrams |
| 🏷️ **Self-Improving** | Tag images → Auto re-embed → Better future searches |

---

## 🚀 Quick Start

```bash
# 1. Install the lightweight RAG service
git clone <repo-url> && cd SpecRAG
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Export the ONNX model (one-time)
python -m venv .venv-export
.venv-export/bin/pip install -r services/embedding/requirements-export.txt
.venv-export/bin/python services/embedding/export_model.py \
  --output models/embedding --optimization O3

# 3. Start the embedding service
docker compose up --build -d embedding

# 4. Re-index documents using the remote embedding API
cp your-specs/*.pdf data/documents/
docker compose run --rm rag specrag reindex -fp -y

# 5. Start RAG, then search over REST
docker compose up -d rag
curl -X POST http://localhost:8080/api/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"authentication flow","top_k":5}'
```

For local CLI development, expose the internal embedding port with
`docker compose -f compose.yaml -f compose.dev.yaml up embedding`.

---

## 🔍 Search Types

Choose the right search for your question:

| Question Type | Command | Example |
|---------------|---------|---------|
| **Conceptual** | `search` | `search "what is HID protocol"` |
| **Exact match** | `search -hy` | `search -hy "Figure 4.1"` |
| **Find diagrams** | `search -pic` | `search -pic "state machine"` |
| **Complex query** | `msearch` | `msearch "reconnect" "link loss" "timeout"` |

**Combine them:** `search -pic -hy "Figure 4.1"` finds the exact diagram.

### Search Workflow

```
Question → Strategy Selection → Search Execution → Analyze Results → Present Answer
              │                        │
              ├── Semantic            ├── Vector (FAISS)
              ├── Hybrid (-hy)        ├── BM25 (exact match)
              └── Multi-query         └── RRF Fusion
```

### RRF Fusion (Reciprocal Rank Fusion)

Thuật toán kết hợp kết quả từ nhiều nguồn search:

```
                    Query: "Figure 4.1"
                           │
              ┌────────────┴────────────┐
              ↓                         ↓
         Vector Search              BM25 Search
         (semantic)                 (exact match)
              │                         │
              └────────────┬────────────┘
                           ↓
                      RRF Fusion
              score = Σ weight/(k + rank)
                           ↓
                    Final Ranking
```

**Tại sao dùng RRF?** Vector score và BM25 score không cùng scale → RRF dùng **rank** thay vì score để merge.

> 📖 **Deep dive:** [Search Guide](docs/guides/searching.md)

---

## 🛠️ Core Commands

```bash
# Process
specrag process -fp          # Full-page extraction (recommended)

# Search
specrag search "query"       # Semantic search
specrag search -hy "query"   # Hybrid (exact + semantic)
specrag search -pic "query"  # Images only
specrag msearch "q1" "q2"    # Multi-query with RRF

# Improve
specrag addtag ID "tag"      # Add tag (triggers re-embed)
specrag addknowledge ID "text" # Add description

# Manage
specrag list                 # Show indexed documents
specrag stats                # Database statistics
specrag clean --yes          # Reset everything
```

> 📖 **Full reference:** [CLI Commands](docs/reference/cli-commands.md)

---

## 🏗️ How It Works

![System Architecture](docs/pic/structure.png)

### Split runtime

- The **embedding container** owns the ONNX model, tokenizer, CLS pooling,
  normalization, batching, and `/v1/embeddings`.
- The **RAG container** owns ingestion, metadata, FAISS/BM25, CLI, and REST API.
- The RAG runtime does not install Torch, Transformers, Sentence Transformers,
  or ONNX Runtime.
- FAISS is single-writer. Run one RAG replica per data volume.

### Tech Stack

| Component | Technology |
|-----------|------------|
| Embedding | `Alibaba-NLP/gte-multilingual-base` (768-dim) |
| Vector DB | FAISS (IndexFlatIP, cosine similarity) |
| PDF Processing | PyMuPDF (fitz) |
| Image Extraction | PyMuPDF full-page rendering |

> 📖 **Architecture details:** [Overview](docs/architecture/overview.md)

---

## 🧠 Models

The `models/` directory stores NLP models for embedding and searching. SpecRAG uses the **Alibaba-NLP/gte-multilingual-base** model from Hugging Face.

### Model Specifications

| Specification | Value |
|---------------|-------|
| **Model** | [Alibaba-NLP/gte-multilingual-base](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) |
| **Parameters** | 305M |
| **Embedding Dimension** | 768 |
| **Max Input Tokens** | 8,192 |
| **Languages** | 75 languages |
| **Architecture** | Transformer++ (BERT + RoPE + GLU) |
| **License** | Apache 2.0 |

### Why This Model?

| Feature | Benefit |
|---------|---------|
| **Multilingual** | Supports 75 languages including Vietnamese and English |
| **Long Context** | 8K tokens allows embedding entire pages |
| **Fast Inference** | Encoder-only (10x faster than decoder LLMs) |
| **State-of-the-Art** | Top performance on multilingual retrieval benchmarks |
| **Elastic Embedding** | Reduces storage costs with dimension flexibility |

### Model Directory Structure

```
models/
└── embedding/
    ├── onnx/model_o3.onnx
    ├── tokenizer.json
    ├── 1_Pooling/config.json
    └── specrag-manifest.json
```

> 📖 **Paper:** [mGTE: Generalized Long-Context Text Representation](https://arxiv.org/abs/2407.19669) (2024)

---

## 🛠️ Development & Build

SpecRAG uses standard Python wheels for development and two Docker images for
deployment. PyInstaller and Cython are no longer part of the build.

### Quick Build
```bash
make setup-env   # Setup venv and install
make test        # Run unit and contract tests
make lint        # Ruff + 300-line source limit
make build       # Build the RAG wheel
docker compose build
```

> 📖 **Detailed Guide:** [Build Instructions](scripts/build.md)

---

## 🤖 Cline Integration

SpecRAG includes ready-to-use rules for **Cline** AI agent in `.clinerules/`:

```
.clinerules/
├── rule_rag_backend.md        # Core rules: search first, no manual PDF reading
└── workflows/
    ├── workflow_rag_backend.md      # Standard search → analyze → answer
    └── workflow_rag_with_knowledge.md # Use pre-analyzed knowledge
```

**How it works:** Cline automatically searches RAG before answering, analyzes images with vision, and adds tags to improve future searches.

> 📖 **Setup guide:** [Cline Integration](docs/integrations/cline.md)

---

## 📁 Project Structure

```
SpecRAG/
├── compose.yaml
├── services/
│   ├── rag/Dockerfile
│   └── embedding/
├── src/specrag/
│   ├── api/
│   ├── cli/
│   ├── embedding/
│   ├── ingestion/
│   ├── search/
│   └── vectorization/
├── config/
├── tests/
└── tools/
```

---

## 📚 Documentation

| | |
|---|---|
| **[Getting Started](docs/getting-started/)** | Installation, Quickstart, Basic Workflow |
| **[Guides](docs/guides/)** | Processing, Searching, Tagging, Knowledge |
| **[Reference](docs/reference/)** | CLI Commands, Configuration |
| **[Architecture](docs/architecture/)** | System Overview, Image Extraction, Search Engine |
| **[Integrations](docs/integrations/)** | Cline AI Agent |

---

## 📄 License

MIT License. Created by **Phung Duc Vu**.
