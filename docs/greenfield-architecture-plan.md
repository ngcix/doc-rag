# Kế Hoạch Xây Dựng Greenfield: SpecRAG Next-Gen

> **Mục tiêu:** Thiết kế lại hệ thống RAG cho tài liệu đặc tả kỹ thuật từ đầu — hiện đại, dễ mở rộng, hỗ trợ multi-user, xử lý song song có hàng đợi, search đồng thời.  
> **Ngày lập:** Tháng 7/2026  
> **Ràng buộc:** License miễn phí cho commercial · Công nghệ hiện đại · Không bắt buộc theo stack cũ

---

## 1. Tóm Tắt Điều Hành

| Khía cạnh | Quyết định |
|-----------|------------|
| **Kiến trúc** | Microservices nhẹ trong monorepo — API, Worker, Embedding Server tách process |
| **Ngôn ngữ chính** | Python 3.12+ (ML/RAG ecosystem) |
| **API** | FastAPI + OpenAPI 3.1 |
| **Queue / Workflow** | Redis + Hatchet (hoặc Temporal) |
| **Vector DB** | Qdrant (primary) + OpenSearch (hybrid lexical) |
| **Metadata & Jobs** | PostgreSQL 16+ |
| **Object Storage** | SeaweedFS hoặc local S3-compatible (MinIO nếu chấp nhận AGPL) |
| **PDF / Document AI** | Docling (layout + table) + PyMuPDF (full-page render) |
| **Embedding** | BGE-M3 hoặc gte-Qwen2 via Infinity / TEI server |
| **Deploy** | Docker Compose (dev) → Kubernetes + Helm (prod) |
| **Package manager** | uv (Astral) |

**Không dùng:** CLI-only monolith, subprocess binary cho API, FAISS file-single-writer làm backend chính cho multi-user.

---

## 2. Nguyên Tắc Thiết Kế

1. **API-first** — Mọi chức năng expose qua HTTP; CLI (nếu có) chỉ là thin client.
2. **Stateful services tách biệt** — Model embedding chạy service riêng, load một lần, scale horizontal.
3. **Write serial, read parallel** — Ingest ghi index qua queue có lock; search đọc đồng thời không block.
4. **Idempotent jobs** — Upload + process có `job_id`, retry an toàn.
5. **Observability by default** — OpenTelemetry traces từ API → queue → worker → vector DB.
6. **License-safe commercial** — Chỉ chọn stack Apache-2.0 / MIT / BSD / PostgreSQL License.

---

## 3. Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                         │
│         Web UI · Mobile · AI Agent (Cline) · CI/CD · Internal Tools          │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTPS (REST + SSE)
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                         API GATEWAY / FastAPI                                  │
│   Auth (JWT) · Rate limit · Upload · Search · Job status · Admin            │
└───────┬──────────────────────┬──────────────────────┬───────────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  PostgreSQL   │    │     Redis       │    │  Object Storage  │
│ users, jobs,  │    │ queue, cache,   │    │ PDF, images,     │
│ doc metadata  │    │ rate limit      │    │ exports          │
└───────────────┘    └────────┬────────┘    └──────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐
     │  Ingest     │  │  Embedding  │  │  Search         │
     │  Workers    │  │  Server     │  │  Service        │
     │  (Hatchet)  │  │  (Infinity/ │  │  (hybrid RRF)   │
     │             │  │   TEI)      │  │                 │
     └──────┬──────┘  └──────┬──────┘  └────────┬────────┘
            │                │                   │
            └────────────────┼───────────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Qdrant (vectors)            │
              │  OpenSearch (BM25 + filter)  │
              └──────────────────────────────┘
