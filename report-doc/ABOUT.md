# 📖 SpecRag - Tài Liệu Kỹ Thuật

> **Specification RAG System** - Hệ thống RAG tối ưu cho tài liệu đặc tả kỹ thuật

## Mục Lục

| # | Tài liệu | Mô tả |
|---|----------|-------|
| 01 | [Tổng Quan Dự Án](./01-overview.md) | Giới thiệu, kiến trúc, features chính |
| 02 | [Cấu Trúc Thư Mục](./02-project-structure.md) | Chi tiết từng folder, file trong project |
| 03 | [Cấu Hình Hệ Thống](./03-configuration.md) | Các config classes, tham số có thể tuỳ chỉnh |
| 04 | [Luồng Xử Lý Chính](./04-flow-process.md) | Pipeline process documents từ đầu đến cuối |
| 05 | [Luồng Trích Xuất Ảnh](./05-flow-image-extraction.md) | Full-page, PyMuPDF, Docling modes |
| 06 | [Luồng Tìm Kiếm](./06-flow-search.md) | Semantic, Hybrid (BM25), Multi-query search |
| 07 | [Luồng Quản Lý Tag](./07-flow-addtag.md) | AddTag, RemoveTag, ResetTags |
| 08 | [Các Lệnh CLI](./08-cli-commands.md) | Tất cả commands với examples |
| 09 | [Thư Viện Dependencies](./09-libraries.md) | Chi tiết từng thư viện sử dụng |
| 10 | [ClineSR Integration](./10-debuit-clineSR.md) | Tích hợp với Cline agent |
| 11 | [Report ClineSR + RAG](./11-report-clineSR-withRAG.md) | Báo cáo tích hợp |
| 12 | [Luồng Knowledge](./12-flow-knowledge.md) | Knowledge Management system |

## Quick Links

### Bắt Đầu Nhanh
→ Xem [01-overview.md](./01-overview.md#6-workflow-cơ-bản)

### Cấu Hình
→ Xem [03-configuration.md](./03-configuration.md)

### Commands
→ Xem [08-cli-commands.md](./08-cli-commands.md)

## Sơ Đồ Tổng Quan

```
                    ┌─────────────────────────────────────────┐
                    │              SPECRAG SYSTEM             │
                    └─────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│    INPUT      │              │   PROCESSING  │              │    OUTPUT     │
│               │              │               │              │               │
│ • PDF         │     ───▶     │ • Chunking    │     ───▶    │ • FAISS Index │
│ • DOCX        │              │ • Extraction  │              │ • Hybrid Search│
│ • Markdown    │              │ • Vectorize   │              │ • CLI/Agent   │
└───────────────┘              └───────────────┘              └───────────────┘
```

## Công Nghệ Chính

| Layer | Công nghệ |
|-------|-----------|
| **Embedding** | Alibaba-NLP/gte-multilingual-base (768-dim) |
| **Vector DB** | FAISS (IndexFlatIP, cosine similarity) |
| **Search** | Semantic + BM25 Hybrid + Multi-Query RRF |
| **PDF Processing** | PyMuPDF (fitz) |
| **Layout Analysis** | Docling (RT-DETR model) |
| **Text Splitting** | LangChain RecursiveCharacterTextSplitter |
| **Config** | Pydantic v2 |

## Đọc Theo Thứ Tự Khuyến Nghị

1. **Mới bắt đầu**: `01-overview.md` → `08-cli-commands.md`
2. **Hiểu sâu luồng**: `04-flow-process.md` → `05-flow-image-extraction.md` → `06-flow-search.md`
3. **Nâng cao**: `12-flow-knowledge.md` → `07-flow-addtag.md`
4. **Tuỳ chỉnh**: `03-configuration.md` → `09-libraries.md`
5. **Agent Integration**: `10-debuit-clineSR.md` → `11-report-clineSR-withRAG.md`

---

*Tài liệu kỹ thuật cho SpecRag - Updated 2026-01*

