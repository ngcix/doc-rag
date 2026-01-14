# 🚀 SpecRag - Specification RAG System

A **high-performance** Retrieval-Augmented Generation (RAG) system optimized for **technical specification documents** (PDF, DOCX, MD).

Designed for **multimodal AI agents** (ClineSR, GaussO MM) with **vision capabilities** to analyze and retrieve diagrams, flowcharts, and technical figures.

![Python](https://img.shields.io/badge/Python-3.11.0-blue)

---

## 💪 Key Strengths

| Strength | Description |
|----------|-------------|
| **🎯 Spec-Optimized** | Designed for technical specs (Bluetooth, HID, A2DP). Auto-detects `Figure X.Y`, `Table X.Y` captions. |
| **🖼️ Full-Page Context** | Captures entire page as image + ALL text context (up to 10,000 chars) for maximum retrieval accuracy. |
| **� Hybrid Search** | Combines **Semantic (Vector)** + **Exact Match (BM25)** for both concept and keyword searches. |
| **🧩 Multi-Query RRF** | Run multiple query variants and fuse results with **Reciprocal Rank Fusion** algorithm. |
| **� Vision-Ready** | Returns image paths for agents with vision capability to analyze diagrams directly. |
| **🏷️ Self-Improving** | Tag images with custom keywords → Auto **re-embed** → Future searches rank higher. |
| **📊 Built-in Eval** | Measure accuracy with Hit Rate / MRR on golden datasets. |

---

## � Search Mechanisms Explained

### 1. Semantic Search (Default)

```bash
python -m src.main search "what is HID protocol?"
```

**How it works:**
- Query → **GTE Embedding** (768-dim vector)
- FAISS cosine similarity search
- Returns top-K documents by **semantic meaning**

**Best for:** Conceptual questions, "What is...", "Explain..."

---

### 2. Hybrid Search (`--hybrid` / `-hy`)

```bash
python -m src.main search -hy "Figure 4.2: Media Payload Format"
```

**How it works:**
- **Vector Search**: Semantic similarity (40% weight)
- **BM25 Search**: Exact keyword matching (60% weight)
- Results merged with **RRF (Reciprocal Rank Fusion)**

**Best for:** Exact names, figure/table titles, specific terms

---

### 3. Image-Only Search (`--pic` / `-pic`)

```bash
python -m src.main search -pic "connection diagram"
```

**How it works:**
- Normal search but **filters** for `content_type = image`
- Returns only extracted images/pages with image paths

**Best for:** Finding diagrams, charts, flowcharts

---

### 4. Multi-Query Search (`msearch`)

```bash
python -m src.main msearch "bluetooth reconnection" "link loss" "timeout recovery"
```

**How it works:**
- Runs **N queries** in parallel
- Each result gets **RRF score** based on rank across queries
- Documents appearing in multiple queries rank higher

**Best for:** Complex/vague questions, "How to...", "Why does..."

---

### 5. Combined Modes

```bash
# Find diagrams with exact title match
python -m src.main search -pic -hy "Interrupt IN Flow Chart"

# Multi-query for images only
python -m src.main msearch -pic "state machine" "connection flow" "FSM diagram"
```

---

## 🚀 Quick Start

### 1. Prepare Data

```text
data/documents/
  ├── HID_SPEC_V10.pdf
  ├── A2DP_v1.4.pdf
  └── Core_v6.0.pdf
```

### 2. Process Documents

You **MUST** specify an extraction strategy:

```bash
# [RECOMMENDED] Full-Page Mode (-fp)
# Best for RAG with diagrams - captures entire page context
python -m src.main process -fp

# Full-page with JPEG format (2-5x smaller files)
python -m src.main process -fp --format jpeg

# [ALTERNATIVE] Docling Mode (-dl)
# Uses Docling layout model for intelligent extraction
python -m src.main process -dl
```

> ⚠️ **Note**: You MUST specify either `-fp` or `-dl`. The system will error if neither is provided.

### 3. Search

```bash
# General question (semantic search)
python -m src.main search "what is the system architecture?"

# Find specific figure (hybrid for exact match)
python -m src.main search -hy "Figure 4.1"

# Find diagrams only
python -m src.main search -pic "connection flow"

# Complex question (multi-query)
python -m src.main msearch "reconnection" "link loss" "recovery"
```

---

## 🏃 Workflow Example

```bash
# 1. Process documents
python -m src.main process -fp

# 2. Search for something
python -m src.main search "system architecture"

# 3. Check tags of an image
python -m src.main listtag HID_SPEC_V10.pdf_p20

# 4. Add a custom tag (system automatically re-embeds!)
python -m src.main addtag HID_SPEC_V10.pdf_p20 "connection-diagram"

# 5. Search with tag (use --hybrid for exact match)
python -m src.main search -hy "connection-diagram"

# 6. Remove wrong tag
python -m src.main removetag HID_SPEC_V10.pdf_p20 "wrong-tag"

# 7. Reset to original tags
python -m src.main resettags HID_SPEC_V10.pdf_p20
```

---

## 🛠️ CLI Reference

| Command | Action | Example |
|---------|--------|---------|
| `process -fp` | Full-page extraction | `python -m src.main process -fp` |
| `process -fp -fmt jpeg` | Full-page JPEG (smaller) | `python -m src.main process -fp -fmt jpeg` |
| `process -dl` | Docling layout extraction | `python -m src.main process -dl` |
| `search` | Semantic search | `python -m src.main search "query"` |
| `search -pic` | Images only | `python -m src.main search -pic "diagram"` |
| `search -hy` | Hybrid (BM25+Vector) | `python -m src.main search -hy "Figure 4.1"` |
| `msearch` | Multi-Query (RRF) | `python -m src.main msearch "q1" "q2"` |
| `listtag` | View tags (original vs user) | `python -m src.main listtag doc_id` |
| `addtag` | Add tag & re-embed | `python -m src.main addtag doc_id "tag"` |
| `removetag` | Remove user-added tag | `python -m src.main removetag doc_id "tag"` |
| `resettags` | Reset to original tags | `python -m src.main resettags doc_id` |
| `addknowledge` | Add knowledge to image | `python -m src.main addknowledge doc_id "text"` |
| `getknowledge` | Get knowledge | `python -m src.main getknowledge doc_id` |
| `eval` | Run accuracy evaluation | `python -m src.main eval` |
| `list` | Show all indexed docs | `python -m src.main list` |
| `stats` | View DB status | `python -m src.main stats` |
| `clean` | Reset database | `python -m src.main clean --yes` |

---

## 📊 Technical Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Embedding Model** | `gte-multilingual-base` | Alibaba-NLP, 768-dim |
| **Vector Database** | FAISS | IndexFlatIP (cosine) |
| **Distance Metric** | Cosine Similarity | Normalized inner product |
| **Image Extraction** | PyMuPDF (fitz) | Full-page DPI 150 |
| **Layout Model** | Docling Heron | `docling-project/docling-layout-heron` |
| **Context Limit** | 10,000 chars | For full-page mode |

---

## 🏗️ Architecture

### Data Pipeline

```
Documents (PDF/DOCX/MD)
       ↓
  ┌────┴────┐
  │  Text   │  PDF
  ↓         ↓
Chunker   Image Extractor
  │          │
  └────┬─────┘
       ↓
 Batch Vectorization (GTE)
       ↓
   FAISS Index
```

### Extraction Strategies

| Strategy | Flag | Model | Best For |
|----------|------|-------|----------|
| **Full-Page** | `-fp` | PyMuPDF | Complex layouts, diagrams |
| **Docling** | `-dl` | Docling Heron | Intelligent layout detection |

---

## 🖼️ Image Extraction Deep Dive

### Full-Page Mode (`-fp`) - How It Works

```
PDF Document                    Processing Flow
┌──────────────────┐
│  Page 1          │           ┌─────────────────────────────────┐
│  [No images]     │  ───────► │ Skip (no images/drawings)       │
└──────────────────┘           └─────────────────────────────────┘

┌──────────────────┐           ┌─────────────────────────────────┐
│  Page 20         │           │ 1. Detect images/drawings       │
│  ┌────────────┐  │           │ 2. Check area ≥ 5% of page      │
│  │ [Diagram]  │  │  ───────► │ 3. Render full page (DPI 150)   │
│  └────────────┘  │           │ 4. Extract ALL text (≤10,000)   │
│  Figure 4.1:...  │           │ 5. Auto-tag (Figure X.Y regex)  │
└──────────────────┘           └─────────────────────────────────┘
```

### Detection Criteria

A page is captured if it has:
- **Embedded images** ≥ `min_width` × `min_height` AND ≥ 5% of page area
- **Vector drawings** with combined area ≥ 2% of page
- **Caption patterns**: `Figure X.Y`, `Table X.Y`, `Hình X.Y`, etc.

### ExtractedImage Data Structure

Each extracted image is stored with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `image_id` | string | Unique ID: `{pdf_name}_p{page}` (e.g., `HID_v10.pdf_p20`) |
| `image_path` | string | Path to saved image: `data/extracted_images/HID_v10.pdf_p20.png` |
| `source_file` | string | Original PDF path |
| `page_number` | int | 1-indexed page number |
| `bbox` | tuple | Bounding box `(x1, y1, x2, y2)` |
| `region_type` | string | `"fullpage"`, `"figure"`, `"table"`, `"chart"` |
| `surrounding_text` | string | **Context**: ALL text from page (≤10,000 chars) |
| `caption` | string | Auto-detected caption (e.g., `"Figure 4.1: Architecture"`) |
| `tags` | string | Combined: `original_tags,user_tags` |
| `original_tags` | string | Auto-extracted tags (immutable) |
| `user_tags` | string | User-added tags via `addtag` (mutable) |
| `knowledge` | string | User-added knowledge via `addknowledge` |

### Vectorization Text Formula

When indexing, the embedding is generated from:

```
Caption: {caption}
Tags: {tags}, {tags}, {tags}, {tags}, {tags}   ← 5x boost
Description: {description}
Context: {surrounding_text}
Type: {region_type}
Source: {filename}, Page {page_number}
```

> 💡 **Tags are repeated 5x** to strongly boost their weight in semantic search.

### Tag Management

| Field | Source | Mutable? |
|-------|--------|----------|
| `original_tags` | Auto-extracted from page text (regex) | ❌ No |
| `user_tags` | Added via `addtag` command | ✅ Yes |
| `tags` | Combined: `original_tags,user_tags` | Auto-updated |

**Commands:**
```bash
# View tags (shows original vs user)
python -m src.main listtag HID_v10.pdf_p20

# Add tag → triggers re-embed
python -m src.main addtag HID_v10.pdf_p20 "my-custom-tag"

# Remove user tag
python -m src.main removetag HID_v10.pdf_p20 "my-custom-tag"

# Reset to original tags only
python -m src.main resettags HID_v10.pdf_p20
```

## 🤖 Agent Integration

Designed for **ClineSR / GaussO MM** multimodal agents:

```
User Query → RAG Search → Top-K Results
                              ↓
                   ┌──────────┴──────────┐
                   │  image_path         │
                   │  context (text)     │
                   │  metadata           │
                   └──────────┬──────────┘
                              ↓
              Agent Vision Analysis + Response
```

### Feedback Loop

```bash
# Agent finds relevant image but hard to search
python -m src.main addtag HID_p42 "state-machine-diagram"

# Tag is boosted 5x in embedding → Future searches rank higher
```

---

## 📁 Project Structure

```text
SpecRag/
├── config/                 # Settings & configurations
├── data/
│   ├── documents/          # Input documents
│   ├── faiss_index/        # Vector index
│   └── extracted_images/   # Extracted images
├── models/                 # Local model cache
│   ├── gte-multilingual-base/
│   └── docling-layout-heron/
├── src/
│   ├── chunking/           # Text splitters
│   ├── image_extraction/   # PDF/Image processing
│   ├── search/             # Search engines
│   ├── vectorization/      # Embedding
│   └── main.py             # CLI entry point
└── tests/                  # Evaluation suite
```

---

## 📄 License

MIT License. Created by Phung Duc Vu.
