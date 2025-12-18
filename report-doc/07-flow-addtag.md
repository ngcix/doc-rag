# 🏷️ Luồng Thêm Tag (AddTag Flow)

## 1. Tổng Quan

Lệnh `addtag` cho phép thêm tag vào document và **tự động re-embed** để tag mới có thể searchable qua semantic search.

```bash
python -m src.main addtag HID_v1.1.1.pdf_p30 "security-diagram"
```

## 2. Tại Sao Cần Re-embed?

### 2.1 Vấn Đề với Metadata-only Tagging

```
Cách truyền thống (Metadata only):
┌─────────────────────────────────────────────────────────────────┐
│  Document: HID.pdf_p30                                          │
│  Embedding: [0.12, -0.34, ...] ← Không thay đổi                │
│  Metadata: {tags: "Figure 4.1, security-diagram"}               │
└─────────────────────────────────────────────────────────────────┘

Query: "security diagram"
Embedding: [0.45, 0.22, ...]

Similarity = dot(query_emb, doc_emb) = 0.23  ← LOW!
(vì original content không chứa "security diagram")
```

### 2.2 Giải Pháp: Re-embedding

```
Cách của Simple RAG (Content + Re-embed):
┌─────────────────────────────────────────────────────────────────┐
│  Document: HID.pdf_p30                                          │
│  Content: "...original text... + Tags: security-diagram x3"    │
│  Embedding: [0.42, 0.18, ...] ← Updated với tag meaning!       │
│  Metadata: {tags: "Figure 4.1,security-diagram"}                │
└─────────────────────────────────────────────────────────────────┘

Query: "security diagram"
Embedding: [0.45, 0.22, ...]

Similarity = dot(query_emb, doc_emb) = 0.78  ← HIGH!
(vì embedding giờ chứa semantic của "security diagram")
```

## 3. Flow Chi Tiết

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ADDTAG FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                         │
│  │  CLI Command    │  addtag HID.pdf_p30 "security-diagram"                 │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        add_tag(doc_id, tag)                          │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 1: Get Current Data                                    │    │    │
│  │  │   - vector_store.get_metadata(doc_id)                       │    │    │
│  │  │   - vector_store.get_content(doc_id)                        │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 2: Update Metadata Tags                                │    │    │
│  │  │   current_tags = "Figure 4.1"                               │    │    │
│  │  │   new_tags = "Figure 4.1,security-diagram"                  │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 3: Update Content (Boost Tag)                          │    │    │
│  │  │   tag_boost = "\nTags: security-diagram x3"                 │    │    │
│  │  │   new_content = old_content + tag_boost                     │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 4: Re-calculate Embedding                              │    │    │
│  │  │   new_embedding = vectorize_text(new_content)               │    │    │
│  │  │   → [0.42, 0.18, ...] (768 dims)                            │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 5: Atomic Update (Delete + Add)                        │    │    │
│  │  │   vector_store.delete([doc_id])                             │    │    │
│  │  │   vector_store.add(ids, embeddings, documents, metadatas)   │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐    │    │
│  │  │ Step 6: Persist to Disk                                     │    │    │
│  │  │   _rebuild_index() → documents.index                        │    │    │
│  │  │   _save() → documents_metadata.pkl                          │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 4. Code Chi Tiết

### 4.1 Main Function

```python
# File: src/main.py

def add_tag(doc_id: str, tag: str):
    """
    Add a tag to a document's metadata AND update its vector embedding.
    """
    vector_store = get_vector_store()
    
    try:
        # ===== STEP 1: Get Current Data =====
        current_metadata = vector_store.get_metadata(doc_id)
        if not current_metadata:
            print(f"Error: Document {doc_id} not found.")
            return

        current_content = vector_store.get_content(doc_id)
        if current_content is None:
            print(f"Error: Could not retrieve content for {doc_id}")
            return

        # ===== STEP 2: Update Metadata Tags =====
        current_tags = current_metadata.get("tags", "")
        if current_tags:
            new_tags = f"{current_tags},{tag}"
        else:
            new_tags = tag
        
        # ===== STEP 3: Update Content (Boost) =====
        # Append tag multiple times to boost semantic weight
        tag_boost = f"\nTags: {tag}, {tag}, {tag}"
        new_content = current_content + tag_boost
        
        print("Re-calculating vector embedding...")
        
        # ===== STEP 4: Generate New Embedding =====
        from src.vectorization.vectorizer import vectorize_text
        new_embedding = vectorize_text(new_content)[0].tolist()
        
        # ===== STEP 5: Atomic Update =====
        # Delete then Add (effective replace)
        vector_store.delete([doc_id])
        
        # Prepare updated metadata
        updated_metadata = current_metadata.copy()
        updated_metadata["tags"] = new_tags
        
        vector_store.add(
            ids=[doc_id],
            embeddings=[new_embedding],
            documents=[new_content],
            metadatas=[updated_metadata]
        )
            
        print(f"Successfully added tag '{tag}' to document '{doc_id}'")
        print(f"Updated Tags: {new_tags}")
        print("Vector embedding updated to include new tag.")
        
    except Exception as e:
        print(f"Error adding tag: {e}")
```

