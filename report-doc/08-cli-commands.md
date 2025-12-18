# 💻 Các Lệnh CLI (Command Line Interface)

## 1. Tổng Quan CLI

Hệ thống sử dụng **argparse** để xử lý command-line arguments. Entry point là `src/main.py`.

```bash
# Cú pháp chung
python -m src.main <command> [options] [arguments]
```

## 2. Danh Sách Lệnh

| Command | Mô tả | Ví dụ |
|---------|-------|-------|
| `process` | Xử lý và index tài liệu | `python -m src.main process -fp` |
| `search` | Tìm kiếm semantic | `python -m src.main search "query"` |
| `list` | Liệt kê tất cả documents | `python -m src.main list` |
| `listtag` | Xem tags của document | `python -m src.main listtag doc_id` |
| `addtag` | Thêm tag và re-embed | `python -m src.main addtag doc_id "tag"` |
| `stats` | Thống kê database | `python -m src.main stats` |
| `clean` | Xóa dữ liệu | `python -m src.main clean --yes` |
| `init` | Tạo thư mục cấu trúc | `python -m src.main init` |

## 3. Chi Tiết Từng Lệnh

---

### 3.1 `process` - Xử Lý Tài Liệu

**Mô tả:** Xử lý tất cả documents trong thư mục input, trích xuất images, chunk text, và vectorize.

**Cú pháp:**
```bash
python -m src.main process [options]
```

**Options:**

| Option | Shortcut | Mô tả | Mặc định |
|--------|----------|-------|----------|
| `--input PATH` | `-i PATH` | Thư mục input | `data/documents/` |
| `--fullpage` | `-fp` | Full-page image extraction | - |
| `--pymupdf` | `-pymu` | Individual image extraction | - |
| `--no-charts` | - | Bỏ qua sequence charts | False |
| `--no-images` | - | Bỏ qua image extraction | False |

**Lưu ý:** Phải chỉ định `-fp` HOẶC `-pymu` trừ khi dùng `--no-images`.

**Ví dụ:**
```bash
# Full-page mode (recommended cho RAG)
python -m src.main process -fp

# PyMuPDF mode (individual images)
python -m src.main process -pymu

# Custom input directory
python -m src.main process -fp -i /path/to/docs

# Text only (no images)
python -m src.main process --no-images

# No charts processing
python -m src.main process -fp --no-charts
```

**Output:**
```
Processing documents from: data/documents
Vector store backend: faiss
FAISS index location: data/faiss_index
--------------------------------------------------

[1/3] Processing documents...
Chunked: HID_v1.1.1.pdf -> 245 chunks
  Extracted 245 text chunks

[2/3] Extracting images from PDFs...
Extracting full pages from: HID_v1.1.1.pdf
  Captured full page 1
  Captured full page 4
  ...
  Extracted 33 images from HID_v1.1.1.pdf
  Total images processed: 33

[3/3] Processing sequence charts...

[4/4] Vectorizing and Storing 278 items...
Batches: 100%|██████████| 9/9 [00:12<00:00,  1.35s/it]
Added/Updated 278 vectors to FAISS index

==================================================
Processing complete!
  Text chunks: 245
  Images extracted: 33
  Total items in database: 278
```

---

### 3.2 `search` - Tìm Kiếm Semantic

**Mô tả:** Tìm kiếm tài liệu dựa trên semantic similarity.

**Cú pháp:**
```bash
python -m src.main search "query" [options]
```

**Arguments:**

| Argument | Mô tả |
|----------|-------|
| `query` | Câu query tìm kiếm (required) |

**Options:**

| Option | Shortcut | Mô tả | Mặc định |
|--------|----------|-------|----------|
| `--top-k N` | `-k N` | Số kết quả trả về | 5 |
| `--no-save` | - | Không lưu input/output logs | False |

**Ví dụ:**
```bash
# Basic search
python -m src.main search "Figure 4.1"

# Get more results
python -m src.main search "system architecture" -k 10

# Don't save logs
python -m src.main search "bluetooth protocol" --no-save
```