```

### Vai trò từng service

| Service | Process | Scale | Ghi chú |
|---------|---------|-------|---------|
| **api** | FastAPI, stateless | N replicas | Không load model nặng |
| **worker-ingest** | Parse PDF, chunk, enqueue embed | 1–N (giới hạn CPU) | Job nặng, queue-backed |
| **embedding** | Infinity / TEI | 1–2 per GPU/CPU pool | Model singleton, gRPC/HTTP |
| **worker-index** | Upsert Qdrant + OpenSearch | 1 writer recommended | Tránh race condition |
| **search** (optional) | Thin layer hoặc gộp vào API | N replicas | Gọi Qdrant + OpenSearch + rerank |

---

## 4. Technology Stack Chi Tiết

### 4.1 Core Runtime

| Thành phần | Công nghệ | License | Lý do chọn (7/2026) |
|------------|-----------|---------|---------------------|
| Language | **Python 3.12+** | PSF | Ecosystem RAG/ML lớn nhất |
| Package manager | **uv** | MIT | Nhanh, lockfile, thay pip/poetry |
| Lint / format | **Ruff** | MIT | All-in-one, chuẩn industry |
| Type check | **Pyright** hoặc **mypy** | MIT | Typed API contracts |
| Config | **Pydantic Settings v2** | MIT | Validation, env-based config |

### 4.2 API & Communication

| Thành phần | Công nghệ | License | Ghi chú |
|------------|-----------|---------|---------|
| HTTP API | **FastAPI** | MIT | Async, OpenAPI, file upload |
| Auth | **FastAPI-Users** + JWT | MIT | Hoặc Keycloak nếu enterprise SSO |
| Rate limiting | **slowapi** + Redis | MIT | Per-user / per-IP |
| Real-time status | **SSE** (Server-Sent Events) | — | Job progress streaming |
| Internal RPC | **HTTP** (embedding server) | — | Đơn giản; gRPC nếu cần latency thấp |

### 4.3 Job Queue & Workflow

| Thành phần | Công nghệ | License | So với Celery |
|------------|-----------|---------|---------------|
| **Khuyến nghị** | **Hatchet** | MIT | Workflow DAG, retry, UI, cloud-native |
| Alternative | **Temporal** | MIT | Durable workflows, phức tạp hơn |
| Broker | **Redis 7+** | BSD | Cache + queue backend |
| Simple MVP | **ARQ** | MIT | Nhẹ, đủ cho phase 1 |

**Workflow mẫu (Hatchet):**

```
upload_received → parse_document → extract_images → chunk_text
    → embed_batch → index_vectors → index_lexical → notify_complete
```

Mỗi step có timeout, retry, concurrency limit per tenant.

### 4.4 Storage Layer

| Layer | Công nghệ | License | Vai trò |
|-------|-----------|---------|---------|
| Relational | **PostgreSQL 16+** | PostgreSQL | Users, tenants, jobs, doc registry |
| Object storage | **SeaweedFS** | Apache 2.0 | PDF gốc, ảnh extracted (commercial-safe hơn MinIO AGPL) |
| Vector DB | **Qdrant** | Apache 2.0 | Dense vectors, filter metadata, HNSW, scale tốt |
| Lexical / Hybrid | **OpenSearch 2.x** | Apache 2.0 | BM25, exact match "Figure 4.1", aggregations |
| Cache | **Redis** | BSD | Hot query cache, session, rate limit |

> **Tại sao không chỉ Qdrant?** Hybrid search (semantic + BM25) cho spec kỹ thuật cần exact match mạnh — OpenSearch xử lý lexical tốt hơn tự build BM25 in-memory.

> **Alternative đơn giản hơn:** PostgreSQL + **pgvector** + **pg_trgm** + **tsvector** — một DB cho MVP, scale kém hơn khi >10M chunks.

### 4.5 Document Intelligence (Ingest)

| Thành phần | Công nghệ | License | Vai trò |
|------------|-----------|---------|---------|
| PDF layout + table | **Docling** | MIT | Table structure, reading order, markdown export |
| Full-page render | **PyMuPDF** | AGPL / Commercial license | Ảnh diagram cho vision agent |
| DOCX | **python-docx** | MIT | Word specs |
| Markdown / Mermaid | **markdown-it** + custom | MIT | Sequence charts |
| Chunking | **chonkie** hoặc **LangChain splitters** | MIT / MIT | Semantic / recursive chunk 512–1024 tokens |
| OCR (scan PDF) | **Surya** hoặc **Tesseract** | GPL / Apache | Chỉ khi PDF scan |

### 4.6 Embedding & Reranking

| Thành phần | Công nghệ | License | Ghi chú |
|------------|-----------|---------|---------|
| Embedding model | **BAAI/bge-m3** | MIT | Multilingual, dense+sparse, SOTA open 2025–2026 |
| Alternative | **Alibaba-NLP/gte-Qwen2** | Apache 2.0 | Context dài, đa ngôn ngữ |
| Serving | **Infinity** (MIT) hoặc **TEI** (Apache 2.0) | — | Batch embed, không load model mỗi request |
| Reranker | **BAAI/bge-reranker-v2-m3** | MIT | Cross-encoder, top-20 → top-5 |
| Sparse (optional) | BGE-M3 sparse vector | MIT | Hybrid native trong một model |

### 4.7 Search Pipeline

```
Query
  → Query expansion (optional, rule-based cho "Figure X.Y")
  → Embed query (Infinity)
  → Parallel retrieval:
        ├── Qdrant: top-K semantic (filter: tenant_id, doc_type, page)
        └── OpenSearch: top-K BM25
  → RRF fusion (k=60)
  → Cross-encoder rerank (top 20 → top 5)
  → Response + citations + image paths
