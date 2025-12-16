# Document Processing Workflow

## Command: `python -m src.main process`

Sơ đồ dưới đây mô tả chi tiết luồng xử lý khi chạy lệnh `process`.

---

## 1. Tổng quan Pipeline

```mermaid
flowchart TB
    START([🚀 Start: python -m src.main process]) --> INIT

    subgraph INIT["⚙️ Initialization"]
        I1[Load Configuration] --> I2[Initialize DocumentChunker]
        I2 --> I3[Initialize TextVectorizer]
        I3 --> I4[Initialize VectorStore]
        I4 --> I5[Initialize ImageExtractor]
        I5 --> I6[Initialize ChartProcessor]
    end

    INIT --> PHASE1
    INIT --> PHASE2
    INIT --> PHASE3

    subgraph PHASE1["📄 Phase 1: Text Processing"]
        direction TB
        T1[Scan directory for documents] --> T2{File Type?}
        T2 -->|PDF| T3[PyPDF2 Reader]
        T2 -->|TXT/MD| T4[Direct File Read]
        T2 -->|DOCX| T5[python-docx Reader]
        T3 --> T6[Raw Text Content]
        T4 --> T6
        T5 --> T6
        T6 --> T7[LangChain RecursiveCharacterTextSplitter]
        T7 --> T8[Text Chunks<br/>chunk_size=512, overlap=50]
        T8 --> T9[Vectorize with GTE Model<br/>768-dim embeddings]
    end

    subgraph PHASE2["🖼️ Phase 2: Image Extraction"]
        direction TB
        IMG1[Scan PDFs in directory] --> IMG2[PyMuPDF fitz.open]
        IMG2 --> IMG3[Extract Embedded Images<br/>page.get_images]
        IMG2 --> IMG4[Extract Vector Drawings<br/>page.get_drawings]
        IMG3 --> IMG5[Validation Filter]
        IMG4 --> IMG6[Clustering Algorithm<br/>Merge nearby paths]
        IMG6 --> IMG7[Render at 150 DPI]
        IMG7 --> IMG5
        IMG5 --> IMG8{Valid Image?}
        IMG8 -->|brightness ≥ 30<br/>std_dev ≥ 15<br/>dark_ratio ≤ 85%| IMG9[✅ Save PNG]
        IMG8 -->|Invalid| IMG10[❌ Discard]
        IMG9 --> IMG11[Extract Surrounding Text]
        IMG11 --> IMG12[Vectorize Image Context]
    end

    subgraph PHASE3["📊 Phase 3: Sequence Charts"]
        direction TB
        C1[Scan .md files] --> C2[Find Mermaid code blocks]
        C2 --> C3[Parse sequenceDiagram]
        C3 --> C4[Extract participants & messages]
        C4 --> C5[Generate description text]
        C5 --> C6[Vectorize description]
    end

    PHASE1 --> STORE
    PHASE2 --> STORE
    PHASE3 --> STORE

    subgraph STORE["💾 Phase 4: Storage"]
        S1[Collect all embeddings] --> S2{Backend?}
        S2 -->|FAISS| S3[FAISS IndexFlatIP<br/>Cosine Similarity]
        S2 -->|ChromaDB| S4[ChromaDB Collection]
        S3 --> S5[Save to data/faiss_index/]
        S4 --> S6[Save to data/vectordb/]
    end

    STORE --> END([✅ Processing Complete!])

    style START fill:#4CAF50,color:#fff
    style END fill:#4CAF50,color:#fff
    style INIT fill:#E3F2FD
    style PHASE1 fill:#FFF3E0
    style PHASE2 fill:#F3E5F5
    style PHASE3 fill:#E8F5E9
    style STORE fill:#FFEBEE
```

---

## 2. Chi tiết Text Chunking

```mermaid
flowchart LR
    subgraph INPUT["Input Document"]
        A[📄 Raw Document<br/>PDF/TXT/MD/DOCX]
    end

    subgraph CHUNKING["Chunking Process"]
        B[Read File Content] --> C[RecursiveCharacterTextSplitter]
        C --> D["Separators Priority:<br/>1. \\n\\n (paragraphs)<br/>2. \\n (lines)<br/>3. . (sentences)<br/>4. space (words)"]
        D --> E[Split into Chunks]
    end

    subgraph OUTPUT["Output Chunks"]
        F["Chunk 1<br/>[0:512]"]
        G["Chunk 2<br/>[462:974]"]
        H["Chunk 3<br/>[924:1436]"]
        I[...]
    end

    INPUT --> CHUNKING
    E --> F
    E --> G
    E --> H
    E --> I

    style INPUT fill:#E3F2FD
    style CHUNKING fill:#FFF3E0
    style OUTPUT fill:#E8F5E9
```