**Output:**
```
Searching for: 'Figure 4.1'
Using backend: faiss
--------------------------------------------------
Search completed. Input: process/input/query_20251218_105537.json, Output: process/output/query_20251218_105537.json
Found 5 results:

[1] Score: 0.8542
    ID: HID_v1.1.1.pdf_p30
    Source: data/documents/HID_v1.1.1.pdf
    Content: Tags: Figure 4.1: Media payload format, Figure 4.1: Media payload format...

[2] Score: 0.7234
    ID: HID_v1.1.1.pdf_p31
    Source: data/documents/HID_v1.1.1.pdf
    Content: Context: The media payload continues with...

...
```

---

### 3.3 `list` - Liệt Kê Documents

**Mô tả:** Hiển thị tất cả documents đã được index.

**Cú pháp:**
```bash
python -m src.main list
```

**Output:**
```
Found 278 documents:
--------------------------------------------------
ID: HID_v1.1.1.pdf_0 | Source: data/documents/HID_v1.1.1.pdf
ID: HID_v1.1.1.pdf_1 | Source: data/documents/HID_v1.1.1.pdf
ID: HID_v1.1.1.pdf_2 | Source: data/documents/HID_v1.1.1.pdf
...
ID: HID_v1.1.1.pdf_p30 | Source: data/documents/HID_v1.1.1.pdf
ID: HID_v1.1.1.pdf_p33 | Source: data/documents/HID_v1.1.1.pdf
...
```

**Note:** Giới hạn output 10,000 documents.

---

### 3.4 `listtag` - Xem Tags

**Mô tả:** Hiển thị tags của một document cụ thể.

**Cú pháp:**
```bash
python -m src.main listtag <doc_id>
```

**Arguments:**

| Argument | Mô tả |
|----------|-------|
| `doc_id` | ID của document (required) |

**Ví dụ:**
```bash
python -m src.main listtag HID_v1.1.1.pdf_p30
```

**Output:**
```
Tags for HID_v1.1.1.pdf_p30: Figure 4.1: Media payload format,security-diagram
```

**Nếu không tìm thấy:**
```
Document unknown_doc not found.
```

---

### 3.5 `addtag` - Thêm Tag

**Mô tả:** Thêm tag vào document và tự động re-embed để tag searchable.

**Cú pháp:**
```bash
python -m src.main addtag <doc_id> <tag>
```

**Arguments:**

| Argument | Mô tả |
|----------|-------|
| `doc_id` | ID của document (required) |
| `tag` | Tag cần thêm (required) |

**Ví dụ:**
```bash
# Single word tag
python -m src.main addtag HID_v1.1.1.pdf_p30 bluetooth

# Multi-word tag (quote required)
python -m src.main addtag HID_v1.1.1.pdf_p30 "security diagram"

# Hyphenated tag
python -m src.main addtag HID_v1.1.1.pdf_p30 data-flow
```

**Output:**
```
Re-calculating vector embedding...
Batches: 100%|██████████| 1/1 [00:00<00:00,  5.23it/s]
Deleted 1 vectors and rebuilt index
Added/Updated 1 vectors to FAISS index
Successfully added tag 'security-diagram' to document 'HID_v1.1.1.pdf_p30'
Updated Tags: Figure 4.1: Media payload format,security-diagram
Vector embedding updated to include new tag.
```

---

### 3.6 `stats` - Thống Kê Database

**Mô tả:** Hiển thị thông tin về vector database.

**Cú pháp:**
```bash
python -m src.main stats
```

**Output:**
```
Vector Database Statistics
--------------------------------------------------
  backend: faiss
  collection_name: documents
  count: 278
  index_type: Flat
  dimension: 768
  index_directory: data/faiss_index
  distance_metric: cosine
```

---

### 3.7 `clean` - Xóa Dữ Liệu

**Mô tả:** Xóa dữ liệu đã xử lý (index, images, logs).

**Cú pháp:**
```bash
python -m src.main clean [options]
```

**Options:**