```

| Kỹ thuật | Công nghệ | License |
|----------|-----------|---------|
| Fusion | Reciprocal Rank Fusion (custom) | — |
| Rerank | bge-reranker via Infinity | MIT |
| Filter | Qdrant payload + OpenSearch bool query | — |

### 4.8 Observability & Ops

| Thành phần | Công nghệ | License |
|------------|-----------|---------|
| Tracing | **OpenTelemetry** | Apache 2.0 |
| Metrics | **Prometheus** | Apache 2.0 |
| Dashboard | **Grafana** | AGPL (OK self-hosted internal) |
| Logging | **structlog** + JSON | MIT |
| Errors | **Sentry** (self-hosted) hoặc GlitchTip | FSL / MIT |

### 4.9 Frontend (tùy chọn)

| Thành phần | Công nghệ | License |
|------------|-----------|---------|
| Framework | **Next.js 15** (App Router) | MIT |
| UI | **shadcn/ui** + Tailwind | MIT |
| Upload | tus.io resumable upload | MIT |
| Search UI | Instant search + SSE job status | — |

---

## 5. License Matrix — Commercial Safe

| Công nghệ | License | Commercial OK? | Ghi chú |
|-----------|---------|----------------|---------|
| FastAPI, Pydantic, uv, Ruff | MIT | ✅ | |
| PostgreSQL | PostgreSQL | ✅ | |
| Redis | BSD-3 | ✅ | |
| Qdrant | Apache 2.0 | ✅ | |
| OpenSearch | Apache 2.0 | ✅ | Thay Elasticsearch (SSPL) |
| Hatchet, Temporal | MIT | ✅ | |
| Docling | MIT | ✅ | |
| PyMuPDF | AGPL-3.0 | ⚠️ | Cần commercial license hoặc thay pypdfium2 |
| BGE models | MIT | ✅ | |
| Infinity / TEI | MIT / Apache 2.0 | ✅ | |
| SeaweedFS | Apache 2.0 | ✅ | |
| MinIO | AGPL-3.0 | ⚠️ | Tránh nếu SaaS multi-tenant |
| ChromaDB | Apache 2.0 | ✅ | OK nhưng Qdrant scale tốt hơn |
| FAISS | MIT | ✅ | OK embedded, không ideal multi-writer |
| Grafana | AGPL | ⚠️ | Self-hosted internal thường OK |

---

## 6. Cấu Trúc Project (Monorepo)

```
specrag-platform/
├── apps/
│   ├── api/                    # FastAPI application
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── routes/
│   │   │   │   ├── documents.py
│   │   │   │   ├── search.py
│   │   │   │   ├── jobs.py
│   │   │   │   └── admin.py
│   │   │   ├── deps.py         # DI: db, redis, auth
│   │   │   └── middleware/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   │
│   ├── worker/                 # Hatchet / ARQ workers
│   │   ├── src/
│   │   │   ├── workflows/
│   │   │   │   └── ingest.py
│   │   │   ├── tasks/
│   │   │   │   ├── parse.py
│   │   │   │   ├── chunk.py
│   │   │   │   └── index.py
│   │   │   └── main.py
│   │   └── Dockerfile
│   │
│   └── web/                    # Next.js (optional)
│       └── ...
│
├── packages/
│   ├── core/                   # Shared RAG logic (pure Python)
│   │   ├── src/specrag_core/
│   │   │   ├── parsing/        # Docling wrappers
│   │   │   ├── chunking/
│   │   │   ├── embedding/      # Infinity client
│   │   │   ├── indexing/       # Qdrant + OpenSearch clients
│   │   │   ├── search/         # Hybrid + RRF + rerank
│   │   │   └── models/         # Pydantic schemas
│   │   └── pyproject.toml
│   │
│   └── db/                     # SQLAlchemy models + Alembic migrations
│       ├── src/specrag_db/
│       └── migrations/
│
├── infra/
│   ├── docker-compose.yml      # Dev: api, worker, postgres, redis, qdrant, opensearch
│   ├── docker-compose.prod.yml
│   └── helm/                   # K8s charts
│
├── docs/
│   ├── architecture.md
│   ├── api-reference.md
│   └── runbooks/
│
├── scripts/
│   ├── seed_dev_data.py
│   └── migrate_from_legacy_specrag.py
│
├── pyproject.toml              # Workspace root (uv workspace)
├── uv.lock
└── README.md
```

### Nguyên tắc tách package

- **`packages/core`** — Không import FastAPI, không side-effect; test unit dễ.
- **`apps/api`** — Chỉ HTTP, auth, validation; gọi `core` + `db`.
- **`apps/worker`** — Background jobs; gọi `core`; không expose HTTP (trừ health).

---

## 7. Data Model (PostgreSQL)

```sql
-- Simplified schema
tenants (id, name, plan, created_at)
users (id, tenant_id, email, role)
documents (id, tenant_id, filename, storage_key, status, page_count, created_at)
ingest_jobs (id, tenant_id, document_id, status, progress, error, created_at, finished_at)
chunks (id, document_id, chunk_index, page_number, content_preview, qdrant_point_id, opensearch_doc_id)
tags (id, chunk_id, tag, source)          -- original | user
knowledge (id, chunk_id, content, author)
search_logs (id, tenant_id, query, latency_ms, result_count, created_at)
```

**Trạng thái `ingest_jobs`:** `queued` → `parsing` → `chunking` → `embedding` → `indexing` → `completed` | `failed`

---

## 8. API Contract (MVP)

### Documents

```
POST   /api/v1/documents/upload          multipart, trả job_id (202)
GET    /api/v1/documents                 list docs theo tenant
GET    /api/v1/documents/{id}            metadata + status
DELETE /api/v1/documents/{id}            soft delete + purge index
```

### Jobs

```
GET    /api/v1/jobs/{job_id}             status + progress %
GET    /api/v1/jobs/{job_id}/events      SSE stream
```

### Search

```
POST   /api/v1/search
  Body: {
    "query": "Figure 4.1 authentication flow",
    "top_k": 5,
    "mode": "hybrid",           // semantic | lexical | hybrid
    "filters": { "doc_ids": [], "content_type": "image" },
    "rerank": true
  }
  Response: { results: [...], latency_ms, citations }
