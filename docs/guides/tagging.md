# 🏷️ Quản Lý Tags

## Tổng Quan

Tags giúp **cải thiện độ chính xác tìm kiếm**. Khi thêm tag:
1. Tag được append vào content
2. Vector embedding được **re-calculate**
3. Lần search sau sẽ rank cao hơn

## Commands

| Command | Mô tả |
|---------|-------|
| `listtag` | Xem tags của document |
| `addtag` | Thêm tag mới |
| `removetag` | Xóa user tag |
| `resettags` | Reset về original tags |

## 1. Xem Tags

```bash
python -m src.main listtag HID_v1.1.1.pdf_p30
```

Output:
```
Tags for HID_v1.1.1.pdf_p30:
  Original (auto-extracted): Figure 4.1: Media payload format
  User-added:                security-diagram
  Combined:                  Figure 4.1: Media payload format,security-diagram
```

## 2. Thêm Tag

```bash
# Single word
python -m src.main addtag HID_v1.1.1.pdf_p30 bluetooth

# Multi-word (cần quotes)
python -m src.main addtag HID_v1.1.1.pdf_p30 "security diagram"
```

Output:
```
Re-calculating vector embedding...
Successfully added tag 'bluetooth' to document 'HID_v1.1.1.pdf_p30'
  Original tags: Figure 4.1: Media payload format
  User tags:     bluetooth
  Combined:      Figure 4.1: Media payload format,bluetooth
Vector embedding updated.

[TIME] Time Report:
  Embedding:  0.25s
  Total:      0.42s
```

## 3. Xóa Tag

Chỉ có thể xóa **user-added tags**. Original tags không thể xóa.

```bash
python -m src.main removetag HID_v1.1.1.pdf_p30 bluetooth
```

Output:
```
Successfully removed tag 'bluetooth' from document 'HID_v1.1.1.pdf_p30'
  Original tags: Figure 4.1: Media payload format
  User tags:     (none)
Vector embedding updated.
```

## 4. Reset Tags

Xóa tất cả user tags, giữ lại original tags.

```bash
python -m src.main resettags HID_v1.1.1.pdf_p30
```

## Cách Tag Boosting Hoạt Động

Khi thêm tag, hệ thống:

```python
# Tags được lặp lại để tăng semantic weight
# Images: 10x repeat
tag_boost = ", ".join([tag] * 10)
content = original_content + f"\nTags: {tag_boost}"

# Re-embed với boosted content
new_embedding = vectorize_text(content)
```

**Kết quả**: Query chứa tag sẽ có similarity score cao hơn.

## Best Practices

### Tag Naming

| ✅ Good | ❌ Bad |
|---------|--------|
| `bluetooth-protocol` | `tag1` |
| `security-architecture` | `important` |
| `state-machine` | `see-page-5` |

### Use Cases

```bash
# Categorize by topic
python -m src.main addtag doc_p30 "authentication"
python -m src.main addtag doc_p45 "security"

# Project labels
python -m src.main addtag spec.pdf_p12 "project-alpha"

# Search với tags
python -m src.main search "project alpha security"
```

## Original vs User Tags

| Type | Nguồn | Có thể xóa? |
|------|-------|-------------|
| **Original** | Auto-extracted từ text (Figure X.Y, Table X) | ❌ |
| **User** | Thêm bằng `addtag` | ✅ |

## Performance Note

Mỗi lần add/remove tag:
- Load embedding model (nếu chưa load)
- Re-embed 1 document (~0.2-0.5s)
- Rebuild FAISS index
- Save to disk

→ Với nhiều tags, nên add lần lượt hoặc batch.

---

**Xem thêm**: [Knowledge Management →](./knowledge.md)