| Option | Shortcut | Mô tả | Mặc định |
|--------|----------|-------|----------|
| `--all` | - | Bao gồm cả models | False |
| `--yes` | `-y` | Bỏ qua xác nhận | False |

**Ví dụ:**
```bash
# Interactive (có confirm)
python -m src.main clean

# Skip confirmation
python -m src.main clean --yes

# Include models (cẩn thận!)
python -m src.main clean --all --yes
```

**Output (interactive):**
```
The following directories will be cleaned:
  ChromaDB database: data/vectordb (0.00 MB)
  FAISS index: data/faiss_index (45.23 MB)
  Extracted images: data/extracted_images (128.56 MB)
  Process input: process/input (0.12 MB)
  Process output: process/output (0.08 MB)

Total: 173.99 MB

Are you sure you want to delete these? [y/N]: y

Cleaning...
  ✓ Cleaned ChromaDB database
  ✓ Cleaned FAISS index
  ✓ Cleaned Extracted images
  ✓ Cleaned Process input
  ✓ Cleaned Process output

Clean completed!
```

**Lưu ý:**
- Không xóa `data/documents/` (input files)
- `--all` sẽ xóa models (~1GB), cần download lại

---

### 3.8 `init` - Khởi Tạo Thư Mục

**Mô tả:** Tạo cấu trúc thư mục cần thiết.

**Cú pháp:**
```bash
python -m src.main init
```

**Output:**
```
Directory structure initialized:
  Documents: data/documents
  Vector DB: data/vectordb
  Process Input: process/input
  Process Output: process/output
```

**Thư mục được tạo:**
- `data/documents/`
- `data/extracted_images/`
- `data/vectordb/`
- `data/faiss_index/`
- `models/`
- `process/input/`
- `process/output/`

---

## 4. Workflow Thực Tế

### 4.1 First-time Setup

```bash
# 1. Initialize structure
python -m src.main init

# 2. Copy documents to data/documents/
cp /path/to/documents/*.pdf data/documents/

# 3. Process with full-page mode
python -m src.main process -fp

# 4. Verify
python -m src.main stats
```

### 4.2 Daily Usage

```bash
# Search for content
python -m src.main search "bluetooth protocol"

# Find specific diagram
python -m src.main search "Figure 3.2"

# Check what's indexed
python -m src.main list

# View tags
python -m src.main listtag HID_v1.1.1.pdf_p30
```

### 4.3 Tag Management

```bash
# Add project tag
python -m src.main addtag HID_v1.1.1.pdf_p30 "project-alpha"

# Add category tags
python -m src.main addtag HID_v1.1.1.pdf_p30 "security"
python -m src.main addtag HID_v1.1.1.pdf_p30 "architecture"

# Verify
python -m src.main listtag HID_v1.1.1.pdf_p30

# Search with new tags
python -m src.main search "project alpha security"
```

### 4.4 Reprocessing

```bash
# Clean old data
python -m src.main clean --yes

# Add new documents
cp /new/documents/*.pdf data/documents/

# Reprocess
python -m src.main process -fp

# Verify
python -m src.main stats
```

## 5. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | CLI argument error |

## 6. Environment Variables (Suggestion)

Có thể mở rộng với env vars:

```bash
# Set device
export RAG_DEVICE=cuda
export RAG_BACKEND=chromadb

# Run commands
python -m src.main process -fp
```

## 7. Help Commands

```bash
# General help
python -m src.main --help

# Command-specific help
python -m src.main process --help
python -m src.main search --help
python -m src.main clean --help
```

**Output `--help`:**
```
usage: main.py [-h] {process,search,stats,init,list,clean,addtag,listtag} ...

Simple RAG System - Document Processing and Search

positional arguments:
  {process,search,stats,init,list,clean,addtag,listtag}
                        Available commands
    process             Process and vectorize documents
    search              Search through documents
    stats               Show vector database statistics
    init                Initialize directory structure
    list                List all documents in the database
    clean               Clean extracted data
    addtag              Add a tag to a document
    listtag             List tags for a document

optional arguments:
  -h, --help            show this help message and exit
```