### 4.2 FAISS Store Methods

```python
# File: src/vectorization/faiss_store.py

def get_metadata(self, doc_id: str) -> dict:
    """Get metadata for a document."""
    return self._metadata.get(doc_id, {})

def get_content(self, doc_id: str) -> Optional[str]:
    """Get the text content of a document."""
    return self._documents.get(doc_id)

def delete(self, ids: list[str]):
    """Delete vectors by ID and rebuild index."""
    deleted_count = 0
    for doc_id in ids:
        if doc_id in self._embeddings:
            del self._embeddings[doc_id]
            self._documents.pop(doc_id, None)
            self._metadata.pop(doc_id, None)
            deleted_count += 1
    
    if deleted_count > 0:
        self._rebuild_index()  # Full rebuild
        self._save()           # Persist
        print(f"Deleted {deleted_count} vectors and rebuilt index")

def add(self, ids, embeddings, documents, metadatas):
    """Add or update vectors."""
    for i, doc_id in enumerate(ids):
        self._embeddings[doc_id] = embeddings[i]
        self._documents[doc_id] = documents[i] if documents else None
        self._metadata[doc_id] = metadatas[i] if metadatas else {}
    
    self._rebuild_index()
    self._save()
```

## 5. Data Transformation

### 5.1 Before AddTag

```python
# In-memory state
self._documents["HID.pdf_p30"] = """
Tags: Figure 4.1: Media payload, Figure 4.1: Media payload, Figure 4.1: Media payload
Caption: Figure 4.1: Media payload format
Context: The media payload format consists of...
Type: fullpage
Source: HID_v1.1.1.pdf, Page 30
"""

self._metadata["HID.pdf_p30"] = {
    "source_file": "data/documents/HID_v1.1.1.pdf",
    "page_number": 30,
    "content_type": "image",
    "tags": "Figure 4.1: Media payload format"
}

self._embeddings["HID.pdf_p30"] = [0.12, -0.34, 0.56, ...]  # 768 dims
```

### 5.2 After AddTag

```python
# After: addtag HID.pdf_p30 "security-diagram"

self._documents["HID.pdf_p30"] = """
Tags: Figure 4.1: Media payload, Figure 4.1: Media payload, Figure 4.1: Media payload
Caption: Figure 4.1: Media payload format
Context: The media payload format consists of...
Type: fullpage
Source: HID_v1.1.1.pdf, Page 30
Tags: security-diagram, security-diagram, security-diagram
"""  # ← Tag appended

self._metadata["HID.pdf_p30"] = {
    "source_file": "data/documents/HID_v1.1.1.pdf",
    "page_number": 30,
    "content_type": "image",
    "tags": "Figure 4.1: Media payload format,security-diagram"  # ← Updated
}

self._embeddings["HID.pdf_p30"] = [0.42, 0.18, 0.61, ...]  # ← NEW embedding!
```

## 6. Sequence Diagram

```
┌──────┐    ┌─────────────┐    ┌────────────┐    ┌─────────────┐
│ CLI  │    │ VectorStore │    │ Vectorizer │    │   FAISS     │
└──┬───┘    └──────┬──────┘    └─────┬──────┘    └──────┬──────┘
   │               │                 │                  │
   │ addtag(id, tag)                 │                  │
   │──────────────>│                 │                  │
   │               │                 │                  │
   │               │ get_metadata(id)                   │
   │               │────────────────────────────────────>
   │               │                 │                  │
   │               │ metadata        │                  │
   │               │<────────────────────────────────────
   │               │                 │                  │
   │               │ get_content(id) │                  │
   │               │────────────────────────────────────>
   │               │                 │                  │
   │               │ content         │                  │
   │               │<────────────────────────────────────
   │               │                 │                  │
   │               │ vectorize_text(new_content)        │
   │               │────────────────>│                  │
   │               │                 │                  │
   │               │ new_embedding   │                  │
   │               │<────────────────│                  │
   │               │                 │                  │
   │               │ delete([id])    │                  │
   │               │────────────────────────────────────>
   │               │                 │                  │
   │               │ add(id, emb, doc, meta)           │
   │               │────────────────────────────────────>
   │               │                 │                  │
   │               │                 │   _rebuild_index()
   │               │                 │   _save()       │
   │               │                 │                  │
   │ "Success!"    │                 │                  │
   │<──────────────│                 │                  │
   │               │                 │                  │
```

