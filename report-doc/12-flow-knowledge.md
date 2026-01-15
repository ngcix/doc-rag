# 🧠 Luồng Quản Lý Knowledge (Knowledge Management Flow)

## 1. Tổng Quan

**Knowledge Management** là tính năng cho phép agent thêm mô tả, giải thích hoặc annotation vào document/image. Knowledge được tích hợp vào vector embedding để tăng khả năng tìm kiếm semantic.

```bash
# Thêm knowledge
python -m src.main addknowledge "HID_SPEC_V10.pdf_p42" "Đây là sơ đồ mô tả luồng kết nối Bluetooth HID"

# Cập nhật (thay thế hoàn toàn)
python -m src.main updateknowledge "HID_SPEC_V10.pdf_p42" "Mô tả mới hoàn toàn"

# Xem knowledge
python -m src.main getknowledge "HID_SPEC_V10.pdf_p42"
```

## 2. Tại Sao Cần Knowledge?

### 2.1 Vấn Đề với Image-only Context

Khi trích xuất ảnh từ PDF, context xung quanh có thể không đủ mô tả chính xác nội dung:

```
Ảnh: [Flowchart phức tạp]
Auto-extracted context: "Figure 4.2 ... See section 3.1 for details..."

→ Agent hiểu ảnh nhưng không thể search bằng semantic vì text không mô tả đầy đủ
```

### 2.2 Giải Pháp: Agent-Added Knowledge

```
Ảnh: [Flowchart phức tạp]
Knowledge: "Đây là state machine diagram mô tả 5 trạng thái kết nối Bluetooth: 
            IDLE → SCANNING → CONNECTING → CONNECTED → DISCONNECTING.
            Transition triggers: user action, timeout, error."

→ Giờ query "bluetooth connection states" sẽ match document này!
```

## 3. Flow Chi Tiết

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ADD KNOWLEDGE FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  CLI Command    │  addknowledge doc_id "knowledge text"                  │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    add_knowledge(identifier, text)                   │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 1: Resolve Identifier                                  │    │    │
│  │  │   - resolve_chunk_id(identifier)                            │    │    │
│  │  │   - Supports: chunk_id OR image_path                        │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 2: Get Current Data                                    │    │    │
│  │  │   - vector_store.get_metadata(doc_id)                       │    │    │
│  │  │   - vector_store.get_content(doc_id)                        │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 3: Append Knowledge                                    │    │    │
│  │  │   current_knowledge = metadata.get("knowledge", "")         │    │    │
│  │  │   new_knowledge = current + "\n\n" + text                   │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 4: Update Content với Knowledge Boost                  │    │    │
│  │  │   knowledge_boost = "\n\n---\nKnowledge:\n{text}"           │    │    │
│  │  │   new_content = old_content + knowledge_boost               │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 5: Re-calculate Embedding                              │    │    │
│  │  │   new_embedding = vectorize_text(new_content)               │    │    │
│  │  │   → [0.42, 0.18, ...] (768 dims)                            │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 6: Atomic Update                                       │    │    │
│  │  │   vector_store.delete([doc_id])                             │    │    │
│  │  │   vector_store.add(ids, embeddings, documents, metadatas)   │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 4. Code Implementation

### 4.1 add_knowledge()

```python
# File: src/main.py

def add_knowledge(identifier: str, knowledge_text: str):
    """
    Add knowledge to a document's metadata AND update its vector embedding.
    Knowledge is appended to existing knowledge.
    """
    start_time = time.perf_counter()
    vector_store = get_vector_store()
    
    # Resolve identifier to chunk_id
    doc_id = resolve_chunk_id(identifier)
    
    # 1. Get current data
    current_metadata = vector_store.get_metadata(doc_id)
    current_content = vector_store.get_content(doc_id)
    
    # 2. Update Metadata Knowledge (append)
    current_knowledge = current_metadata.get("knowledge", "")
    if current_knowledge:
        new_knowledge = f"{current_knowledge}\n\n{knowledge_text}"
    else:
        new_knowledge = knowledge_text
    
    # 3. Update Content for Vectorization (semantic boost)
    knowledge_boost = f"\n\n---\nKnowledge:\n{knowledge_text}"
    new_content = current_content + knowledge_boost
    
    # 4. Generate New Embedding
    from src.vectorization.vectorizer import vectorize_text
    new_embedding = vectorize_text(new_content)[0].tolist()
    
    # 5. Atomic Update (Delete then Add)
    vector_store.delete([doc_id])
    
    updated_metadata = current_metadata.copy()
    updated_metadata["knowledge"] = new_knowledge
    
    vector_store.add(
        ids=[doc_id],
        embeddings=[new_embedding],
        documents=[new_content],
        metadatas=[updated_metadata]
    )
    
    print(f"Successfully added knowledge to document '{doc_id}'")
```

### 4.2 update_knowledge()

```python
def update_knowledge(identifier: str, knowledge_text: str):
    """
    Replace existing knowledge with new knowledge.
    """
    doc_id = resolve_chunk_id(identifier)
    current_content = vector_store.get_content(doc_id)
    
    # Remove old knowledge section if exists
    if "\n\n---\nKnowledge:" in current_content:
        base_content = current_content.split("\n\n---\nKnowledge:")[0]
    else:
        base_content = current_content
    
    # Rebuild content with NEW knowledge only
    knowledge_boost = f"\n\n---\nKnowledge:\n{knowledge_text}"
    new_content = base_content + knowledge_boost
    
    # Re-embed and update
    new_embedding = vectorize_text(new_content)[0].tolist()
    
    # Atomic update
    vector_store.delete([doc_id])
    updated_metadata["knowledge"] = knowledge_text  # Replace completely
    vector_store.add(...)
```

