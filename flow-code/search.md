# Search Workflow

## Command: `python -m src.main search "<query>"`

Sơ đồ dưới đây mô tả chi tiết luồng tìm kiếm semantic trong hệ thống RAG.

---

## 1. Tổng quan Search Pipeline

```mermaid
flowchart TB
    START([🔍 Start: python -m src.main search "query"]) --> PARSE

    subgraph PARSE["📝 Parse Arguments"]
        P1[Extract query string]
        P2[Get top_k parameter<br/>default: 5]
        P3[Get save_results flag<br/>default: true]
    end

    PARSE --> INIT

    subgraph INIT["⚙️ Initialize Components"]
        I1[Load SearchEngine] --> I2[Load TextVectorizer]
        I2 --> I3[Load VectorStore<br/>FAISS or ChromaDB]
        I3 --> I4[Load GTE Model<br/>if not cached]
    end

    INIT --> VECTORIZE

    subgraph VECTORIZE["🧠 Query Vectorization"]
        V1["Input: 'authentication flow'"]
        V2[GTE Model Encode]
        V3[L2 Normalization]
        V4["Output: [0.023, -0.156, ..., 0.042]<br/>768-dim vector"]
        V1 --> V2 --> V3 --> V4
    end

    VECTORIZE --> SEARCH

    subgraph SEARCH["🔎 Similarity Search"]
        S1[Load FAISS Index<br/>or ChromaDB Collection]
        S2[Compute Cosine Similarity<br/>query · document vectors]
        S3[Sort by Score Descending]
        S4[Get Top-K Results]
        S1 --> S2 --> S3 --> S4
    end

    SEARCH --> FILTER

    subgraph FILTER["🎯 Filter & Rank"]
        F1{Score ≥ Threshold?}
        F1 -->|"score ≥ 0.5"| F2[✅ Include Result]
        F1 -->|"score < 0.5"| F3[❌ Exclude]
        F2 --> F4[Attach Metadata]
        F4 --> F5[Format Results]
    end

    FILTER --> OUTPUT

    subgraph OUTPUT["📤 Output"]
        O1[Display to Terminal]
        O2[Save to process/input/]
        O3[Save to process/output/]
    end

    OUTPUT --> END([✅ Search Complete!])

    style START fill:#2196F3,color:#fff
    style END fill:#4CAF50,color:#fff
    style PARSE fill:#E3F2FD
    style INIT fill:#FFF3E0
    style VECTORIZE fill:#F3E5F5
    style SEARCH fill:#E8F5E9
    style FILTER fill:#FFEBEE
    style OUTPUT fill:#E0F7FA
```

---

## 2. Chi tiết Query Vectorization

```mermaid
flowchart LR
    subgraph INPUT["User Query"]
        Q1["'authentication flow diagram'"]
    end

    subgraph TOKENIZE["Tokenization"]
        T1[BERT Tokenizer]
        T2["[CLS] authentication flow diagram [SEP]"]
        T3[Token IDs: [101, 8285, 2340, ...]]
    end

    subgraph ENCODE["Model Forward Pass"]
        E1[BERT Encoder<br/>12 layers]
        E2[Self-Attention]
        E3[Feed Forward]
        E4[Pooling Layer]
    end

    subgraph OUTPUT["Query Embedding"]
        O1["768-dim float vector"]
        O2[L2 Normalize]
        O3["||v|| = 1.0"]
    end

    INPUT --> TOKENIZE --> ENCODE --> OUTPUT

    style INPUT fill:#E3F2FD
    style TOKENIZE fill:#FFF3E0
    style ENCODE fill:#F3E5F5
    style OUTPUT fill:#E8F5E9
```

---

## 3. FAISS Similarity Search

```mermaid
flowchart TD
    subgraph QUERY["Query Vector"]
        Q["q = [0.023, -0.156, ..., 0.042]<br/>Normalized: ||q|| = 1"]
    end

    subgraph INDEX["FAISS Index (IndexFlatIP)"]
        I1["Document 1: d₁ = [0.015, -0.089, ...]"]
        I2["Document 2: d₂ = [0.078, 0.234, ...]"]
        I3["Document 3: d₃ = [-0.045, 0.112, ...]"]
        IN["Document N: dₙ = [...]"]
    end

    subgraph COMPUTE["Compute Similarities"]
        C1["sim(q, d₁) = q · d₁ = 0.82"]
        C2["sim(q, d₂) = q · d₂ = 0.45"]
        C3["sim(q, d₃) = q · d₃ = 0.91"]
        CN["sim(q, dₙ) = q · dₙ = 0.33"]
    end

    subgraph SORT["Sort & Top-K"]
        S1["1. Document 3: 0.91"]
        S2["2. Document 1: 0.82"]
        S3["3. Document 2: 0.45"]
        S4["..."]
    end

    QUERY --> COMPUTE
    INDEX --> COMPUTE
    COMPUTE --> SORT

    style QUERY fill:#E3F2FD
    style INDEX fill:#FFF3E0
    style COMPUTE fill:#F3E5F5
    style SORT fill:#E8F5E9
```

