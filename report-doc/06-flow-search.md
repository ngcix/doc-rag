# 🔍 Luồng Tìm Kiếm Semantic (Search Flow)

## 1. Tổng Quan

Khi chạy lệnh `python -m src.main search "query"`, hệ thống thực hiện:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SEARCH PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  User Query  │───▶│  Vectorize   │───▶│ FAISS Search │───▶│  Results  │ │
│  │   "Figure 4" │    │   (768-dim)  │    │   (Top-K)    │    │  Ranking  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│                                                                      │      │
│                                                                      ▼      │
│                                                              ┌───────────┐  │
│                                                              │  Output   │  │
│                                                              │  + Save   │  │
│                                                              └───────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. Search Flow Chi Tiết

### 2.1 Entry Point

```python
# File: src/main.py

def search_documents(query: str, top_k: int = 5, save_results: bool = True):
    """Search through vectorized documents."""
    
    print(f"Searching for: '{query}'")
    print(f"Using backend: {settings.vectordb.backend}")
    
    # Get search engine instance
    engine = get_search_engine()
    
    if save_results:
        results = engine.search_and_save(query, top_k=top_k)
    else:
        results = engine.search(query, top_k=top_k)
    
    # Display results
    print(engine.format_results(results, format_type="text"))
    
    return results
```

### 2.2 SearchEngine Class

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SearchEngine                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Properties (Lazy Loading):                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  @property                                                              │ │
│  │  def vectorizer:                                                        │ │
│  │      if self._vectorizer is None:                                       │ │
│  │          self._vectorizer = get_vectorizer()  # TextVectorizer          │ │
│  │      return self._vectorizer                                            │ │
│  │                                                                         │ │
│  │  @property                                                              │ │
│  │  def vector_store:                                                      │ │
│  │      if self._vector_store is None:                                     │ │
│  │          self._vector_store = get_vector_store()  # FAISS/ChromaDB      │ │
│  │      return self._vector_store                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Methods:                                                                    │
│  ├── search(query, top_k, threshold)        → List[SearchResult]            │
│  ├── search_and_save(query, ...)            → List[SearchResult] + logs     │
│  ├── batch_search(queries, ...)             → Dict[query, results]          │
│  └── format_results(results, format_type)   → str                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Search Method Flow

```python
# File: src/search/engine.py

def search(
    self,
    query: str,
    top_k: Optional[int] = None,
    threshold: Optional[float] = None,
    filter_metadata: Optional[dict] = None
) -> list[SearchResult]:
    """Perform semantic search."""
    
    top_k = top_k or self.config.top_k  # Default: 5
    threshold = threshold or self.config.score_threshold  # Default: 0.5
    
    # Step 1: Vectorize the query
    query_embedding = self.vectorizer.vectorize(query)[0].tolist()
    
    # Step 2: Search in vector store
    raw_results = self.vector_store.search_similar(
        query_embedding=query_embedding,
        top_k=top_k,
        threshold=threshold
    )
    
    # Step 3: Convert to SearchResult objects
    results = []
    for r in raw_results:
        result = SearchResult(
            rank=r["rank"],
            document=r["document"],
            similarity=r["similarity"],
            metadata=r["metadata"],
            chunk_id=r["id"]
        )
        results.append(result)
    
    return results
```

## 3. Vectorization Step

### 3.1 Query Embedding

```python
# File: src/vectorization/vectorizer.py

def vectorize(self, texts: Union[str, list[str]], ...):
    """Convert text to vector embedding."""
    
    if isinstance(texts, str):
        texts = [texts]
    
    # Use SentenceTransformer
    embeddings = self.model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,  # Critical for cosine similarity
        convert_to_numpy=True
    )
    
    return embeddings  # Shape: (1, 768) for single query
```

### 3.2 Model Loading (First Call)

```python
def _load_model(self):
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer(
        self.config.model_name,  # Local path or HuggingFace ID
        cache_folder=str(self.config.model_cache_dir),
        device=self.config.device,  # "cpu" or "cuda"
        trust_remote_code=True,
        model_kwargs={"local_files_only": True},
        tokenizer_kwargs={"local_files_only": True}
    )
    
    model.max_seq_length = self.config.max_seq_length  # 8192
    
    return model
```

**Thư viện được gọi:**
```
SentenceTransformer
    └── transformers (HuggingFace)
        └── torch (PyTorch backend)
            └── CPU/CUDA computation
```

## 4. FAISS Search Step

### 4.1 search_similar Method