```

### Knowledge enrichment (từ SpecRAG cũ)

```
POST   /api/v1/chunks/{id}/tags
POST   /api/v1/chunks/{id}/knowledge
```

---

## 9. Xử Lý Concurrency — Mapping Use Case

### 9.1 Nhiều người upload đồng thời

| Cơ chế | Chi tiết |
|--------|----------|
| Upload | API lưu object storage ngay, tạo `ingest_job`, enqueue |
| Response | `202 Accepted` — không block đến khi process xong |
| Limit | Per-tenant: max 10 upload/phút, max 5 job active |
| Storage | Path: `s3://{tenant}/{doc_id}/original.pdf` |

### 9.2 Xử lý song song nhiều doc (có giới hạn)

| Cơ chế | Chi tiết |
|--------|----------|
| Queue | Hatchet workflow per document |
| Concurrency | `MAX_INGEST_WORKERS=2` (config theo CPU/RAM) |
| Embedding batch | Gom chunk → batch 32–64 gửi Infinity |
| Index write | **1 worker** ghi Qdrant + OpenSearch (mutex Redis) |
| Backpressure | Queue depth > 100 → API trả `503` + `Retry-After` |

### 9.3 Nhiều request search đồng thời

| Cơ chế | Chi tiết |
|--------|----------|
| API | Stateless, scale horizontal |
| Embedding query | Infinity server — batch requests tự động |
| Vector search | Qdrant — designed for concurrent read |
| Lexical | OpenSearch — concurrent read |
| Rerank | Semaphore max 8 concurrent (CPU-heavy) |
| Cache | Redis cache kết quả search 60s (query hash + filters) |

