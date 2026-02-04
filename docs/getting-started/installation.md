# 📦 Cài Đặt

## Yêu Cầu Hệ Thống

- Python 3.10 hoặc 3.11
- 4GB RAM (khuyến nghị 8GB)
- 2GB disk space cho models

## Cài Đặt Cơ Bản

### 1. Clone Repository

```bash
git clone <repository-url>
cd SpecRAG
```

### 2. Tạo Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

### 4. Khởi Tạo Thư Mục

```bash
specrag init
```

Output:
```
Directory structure initialized:
  Documents: data/documents
  Vector DB: data/vectordb
  Process Input: process/input
  Process Output: process/output
```

## Cài Đặt Nâng Cao

### GPU Support (Optional)

```bash
# PyTorch với CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118

# FAISS GPU
pip install faiss-gpu
```

### Docling (Cho AI Layout Detection)

```bash
pip install docling
```

## Kiểm Tra Cài Đặt

```bash
# Xem help
specrag --help

# Xem stats (sẽ báo empty nếu chưa có data)
specrag stats
```

## Cấu Trúc Thư Mục Sau Cài Đặt

```
SpecRAG/
├── data/
│   ├── documents/          # Đặt tài liệu cần xử lý
│   ├── extracted_images/   # Hình ảnh trích xuất
│   ├── faiss_index/        # Vector database
│   └── vectordb/           # ChromaDB (alternative)
├── models/                 # Local embedding models
├── process/
│   ├── input/              # Query logs
│   └── output/             # Result logs
└── src/                    # Source code
```

---

**Tiếp theo**: [Quickstart →](./quickstart.md)
