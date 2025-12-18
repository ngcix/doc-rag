# 📚 Tổng Quan Dự Án Simple RAG System

## 1. Giới Thiệu

**Simple RAG** là hệ thống **Retrieval-Augmented Generation (RAG)** production-ready, được thiết kế để xử lý tài liệu từ đầu đến cuối:

- **Đầu vào**: Tài liệu raw (PDF, DOCX, MD, TXT)
- **Xử lý**: Chunking thông minh, trích xuất hình ảnh, vectorization
- **Đầu ra**: Semantic search chính xác với hybrid ranking

## 2. Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SIMPLE RAG SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │ Documents  │───▶│   Chunking   │───▶│ Vectorization│───▶│ Vector DB   │ │
│  │ (PDF/DOCX) │    │  (LangChain) │    │   (GTE 768d) │    │ (FAISS)     │ │
│  └────────────┘    └──────────────┘    └──────────────┘    └─────────────┘ │
│                                                                    │        │
│  ┌────────────┐    ┌──────────────┐                               ▼        │
│  │    PDF     │───▶│   Image      │──────────────────────▶ ┌─────────────┐ │
│  │  (Images)  │    │  Extraction  │                        │   Search    │ │
│  └────────────┘    └──────────────┘                        │   Engine    │ │
│                                                             └─────────────┘ │
│  ┌────────────┐    ┌──────────────┐                               │        │
│  │  Markdown  │───▶│  Sequence    │──────────────────────────────▶│        │
│  │  (Mermaid) │    │   Charts     │                               ▼        │
│  └────────────┘    └──────────────┘                        ┌─────────────┐ │
│                                                             │   Results   │ │
│                                                             └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Core Components

### 3.1 Document Chunking (`src/chunking/`)
- **Công nghệ**: LangChain `RecursiveCharacterTextSplitter`
- **Chức năng**: Chia văn bản thành chunks nhỏ tối ưu cho vectorization
- **Hỗ trợ**: TXT, MD, PDF, DOCX

### 3.2 Image Extraction (`src/image_extraction/`)
- **Công nghệ**: PyMuPDF (fitz) + PaddleOCR PP-Structure
- **Chức năng**: Trích xuất hình ảnh từ PDF với auto-tagging
- **2 chế độ**: 
  - Full-page mode (context-rich)
  - PyMuPDF mode (individual images)

### 3.3 Vectorization (`src/vectorization/`)
- **Model**: `Alibaba-NLP/gte-multilingual-base` (768 dimensions)
- **Backend**: FAISS (mặc định) hoặc ChromaDB
- **Đặc điểm**: Hỗ trợ multilingual, max context 8192 tokens

### 3.4 Search Engine (`src/search/`)
- **Loại**: Semantic Search + Keyword Boosting
- **Thuật toán**: Cosine Similarity trên normalized vectors
- **Output**: Ranked results với similarity scores

### 3.5 Sequence Charts (`src/sequence_chart/`)
- **Định dạng**: Mermaid diagrams
- **Chức năng**: Parse, render, vectorize sequence diagrams

## 4. Key Features

| Feature | Mô tả |
|---------|-------|
| 🧠 **Intelligent Chunking** | Recursive splitting bảo toàn context |
| ⚡ **High-Perf Vectorization** | GTE model 768-dim, multilingual |
| 🔍 **Hybrid Search** | Semantic + Tag boosting |
| 🖼️ **Smart Image Extraction** | Full-page capture + auto-tagging |
| 📊 **Dual Backend** | FAISS (speed) + ChromaDB (features) |
| 📈 **Sequence Charts** | Mermaid parsing và vectorization |

## 5. Công Nghệ Chính

### Embedding Model
- **Model**: `Alibaba-NLP/gte-multilingual-base`
- **Dimension**: 768
- **Max Sequence Length**: 8192 tokens
- **Đặc điểm**: State-of-the-art multilingual embedding

### Vector Database
- **Primary**: FAISS (Facebook AI Similarity Search)
- **Alternative**: ChromaDB
- **Distance Metric**: Cosine similarity

### Document Processing
- **PDF**: PyMuPDF (fitz)
- **DOCX**: python-docx
- **Text Splitting**: LangChain

### Image Analysis
- **Layout Detection**: PaddleOCR PP-Structure
- **Image Processing**: PIL/Pillow
- **Quality Filtering**: Brightness, variance checks

## 6. Workflow Cơ Bản

```bash
# 1. Process documents (extract full-page images)
python -m src.main process -fp

# 2. Search for something
python -m src.main search "system architecture"

# 3. Check tags of an image
python -m src.main listtag A2DP_v1.4.pdf_p18

# 4. Add a manual tag (auto re-embed)
python -m src.main addtag A2DP_v1.4.pdf_p18 "security-diagram"

# 5. Search with new tag
python -m src.main search "security diagram"
```

## 7. Điểm Nổi Bật

### Hybrid Mode Processing
Hệ thống xử lý song song:
1. **Text chunks**: Từ tất cả documents (cho granular search)
2. **Full-page images**: Từ PDFs chứa hình (cho visual context)

### Auto-Tagging System
Tự động phát hiện và gắn tags từ văn bản:
- `Figure X.Y: Description`
- `Table X: Description`
- `Fig. X - Description`

### Tag Boosting
Tags được lặp 3 lần trong embedding content để tăng trọng số:
```python
f"Tags: {tag}, {tag}, {tag}"
```

### Dynamic Re-embedding
Khi thêm tag mới qua `addtag`:
1. Append tag vào content
2. Re-calculate vector embedding
3. Update database ngay lập tức

## 8. Use Cases

1. **Technical Documentation Search**: Tìm kiếm trong tài liệu kỹ thuật phức tạp
2. **Diagram Retrieval**: Tìm nhanh Figure/Table theo mô tả
3. **Knowledge Base**: Xây dựng knowledge base từ PDFs
4. **Code Documentation**: Index và search trong docs dự án