**Configuration:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `chunk_size` | 512 | Characters per chunk |
| `chunk_overlap` | 50 | Overlap between consecutive chunks |
| `separators` | `[\n\n, \n, . , , ]` | Priority order for splitting |

---

## 3. Chi tiết Image Extraction

```mermaid
flowchart TD
    subgraph PDF["📄 PDF Document"]
        P1[page.get_images] --> P2[Embedded Bitmaps<br/>PNG/JPEG]
        P1b[page.get_drawings] --> P3[Vector Paths<br/>Lines, Shapes]
    end

    subgraph PROCESS["Processing"]
        P2 --> V1[fitz.Pixmap]
        P3 --> C1[Cluster nearby paths<br/>merge_distance=50px]
        C1 --> C2[page.get_pixmap<br/>clip=region, dpi=150]
        V1 --> ALPHA[Handle Alpha Channel]
        C2 --> ALPHA
        ALPHA --> VAL{Validation}
    end

    subgraph VALIDATION["Validation Checks"]
        VAL -->|"mean brightness < 30"| REJ1[❌ Too Dark]
        VAL -->|"std_dev < 15"| REJ2[❌ Solid Color]
        VAL -->|"dark_ratio > 85%"| REJ3[❌ Mostly Black]
        VAL -->|"width < 50 or height < 50"| REJ4[❌ Too Small]
        VAL -->|"All checks passed"| SAVE[✅ Valid Image]
    end

    subgraph OUTPUT["Output"]
        SAVE --> PNG["📁 data/extracted_images/<br/>{filename}_p{page}_img{idx}_{hash}.png"]
        SAVE --> CTX[Extract surrounding text]
        CTX --> VEC[Vectorize context<br/>for semantic search]
    end

    style PDF fill:#E3F2FD
    style PROCESS fill:#FFF3E0
    style VALIDATION fill:#FFEBEE
    style OUTPUT fill:#E8F5E9
```

---

## 4. Chi tiết PaddleOCR PP-Structure và PyMuPDF

### Tổng quan hai công nghệ

Dự án sử dụng **hai phương pháp** để trích xuất hình ảnh từ documents:

| Công nghệ | Vai trò | Khi nào sử dụng |
|-----------|---------|-----------------|
| **PyMuPDF (fitz)** | Phương pháp chính | Trích xuất trực tiếp từ PDF |
| **PaddleOCR PP-Structure** | Phương pháp bổ sung | Phân tích layout phức tạp, xử lý ảnh |

### 4.1 PyMuPDF (fitz) - Phương pháp chính

```mermaid
flowchart TB
    subgraph PYMUPDF["🔧 PyMuPDF (fitz)"]
        direction TB
        P1["fitz.open(pdf_path)"] --> P2["doc[page_num]"]
        
        subgraph EXTRACT["Extraction Methods"]
            P2 --> E1["page.get_images(full=True)<br/>→ Embedded bitmaps (PNG/JPEG)"]
            P2 --> E2["page.get_drawings()<br/>→ Vector paths (lines, shapes)"]
        end
        
        E1 --> PIX1["fitz.Pixmap(doc, xref)<br/>Convert to image data"]
        E2 --> CLUSTER["Cluster nearby paths<br/>merge_distance=50px"]
        CLUSTER --> PIX2["page.get_pixmap(clip=region, dpi=150)<br/>Render vector to raster"]
    end

    subgraph OUTPUT["Output"]
        PIX1 --> SAVE["Save as PNG"]
        PIX2 --> SAVE
    end

    style PYMUPDF fill:#E3F2FD
    style OUTPUT fill:#E8F5E9
```

**Ưu điểm PyMuPDF:**
- ⚡ **Nhanh**: Trích xuất trực tiếp từ PDF, không cần render toàn trang
- 🎯 **Chính xác**: Lấy đúng embedded images gốc
- 📐 **Vector support**: Trích xuất cả vector drawings (diagrams, flowcharts)
- 💾 **Nhẹ**: Không cần GPU, chạy nhanh trên CPU

