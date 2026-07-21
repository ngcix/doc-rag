# SpecRAG — Project Summary

> Tóm tắt tổng quan về dự án SpecRAG: mục đích, công nghệ, cấu trúc, và cách vận hành.

**Phiên bản:** v0.3.2  
**Ngôn ngữ chính:** Python 3.10+  
**Loại ứng dụng:** CLI + HTTP API (FastAPI `/api/v1`)

---

## 1. SpecRAG là gì?

**SpecRAG** (Specification RAG System) là hệ thống **Retrieval-Augmented Generation (RAG)** chuyên cho tài liệu đặc tả kỹ thuật — PDF, DOCX, Markdown.

Hệ thống:

1. **Ingest** — chia nhỏ văn bản, trích xuất ảnh full-page từ PDF, xử lý sơ đồ Mermaid
2. **Embed** — chuyển nội dung thành vector 768 chiều bằng model đa ngôn ngữ
3. **Index** — lưu vector vào FAISS (mặc định) hoặc ChromaDB
4. **Search** — semantic search, hybrid BM25+vector, multi-query RRF
5. **Enrich** — gắn tag và bổ sung knowledge, tự động re-embed để cải thiện kết quả

Điểm mạnh so với RAG thông thường:

| Tính năng | Mô tả |
|-----------|-------|
| Spec-optimized | Tự nhận diện `Figure X.Y`, `Table X.Y` trong tài liệu kỹ thuật |
| Full-page context | Chụp cả trang PDF + 10.000 ký tự ngữ cảnh xung quanh |
| Hybrid search | Kết hợp semantic + BM25 exact match qua RRF |
| Vision-ready | Trả về đường dẫn ảnh để AI agent phân tích diagram |
| Self-improving | `addtag` / `addknowledge` → re-embed → tìm kiếm tốt hơn theo thời gian |

---

## 2. Công nghệ sử dụng

### Core stack

| Layer | Công nghệ | Vai trò |
|-------|-----------|---------|
| Runtime | Python 3.10+ | Toàn bộ logic ứng dụng |
| Embedding | Alibaba-NLP/gte-multilingual-base | Model 305M params, 768-dim, 75 ngôn ngữ, context 8K |
| ML backend | PyTorch + Transformers + Sentence-Transformers | Load model, tạo embedding |
| Vector DB | FAISS (`faiss-cpu`) | Lưu trữ & tìm kiếm vector (mặc định) |
| Vector DB (alt) | ChromaDB | Backend thay thế, filter metadata phong phú hơn |
| PDF | PyMuPDF (`fitz`) | Trích text + render ảnh full-page |
| DOCX | python-docx | Đọc file Word |
| Chunking | LangChain `RecursiveCharacterTextSplitter` | Chia văn bản 512 chars, overlap 150 |
| Config | Pydantic v2 + `config/setting.json` | Cấu hình typed, override runtime |
| Image | Pillow | Xử lý ảnh |
| Search | Custom BM25 + RRF | Hybrid & multi-query fusion |
| HTTP API | FastAPI + Uvicorn | REST `/api/v1` (search, documents, chunks tags/knowledge) |

### Dev / build (tùy chọn)

| Tool | Mục đích |
|------|----------|
| ruff | Lint & format |
| pytest | Unit test (thư mục `tests/` được tham chiếu nhưng chưa có trong repo) |
| PyInstaller | Đóng gói executable Windows |
| Cython | Biên dịch `src/` sang binary extension |

### Chưa có / phase sau

- Document upload + job queue (stub `501` trên `/api/v1/documents/upload`, `/api/v1/jobs/{id}`)
- Docker / docker-compose, CI/CD
- Database server (PostgreSQL, Redis, Qdrant…)
- Auth / JWT

---

## 3. Cấu trúc thư mục

