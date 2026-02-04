# 📄 Xử Lý Documents

## Tổng Quan

Lệnh `process` thực hiện:
1. **Chunking**: Chia văn bản thành chunks
2. **Image Extraction**: Trích xuất hình ảnh từ PDFs
3. **Vectorization**: Chuyển đổi thành vectors
4. **Storage**: Lưu vào FAISS database

## Cú Pháp

```bash
specrag process [OPTIONS]
```

## Options

| Option | Shortcut | Mô tả |
|--------|----------|-------|
| `--input PATH` | `-i` | Thư mục input (default: `data/documents/`) |
| `--fullpage` | `-fp` | Full-page image extraction (recommended) |
| `--docling` | `-dl` | Docling AI extraction |
| `--docling1` | `-dl1` | Docling legacy |
| `--format` | `-fmt` | Định dạng ảnh: png/jpeg |
| `--no-charts` | | Bỏ qua sequence charts |
| `--no-images` | | Bỏ qua image extraction |

## Image Extraction Modes

### 1. Full-page Mode (`-fp`) - Khuyến nghị

```bash
specrag process -fp
```

- Capture toàn bộ trang chứa hình ảnh
- Context đầy đủ (10K chars)
- Tốt cho RAG, architecture diagrams

### 2. Docling Mode (`-dl`)

```bash
specrag process -dl
```

- Sử dụng AI (RT-DETR) để detect layout
- Crop chính xác từng figure/table
- Tốt cho precise extraction

### 3. Docling Legacy (`-dl1`)

```bash
specrag process -dl1
```

- Phiên bản Docling cũ
- Dùng khi cần tương thích

## Ví Dụ Sử Dụng

### Cơ bản

```bash
# Full-page mode (phổ biến nhất)
specrag process -fp

# Docling AI mode
specrag process -dl
```

### Tùy chọn nâng cao

```bash
# Custom input directory
specrag process -fp -i /path/to/docs

# JPEG format (nhỏ hơn PNG)
specrag process -fp --format jpeg

# Chỉ text, không images
specrag process --no-images
```

### Reprocessing

```bash
# Xóa data cũ trước khi reprocess
specrag clean --yes

# Process lại
specrag process -fp
```

## Output

```
Processing documents from: data/documents
Vector store backend: faiss
FAISS index location: data/faiss_index
--------------------------------------------------

[1/3] Processing documents (Parallel)...
  Found 5 files to chunk.
  Chunking files: 100%|██████████| 5/5
  Extracted 245 text chunks (took 2.34s)

[2/3] Extracting images from PDFs (Parallel)...
  Extracting from PDFs: 100%|██████████| 3/3
  Total images processed: 33 (took 5.12s)

[3/3] Processing sequence charts...
  Charts processing completed (took 0.5s)

[4/4] Vectorizing and Storing 278 items...
  Vectorization completed (took 12.5s)

==================================================
Processing complete!
  Text chunks: 245
  Images extracted: 33
  Total items in database: 278
[TIME] Time Report:
  Chunking:      2.34s
  Image Extract: 5.12s
  Charts:        0.5s
  Vectorization: 12.5s
  -----------------
  Total:         20.46s
```

## Xử Lý Các Loại File

| Extension | Xử lý |
|-----------|-------|
| `.pdf` | Text extraction + Image extraction |
| `.docx` | Text extraction |
| `.md`, `.markdown` | Text extraction + Mermaid charts |
| `.txt` | Text extraction |

## Tips

1. **Lần đầu**: Dùng `-fp` để có context đầy đủ
2. **Nhiều PDFs lớn**: Chạy parallel tự động
3. **Cần precise cropping**: Dùng `-dl`
4. **Tiết kiệm disk**: Dùng `--format jpeg`

---

**Xem thêm**: [CLI Reference →](../reference/cli-commands.md)