```python
# File: src/vectorization/faiss_store.py

def search_similar(
    self,
    query_embedding: list[float],
    top_k: int = 5,
    threshold: Optional[float] = None
) -> list[dict]:
    """Search for similar documents."""
    
    import faiss
    
    if self._index is None or self._index.ntotal == 0:
        return []
    
    # Convert to numpy and normalize
    query_np = np.array([query_embedding], dtype=np.float32)
    if self.config.distance_metric == "cosine":
        faiss.normalize_L2(query_np)
    
    # FAISS search
    # Fetch more candidates to handle ghost vectors
    search_k = min(top_k * 4, self._index.ntotal)
    distances, indices = self._index.search(query_np, search_k)
    
    # Format results
    results = []
    for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx == -1:
            continue
        
        doc_id = self._idx_to_id.get(idx)
        if not doc_id:
            continue  # Ghost vector (deleted)
        
        if len(results) >= top_k:
            break
        
        # For Inner Product on normalized vectors: score = similarity
        similarity = float(dist)
        
        if threshold is not None and similarity < threshold:
            continue
        
        results.append({
            "id": doc_id,
            "document": self._documents.get(doc_id),
            "metadata": self._metadata.get(doc_id, {}),
            "distance": float(dist),
            "similarity": similarity,
            "rank": len(results) + 1
        })
    
    return results
```

### 4.2 FAISS Index Type

```python
def _create_index(self, dimension: int):
    import faiss
    
    self._dimension = dimension  # 768
    
    if self.config.faiss_index_type == "Flat":
        # Exact search - best for < 100K vectors
        if self.config.distance_metric == "cosine":
            # Inner Product on normalized vectors = Cosine Similarity
            self._index = faiss.IndexFlatIP(dimension)
        else:
            self._index = faiss.IndexFlatL2(dimension)
```

**Giải thích IndexFlatIP:**
```
IndexFlatIP = Inner Product (Dot Product) index

For normalized vectors:
    cosine_similarity(A, B) = dot_product(A, B) / (|A| * |B|)
    
    Since |A| = |B| = 1 (normalized):
    cosine_similarity(A, B) = dot_product(A, B)
    
→ FAISS IndexFlatIP gives cosine similarity directly!
```

### 4.3 Search Algorithm Visualization

```
Query: "Figure 4.1"
    │
    ▼
Vectorize → [0.12, -0.34, 0.56, ...] (768 dims)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FAISS Index (in-memory)                       │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Doc 1 Vector    │  │ Doc 2 Vector    │  │ Doc 3 Vector    │  │
│  │ [0.11, -0.32..] │  │ [0.45, 0.12...] │  │ [0.13, -0.33..] │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│         │                     │                     │           │
│         ▼                     ▼                     ▼           │
│    dot(Q, D1)            dot(Q, D2)            dot(Q, D3)       │
│    = 0.87                = 0.23                = 0.85           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Sort by score: [D1: 0.87, D3: 0.85, D2: 0.23, ...]
    │
    ▼
Return top_k results with score >= threshold
```

## 5. Result Formatting

### 5.1 SearchResult Class

```python
class SearchResult:
    def __init__(
        self,
        rank: int,
        document: str,
        similarity: float,
        metadata: dict,
        chunk_id: str
    ):
        self.rank = rank
        self.document = document
        self.similarity = similarity
        self.metadata = metadata
        self.chunk_id = chunk_id
    
    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "document": self.document,
            "similarity": round(self.similarity, 4),
            "metadata": self.metadata,
            "chunk_id": self.chunk_id
        }
```

### 5.2 Format Options

```python
def format_results(self, results: list[SearchResult], format_type: str = "text"):
    if not results:
        return "No results found."
    
    if format_type == "json":
        return json.dumps([r.to_dict() for r in results], indent=2)
    
    elif format_type == "markdown":
        lines = ["# Search Results\n"]
        for r in results:
            lines.append(f"## Result {r.rank} (Similarity: {r.similarity:.4f})")
            lines.append(f"\n**Source:** {r.metadata.get('source_file')}\n")
            lines.append(f"```\n{r.document}\n```\n")
        return "\n".join(lines)
    
    else:  # text (default)
        lines = [f"Found {len(results)} results:\n"]
        for r in results:
            lines.append(f"[{r.rank}] Score: {r.similarity:.4f}")
            lines.append(f"    ID: {r.chunk_id}")
            lines.append(f"    Source: {r.metadata.get('source_file')}")
            lines.append(f"    Content: {r.document[:200]}...")
            lines.append("")
        return "\n".join(lines)
```

## 6. Save Results (Logging)

### 6.1 search_and_save Method

```python
def search_and_save(self, query: str, query_id: Optional[str] = None, **kwargs):
    """Perform search and save input/output."""
    
    timestamp = datetime.now().isoformat()
    query_id = query_id or f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Save INPUT
    input_data = {
        "query_id": query_id,
        "query": query,
        "timestamp": timestamp,
        "parameters": {
            "top_k": kwargs.get("top_k", self.config.top_k),
            "threshold": kwargs.get("threshold", self.config.score_threshold)
        }
    }
    
    input_file = PROCESS_INPUT_DIR / f"{query_id}.json"
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(input_data, f, ensure_ascii=False, indent=2)
    
    # Perform SEARCH
    results = self.search(query, **kwargs)
    
    # Save OUTPUT
    output_data = {
        "query_id": query_id,
        "query": query,
        "timestamp": timestamp,
        "result_count": len(results),
        "results": [r.to_dict() for r in results]
    }
    
    output_file = PROCESS_OUTPUT_DIR / f"{query_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"Search completed. Input: {input_file}, Output: {output_file}")
    
    return results
```

