# 💻 CLI Commands Reference

## Cú Pháp Chung

```bash
python -m src.main <command> [options] [arguments]
```

## Danh Sách Commands

| Command | Mô tả |
|---------|-------|
| `process` | Xử lý và index tài liệu |
| `search` | Tìm kiếm semantic/hybrid |
| `msearch` | Multi-query search |
| `list` | Liệt kê documents |
| `stats` | Thống kê database |
| `clean` | Xóa dữ liệu |
| `init` | Khởi tạo thư mục |
| `addtag` | Thêm tag |
| `listtag` | Xem tags |
| `removetag` | Xóa user tag |
| `resettags` | Reset tags |
| `addknowledge` | Thêm knowledge |
| `updateknowledge` | Cập nhật knowledge |
| `getknowledge` | Xem knowledge |
| `eval` | Chạy evaluation |

---

## process

Xử lý và vectorize documents.

```bash
python -m src.main process [OPTIONS]
```

| Option | Shortcut | Mô tả | Default |
|--------|----------|-------|---------|
| `--input` | `-i` | Thư mục input | `data/documents/` |
| `--fullpage` | `-fp` | Full-page extraction | - |
| `--docling` | `-dl` | Docling AI extraction | - |
| `--docling1` | `-dl1` | Docling legacy | - |
| `--format` | `-fmt` | png/jpeg | png |
| `--no-charts` | | Skip sequence charts | false |
| `--no-images` | | Skip image extraction | false |

**Lưu ý**: Phải chỉ định `-fp`, `-dl`, hoặc `-dl1` trừ khi dùng `--no-images`.

```bash
# Examples
python -m src.main process -fp
python -m src.main process -dl
python -m src.main process -fp --format jpeg
python -m src.main process --no-images
```

---

## search

Tìm kiếm semantic.

```bash
python -m src.main search "query" [OPTIONS]
```

| Option | Shortcut | Mô tả | Default |
|--------|----------|-------|---------|
| `--top-k` | `-k` | Số kết quả | 5 |
| `--hybrid` | `-hy` | BM25 + Vector | off |
| `--pic` | `-pic` | Images only | off |
| `--no-save` | | Không lưu logs | off |

```bash
# Examples
python -m src.main search "authentication"
python -m src.main search -hy "Figure 4.1"
python -m src.main search -pic "state machine"
python -m src.main search -k 10 "connection"
```

---

## msearch

Multi-query search với RRF fusion.

```bash
python -m src.main msearch "query1" "query2" [...] [OPTIONS]
```

| Option | Shortcut | Mô tả | Default |
|--------|----------|-------|---------|
| `--top-k` | `-k` | Số kết quả merged | 5 |
| `--hybrid` | `-hy` | BM25 + Vector | off |
| `--pic` | `-pic` | Images only | off |
| `--no-save` | | Không lưu logs | off |

```bash
# Examples
python -m src.main msearch "reconnection" "link loss" "timeout"
python -m src.main msearch -hy "Figure 4.1" "Media payload"
```

---

## list

Liệt kê documents đã index.

```bash
python -m src.main list
```

---

## stats

Thống kê database.

```bash
python -m src.main stats
```

Output:
```
Vector Database Statistics
--------------------------------------------------
  backend: faiss
  collection_name: documents
  count: 278
  index_type: Flat
  dimension: 768
```

---

## clean

Xóa dữ liệu đã xử lý.

```bash
python -m src.main clean [OPTIONS]
```

| Option | Shortcut | Mô tả |
|--------|----------|-------|
| `--all` | | Bao gồm models |
| `--yes` | `-y` | Skip confirmation |

```bash
# Examples
python -m src.main clean --yes
python -m src.main clean --all --yes
```

---

## init

Khởi tạo thư mục cấu trúc.

```bash
python -m src.main init
```

---

## addtag

Thêm tag vào document.

```bash
python -m src.main addtag <doc_id> <tag>
```

```bash
# Examples
python -m src.main addtag HID.pdf_p30 bluetooth
python -m src.main addtag HID.pdf_p30 "security diagram"
```

---

## listtag

Xem tags của document.

```bash
python -m src.main listtag <doc_id>
```

---

## removetag

Xóa user-added tag.

```bash
python -m src.main removetag <doc_id> <tag>
```

---

## resettags

Reset về original tags.

```bash
python -m src.main resettags <doc_id>
```

---

## addknowledge

Thêm knowledge (append).

```bash
python -m src.main addknowledge <identifier> <knowledge_text>
```

```bash
# Examples
python -m src.main addknowledge HID_p42 "State machine với 5 trạng thái"
```

---

## updateknowledge

Thay thế knowledge.

```bash
python -m src.main updateknowledge <identifier> <knowledge_text>
```

---

## getknowledge

Xem knowledge.

```bash
python -m src.main getknowledge <identifier>
```

---

## eval

Chạy retrieval evaluation.

```bash
python -m src.main eval [OPTIONS]
```

| Option | Default |
|--------|---------|
| `--dataset` | `tests/data/golden_dataset.json` |
| `--top-k` | 5 |

---

## Help

```bash
python -m src.main --help
python -m src.main process --help
python -m src.main search --help
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | CLI argument error |
