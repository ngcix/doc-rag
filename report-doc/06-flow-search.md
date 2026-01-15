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

## 9. Hybrid Search (BM25 + Vector)

### 9.1 Tổng Quan Hybrid Search

Hybrid Search kết hợp **BM25** (lexical search) và **Vector Search** (semantic) để tận dụng ưu điểm của cả hai:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HYBRID SEARCH PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Query: "Figure 4.1: Media payload format"                                   │
│           │                                                                  │
│           ├─────────────────────┬────────────────────────┐                   │
│           │                     │                        │                   │
│           ▼                     ▼                        ▼                   │
│  ┌────────────────┐    ┌────────────────┐       ┌────────────────┐          │
│  │  BM25 Search   │    │ Vector Search  │       │   RRF Fusion   │          │
│  │  (Exact Match) │    │  (Semantic)    │   →   │ (Merge Ranks)  │          │
│  │  Rank: [1,2,5] │    │ Rank: [3,1,2]  │       │ Final: [1,2,3] │          │
│  └────────────────┘    └────────────────┘       └────────────────┘          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Khi nào dùng Hybrid?**
- Tìm exact term như "Figure 4.1" → BM25 match chính xác
- Tìm concept như "connection diagram" → Vector match semantic

### 9.2 BM25 Algorithm (Internal Implementation)

BM25 (Best Matching 25) là thuật toán ranking dựa trên term frequency:

```python
# File: src/search/bm25.py

class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        k1: Term frequency saturation (default 1.5)
        b:  Length normalization (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.doc_freqs = {}   # term → count docs containing term
        self.term_freqs = {}  # doc_idx → {term: count}
        self.idf = {}         # term → IDF score
```

**BM25 Score Formula:**

```
score(q, d) = Σ IDF(term) × (tf × (k1 + 1)) / (tf + k1 × (1 - b + b × |d|/avgdl))

Where:
- IDF(term) = log((N - df + 0.5) / (df + 0.5) + 1)
- tf = term frequency in document
- |d| = document length
- avgdl = average document length
- N = total documents
- df = document frequency of term
```

**Python Implementation:**

```python
def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
    query_tokens = self._tokenize(query)
    scores = []
    
    for idx in range(self.N):
        score = 0.0
        doc_len = self.doc_lengths[idx]
        tf_doc = self.term_freqs[idx]
        
        for term in query_tokens:
            if term not in self.idf:
                continue
            tf = tf_doc.get(term, 0)
            if tf == 0:
                continue
            
            idf = self.idf[term]
            
            # BM25 scoring formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
            score += idf * numerator / denominator
        
        if score > 0:
            scores.append((self.doc_ids[idx], score))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
```

### 9.3 Reciprocal Rank Fusion (RRF)

RRF kết hợp kết quả từ nhiều nguồn bằng công thức:

```
RRF_score(d) = Σ (weight / (k + rank(d)))

Where:
- k = 60 (default, smoothing constant)
- rank(d) = vị trí của document d trong danh sách kết quả
- weight = trọng số của nguồn (vector: 0.5, bm25: 0.5)
```

**Ví dụ:**

```
Vector results:     BM25 results:
1. doc_A            1. doc_B  
2. doc_B            2. doc_A
3. doc_C            3. doc_D

RRF scores (k=60):
doc_A: 0.5/(60+1) + 0.5/(60+2) = 0.0082 + 0.0081 = 0.0163
doc_B: 0.5/(60+2) + 0.5/(60+1) = 0.0081 + 0.0082 = 0.0163  
doc_C: 0.5/(60+3) = 0.0079
doc_D: 0.5/(60+3) = 0.0079

Final ranking: [doc_A, doc_B, doc_C, doc_D] (tie-break by appearance)
```

### 9.4 HybridSearchEngine Class

