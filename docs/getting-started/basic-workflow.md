# 🔄 Workflow Cơ Bản

## Tổng Quan

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   1. PROCESS    │ ──▶ │    2. SEARCH    │ ──▶ │   3. ENHANCE    │
│                 │     │                 │     │                 │
│ Nạp documents   │     │ Tìm kiếm        │     │ Thêm tags/      │
│ vào database    │     │ thông tin       │     │ knowledge       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 1. Process Documents

### First-time Setup

```bash
# Khởi tạo thư mục
python -m src.main init

# Copy documents
cp /path/to/docs/*.pdf data/documents/

# Process với full-page mode
python -m src.main process -fp
```

### Reprocessing (khi có documents mới)

```bash
# Xóa data cũ
python -m src.main clean --yes

# Copy documents mới
cp /new/docs/*.pdf data/documents/

# Process lại
python -m src.main process -fp

# Verify
python -m src.main stats
```

## 2. Search Documents

### Semantic Search (Mặc định)

```bash
python -m src.main search "bluetooth protocol"
```

### Hybrid Search (Tốt cho exact match)

```bash
python -m src.main search -hy "Figure 4.1: Media payload"
```

### Multi-Query Search (Tốt cho câu hỏi phức tạp)

```bash
python -m src.main msearch "reconnection" "link loss" "timeout"
```

### Image-Only Search

```bash
python -m src.main search -pic "state machine diagram"
```

## 3. Enhance Database

### Thêm Tags

```bash
# Xem tags hiện tại
python -m src.main listtag HID_v1.1.1.pdf_p30

# Thêm tag
python -m src.main addtag HID_v1.1.1.pdf_p30 "bluetooth"

# Search với tag mới
python -m src.main search "bluetooth"
```

### Thêm Knowledge

```bash
# Thêm mô tả chi tiết
python -m src.main addknowledge HID_p42 "Đây là state machine diagram mô tả Bluetooth connection"

# Xem knowledge
python -m src.main getknowledge HID_p42
```

## Daily Usage Pattern

```bash
# 1. Search for information
python -m src.main search "what I need"

# 2. Find images
python -m src.main search -pic "diagram type"

# 3. Add tags to improve future searches
python -m src.main addtag doc_id "relevant-tag"

# 4. Add knowledge when needed
python -m src.main addknowledge doc_id "detailed description"
```

## Lưu Ý

- **Process chạy một lần** khi có documents mới
- **Search chạy nhiều lần** trong quá trình làm việc
- **Tags/Knowledge** giúp cải thiện độ chính xác theo thời gian

---

**Xem thêm**: [Guides →](../guides/)