### Cosine Similarity Formula:

```
                    q · d
similarity(q, d) = ─────────
                   ||q|| × ||d||

Với normalized vectors (||q|| = ||d|| = 1):
similarity(q, d) = q · d (inner product)
```

---

## 4. Tìm kiếm trên Image Results (PaddleOCR/PyMuPDF)

Khi `process` command chạy, hình ảnh được trích xuất bằng **PyMuPDF** và **PaddleOCR PP-Structure** sẽ được vectorize và lưu vào database. Khi search, query sẽ tìm kiếm trên cả text chunks và image contexts.

### 4.1 Image Data Structure trong Vector Store

```mermaid
flowchart LR
    subgraph EXTRACTION["Image Extraction (process command)"]
        E1["PyMuPDF<br/>Embedded images"]
        E2["PyMuPDF<br/>Vector drawings"]
        E3["PP-Structure<br/>Layout regions"]
    end
    
    subgraph VECTORIZE["Vectorization"]
        V1["Image Context Text<br/>(caption, description,<br/>surrounding text)"]
        V2["GTE Model Encode"]
        V3["768-dim embedding"]
    end
    
    subgraph STORE["Vector Store"]
        S1["chunk_id: 'img_abc123'"]
        S2["content: 'Figure 1: Login flow...'"]
        S3["metadata: {type: 'extracted_image',<br/>region_type: 'figure',<br/>image_path: '...',<br/>source_file: '...',<br/>page_number: 1}"]
    end
    
    EXTRACTION --> VECTORIZE --> STORE

    style EXTRACTION fill:#E3F2FD
    style VECTORIZE fill:#F3E5F5
    style STORE fill:#E8F5E9
```

### 4.2 Image Search Flow

```mermaid
flowchart TD
    QUERY["🔍 User Query:<br/>'authentication diagram'"] --> ENCODE["Encode query<br/>with GTE model"]
    
    ENCODE --> SEARCH["FAISS similarity search"]
    
    SEARCH --> RESULTS["Search Results"]
    
    subgraph RESULTS["Mixed Results"]
        R1["Text Chunk<br/>similarity: 0.89<br/>type: 'text'"]
        R2["Image Context<br/>similarity: 0.85<br/>type: 'extracted_image'<br/>region_type: 'drawing'"]
        R3["Text Chunk<br/>similarity: 0.78<br/>type: 'text'"]
    end
    
    RESULTS --> DISPLAY
    
    subgraph DISPLAY["Display Results"]
        D1["Show text content"]
        D2["Show image path + context<br/>📸 data/extracted_images/auth_p1_drawing0_abc123.png"]
    end

    style QUERY fill:#2196F3,color:#fff
    style RESULTS fill:#FFF3E0
    style DISPLAY fill:#E8F5E9
```

### 4.3 Cách image context được tạo

Khi hình ảnh được trích xuất (bởi PyMuPDF hoặc PP-Structure), hệ thống tạo text để vectorize:

```python
# Trong ExtractedImage.get_vectorization_text():
def get_vectorization_text(self) -> str:
    parts = []
    if self.caption:
        parts.append(f"Caption: {self.caption}")
    if self.description:
        parts.append(f"Description: {self.description}")
    if self.surrounding_text:
        parts.append(f"Context: {self.surrounding_text}")
    parts.append(f"Type: {self.region_type}")  # figure, table, drawing
    parts.append(f"Source: {Path(self.source_file).name}, Page {self.page_number}")
    return "\n".join(parts)
```

**Ví dụ text được vectorize cho một hình:**
```
Caption: Figure 3: Authentication Flow
Description: Drawing from auth_guide.pdf, page 2
Context: The authentication process begins when the user submits credentials...
Type: drawing
Source: auth_guide.pdf, Page 2
```

### 4.4 Image Metadata trong Search Result

```mermaid
classDiagram
    class ImageSearchResult {
        +str chunk_id: "img_abc123"
        +str content: "Caption: Figure 1..."
        +float similarity: 0.85
        +dict metadata
    }
    
    class ImageMetadata {
        +str type: "extracted_image"
        +str region_type: "figure|table|drawing"
        +str image_path: "data/extracted_images/..."
        +str source_file: "document.pdf"
        +int page_number: 1
        +str bbox: "(10, 20, 500, 400)"
    }
    
    ImageSearchResult --> ImageMetadata
```

### 4.5 Ví dụ Search Output có Image