---

## 10. So Sánh Với SpecRAG Hiện Tại

| Khía cạnh | SpecRAG cũ | Greenfield |
|-----------|------------|------------|
| Interface | CLI only | API-first + optional CLI |
| Model load | Mỗi CLI invocation | Embedding server persistent |
| Vector store | FAISS file, single writer | Qdrant distributed |
| Lexical search | BM25 in-memory rebuild | OpenSearch persistent index |
| Multi-user | Không | Tenant isolation + auth |
| Job queue | Không | Hatchet + Redis |
| Upload | Copy file local | Object storage + job tracking |
| Observability | print logs | OpenTelemetry + metrics |
| Deploy | Manual / PyInstaller | Docker + K8s |
| Test | Thiếu | pytest + integration + contract tests |

**Giữ lại từ SpecRAG cũ (domain logic):**

- Auto-detect `Figure X.Y`, `Table X.Y`
- Full-page PDF capture cho vision agent
- Tag boosting + knowledge enrichment
- Hybrid search + RRF
- Workflow agent (Cline rules) — chuyển sang gọi REST API

---

## 11. Lộ Trình Triển Khai

### Phase 0 — Foundation (2–3 tuần)

- [ ] Monorepo `uv` workspace
- [ ] `packages/core`: chunking + embedding client stub
- [ ] `apps/api`: health, auth skeleton, upload → S3
- [ ] Docker Compose: Postgres, Redis, Qdrant, MinIO/SeaweedFS
- [ ] CI: Ruff, Pyright, pytest

### Phase 1 — MVP Ingest + Search (4–6 tuần)

- [ ] Docling parse PDF → markdown + tables
- [ ] PyMuPDF full-page images
- [ ] Infinity embedding server
- [ ] Index Qdrant + OpenSearch
- [ ] `POST /search` hybrid + RRF
- [ ] Hatchet ingest workflow
- [ ] Job status API + SSE

### Phase 2 — Multi-tenant Production (4–6 tuần)

- [ ] Tenant isolation (Qdrant collection per tenant hoặc payload filter)
- [ ] Rate limiting, quotas
- [ ] Tags + knowledge API
- [ ] Cross-encoder rerank
- [ ] Migration tool từ SpecRAG FAISS export
- [ ] Prometheus + Grafana dashboards

### Phase 3 — Advanced (ongoing)

