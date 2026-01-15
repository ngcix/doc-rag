# Cline + SpecRag Integration Report (Summary)

> 📖 **Chi tiết đầy đủ**: [10-debuit-clineSR.md](./10-debuit-clineSR.md)

---

## 1. Phase 1: INGESTION (Nạp dữ liệu)

```mermaid
sequenceDiagram
    participant Doc as Documents (PDF/MD)
    participant Chunker as Text Chunker
    participant ImgExt as Image Extractor (PyMuPDF)
    participant Embed as Embedding (gte-multilingual-base)
    participant DB as FAISS Database

    Doc->>Chunker: ① Extract text
    Doc->>ImgExt: ① Extract images
    Chunker->>Embed: ② N text chunks
    ImgExt->>Embed: ② M images + OCR
    Embed->>DB: ③ Vectorize & Store (N+M embeddings)
```

---

## 2. Phase 2: RETRIEVAL (Tìm kiếm)

```mermaid
sequenceDiagram
    actor User
    participant Cline as Cline (Vision LLM)
    participant CLI as SpecRag CLI
    participant DB as FAISS Database

    User->>Cline: ④ "Show me OAuth diagram"
    Cline->>CLI: ⑤ search "OAuth diagram"
    CLI->>DB: ⑥ Similarity search
    DB-->>CLI: Top-K results (text + image paths)
    CLI-->>Cline: Context returned
    Cline->>Cline: ⑦ Vision: Analyze images
    Cline-->>User: Response with text + images
```

---

## 3. Phase 3: FEEDBACK (Cải thiện)

```mermaid
sequenceDiagram
    actor User
    participant Cline as Cline (Vision LLM)
    participant CLI as addtag CLI
    participant Embed as Embedding Model
    participant DB as FAISS Database

    User->>Cline: "Yes, that's the OAuth flow"
    Cline->>CLI: ⑧ addtag "doc_id" "oauth, auth-flow"
    CLI->>CLI: Tag Boost (5x repeat)
    CLI->>Embed: Re-embed with boosted content
    Embed->>DB: Update vector
    CLI-->>Cline: Tag added successfully
    Note over DB: Next search ranks higher!
```

---

## 4. Kiến Trúc Kết Nối Module

```mermaid
flowchart TB
    subgraph INPUT [📥 Input Layer]
        User[👤 User]
        Docs[📄 Documents]
        QueryInput[📧 Query: Text + Image]
    end

    subgraph PROCESS [⚙️ Processing Layer]
        Chunker[🔪 Chunker]
        ImgExt[🖼️ ImgExt]
        Embed[🧠 Embedding]
    end

    subgraph STORAGE [💾 Storage Layer]
        FAISS[(FAISS DB)]
    end

    subgraph AGENT [🤖 Agent Layer: ClineSR / GaussO MM]
        direction TB
        VisionProc[👁️ Vision Processing]
        TextProc[📝 Text Processing]
        Reasoning[🧠 Reasoning & Generation]
    end

    subgraph OUTPUT [📤 Output Layer]
        Response[💬 Response: Text + Images]
    end

    %% Ingestion Flow (①②③)
    Docs -->|① Extract| Chunker
    Docs -->|① Extract| ImgExt
    Chunker -->|② N chunks| Embed
    ImgExt -->|② M images + OCR| Embed
    Embed -->|③ Vectorize| FAISS

    %% Query Flow (④⑤⑥⑦)
    User -->|④ Multimodal Query| QueryInput
    QueryInput -->|Image Input| VisionProc
    QueryInput -->|Text Input| TextProc
    VisionProc --> Reasoning
    TextProc --> Reasoning
    Reasoning -->|⑤ Encode Query| Embed
    Embed -->|⑤ Query Vector| FAISS
    FAISS -->|⑥ Top-K Context| Reasoning
    Reasoning -->|⑦ Generate| Response

    %% Feedback Flow (⑧)
    Reasoning -.->|⑧ Tag + Re-embed| Embed
    Embed -.->|⑧ Update Index| FAISS

    %% Output to User
    Response --> User

    classDef inputStyle fill:#e3f2fd,stroke:#1565c0
    classDef processStyle fill:#f3e5f5,stroke:#7b1fa2
    classDef storageStyle fill:#e1f5fe,stroke:#0277bd
    classDef agentStyle fill:#fce4ec,stroke:#c2185b
    classDef outputStyle fill:#e8f5e9,stroke:#2e7d32

    class User,Docs,QueryInput inputStyle
    class Chunker,ImgExt,Embed processStyle
    class FAISS storageStyle
    class VisionProc,TextProc,Reasoning agentStyle
    class Response outputStyle
```

