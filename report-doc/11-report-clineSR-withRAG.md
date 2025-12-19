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
flowchart LR
    subgraph INPUT [📥 Input Layer]
        User[👤 User]
        Docs[📄 Documents]
    end

    subgraph PROCESS [⚙️ Processing Layer]
        Chunker[🔪 Chunker]
        ImgExt[🖼️ ImgExt]
        Embed[🧠 Embedding]
    end

    subgraph STORAGE [💾 Storage Layer]
        FAISS[(FAISS DB)]
    end

    subgraph AGENT [🤖 Agent Layer]
        Cline[🌟 Cline]
    end

    subgraph OUTPUT [📤 Output Layer]
        Response[💬 Response]
    end

    %% Ingestion Flow (①②③)
    Docs -->|①| Chunker
    Docs -->|①| ImgExt
    Chunker -->|②| Embed
    ImgExt -->|②| Embed
    Embed -->|③| FAISS

    %% Query Flow (④⑤⑥⑦)
    User -->|④ Query| Cline
    Cline -->|⑤ Encode Query| Embed
    Embed -->|⑤ Vector| FAISS
    FAISS -->|⑥ Context| Cline
    Cline -->|⑦| Response
    Response --> User

    %% Feedback Flow (⑧)
    Cline -.->|⑧ Re-embed| Embed
    Embed -.->|⑧ Update| FAISS

    classDef inputStyle fill:#e3f2fd,stroke:#1565c0
    classDef processStyle fill:#f3e5f5,stroke:#7b1fa2
    classDef storageStyle fill:#e1f5fe,stroke:#0277bd
    classDef agentStyle fill:#fce4ec,stroke:#c2185b
    classDef outputStyle fill:#e8f5e9,stroke:#2e7d32

    class User,Docs inputStyle
    class Chunker,ImgExt,Embed processStyle
    class FAISS storageStyle
    class Cline agentStyle
    class Response outputStyle
```

**Flow Legend:**
- **Solid arrows (→)**: Main data flow
- **Dotted arrow (⇢)**: Feedback loop
- **① → ③**: Ingestion pipeline (Docs → Embed → FAISS)
- **④ → ⑦**: Query pipeline (User → Cline → **Embed** → FAISS → Cline → Response)
- **⑧**: Feedback loop (Cline → **Embed** → FAISS update)

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