```python
# File: src/search/bm25.py

class HybridSearchEngine:
    def __init__(self, vector_store, vectorizer, rrf_k: int = 60):
        self.vector_store = vector_store
        self.vectorizer = vectorizer
        self.rrf_k = rrf_k
        self.bm25_index = None
    
    def search(self, query: str, top_k: int = 10,
               vector_weight: float = 0.5, bm25_weight: float = 0.5):
        
        # 1. Vector search
        query_embedding = self.vectorizer.vectorize(query)[0].tolist()
        vector_results = self.vector_store.search_similar(query_embedding, top_k * 3)
        
        # 2. BM25 search
        bm25_results = self.bm25_index.search(query, top_k * 3)
        
        # 3. RRF Fusion
        rrf_scores = {}
        for rank, result in enumerate(vector_results, 1):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + vector_weight / (self.rrf_k + rank)
        
        for rank, (doc_id, _) in enumerate(bm25_results, 1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + bm25_weight / (self.rrf_k + rank)
        
        # 4. Sort and return
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        return sorted_ids[:top_k]
```

### 9.5 CLI Usage

```bash
# Semantic only (default)
python -m src.main search "connection state machine"

# Hybrid search (BM25 + Vector)
python -m src.main search -hy "Figure 4.1: Media payload format"

# Hybrid + Images only
python -m src.main search -hy -pic "state diagram"
```

---

## 10. Multi-Query Search (msearch)

### 10.1 Tổng Quan

`msearch` cho phép tìm kiếm với nhiều queries và merge kết quả, cải thiện recall cho các câu hỏi phức tạp:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-QUERY SEARCH                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input queries:                                                              │
│  ├── "bluetooth reconnection"                                                │
│  ├── "link loss"                                                             │
│  └── "timeout recovery"                                                      │
│           │                                                                  │
│           ├──────────────┬──────────────┬──────────────┐                     │
│           ▼              ▼              ▼              ▼                     │
│      ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────┐           │
│      │ Search1 │    │ Search2 │    │ Search3 │    │ RRF Merge   │           │
│      │ [A,B,C] │    │ [B,D,A] │    │ [C,A,E] │ →  │ [A,B,C,D,E] │           │
│      └─────────┘    └─────────┘    └─────────┘    └─────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Implementation

```python
# File: src/main.py

def multi_search(
    queries: list[str],
    top_k: int = 5,
    images_only: bool = False,
    use_hybrid: bool = False,
    save_results: bool = True
):
    """Search with multiple queries and merge using RRF."""
    
    engine = get_search_engine()
    all_results = []
    
    # Run each query
    for query in queries:
        if use_hybrid:
            results = engine.hybrid_search(query, top_k=top_k * 2)
        else:
            results = engine.search(query, top_k=top_k * 2)
        all_results.append(results)
    
    # RRF merge
    rrf_scores = {}
    for query_results in all_results:
        for rank, result in enumerate(query_results, 1):
            doc_id = result.chunk_id
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (60 + rank)
    
    # Sort by RRF score
    merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    return merged[:top_k]
```

### 10.3 CLI Usage

```bash
# Multi-query semantic search
python -m src.main msearch "bluetooth reconnection" "link loss" "timeout"

# Multi-query với hybrid
python -m src.main msearch -hy "Figure 4.1" "Media payload" "HID report"

# Multi-query images only
python -m src.main msearch -pic "state machine" "FSM" "transition diagram"
```

---

## 11. Tag Boosting trong Search

### 11.1 How Tag Boosting Works

Khi process images, tags được repeat 5 lần:

```python
# In ExtractedImage.get_vectorization_text()
if self.tags:
    parts.append(f"Tags: {self.tags}, {self.tags}, {self.tags}, {self.tags}, {self.tags}")
```

**Effect on embedding:**

```
Original text:    "Figure 4.1: Media payload"
Boosted text:     "Tags: Figure 4.1, Figure 4.1, Figure 4.1, Figure 4.1, Figure 4.1\nContext: ..."

→ The phrase "Figure 4.1" appears more frequently
→ Embedding vector shifts toward "Figure 4.1" meaning
→ Query "Figure 4.1" gets higher similarity score
```

### 11.2 Search Example

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