```
spec-rag/
├── .clinerules/              # Rules & workflows cho AI agent (Cline)
├── config/
│   └── setting.json          # Cấu hình runtime
├── docs/                     # Tài liệu (tiếng Việt + Anh)
├── models/                   # Cache model Hugging Face (~1.5 GB, tải lúc runtime)
├── scripts/                  # Build (PyInstaller/Cython), phân tích ảnh Gauss AI
├── src/                      # Mã nguồn chính
│   ├── specrag/
│   │   ├── __main__.py       # CLI entry point
│   │   ├── api/              # FastAPI app, schemas, routes (/api/v1)
│   │   ├── api_server.py     # uvicorn entry (`specrag server`)
│   │   ├── ops/              # Callable ops (CLI + API dùng chung)
│   │   ├── config/           # Pydantic settings, path constants
│   │   ├── chunking/         # Chia nhỏ văn bản
│   │   ├── image_extraction/ # Trích ảnh full-page PDF
│   │   ├── vectorization/    # Embedding + FAISS/ChromaDB store
│   │   ├── search/           # Semantic + BM25 hybrid search
│   │   ├── sequence_chart/   # Xử lý sơ đồ Mermaid
│   │   ├── path_resolver.py  # Portable paths khi copy/move database
│   │   └── cli_output.py     # Chuẩn hóa output console
│   └── ...
├── pyproject.toml            # Package metadata, deps, CLI entry `specrag`
├── requirements.txt          # Dependencies runtime tối thiểu
└── requirements.lock         # Lockfile đầy đủ (kèm CUDA, dev tools)

# Thư mục runtime (tạo bởi `specrag init`, gitignored):
├── data/
│   ├── documents/            # Input: PDF, DOCX, MD, TXT
│   ├── extracted_images/     # Ảnh full-page: {doc}_p{page}.png
│   ├── faiss_index/          # documents.index + documents_metadata.pkl
│   └── vectordb/             # ChromaDB (nếu backend=chromadb)
└── process/
    ├── input/                # Log query JSON
    └── output/               # Log kết quả search JSON (dùng bởi Cline agent)
```

---

## 4. Kiến trúc pipeline

```
Documents (PDF/DOCX/MD)
    │
    ├─► Chunking (LangChain, 512/150)
    ├─► Image Extraction (PyMuPDF full-page, -fp)
    └─► Sequence Charts (Mermaid → render → vectorize)
            │
            ▼
    Vectorization (GTE 768-dim, CPU/GPU)
            │
            ▼
    Vector Store (FAISS mặc định / ChromaDB)
            │
            ▼
    Search Engine
    ├─ Semantic (cosine similarity)
    ├─ Hybrid (-hy): BM25 + Vector → RRF
    └─ Multi-query (msearch): nhiều query → RRF merge
            │
            ▼
    CLI output + JSON logs (process/output/)
```

### Module responsibilities

| Module | Trách nhiệm |
|--------|-------------|
| `src/main.py` | CLI orchestration, argparse, parallel processing |
| `src/config/` | Load settings, tạo thư mục, hằng số đường dẫn |
| `src/chunking/` | Split tài liệu thành chunks có metadata |
| `src/image_extraction/` | Render full-page PDF, auto-tag Figure/Table |
| `src/vectorization/` | Embed text, persist FAISS/ChromaDB |
| `src/search/` | Semantic search, BM25 hybrid, result logging |
| `src/sequence_chart/` | Parse & render Mermaid diagrams |
| `.clinerules/` | Buộc AI agent search RAG trước, không đọc PDF thủ công |

### Design patterns

- **Singleton factories:** `get_vectorizer()`, `get_vector_store()`, `get_search_engine()`
- **Lazy loading:** Model embedding chỉ load khi cần; FAISS index rebuild lần search đầu
- **Config-driven backend:** Chuyển FAISS ↔ ChromaDB qua `setting.json`
- **Self-improving RAG:** Tag/knowledge → re-embed → rebuild index

---

## 5. Lệnh CLI chính

| Lệnh | Mô tả |
|------|-------|
| `specrag init` | Tạo cấu trúc thư mục runtime |
| `specrag process -fp` | Ingest + vectorize (bắt buộc `-fp` khi trích ảnh) |
| `specrag search "query"` | Semantic search |
| `specrag search -hy "Figure 4.1"` | Hybrid BM25 + vector |
| `specrag search -pic "diagram"` | Chỉ tìm ảnh |
| `specrag msearch "q1" "q2"` | Multi-query RRF fusion |
| `specrag stats` | Thống kê vector database |
| `specrag list` | Liệt kê documents đã index |
| `specrag clean` | Xóa dữ liệu đã xử lý |
| `specrag addtag / removetag / resettags` | Quản lý tag |
| `specrag addknowledge / getknowledge` | Bổ sung annotation |
| `specrag eval` | Đánh giá retrieval (cần `tests/`) |
| `specrag server` | Chạy FastAPI HTTP API (mặc định `:8080`, docs tại `/docs`) |

### HTTP API (tóm tắt)

