# 📖 Simple RAG System - Tài Liệu Kỹ Thuật

## Mục Lục

| # | Tài liệu | Mô tả |
|---|----------|-------|
| 01 | [Tổng Quan Dự Án](./01-overview.md) | Giới thiệu, kiến trúc, features chính |
| 02 | [Cấu Trúc Thư Mục](./02-project-structure.md) | Chi tiết từng folder, file trong project |
| 03 | [Cấu Hình Hệ Thống](./03-configuration.md) | Các config classes, tham số có thể tuỳ chỉnh |
| 04 | [Luồng Xử Lý Chính](./04-flow-process.md) | Pipeline process documents từ đầu đến cuối |
| 05 | [Luồng Trích Xuất Ảnh](./05-flow-image-extraction.md) | Full-page mode vs PyMuPDF mode |
| 06 | [Luồng Tìm Kiếm](./06-flow-search.md) | Semantic search với FAISS |
| 07 | [Luồng Thêm Tag](./07-flow-addtag.md) | AddTag và re-embedding |
| 08 | [Các Lệnh CLI](./08-cli-commands.md) | Tất cả commands với examples |
| 09 | [Thư Viện Dependencies](./09-libraries.md) | Chi tiết từng thư viện sử dụng |

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
                    │           SIMPLE RAG SYSTEM             │
                    └─────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│    INPUT      │              │   PROCESSING  │              │    OUTPUT     │
│               │              │               │              │               │
│ • PDF         │     ───▶     │ • Chunking    │     ───▶     │ • FAISS Index │
│ • DOCX        │              │ • Extraction  │              │ • Search API  │
│ • Markdown    │              │ • Vectorize   │              │ • CLI Results │
└───────────────┘              └───────────────┘              └───────────────┘
```

## Công Nghệ Chính

| Layer | Công nghệ |
|-------|-----------|
| **Embedding** | Alibaba-NLP/gte-multilingual-base (768-dim) |
| **Vector DB** | FAISS (default) / ChromaDB |
| **PDF Processing** | PyMuPDF (fitz) |
| **Text Splitting** | LangChain RecursiveCharacterTextSplitter |
| **Layout Analysis** | PaddleOCR PP-Structure (optional) |
| **Config** | Pydantic v2 |

## Đọc Theo Thứ Tự Khuyến Nghị

1. **Mới bắt đầu**: `01-overview.md` → `08-cli-commands.md`
2. **Hiểu sâu luồng**: `04-flow-process.md` → `05-flow-image-extraction.md` → `06-flow-search.md`
3. **Tuỳ chỉnh**: `03-configuration.md` → `09-libraries.md`
4. **Contribute**: `02-project-structure.md` → all flows

---

*Tài liệu được tạo tự động từ source code analysis.*

