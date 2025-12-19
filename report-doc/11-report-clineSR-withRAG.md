# Cline + Simple RAG Integration Report (Summary)

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
    participant CLI as Simple RAG CLI
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
    CLI->>CLI: Tag Boost (3x repeat)
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
    Docs -->|①| Chunker
    Docs -->|①| ImgExt
    Chunker -->|②| Embed
    ImgExt -->|②| Embed
    Embed -->|③| FAISS

    %% Query Flow (④⑤⑥⑦)
    User -->|④| QueryInput
    QueryInput -->|Image| VisionProc
    QueryInput -->|Text| TextProc
    VisionProc --> Reasoning
    TextProc --> Reasoning
    Reasoning -->|⑤ Encode| Embed
    Embed -->|⑤ Vector| FAISS
    FAISS -->|⑥ Context| Reasoning
    Reasoning -->|⑦| Response

    %% Feedback Flow (⑧)
    Reasoning -.->|⑧ Re-embed| Embed
    Embed -.->|⑧ Update| FAISS

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

**Flow Legend:**
- **Solid arrows (→)**: Main data flow
- **Dotted arrow (⇢)**: Feedback loop
- **① → ③**: Ingestion pipeline (Docs → Embed → FAISS)
- **④ → ⑦**: Query pipeline (User → **Text+Image** → Agent → Embed → FAISS → Agent → Response)
- **⑧**: Feedback loop (Agent → **Embed** → FAISS update)

**Agent Layer Details (ClineSR / GaussO MM):**
- **👁️ Vision Processing**: Phân tích hình ảnh đầu vào từ user
- **📝 Text Processing**: Xử lý câu hỏi text
- **🧠 Reasoning & Generation**: Kết hợp context + multimodal input → tạo response

---

## 5. Tổng quan 8 bước

| Step | Component | Action |
|------|-----------|--------|
| **①** | Chunker & ImgExt | Extract content từ documents |
| **②** | Embedding Model | Vectorize text + images (OCR) |
| **③** | FAISS | Index vectors |
| **④** | User | Gửi câu hỏi |
| **⑤** | Search | Similarity search trong FAISS |
| **⑥** | Cline | Nhận context + vision analysis |
| **⑦** | Cline | Generate response |
| **⑧** | Feedback | Tag + Re-embed để cải thiện |

---

## Key Highlights

- **Vision-Enhanced RAG**: Cline có khả năng "xem" và phân tích hình ảnh
- **Hybrid Search**: Text chunks + Full-page images trong cùng database
- **Self-Improving**: Feedback loop (⑧) giúp database chính xác hơn theo thời gian
- **Tag Boosting**: Lặp lại tag 3x để tăng semantic weight khi re-embed
