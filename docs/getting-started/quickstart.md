# ⚡ Quickstart - Bắt Đầu Trong 5 Phút

## Bước 1: Chuẩn Bị Documents

Copy các file PDF/DOCX/Markdown vào thư mục `data/documents/`:

```bash
cp /path/to/your/*.pdf data/documents/
```

## Bước 2: Process Documents

Xử lý và vectorize tất cả documents:

```bash
# Full-page mode (khuyến nghị cho RAG)
specrag process -fp
```

Output:
```
Processing documents from: data/documents
Vector store backend: faiss
--------------------------------------------------
[1/3] Processing documents...
  Extracted 245 text chunks
[2/3] Extracting images from PDFs...
  Total images processed: 33
[3/3] Processing sequence charts...
[4/4] Vectorizing and Storing 278 items...
==================================================
Processing complete!
  Text chunks: 245
  Images extracted: 33
  Total items in database: 278
```

## Bước 3: Tìm Kiếm

```bash
# Tìm kiếm semantic
specrag search "authentication flow"

# Tìm kiếm hybrid (BM25 + Vector)
specrag search -hy "Figure 4.1"

# Chỉ tìm hình ảnh
specrag search -pic "state machine diagram"
```

## Bước 4: Xem Kết Quả

```bash
# Liệt kê documents đã index
specrag list

# Xem stats
specrag stats
```

## Quick Reference

| Lệnh | Mô tả |
|------|-------|
| `process -fp` | Xử lý với full-page images |
| `search "query"` | Tìm kiếm semantic |
| `search -hy "query"` | Tìm kiếm hybrid |
| `search -pic "query"` | Chỉ tìm images |
| `list` | Liệt kê documents |
| `stats` | Thống kê database |
| `clean --yes` | Xóa dữ liệu |

---

**Tiếp theo**: [Workflow Cơ Bản →](./basic-workflow.md)
