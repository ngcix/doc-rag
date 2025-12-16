# Document Processing Workflow

## Command: `python -m src.main process`

Sơ đồ dưới đây mô tả chi tiết luồng xử lý khi chạy lệnh `process`.

---

## 1. Tổng quan Pipeline

```mermaid
flowchart TB
    START([🚀 Start: python -m src.main process]) --> INIT

    subgraph INIT["⚙️ Initialization"]
        I1[Load Configuration] --> I2[Initialize DocumentChunker]
        I2 --> I3[Initialize TextVectorizer]
        I3 --> I4[Initialize VectorStore]
        I4 --> I5[Initialize ImageExtractor]
        I5 --> I6[Initialize ChartProcessor]
    end

    INIT --> PHASE1
    INIT --> PHASE2
    INIT --> PHASE3

    subgraph PHASE1["📄 Phase 1: Text Processing"]
        direction TB
        T1[Scan directory for documents] --> T2{File Type?}
        T2 -->|PDF| T3[PyPDF2 Reader]
        T2 -->|TXT/MD| T4[Direct File Read]
        T2 -->|DOCX| T5[python-docx Reader]
        T3 --> T6[Raw Text Content]
        T4 --> T6
        T5 --> T6
        T6 --> T7[LangChain RecursiveCharacterTextSplitter]
        T7 --> T8[Text Chunks<br/>chunk_size=512, overlap=50]
        T8 --> T9[Vectorize with GTE Model<br/>768-dim embeddings]
    end

    subgraph PHASE2["🖼️ Phase 2: Image Extraction"]
        direction TB
        IMG1[Scan PDFs in directory] --> IMG2[PyMuPDF fitz.open]
        IMG2 --> IMG3[Extract Embedded Images<br/>page.get_images]
        IMG2 --> IMG4[Extract Vector Drawings<br/>page.get_drawings]
        IMG3 --> IMG5[Validation Filter]
        IMG4 --> IMG6[Clustering Algorithm<br/>Merge nearby paths]
        IMG6 --> IMG7[Render at 150 DPI]
        IMG7 --> IMG5
        IMG5 --> IMG8{Valid Image?}
        IMG8 -->|brightness ≥ 30<br/>std_dev ≥ 15<br/>dark_ratio ≤ 85%| IMG9[✅ Save PNG]
        IMG8 -->|Invalid| IMG10[❌ Discard]
        IMG9 --> IMG11[Extract Surrounding Text]
        IMG11 --> IMG12[Vectorize Image Context]
    end

    subgraph PHASE3["📊 Phase 3: Sequence Charts"]
        direction TB
        C1[Scan .md files] --> C2[Find Mermaid code blocks]
        C2 --> C3[Parse sequenceDiagram]
        C3 --> C4[Extract participants & messages]
        C4 --> C5[Generate description text]
        C5 --> C6[Vectorize description]
    end

    PHASE1 --> STORE
    PHASE2 --> STORE
    PHASE3 --> STORE

    subgraph STORE["💾 Phase 4: Storage"]
        S1[Collect all embeddings] --> S2{Backend?}
        S2 -->|FAISS| S3[FAISS IndexFlatIP<br/>Cosine Similarity]
        S2 -->|ChromaDB| S4[ChromaDB Collection]
        S3 --> S5[Save to data/faiss_index/]
        S4 --> S6[Save to data/vectordb/]
    end

    STORE --> END([✅ Processing Complete!])

    style START fill:#4CAF50,color:#fff
    style END fill:#4CAF50,color:#fff
    style INIT fill:#E3F2FD
    style PHASE1 fill:#FFF3E0
    style PHASE2 fill:#F3E5F5
    style PHASE3 fill:#E8F5E9
    style STORE fill:#FFEBEE
```

---

## 2. Chi tiết Text Chunking

```mermaid
flowchart LR
    subgraph INPUT["Input Document"]
        A[📄 Raw Document<br/>PDF/TXT/MD/DOCX]
    end

    subgraph CHUNKING["Chunking Process"]
        B[Read File Content] --> C[RecursiveCharacterTextSplitter]
        C --> D["Separators Priority:<br/>1. \\n\\n (paragraphs)<br/>2. \\n (lines)<br/>3. . (sentences)<br/>4. space (words)"]
        D --> E[Split into Chunks]
    end

    subgraph OUTPUT["Output Chunks"]
        F["Chunk 1<br/>[0:512]"]
        G["Chunk 2<br/>[462:974]"]
        H["Chunk 3<br/>[924:1436]"]
        I[...]
    end

    INPUT --> CHUNKING
    E --> F
    E --> G
    E --> H
    E --> I

    style INPUT fill:#E3F2FD
    style CHUNKING fill:#FFF3E0
    style OUTPUT fill:#E8F5E9
```

