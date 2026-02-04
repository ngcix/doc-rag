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
specrag init

# Copy documents
cp /path/to/docs/*.pdf data/documents/

# Process với full-page mode
specrag process -fp
```

### Reprocessing (khi có documents mới)

```bash
# Xóa data cũ
specrag clean --yes

# Copy documents mới
cp /new/docs/*.pdf data/documents/

# Process lại
specrag process -fp

# Verify
specrag stats
```

## 2. Search Documents

### Semantic Search (Mặc định)

```bash
specrag search "bluetooth protocol"
```

### Hybrid Search (Tốt cho exact match)

```bash
specrag search -hy "Figure 4.1: Media payload"
```

### Multi-Query Search (Tốt cho câu hỏi phức tạp)

```bash
specrag msearch "reconnection" "link loss" "timeout"
```

### Image-Only Search

```bash
specrag search -pic "state machine diagram"
```

## 3. Enhance Database

### Thêm Tags

```bash
# Xem tags hiện tại
specrag listtag HID_v1.1.1.pdf_p30

# Thêm tag
specrag addtag HID_v1.1.1.pdf_p30 "bluetooth"

# Search với tag mới
specrag search "bluetooth"
```

### Thêm Knowledge

```bash
# Thêm mô tả chi tiết
specrag addknowledge HID_p42 "Đây là state machine diagram mô tả Bluetooth connection"

# Xem knowledge
specrag getknowledge HID_p42
```

## Daily Usage Pattern

```bash
# 1. Search for information
specrag search "what I need"

# 2. Find images
specrag search -pic "diagram type"

# 3. Add tags to improve future searches
specrag addtag doc_id "relevant-tag"

# 4. Add knowledge when needed
specrag addknowledge doc_id "detailed description"
```

## Lưu Ý

- **Process chạy một lần** khi có documents mới
- **Search chạy nhiều lần** trong quá trình làm việc
- **Tags/Knowledge** giúp cải thiện độ chính xác theo thời gian

---

**Xem thêm**: [Guides →](../guides/)