**Code flow trong `extractor.py`:**
```python
# Line 159-250: Trích xuất embedded images
def _extract_pdf_with_pymupdf(self, pdf_path: Path):
    doc = fitz.open(str(pdf_path))
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)  # Lấy danh sách images
        for img in image_list:
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)  # Chuyển thành Pixmap
            # Xử lý alpha channel, color space...
            pix.save(str(image_path))

# Line 252-357: Trích xuất vector drawings
def _extract_drawings_with_pymupdf(self, pdf_path: Path):
    drawings = page.get_drawings()  # Lấy vector paths
    # Cluster nearby rects để gom thành diagram
    for rect in clusters:
        pix = page.get_pixmap(clip=rect, dpi=150)  # Render vùng
```

---

### 4.2 PaddleOCR PP-Structure - Phân tích Layout

```mermaid
flowchart TB
    subgraph PADDLE["🤖 PaddleOCR PP-Structure V3"]
        direction TB
        PP1["PPStructureV3()"] --> PP2["engine.predict(image_path)"]
        
        PP2 --> ANALYSIS["Layout Analysis"]
        
        subgraph REGIONS["Detected Regions"]
            R1["📊 Figure / Image / Chart"]
            R2["📋 Table"]
            R3["📝 Text / Title / Paragraph"]
            R4["📸 Picture"]
        end
        
        ANALYSIS --> REGIONS
        
        REGIONS --> BBOX["Bounding Box (x1, y1, x2, y2)"]
        BBOX --> CROP["Crop region from image"]
    end

    subgraph CONTEXT["Text Context"]
        C1["Extract surrounding text"]
        C2["Get nearby text blocks"]
        C3["Caption detection"]
    end

    REGIONS --> CONTEXT

    style PADDLE fill:#F3E5F5
    style CONTEXT fill:#FFF3E0
```

**Ưu điểm PaddleOCR PP-Structure:**
- 🧠 **AI-powered**: Deep learning model phát hiện layout chính xác
- 📊 **Multi-region**: Phân biệt được figure, table, text, chart
- 📖 **Context aware**: Lấy được text context xung quanh hình
- 🌐 **OCR tích hợp**: Có thể OCR text trong hình

**Khi nào PP-Structure được gọi (trong `extractor.py`):**
```python
# Line 112-128: Khởi tạo PP-Structure engine (lazy loading)
def _init_structure_engine(self):
    from paddleocr import PPStructureV3
    engine = PPStructureV3(
        use_doc_orientation_classify=False,  # Không cần xoay trang
        use_doc_unwarping=False,  # Không cần làm phẳng
    )
    return engine

# Line 396-486: Xử lý ảnh với PP-Structure
def _extract_from_image(self, image_path, source_file, page_number):
    results = self.structure_engine.predict(input=str(image_path))
    
    for result in results:
        layout_result = result.layout_parsing_result
        for box in layout_result.get('boxes', []):
            region_type = box.get('type')  # 'figure', 'table', etc.
            bbox = box.get('bbox')
            # Crop and save region...
```

---

### 4.3 So sánh hai phương pháp

```mermaid
flowchart LR
    subgraph COMPARISON["Comparison"]
        direction TB
        
        subgraph PYMUPDF_PROS["PyMuPDF ✅"]
            PM1["Fast extraction"]
            PM2["Native PDF objects"]
            PM3["Vector drawings support"]
            PM4["No GPU needed"]
        end
        
        subgraph PADDLE_PROS["PP-Structure ✅"]
            PP1["AI layout detection"]
            PP2["Region classification"]
            PP3["Text context extraction"]
            PP4["Works on any image"]
        end
    end

    style PYMUPDF_PROS fill:#E8F5E9
    style PADDLE_PROS fill:#F3E5F5
```

| Tiêu chí | PyMuPDF | PP-Structure |
|----------|---------|--------------|
| **Tốc độ** | ⚡ Rất nhanh | 🐢 Chậm hơn (AI model) |
| **Độ chính xác** | Cao với PDF chuẩn | Cao với layout phức tạp |
| **GPU** | Không cần | Có thể dùng để tăng tốc |
| **Input** | Chỉ PDF | Mọi định dạng ảnh |
| **Output** | Raw images | Classified regions |

---

### 4.4 Luồng xử lý thực tế

