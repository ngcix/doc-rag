# 🔍 Tìm Kiếm

## Các Loại Search

| Loại | Command | Mô tả |
|------|---------|-------|
| Semantic | `search` | Tìm theo ý nghĩa |
| Hybrid | `search -hy` | BM25 + Vector |
| Multi-query | `msearch` | Nhiều queries, merge RRF |
| Image-only | `search -pic` | Chỉ trả về images |

## 1. Semantic Search (Mặc định)

Tìm kiếm dựa trên **ý nghĩa ngữ nghĩa**, không cần exact match.

```bash
python -m src.main search "authentication flow"
```

**Khi nào dùng**:
- Tìm theo concept/ý nghĩa
- Không nhớ chính xác từ khóa
- Câu hỏi tự nhiên

## 2. Hybrid Search

Kết hợp **BM25** (exact match) + **Vector** (semantic).

```bash
python -m src.main search -hy "Figure 4.1: Media payload"
```

**Khi nào dùng**:
- Cần exact match (Figure number, Table number)
- Tìm thuật ngữ kỹ thuật cụ thể
- Kết hợp keyword + semantic

## 3. Multi-Query Search

Tìm với nhiều queries, merge kết quả bằng **RRF** (Reciprocal Rank Fusion).

```bash
python -m src.main msearch "reconnection" "link loss" "timeout recovery"
```

**Khi nào dùng**:
- Câu hỏi phức tạp cần nhiều góc nhìn
- Cải thiện recall cho topic rộng
- Tìm documents liên quan đến nhiều concepts

## 4. Image-Only Search

Chỉ trả về kết quả là hình ảnh.

```bash
python -m src.main search -pic "state machine diagram"

# Kết hợp với hybrid
python -m src.main search -hy -pic "Figure 4.1"
```

**Khi nào dùng**:
- Tìm diagrams, flowcharts
- Tìm tables, figures
- Cần visual reference

## Options

| Option | Shortcut | Mô tả | Default |
|--------|----------|-------|---------|
| `--top-k` | `-k` | Số kết quả | 5 |
| `--hybrid` | `-hy` | Hybrid search | off |
| `--pic` | `-pic` | Images only | off |
| `--no-save` | | Không lưu logs | off |

## Ví Dụ Chi Tiết

### Tìm diagram cụ thể

```bash
# Hybrid + image để tìm Figure chính xác
python -m src.main search -hy -pic "Figure 4.1"
```

### Tìm với nhiều từ khóa

```bash
# Multi-query cho topic phức tạp
python -m src.main msearch "bluetooth pairing" "security" "PIN code"
```

### Tìm nhiều kết quả hơn

```bash
# Tăng top-k
python -m src.main search -k 10 "connection state"
```

## Output Mẫu

```
Searching for: 'authentication flow'
Using backend: faiss
--------------------------------------------------
Found 5 results:

[1] Score: 0.8542
    ID: HID_v1.1.1.pdf_p30
    Source: data/documents/HID_v1.1.1.pdf
    Content: Tags: Figure 4.1: Authentication flow...

[2] Score: 0.7234
    ID: HID_v1.1.1.pdf_chunk_45
    Source: data/documents/HID_v1.1.1.pdf
    Content: The authentication process begins with...

[TIME] Search completed in 0.15s
```

## So Sánh Các Phương Pháp

| Phương pháp | Speed | Exact Match | Semantic | Use Case |
|-------------|-------|-------------|----------|----------|
| Semantic | ⚡⚡⚡ | ❌ | ✅✅✅ | Concept search |
| Hybrid | ⚡⚡ | ✅✅ | ✅✅ | Figure/Table lookup |
| Multi-query | ⚡ | ✅ | ✅✅✅ | Complex questions |

## Tips

1. **Default**: Dùng semantic search trước
2. **Figure/Table**: Dùng hybrid `-hy`
3. **Không tìm thấy**: Thử multi-query với các phrasings khác nhau
4. **Quá nhiều results**: Giảm `-k` hoặc dùng `-pic` để filter

---

**Xem thêm**: [Search Engine Architecture →](../architecture/search-engine.md)