---

### 🔵 INGESTION PIPELINE (Steps ①②③)

```
📄 Documents (PDF/Markdown)
         ↓ ①
   ┌─────┴──────┐
   ↓            ↓
🔪 Chunker   🖼️ ImgExt
(~500 tokens)  (PyMuPDF)
   ↓            ↓
   N chunks     M images + OCR
   └─────┬──────┘
         ↓ ②
   🧠 Embedding Model
   (gte-multilingual-base)
         ↓ ③
   💾 FAISS Database
   (N+M vectors indexed)
```

| Step | Component | Input | Output |
|------|-----------|-------|--------|
| **①** | Chunker & ImgExt | PDF/MD files | N text chunks (~500 tokens each) + M images |
| **②** | Embedding Model | Text + OCR content | 768-dim vectors for each chunk/image |
| **③** | FAISS Index | N+M embeddings | Indexed vector database |

---

### 🟢 QUERY PIPELINE (Steps ④⑤⑥⑦)

```
👤 User
   ↓ ④ Multimodal Query
📧 Query (Text + Image)
   ├──→ 📝 Text Processing
   └──→ 👁️ Vision Processing
         ↓
   🧠 Reasoning (ClineSR/GaussO MM)
         ↓ ⑤
   🧠 Embed → Query Vector
         ↓
   💾 FAISS Similarity Search
         ↓ ⑥
   📑 Top-K Results (text + image paths)
         ↓
   🧠 Reasoning + Vision Analysis
         ↓ ⑦
   💬 Response (Text + Images)
         ↓
   👤 User receives answer
```

| Step | Component | Input | Output |
|------|-----------|-------|--------|
| **④** | User → Agent | Text query + optional image | Multimodal input to Agent |
| **⑤** | Agent → Embed → FAISS | Query content | Query vector → Similarity search |
| **⑥** | FAISS → Agent | Query vector | Top-K relevant chunks + image paths |
| **⑦** | Agent (Vision + Reasoning) | Context + original query | Generated response with images |

---

### � FEEDBACK LOOP (Step ⑧)

```
🧠 Agent (After generating response)
   ↓
   Decision: Tag this content for better search
   ↓ ⑧
🏷️ addtag CLI
   ├── 1. Retrieve current content
   ├── 2. Boost: content + "Tags: oauth, oauth, oauth, oauth, oauth, ..." (5x)
   ├── 3. Re-embed with gte-multilingual-base
   ├── 4. DELETE old FAISS entry
   └── 5. ADD new entry with boosted vector
   ↓
💾 FAISS Database UPDATED
   ↓
✨ Next search ranks this document higher!
```

| Step | Action | Description |
|------|--------|-------------|
| **⑧.1** | Retrieve | Lấy content và metadata hiện tại từ FAISS |
| **⑧.2** | Tag Boost | Append tag lặp lại 5x để tăng semantic weight |
| **⑧.3** | Re-embed | Tạo embedding mới với boosted content |
| **⑧.4** | Delete | Xóa entry cũ khỏi index |
| **⑧.5** | Add | Thêm entry mới với vector cập nhật |

---

## 5. Agent Layer Details (ClineSR / GaussO MM)

| Component | Description |
|-----------|-------------|
| **👁️ Vision Processing** | Phân tích hình ảnh đầu vào từ user (screenshot, diagram, photo) |
| **📝 Text Processing** | Xử lý câu hỏi dạng text, extract intent và keywords |
| **🧠 Reasoning & Generation** | Kết hợp: query + retrieved context + vision analysis → generate response |

**Capabilities:**

- Multimodal input: Nhận cả text và image từ user
- Vision analysis: "Xem" và hiểu nội dung hình ảnh
- Context fusion: Kết hợp retrieved text chunks với image OCR
- Self-improvement: Tự động tag để cải thiện search quality

---

## 6. Key Highlights

| Feature | Description |
|---------|-------------|
| **Vision-Enhanced RAG** | Agent có khả năng "xem" và phân tích hình ảnh |
| **Multimodal Query** | User có thể query bằng text + image |
| **Hybrid Search** | BM25 + Vector kết hợp cho exact + semantic match |
| **Multi-Query (msearch)** | Tìm kiếm đa queries, merge bằng RRF |
| **Knowledge Management** | Thêm mô tả/annotation vào documents |
| **Self-Improving** | Feedback loop (⑧) giúp database chính xác hơn theo thời gian |
| **Tag Boosting** | Lặp lại tag 5x để tăng semantic weight khi re-embed |

---

> 📖 **Chi tiết đầy đủ**: [10-debuit-clineSR.md](./10-debuit-clineSR.md)