## 7. Persistence

### 7.1 What Gets Saved

```python
# File: data/faiss_index/documents_metadata.pkl

{
    'metadata': {
        'HID.pdf_p30': {
            'source_file': '...',
            'tags': 'Figure 4.1,security-diagram'  # Updated
        }
    },
    'documents': {
        'HID.pdf_p30': '...content + tag boost...'  # Updated
    },
    'embeddings': {
        'HID.pdf_p30': [0.42, 0.18, ...]  # Updated
    },
    'dimension': 768
}
```

### 7.2 Index Rebuild

```python
def _rebuild_index(self):
    """Rebuild FAISS index from scratch."""
    
    # 1. Prepare all embeddings
    ids = list(self._embeddings.keys())
    matrix = np.array(list(self._embeddings.values()), dtype=np.float32)
    
    # 2. Normalize for cosine
    faiss.normalize_L2(matrix)
    
    # 3. Create fresh index
    self._create_index(self._dimension)
    
    # 4. Add all vectors
    self._index.add(matrix)
    
    # 5. Rebuild ID mappings
    self._id_to_idx = {doc_id: i for i, doc_id in enumerate(ids)}
    self._idx_to_id = {i: doc_id for i, doc_id in enumerate(ids)}
```

## 8. ListTag Command

### 8.1 Usage

```bash
python -m src.main listtag HID_v1.1.1.pdf_p30
```

### 8.2 Implementation

```python
# File: src/main.py

def list_tags(doc_id: str):
    """List tags for a document."""
    vector_store = get_vector_store()
    
    try:
        metadata = vector_store.get_metadata(doc_id)
        if not metadata:
            print(f"Document {doc_id} not found.")
            return

        tags = metadata.get("tags", "No tags found")
        print(f"Tags for {doc_id}: {tags}")
        
    except Exception as e:
        print(f"Error listing tags: {e}")
```

### 8.3 Output

```
Tags for HID_v1.1.1.pdf_p30: Figure 4.1: Media payload format,security-diagram
```

## 9. Use Cases

### 9.1 Manual Categorization

```bash
# Tag images by topic
python -m src.main addtag HID.pdf_p30 "bluetooth"
python -m src.main addtag HID.pdf_p45 "security"
python -m src.main addtag HID.pdf_p67 "data-flow"

# Now searchable
python -m src.main search "bluetooth diagrams"
```

### 9.2 Project-specific Labels

```bash
# Tag for project filtering
python -m src.main addtag report.pdf_p12 "project-alpha"
python -m src.main addtag spec.pdf_p5 "project-alpha"

# Search within project
python -m src.main search "project alpha architecture"
```

### 9.3 Review/Approval Status

```bash
# Mark as reviewed
python -m src.main addtag diagram.pdf_p3 "reviewed-2024"
python -m src.main addtag diagram.pdf_p3 "approved"
```

## 10. Best Practices

### 10.1 Tag Naming

| Good Tags | Bad Tags |
|-----------|----------|
| `bluetooth-protocol` | `tag1` |
| `security-architecture` | `important` |
| `data-flow-diagram` | `see-page-5` |
| `hid-class-device` | `??` |

### 10.2 Multiple Tags

```bash
# Add multiple tags sequentially
python -m src.main addtag doc.pdf_p1 "tag1"
python -m src.main addtag doc.pdf_p1 "tag2"
python -m src.main addtag doc.pdf_p1 "tag3"

# Result: tags = "original,tag1,tag2,tag3"
```

### 10.3 Performance Note

Mỗi lần addtag sẽ:
1. Load model (nếu chưa load)
2. Re-embed 1 document
3. Rebuild toàn bộ FAISS index
4. Save to disk

→ Với dataset lớn, nên batch nhiều tags cùng lúc (future enhancement).

