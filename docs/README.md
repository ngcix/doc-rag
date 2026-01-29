# 📖 SpecRAG Documentation

> **Specification RAG System** - Hệ thống RAG tối ưu cho tài liệu đặc tả kỹ thuật

## 🚀 Bắt Đầu Nhanh

| Tài liệu                                               | Mô tả                |
| ------------------------------------------------------ | -------------------- |
| [Cài đặt](./getting-started/installation.md)           | Hướng dẫn cài đặt    |
| [Quickstart](./getting-started/quickstart.md)          | Bắt đầu trong 5 phút |
| [Workflow cơ bản](./getting-started/basic-workflow.md) | Quy trình làm việc   |

## 📚 Hướng Dẫn Sử Dụng

| Tài liệu                                  | Mô tả                                |
| ----------------------------------------- | ------------------------------------ |
| [Xử lý Documents](./guides/processing.md) | Process và index tài liệu            |
| [Tìm kiếm](./guides/searching.md)         | Semantic, Hybrid, Multi-query search |
| [Quản lý Tags](./guides/tagging.md)       | AddTag, RemoveTag, ResetTags         |
| [Knowledge](./guides/knowledge.md)        | Thêm mô tả/annotation                |

## 📋 Tài Liệu Tham Khảo

| Tài liệu                                      | Mô tả                    |
| --------------------------------------------- | ------------------------ |
| [CLI Commands](./reference/cli-commands.md)   | Tất cả lệnh với examples |
| [Configuration](./reference/configuration.md) | Các tham số cấu hình     |

## 🏗️ Kiến Trúc (Cho Developers)

| Tài liệu                                                | Mô tả                        |
| ------------------------------------------------------- | ---------------------------- |
| [Tổng quan](./architecture/overview.md)                 | Kiến trúc hệ thống           |
| [Cấu trúc Project](./architecture/project-structure.md) | Chi tiết folders và files    |
| [Image Extraction](./architecture/image-extraction.md)  | Deep dive: trích xuất ảnh    |
| [Search Engine](./architecture/search-engine.md)        | Deep dive: search algorithms |

## 🔌 Tích Hợp

| Tài liệu                                     | Mô tả                    |
| -------------------------------------------- | ------------------------ |
| [Cline Integration](./integrations/cline.md) | Tích hợp với Cline Agent |

## 🛠️ Development

| Tài liệu                                      | Mô tả            |
| --------------------------------------------- | ---------------- |
| [Dependencies](./development/dependencies.md) | Thư viện sử dụng |

## 🤖 Workflow cho AI Agent

| Tài liệu                                                                      | Mô tả                                            |
| ----------------------------------------------------------------------------- | ------------------------------------------------ |
| [Hướng dẫn sử dụng](./how-to-use.md)                                          | Chi tiết các bước thực hiện của AI Agent         |
| [RAG Backend Workflow](file:///.clinerules/workflows/workflow_rag_backend.md) | Quy trình tự động tìm kiếm, mô tả ảnh và gắn tag |

> [!NOTE]
> **Workflow RAG Backend Search and Analysis** là quy trình chuẩn hóa giúp AI Agent (như Cline) thực hiện công việc tra cứu tài liệu một cách thông minh:
>
> - **Phân tích câu hỏi**: Tự động gợi ý các hướng tìm kiếm cụ thể nếu câu hỏi quá chung chung.
> - **Tìm kiếm đa phương thức**: Kết hợp Semantic Search, Image-only Search và Hybrid Search (BM25).
> - **Xử lý hình ảnh**: Tự động mô tả nội dung hình ảnh và re-rank kết quả dựa trên độ liên quan thực tế.
> - **Gắn thẻ thông minh (Smart Tagging)**: Hỗ trợ tạo và cập nhật metadata cho hình ảnh thông qua tương tác với người dùng.
> - **Dọn dẹp tự động**: Quản lý các file kết quả tạm trong thư mục `process/` sau khi hoàn thành.

---

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

| Layer               | Công nghệ                                   |
| ------------------- | ------------------------------------------- |
| **Embedding**       | Alibaba-NLP/gte-multilingual-base (768-dim) |
| **Vector DB**       | FAISS (IndexFlatIP, cosine similarity)      |
| **Search**          | Semantic + BM25 Hybrid + Multi-Query RRF    |
| **PDF Processing**  | PyMuPDF (fitz)                              |
| **Layout Analysis** | Docling (RT-DETR model)                     |
| **Text Splitting**  | LangChain RecursiveCharacterTextSplitter    |
| **Config**          | Pydantic v2                                 |

---

_Tài liệu kỹ thuật cho SpecRAG - Updated 2026-01_