```bash
specrag server --host 0.0.0.0 --port 8080
# OpenAPI: http://localhost:8080/docs
# POST /api/v1/search
# GET  /api/v1/documents
# GET|POST|DELETE /api/v1/chunks/{id}/tags
# GET|POST|PUT    /api/v1/chunks/{id}/knowledge
```

Upload/jobs chưa implement (trả `501`).

---

## 6. Cấu hình quan trọng

File: `config/setting.json`

| Nhóm | Giá trị mặc định | Ghi chú |
|------|------------------|---------|
| `chunking.chunk_size` | 512 | Kích thước chunk |
| `chunking.chunk_overlap` | 150 | Overlap giữa chunks |
| `model.device` | `cpu` | Đổi `cuda` nếu có GPU |
| `vectordb.backend` | `faiss` | Hoặc `chromadb` |
| `search.top_k` | 5 | Số kết quả trả về |
| `search.score_threshold` | 0.7 | Ngưỡng similarity |
| `performance.max_workers` | `auto` | Song song hóa chunking/extraction |
| `performance.embedding_threads` | `auto` | CPU threads cho embedding |
| `image_extraction.context_chars` | 10000 | Ngữ cảnh text quanh ảnh |

---

## 7. Hiệu năng & thời gian khởi động

CLI có thể **chậm lúc khởi động** vì các lý do sau:

| Giai đoạn | Thời gian ước lượng | Nguyên nhân |
|-----------|---------------------|-------------|
| Import modules | Vài giây | `main.py` import LangChain, NumPy, Pydantic... ngay cả với `init`/`--help` |
| Load embedding model | 10–30+ giây | Model 305M params vào RAM (CPU mặc định) |
| Load FAISS metadata | 1–10+ giây | Đọc pickle embeddings từ disk |
| Rebuild FAISS index | Tùy số vector | Lazy rebuild lần search đầu tiên |
| Embed query | 0.2–1 giây | Mỗi lần search |
| `process` | Phút → chục phút | Chunk + extract + vectorize hàng loạt |

**Lần chạy đầu tiên** còn phải tải model ~1.5 GB vào `models/` nếu chưa có cache.

---

## 8. Tích hợp AI Agent

SpecRAG được thiết kế để dùng cùng **Cline** (hoặc agent tương tự):

- `.clinerules/` định nghĩa workflow: search RAG trước, không đọc PDF trực tiếp
- Kết quả search lưu JSON vào `process/output/` để agent đọc
- Hỗ trợ `-pic` trả path ảnh để agent phân tích diagram
- `addtag` / `addknowledge` cho phép agent cải thiện index theo thời gian

---

## 9. Hạn chế & gaps hiện tại

| Vấn đề | Chi tiết |
|-------|----------|
| Thiếu `tests/` | Được tham chiếu trong `pyproject.toml` và lệnh `eval`, chưa có trong repo |
| Upload / jobs | HTTP stub `501`; ingest vẫn qua CLI `process` |
| CPU mặc định | Chậm hơn GPU đáng kể |
| PyInstaller | Chỉ document cho Windows; Linux fail do deps ~7.5 GB |
| Không có Docker/CI | Deploy thủ công, không pipeline tự động |
| CLI cold start | Mỗi lần gọi CLI = process mới → load lại model; `specrag server` giữ model in-process |

---

## 10. Cài đặt nhanh

```bash
git clone <repo-url> && cd spec-rag
python -m venv .venv && source .venv/bin/activate
pip install -e .

specrag init
cp your-specs/*.pdf data/documents/
specrag process -fp
specrag search "authentication flow"
```

---

## 11. Tài liệu liên quan

| Tài liệu | Nội dung |
|----------|----------|
| [README chính](../README.md) | Overview & quick start |
| [Docs index](./README.md) | Mục lục toàn bộ tài liệu |
| [Kiến trúc](./architecture/overview.md) | Pipeline chi tiết |
| [Cấu trúc project](./architecture/project-structure.md) | Chi tiết từng module |
| [CLI Commands](./reference/cli-commands.md) | Tham khảo lệnh đầy đủ |
| [Configuration](./reference/configuration.md) | Tham số cấu hình |
| [Cline Integration](./integrations/cline.md) | Tích hợp AI agent |
| [Dependencies](./development/dependencies.md) | Chi tiết thư viện |

---

_SpecRAG v0.3.2 — MIT License — Samsung team_