**Configuration:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `chunk_size` | 512 | Characters per chunk |
| `chunk_overlap` | 50 | Overlap between consecutive chunks |
| `separators` | `[\n\n, \n, . , , ]` | Priority order for splitting |

---

## 3. Chi tiết Image Extraction

```mermaid
flowchart TD
    subgraph PDF["📄 PDF Document"]
        P1[page.get_images] --> P2[Embedded Bitmaps<br/>PNG/JPEG]
        P1b[page.get_drawings] --> P3[Vector Paths<br/>Lines, Shapes]
    end

    subgraph PROCESS["Processing"]
        P2 --> V1[fitz.Pixmap]
        P3 --> C1[Cluster nearby paths<br/>merge_distance=50px]
        C1 --> C2[page.get_pixmap<br/>clip=region, dpi=150]
        V1 --> ALPHA[Handle Alpha Channel]
        C2 --> ALPHA
        ALPHA --> VAL{Validation}
    end

    subgraph VALIDATION["Validation Checks"]
        VAL -->|"mean brightness < 30"| REJ1[❌ Too Dark]
        VAL -->|"std_dev < 15"| REJ2[❌ Solid Color]
        VAL -->|"dark_ratio > 85%"| REJ3[❌ Mostly Black]
        VAL -->|"width < 50 or height < 50"| REJ4[❌ Too Small]
        VAL -->|"All checks passed"| SAVE[✅ Valid Image]
    end

    subgraph OUTPUT["Output"]
        SAVE --> PNG["📁 data/extracted_images/<br/>{filename}_p{page}_img{idx}_{hash}.png"]
        SAVE --> CTX[Extract surrounding text]
        CTX --> VEC[Vectorize context<br/>for semantic search]
    end

    style PDF fill:#E3F2FD
    style PROCESS fill:#FFF3E0
    style VALIDATION fill:#FFEBEE
    style OUTPUT fill:#E8F5E9
```

---

## 4. Chi tiết Vectorization

```mermaid
flowchart LR
    subgraph INPUT["Input"]
        T1["Text Chunk<br/>'The authentication flow...'"]
        T2["Image Context<br/>'Figure 1: Login diagram...'"]
        T3["Chart Description<br/>'Sequence: User → Server'"]
    end

    subgraph MODEL["GTE Model"]
        M1["Alibaba-NLP/gte-multilingual-base"]
        M2["Max Sequence: 8192 tokens"]
        M3["Embedding Dimension: 768"]
    end

    subgraph PROCESS["Processing"]
        E1[SentenceTransformer.encode]
        E2[L2 Normalization]
    end

    subgraph OUTPUT["Output"]
        V1["[0.023, -0.156, 0.089, ..., 0.042]<br/>768-dimensional vector"]
    end

    INPUT --> MODEL
    MODEL --> PROCESS
    PROCESS --> OUTPUT

    style INPUT fill:#E3F2FD
    style MODEL fill:#FFF3E0
    style PROCESS fill:#F3E5F5
    style OUTPUT fill:#E8F5E9
```

---

## 5. Storage Architecture

```mermaid
flowchart TB
    subgraph VECTORS["Vectorized Data"]
        V1[Text Chunk Embeddings]
        V2[Image Context Embeddings]
        V3[Chart Description Embeddings]
    end

    subgraph FAISS["FAISS Backend (Default)"]
        F1[IndexFlatIP<br/>Inner Product Search]
        F2[L2 Normalized Vectors]
        F3["Cosine Similarity =<br/>Dot Product"]
        F1 --> F4[(documents.index)]
        F1 --> F5[(documents_metadata.pkl)]
    end

    subgraph CHROMA["ChromaDB Backend (Alternative)"]
        C1[PersistentClient]
        C2[HNSW Index]
        C1 --> C3[(SQLite + Parquet)]
    end

    VECTORS --> FAISS
    VECTORS --> CHROMA

    style VECTORS fill:#E3F2FD
    style FAISS fill:#E8F5E9
    style CHROMA fill:#FFF3E0
```

---

## 6. Output Summary

Khi `process` hoàn thành, terminal sẽ hiển thị:

```
==================================================
Processing complete!
  Text chunks: 150
  Images extracted: 125
  Total items in database: 275
```

### File Outputs:

| Location | Content |
|----------|---------|
| `data/faiss_index/documents.index` | FAISS vector index |
| `data/faiss_index/documents_metadata.pkl` | Metadata + documents |
| `data/extracted_images/*.png` | Extracted images from PDFs |

---

## 7. Command Options

```bash
# Full processing (text + images + charts)
python -m src.main process

# Skip image extraction
python -m src.main process --no-images

# Skip Mermaid chart processing
python -m src.main process --no-charts

# Custom input directory
python -m src.main process --input /path/to/documents
```