- [ ] ColPali / visual retrieval cho diagram-heavy pages
- [ ] Query routing (conceptual vs exact-match auto)
- [ ] Web UI (Next.js)
- [ ] Agent SDK (Python + TypeScript client)
- [ ] Evaluation harness (RAGAS / custom spec benchmark)

---

## 12. Quyết Định Kiến Trúc Cần Chốt Sớm

| # | Câu hỏi | Khuyến nghị |
|---|---------|-------------|
| 1 | Monorepo hay polyrepo? | **Monorepo** cho team <10 người |
| 2 | pgvector hay Qdrant? | **Qdrant** nếu >100K chunks hoặc cần filter phức tạp |
| 3 | Hatchet hay Temporal? | **Hatchet** MVP; **Temporal** nếu workflow rất phức tạp |
| 4 | Gộp search vào API hay tách service? | **Gộp API** phase 1; tách khi CPU rerank bottleneck |
| 5 | PyMuPDF AGPL? | Mua license hoặc dùng **pypdfium2** (Apache/BSD) cho commercial |
| 6 | Self-host hay cloud managed? | Dev self-host; prod Qdrant Cloud / OpenSearch managed tùy budget |

---

## 13. Ước Lượng Tài Nguyên (Production nhỏ — 50 users)

| Service | CPU | RAM | Disk |
|---------|-----|-----|------|
| API × 2 | 2 core | 2 GB | — |
| Worker ingest × 2 | 4 core | 8 GB | — |
| Infinity (bge-m3) | 4 core | 8 GB | 2 GB model |
| Qdrant | 2 core | 4 GB | 50 GB SSD |
| OpenSearch | 2 core | 4 GB | 50 GB SSD |
| PostgreSQL | 2 core | 4 GB | 20 GB |
| Redis | 1 core | 1 GB | — |
| Object storage | — | — | 200 GB |

**Tổng tối thiểu:** ~16 CPU, 32 GB RAM (có thể gộp dev trên 1 máy 32 GB).

---

## 14. Rủi Ro & Giảm Thiểu

| Rủi ro | Mức | Giảm thiểu |
|--------|-----|------------|
| Index corruption multi-writer | Cao | Single index writer + queue |
| Embedding server SPOF | Trung bình | Health check + restart policy; 2 replicas |
| OpenSearch memory | Trung bình | Index lifecycle, shard sizing |
| Docling parse chậm | Trung bình | Timeout per doc; worker scale |
| AGPL PyMuPDF | Pháp lý | Commercial license hoặc thay thế |
| Model drift | Thấp | Pin model version; eval suite |

---

## 15. Kết Luận

Xây greenfield **không nên** bọc binary CLI cũ. Nên:

1. **Monorepo** với `apps/` (API, worker) + `packages/core` (RAG logic thuần).
2. **FastAPI + PostgreSQL + Redis + Qdrant + OpenSearch** — stack mature, license-safe, phù hợp hybrid search spec kỹ thuật.
3. **Infinity/TEI** cho embedding persistent — giải quyết pain point load model mỗi request.
4. **Hatchet** cho ingest workflow có giới hạn concurrency và retry.
5. **Docling + PyMuPDF** cho parse PDF hiện đại với figure/table awareness.

Cấu trúc này đáp ứng đủ 3 use case (multi-upload, parallel process có queue, concurrent search) và mở rộng tốt hơn SpecRAG CLI monolith.

---

## 16. Tài Liệu Tham Khảo

| Tài liệu | URL |
|----------|-----|
| Docling | https://github.com/docling-project/docling |
| Qdrant | https://qdrant.tech/documentation/ |
| Hatchet | https://docs.hatchet.run/ |
| Infinity Embeddings | https://github.com/michaelfeil/infinity |
| BGE-M3 | https://huggingface.co/BAAI/bge-m3 |
| OpenSearch | https://opensearch.org/ |
| uv package manager | https://docs.astral.sh/uv/ |
| FastAPI | https://fastapi.tiangolo.com/ |

---

_SpecRAG Greenfield Architecture Plan · v1.0 · July 2026_