### 6.2 Output File Structure

**Input file:** `process/input/query_20251218_105537.json`
```json
{
  "query_id": "query_20251218_105537",
  "query": "Figure 4.1",
  "timestamp": "2025-12-18T10:55:37.123456",
  "parameters": {
    "top_k": 5,
    "threshold": 0.5
  }
}
```

**Output file:** `process/output/query_20251218_105537.json`
```json
{
  "query_id": "query_20251218_105537",
  "query": "Figure 4.1",
  "timestamp": "2025-12-18T10:55:37.123456",
  "result_count": 3,
  "results": [
    {
      "rank": 1,
      "document": "Tags: Figure 4.1: Media payload format...",
      "similarity": 0.8542,
      "metadata": {
        "source_file": "data/documents/HID_v1.1.1.pdf",
        "page_number": 30,
        "content_type": "image"
      },
      "chunk_id": "HID_v1.1.1.pdf_p30"
    }
  ]
}
```

## 7. Sequence Diagram

```
┌──────┐     ┌────────────┐     ┌────────────┐     ┌─────────────┐
│ CLI  │     │SearchEngine│     │ Vectorizer │     │ VectorStore │
└──┬───┘     └─────┬──────┘     └─────┬──────┘     └──────┬──────┘
   │               │                  │                   │
   │ search(query) │                  │                   │
   │──────────────>│                  │                   │
   │               │                  │                   │
   │               │ vectorize(query) │                   │
   │               │─────────────────>│                   │
   │               │                  │                   │
   │               │ [768-dim vector] │                   │
   │               │<─────────────────│                   │
   │               │                  │                   │
   │               │ search_similar(embedding, top_k)    │
   │               │─────────────────────────────────────>│
   │               │                  │                   │
   │               │                  │    FAISS search   │
   │               │                  │    (dot product)  │
   │               │                  │                   │
   │               │ [raw_results]    │                   │
   │               │<─────────────────────────────────────│
   │               │                  │                   │
   │  [SearchResult[]]                │                   │
   │<──────────────│                  │                   │
   │               │                  │                   │
   │ format_results()                 │                   │
   │──────────────>│                  │                   │
   │               │                  │                   │
   │ formatted_str │                  │                   │
   │<──────────────│                  │                   │
   │               │                  │                   │
```

## 8. Performance Considerations

### 8.1 FAISS Efficiency

| Operation | Time Complexity | Notes |
|-----------|-----------------|-------|
| IndexFlatIP search | O(n × d) | n = vectors, d = 768 |
| Normalization | O(d) | Done once per query |
| Top-K selection | O(n log k) | FAISS optimized |

### 8.2 Optimization Tips

1. **Pre-normalized vectors**: Vectors đã normalized khi add → không cần normalize lại
2. **Batch search**: Dùng `batch_search()` cho nhiều queries
3. **Index type**: Dùng IVF/HNSW cho > 100K vectors
4. **GPU**: Đổi `device="cuda"` nếu có GPU

### 8.3 Memory Usage

```
768 dimensions × 4 bytes × N vectors = 3KB per vector

Example:
- 10,000 vectors ≈ 30 MB
- 100,000 vectors ≈ 300 MB
- 1,000,000 vectors ≈ 3 GB
```

## 9. Hybrid Search (Tags + Semantic)

### 9.1 How Tag Boosting Works

Khi process images, tags được repeat 3 lần:
```python
# In ExtractedImage.get_vectorization_text()
if self.tags:
    parts.append(f"Tags: {self.tags}, {self.tags}, {self.tags}")
```

**Effect on embedding:**
```
Original text:    "Figure 4.1: Media payload"
Boosted text:     "Tags: Figure 4.1, Figure 4.1, Figure 4.1\nContext: ..."

→ The phrase "Figure 4.1" appears more frequently
→ Embedding vector shifts toward "Figure 4.1" meaning
→ Query "Figure 4.1" gets higher similarity score
```

### 9.2 Search Example

```
Query: "Figure 4.1"
                    │
                    ▼
        ┌─────────────────────────────────┐
        │ Vectorize query                 │
        │ → Embedding captures "Figure",  │
        │   "4", "1", semantic meaning    │
        └────────────────┬────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────┐
        │ FAISS search                    │
        │                                 │
        │ Result 1: HID.pdf_p30           │
        │   content: "Tags: Figure 4.1,   │
        │            Figure 4.1, ..."     │
        │   similarity: 0.854 ✓ HIGH      │
        │                                 │
        │ Result 2: HID.pdf_12            │
        │   content: "Chapter 4 intro..." │
        │   similarity: 0.312 ✗ LOW       │
        └─────────────────────────────────┘
```

