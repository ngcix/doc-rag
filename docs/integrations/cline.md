# 🤖 Cline Integration

## Tổng Quan

SpecRAG được thiết kế để tích hợp với **Cline** (LLM Agent) qua CLI. Cline có khả năng **Vision** để xử lý cả văn bản và hình ảnh.

### Capabilities

- **Đọc kết quả văn bản** từ SpecRAG search
- **"Nhìn" và phân tích hình ảnh** từ search results
- **Hiểu context** từ cả text + images
- **Tự động gắn tag** để cải thiện search quality

## Quy Trình 3 Phases

### Phase 1: INGESTION - Nạp Tài Liệu

```
User → Cline: "Learn this document: specs.pdf"
                    ↓
Cline → CLI: python -m src.main process -fp
                    ↓
           ┌────────┴────────┐
           ↓                 ↓
    Text Chunking     Image Extraction
           ↓                 ↓
           └────────┬────────┘
                    ↓
            Vectorization (GTE)
                    ↓
            FAISS Database
                    ↓
Cline → User: "Ingested. I can now search."
```

**CLI Command**:
```bash
python -m src.main process -fp --input ./docs
```

### Phase 2: RETRIEVAL - Tìm Kiếm

```
User → Cline: "Show me the OAuth diagram"
                    ↓
Cline → CLI: python -m src.main search -pic "OAuth diagram"
                    ↓
            FAISS Similarity Search
                    ↓
            Top-K Results (text + image paths)
                    ↓
Cline: Vision Analysis (read images)
                    ↓
Cline → User: Response với text + images
```

**CLI Commands**:
```bash
# Semantic search
python -m src.main search "authentication flow"

# Hybrid search (tốt cho exact match)
python -m src.main search -hy "Figure 4.1"

# Image-only search
python -m src.main search -pic "state machine"
```

### Phase 3: FEEDBACK - Cải Thiện

```
User → Cline: "Yes, that's the OAuth flow"
                    ↓
Cline decides: This image is relevant, tag it
                    ↓
Cline → CLI: python -m src.main addtag doc_id "oauth"
                    ↓
            Tag Boost + Re-embedding
                    ↓
            FAISS Database Updated
                    ↓
Next search ranks this document higher!
```

**CLI Commands**:
```bash
# Add tag
python -m src.main addtag HID_p42 "oauth"

# Add knowledge
python -m src.main addknowledge HID_p42 "OAuth2 flow diagram"
```

## Architecture với Cline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLINE + SPECRAG SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐                                                              │
│  │    User    │                                                              │
│  └─────┬──────┘                                                              │
│        │ Natural Language                                                    │
│        ▼                                                                     │
│  ┌─────────────────────────────────────────────┐                            │
│  │            Cline (LLM Agent)                │                            │
│  │  ┌─────────────┐  ┌─────────────────────┐   │                            │
│  │  │   Vision    │  │  Text Processing    │   │                            │
│  │  │  Capability │  │  + Reasoning        │   │                            │
│  │  └─────────────┘  └─────────────────────┘   │                            │
│  └──────────────────────┬──────────────────────┘                            │
│                         │ CLI Commands                                       │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────┐                            │
│  │            SpecRAG CLI                      │                            │
│  │  process | search | addtag | addknowledge  │                            │
│  └──────────────────────┬──────────────────────┘                            │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────┐                            │
│  │            FAISS Vector Database            │                            │
│  │  Text Chunks + Image Embeddings + Metadata  │                            │
│  └─────────────────────────────────────────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tag Boosting Workflow

Khi Cline thêm tag:

```python
# 1. Original content
"Image showing authentication flow..."

# 2. After addtag "oauth"
"Image showing authentication flow...
 Tags: oauth, oauth, oauth, oauth, oauth, oauth, oauth, oauth, oauth, oauth"
 
# 3. Re-embed với boosted content
new_embedding = vectorize(boosted_content)

# 4. Update FAISS
delete(old_entry)
add(new_entry_with_boosted_embedding)
```

**Result**: Query "oauth" sẽ rank document này cao hơn.

## Use Cases

### 1. Technical Documentation

```bash
# Nạp specs
python -m src.main process -fp -i ./bluetooth-specs/

# Tìm diagrams
python -m src.main search -pic "connection state machine"

# Tag kết quả
python -m src.main addtag result_id "bluetooth-fsm"
```

### 2. Architecture Analysis

```bash
# Search cho architecture
python -m src.main search "system architecture overview"

# Thêm knowledge
python -m src.main addknowledge arch_p5 "Main system architecture showing microservices"
```

### 3. Multi-Query for Complex Questions

```bash
# Câu hỏi phức tạp
python -m src.main msearch "authentication" "security" "token flow"
```

## Best Practices

### Ingestion
- Dùng `-fp` (full-page) cho technical docs
- Dùng `-dl` (Docling) cho precise figure extraction

### Search
- Start với semantic search
- Dùng `-hy` hybrid cho exact Figure/Table lookup
- Dùng `-pic` khi cần visual reference

### Feedback
- Tag khi Cline "hiểu" đúng nội dung
- Add knowledge cho detailed explanations
- Tags = keywords, Knowledge = descriptions

## Comparison: RAG Truyền Thống vs Vision-Enhanced

| Aspect | Traditional RAG | Vision-Enhanced (Cline+SpecRAG) |
|--------|-----------------|--------------------------------|
| Input | Text only | Text + Images |
| Output | Text results | Text + Image paths |
| LLM | Text-only | Multimodal (Vision) |
| Feedback | Manual/None | Automated (addtag) |
| Improvement | Static | Self-improving |

## Summary

1. **Multimodal**: Xử lý cả văn bản và hình ảnh
2. **Intelligent**: Cline "hiểu" thực sự nội dung
3. **Self-Improving**: Database tự cải thiện qua feedback
4. **User-Friendly**: Kết quả trực quan với images

---

**Xem thêm**:
- [CLI Commands →](../reference/cli-commands.md)
- [Tagging Guide →](../guides/tagging.md)
- [Knowledge Guide →](../guides/knowledge.md)