### 4.3 get_knowledge()

```python
def get_knowledge(identifier: str):
    """Get knowledge for a document."""
    doc_id = resolve_chunk_id(identifier)
    
    metadata = vector_store.get_metadata(doc_id)
    knowledge = metadata.get("knowledge", "")
    
    if knowledge:
        print(f"Knowledge for {doc_id}:")
        print("-" * 50)
        print(knowledge)
    else:
        print(f"No knowledge found for {doc_id}")
```

### 4.4 resolve_chunk_id()

Hỗ trợ input flexible - có thể dùng chunk_id hoặc image_path:

```python
def resolve_chunk_id(identifier: str) -> str:
    """
    Resolve identifier (chunk_id or image_path) to chunk_id.
    
    Examples:
        "HID_SPEC_V10.pdf_p42"  →  "HID_SPEC_V10.pdf_p42"
        "data/extracted_images/HID_SPEC_V10.pdf_p42.png"  →  "HID_SPEC_V10.pdf_p42"
    """
    vector_store = get_vector_store()
    
    # First, check if identifier is already a valid chunk_id
    metadata = vector_store.get_metadata(identifier)
    if metadata:
        return identifier
    
    # If not found, try to find by image_path in metadata
    identifier_path = Path(identifier).name  # Get filename only
    
    all_docs = vector_store.list_documents()
    for doc_id in all_docs.keys():
        doc_metadata = vector_store.get_metadata(doc_id)
        if doc_metadata:
            img_path = doc_metadata.get("image_path", "")
            if img_path and Path(img_path).name == identifier_path:
                return doc_id
    
    return identifier  # Return original if no match
```

## 5. Data Structure

### 5.1 Metadata với Knowledge

```python
# In FAISS store: self._metadata[doc_id]
{
    "source_file": "data/documents/HID_SPEC_V10.pdf",
    "page_number": 42,
    "content_type": "image",
    "image_path": "data/extracted_images/HID_SPEC_V10.pdf_p42.png",
    "tags": "Figure 4.2: Connection State Machine",
    "original_tags": "Figure 4.2: Connection State Machine",
    "user_tags": "",
    "knowledge": "Đây là state machine diagram..."  # ← NEW FIELD
}
```

### 5.2 Content với Knowledge Boost

```
Tags: Figure 4.2, Figure 4.2, Figure 4.2, Figure 4.2, Figure 4.2
Caption: Figure 4.2: Connection State Machine
Context: This diagram shows the connection flow...
Type: fullpage
Source: HID_SPEC_V10.pdf, Page 42

---
Knowledge:
Đây là state machine diagram mô tả 5 trạng thái kết nối Bluetooth:
IDLE → SCANNING → CONNECTING → CONNECTED → DISCONNECTING.
Transition triggers: user action, timeout, error.
```

## 6. So Sánh: Tags vs Knowledge

| Aspect | Tags | Knowledge |
|--------|------|-----------|
| **Mục đích** | Keywords ngắn gọn | Mô tả chi tiết, giải thích |
| **Format** | Comma-separated | Markdown text (multi-line) |
| **Boosting** | 5x repeat | 1x (trong section riêng) |
| **Thêm** | `addtag` | `addknowledge` |
| **Thay thế** | N/A (chỉ append) | `updateknowledge` |
| **Xóa** | `removetag`, `resettags` | `updateknowledge ""` |

## 7. Use Cases

### 7.1 Agent Annotation

```bash
# Agent nhìn ảnh, hiểu nội dung, thêm mô tả
addknowledge "HID_p42" "This flowchart shows Bluetooth HID connection lifecycle..."

# Sau đó search sẽ match
search "bluetooth connection lifecycle"  # → Returns HID_p42
```

### 7.2 Expert Knowledge Injection

```bash
# SME thêm technical details
addknowledge "A2DP_p18" "Đây là SBC encoder flow. Bitpool range: 2-53. 
Joint Stereo được dùng để giảm bitrate khi channel similarity cao."
```

### 7.3 Correction/Clarification

```bash
# Sửa lại mô tả sai
updateknowledge "Core_v6_p100" "Đây KHÔNG phải BR/EDR diagram. 
Đây là BLE (Bluetooth Low Energy) advertisement flow."
```

## 8. CLI Reference

| Command | Mô tả | Example |
|---------|-------|---------|
| `addknowledge` | Append knowledge | `addknowledge doc_id "text"` |
| `updateknowledge` | Replace knowledge | `updateknowledge doc_id "new text"` |
| `getknowledge` | View knowledge | `getknowledge doc_id` |

**Output Example:**

```
$ python -m src.main getknowledge HID_SPEC_V10.pdf_p42
Knowledge for HID_SPEC_V10.pdf_p42:
--------------------------------------------------
Đây là state machine diagram mô tả 5 trạng thái kết nối Bluetooth:
IDLE → SCANNING → CONNECTING → CONNECTED → DISCONNECTING.
Transition triggers: user action, timeout, error.
--------------------------------------------------
```

## 9. Lưu Ý Performance

- Mỗi lần add/update knowledge sẽ:
  1. Load embedding model (nếu chưa load)
  2. Re-embed 1 document
  3. Rebuild FAISS index
  4. Save to disk

- Thời gian trung bình: ~2-5 giây cho 1 document
- Knowledge dài hơn có thể tăng embedding time nhẹ

