# 🧠 Knowledge Management

## Tổng Quan

**Knowledge** là mô tả chi tiết/annotation cho document. Khác với tags (keywords ngắn), knowledge là text dài mô tả nội dung.

| Aspect | Tags | Knowledge |
|--------|------|-----------|
| **Format** | Keywords ngắn | Text dài (markdown) |
| **Boosting** | 10x repeat | 1x trong section riêng |
| **Mục đích** | Quick categorization | Detailed description |

## Commands

| Command | Mô tả |
|---------|-------|
| `addknowledge` | Thêm knowledge (append) |
| `updateknowledge` | Thay thế knowledge |
| `getknowledge` | Xem knowledge |

## 1. Thêm Knowledge

```bash
python -m src.main addknowledge HID_p42 "Đây là state machine diagram mô tả 5 trạng thái Bluetooth"
```

Output:
```
Re-calculating vector embedding...
Successfully added knowledge to document 'HID_p42'
Knowledge preview: Đây là state machine diagram mô tả 5 trạng thái Bluetooth...

[TIME] Time Report:
  Embedding:  0.32s
  Total:      0.48s
```

## 2. Xem Knowledge

```bash
python -m src.main getknowledge HID_p42
```

Output:
```
Knowledge for HID_p42:
--------------------------------------------------
Đây là state machine diagram mô tả 5 trạng thái Bluetooth:
IDLE → SCANNING → CONNECTING → CONNECTED → DISCONNECTING.
Transition triggers: user action, timeout, error.
--------------------------------------------------
```

## 3. Cập Nhật Knowledge

Thay thế hoàn toàn knowledge hiện tại:

```bash
python -m src.main updateknowledge HID_p42 "Mô tả mới hoàn toàn"
```

## Flexible Identifier

Có thể dùng **chunk_id** hoặc **image_path**:

```bash
# Bằng chunk_id
python -m src.main addknowledge HID_SPEC_V10.pdf_p42 "description"

# Bằng image path
python -m src.main addknowledge "data/extracted_images/HID_SPEC_V10.pdf_p42.png" "description"
```

## Cách Knowledge Được Lưu

```python
# Knowledge được append vào content
content = original_content + f"""

---
Knowledge:
{knowledge_text}
"""

# Re-embed với knowledge
new_embedding = vectorize_text(content)

# Lưu trong metadata
metadata["knowledge"] = knowledge_text
```

## Use Cases

### 1. Agent Annotation

Agent (Cline) nhìn ảnh, hiểu nội dung, thêm mô tả:

```bash
addknowledge "HID_p42" "This flowchart shows Bluetooth HID connection lifecycle with 5 states"
```

### 2. Expert Knowledge Injection

SME thêm technical details:

```bash
addknowledge "A2DP_p18" "Đây là SBC encoder flow. Bitpool range: 2-53. Joint Stereo được dùng khi channel similarity cao."
```

### 3. Correction/Clarification

Sửa lại mô tả không chính xác:

```bash
updateknowledge "Core_v6_p100" "Đây KHÔNG phải BR/EDR diagram. Đây là BLE advertisement flow."
```

## Knowledge vs Tags

| Scenario | Dùng Tags | Dùng Knowledge |
|----------|-----------|----------------|
| Quick categorization | ✅ `bluetooth`, `security` | |
| Detailed explanation | | ✅ "This diagram shows..." |
| Keyword matching | ✅ | |
| Semantic understanding | | ✅ |

## Best Practices

1. **Be specific**: Mô tả chi tiết nội dung thực sự trong document
2. **Include keywords**: Đưa các keywords quan trọng vào knowledge
3. **Use markdown**: Có thể format với markdown
4. **Keep updated**: Update khi hiểu biết thay đổi

## Ví Dụ Markdown Knowledge

```bash
python -m src.main addknowledge doc_id "
## State Machine Overview
- **States**: IDLE, SCANNING, CONNECTING, CONNECTED, DISCONNECTING
- **Transitions**: Triggered by user actions, timeouts, or errors
- **Key Feature**: Automatic reconnection on link loss

### Related Sections
See Figure 4.2 for detailed timing diagram.
"
```

---

**Xem thêm**: [Tagging →](./tagging.md) | [Cline Integration →](../integrations/cline.md)