```mermaid
flowchart TD
    INPUT[/"📄 Input File"/] --> CHECK{File Type?}
    
    CHECK -->|PDF| PDF_FLOW
    CHECK -->|Image| IMG_FLOW
    
    subgraph PDF_FLOW["PDF Processing"]
        direction TB
        P1["PyMuPDF: Extract embedded images<br/>(Primary method)"]
        P2["PyMuPDF: Extract vector drawings<br/>(Diagrams, flowcharts)"]
        P3["Fallback: pdf2image + PP-Structure<br/>(If PyMuPDF fails)"]
        P1 --> P2
        P2 -.->|"On error"| P3
    end
    
    subgraph IMG_FLOW["Image Processing"]
        direction TB
        I1["PP-Structure: Analyze layout"]
        I2["Detect regions (figure/table/text)"]
        I3["Crop and save regions"]
        I1 --> I2 --> I3
    end
    
    PDF_FLOW --> VALIDATE
    IMG_FLOW --> VALIDATE
    
    VALIDATE["Validation Filter<br/>brightness, std_dev, dark_ratio"]
    VALIDATE --> SAVE["Save valid images<br/>+ Extract text context"]

    style PDF_FLOW fill:#E3F2FD
    style IMG_FLOW fill:#F3E5F5
    style VALIDATE fill:#FFEBEE
    style SAVE fill:#E8F5E9
```

---

### 4.5 Cấu hình Image Extraction

```python
@dataclass  
class ImageExtractionConfig:
    # Output settings
    output_dir: Path = EXTRACTED_IMAGES_DIR
    image_format: str = "png"
    
    # Size filters
    min_width: int = 50      # Bỏ qua ảnh < 50px
    min_height: int = 50
    
    # Quality filters (tránh black/empty images)
    min_brightness: float = 30.0     # Mean brightness >= 30
    min_std_dev: float = 15.0        # Variance >= 15
    max_dark_pixel_ratio: float = 0.85  # Dark pixels < 85%
    
    # Region types to extract
    extract_tables: bool = True
    extract_figures: bool = True
    
    # Context extraction
    context_chars: int = 500  # Lấy 500 chars xung quanh ảnh
    
    # Vector drawings clustering
    cluster_merge_distance: int = 50   # Merge paths within 50px
    min_diagram_size: int = 100        # Min diagram size
```

---

## 5. Chi tiết Vectorization

```mermaid
flowchart LR
    subgraph INPUT["Input"]
        T1["Text Chunk<br/>'The authentication flow...'"]
        T2["Image Context<br/>'Figure 1: Login diagram...'"]
        T3["Chart Description<br/>'Sequence: User → Server'"]
    end

    subgraph MODEL["GTE Model"]
        M1["Alibaba-NLP/gte-multilingual-base"]
        M2["Max Sequence: 8192 tokens"]
        M3["Embedding Dimension: 768"]
    end

    subgraph PROCESS["Processing"]
        E1[SentenceTransformer.encode]
        E2[L2 Normalization]
    end

    subgraph OUTPUT["Output"]
        V1["[0.023, -0.156, 0.089, ..., 0.042]<br/>768-dimensional vector"]
    end

    INPUT --> MODEL
    MODEL --> PROCESS
    PROCESS --> OUTPUT

    style INPUT fill:#E3F2FD
    style MODEL fill:#FFF3E0
    style PROCESS fill:#F3E5F5
    style OUTPUT fill:#E8F5E9
```

---

## 6. Storage Architecture

```mermaid
flowchart TB
    subgraph VECTORS["Vectorized Data"]
        V1[Text Chunk Embeddings]
        V2[Image Context Embeddings]
        V3[Chart Description Embeddings]
    end

    subgraph FAISS["FAISS Backend (Default)"]
        F1[IndexFlatIP<br/>Inner Product Search]
        F2[L2 Normalized Vectors]
        F3["Cosine Similarity =<br/>Dot Product"]
        F1 --> F4[(documents.index)]
        F1 --> F5[(documents_metadata.pkl)]
    end

    subgraph CHROMA["ChromaDB Backend (Alternative)"]
        C1[PersistentClient]
        C2[HNSW Index]
        C1 --> C3[(SQLite + Parquet)]
    end

    VECTORS --> FAISS
    VECTORS --> CHROMA

    style VECTORS fill:#E3F2FD
    style FAISS fill:#E8F5E9
    style CHROMA fill:#FFF3E0
```

---

## 7. Output Summary

Khi `process` hoàn thành, terminal sẽ hiển thị:

```
==================================================
Processing complete!
  Text chunks: 150
  Images extracted: 125
  Total items in database: 275
```

### File Outputs:

| Location | Content |
|----------|---------|
| `data/faiss_index/documents.index` | FAISS vector index |
| `data/faiss_index/documents_metadata.pkl` | Metadata + documents |
| `data/extracted_images/*.png` | Extracted images from PDFs |

---

## 8. Command Options

```bash
# Full processing (text + images + charts)
python -m src.main process

# Skip image extraction
python -m src.main process --no-images

# Skip Mermaid chart processing
python -m src.main process --no-charts

# Custom input directory
python -m src.main process --input /path/to/documents
```