```
Searching for: 'login authentication diagram'
Using backend: faiss
--------------------------------------------------
Found 5 results:

[1] Score: 0.9123
    Type: text
    Source: data/documents/auth_spec.pdf
    Content: The authentication flow begins when the user submits...

[2] Score: 0.8756  📸 IMAGE RESULT
    Type: extracted_image (drawing)
    Source: data/documents/auth_spec.pdf, Page 2
    Image: data/extracted_images/auth_spec_p2_drawing0_abc123.png
    Context: Figure 3: OAuth 2.0 login flow diagram showing...

[3] Score: 0.8234
    Type: text
    Source: data/documents/security_guide.md
    Content: OAuth 2.0 authentication requires the following steps...
```

---

## 5. SearchResult Structure

```mermaid
classDiagram
    class SearchResult {
        +int rank
        +str document
        +float similarity
        +dict metadata
        +str chunk_id
        +to_dict() dict
    }

    class Metadata {
        +str source_file
        +int chunk_index
        +int total_chunks
        +str file_extension
        +int file_size
    }

    SearchResult --> Metadata : contains
```

### Example Result:

```json
{
    "rank": 1,
    "document": "The authentication flow begins when the user...",
    "similarity": 0.9123,
    "metadata": {
        "source_file": "auth_spec.pdf",
        "chunk_index": 5,
        "total_chunks": 42,
        "file_extension": ".pdf"
    },
    "chunk_id": "auth_spec.pdf_5"
}
```

---

## 6. Output Formats

```mermaid
flowchart LR
    subgraph RESULTS["Search Results"]
        R[List of SearchResult]
    end

    subgraph FORMATS["Output Formats"]
        F1["📄 Text Format<br/>(Terminal Display)"]
        F2["📋 JSON Format<br/>(Programmatic)"]
        F3["📝 Markdown Format<br/>(Documentation)"]
    end

    subgraph FILES["Saved Files"]
        FILE1["process/input/<br/>query_{timestamp}.json"]
        FILE2["process/output/<br/>query_{timestamp}.json"]
    end

    RESULTS --> FORMATS
    RESULTS --> FILES

    style RESULTS fill:#E3F2FD
    style FORMATS fill:#FFF3E0
    style FILES fill:#E8F5E9
```

### Terminal Output Example:

```
Searching for: 'authentication flow'
Using backend: faiss
--------------------------------------------------
Found 5 results:

[1] Score: 0.9123
    Source: data/documents/auth_spec.pdf
    Content: The authentication flow begins when the user submits credentials...

[2] Score: 0.8756
    Source: data/documents/security_guide.md
    Content: OAuth 2.0 authentication flow involves the following steps...

[3] Score: 0.8234
    Source: data/documents/api_docs.pdf
    Content: API authentication requires a valid JWT token...
```

---

## 7. Process/Input JSON Structure

```mermaid
flowchart TD
    subgraph INPUT_JSON["process/input/query_20241216_112000.json"]
        I1["query_id: 'query_20241216_112000'"]
        I2["query: 'authentication flow'"]
        I3["timestamp: '2024-12-16T11:20:00'"]
        I4["parameters:"]
        I5["  top_k: 5"]
        I6["  threshold: 0.5"]
    end

    style INPUT_JSON fill:#E3F2FD
```

---

## 8. Process/Output JSON Structure

```mermaid
flowchart TD
    subgraph OUTPUT_JSON["process/output/query_20241216_112000.json"]
        O1["query_id: 'query_20241216_112000'"]
        O2["query: 'authentication flow'"]
        O3["timestamp: '2024-12-16T11:20:00'"]
        O4["result_count: 5"]
        O5["results: ["]
        O6["  {rank: 1, similarity: 0.91, ...},"]
        O7["  {rank: 2, similarity: 0.87, ...},"]
        O8["  ..."]
        O9["]"]
    end

    style OUTPUT_JSON fill:#E8F5E9
```

---

## 9. Configuration

```python
# config/settings.py
class SearchConfig:
    top_k: int = 5              # Number of results to return
    score_threshold: float = 0.5 # Minimum similarity score
    include_metadata: bool = True # Include source info
```

---

## 10. Command Options

```bash
# Basic search
python -m src.main search "authentication flow"

# Get more results
python -m src.main search "user login" --top-k 10

# Don't save input/output files
python -m src.main search "API security" --no-save
```

---

## 11. Search Performance

| Dataset Size | Index Type | Search Time |
|--------------|------------|-------------|
| < 10,000 vectors | Flat | < 10ms |
| 10,000 - 100,000 | Flat | 10-50ms |
| > 100,000 | IVF/HNSW | 5-20ms |

**Note:** FAISS IndexFlatIP performs exhaustive search on all vectors. For larger datasets, consider switching to IVF or HNSW index types in `config/settings.py`.
