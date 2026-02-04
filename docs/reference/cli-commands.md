# 💻 CLI Commands Reference

## Cú Pháp Chung

```bash
specrag <command> [options] [arguments]
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
specrag process [OPTIONS]
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
specrag process -fp
specrag process -dl
specrag process -fp --format jpeg
specrag process --no-images
```

---

## search

Tìm kiếm semantic.

```bash
specrag search "query" [OPTIONS]
```

| Option | Shortcut | Mô tả | Default |
|--------|----------|-------|---------|
| `--top-k` | `-k` | Số kết quả | 5 |
| `--hybrid` | `-hy` | BM25 + Vector | off |
| `--pic` | `-pic` | Images only | off |
| `--no-save` | | Không lưu logs | off |

```bash
# Examples
specrag search "authentication"
specrag search -hy "Figure 4.1"
specrag search -pic "state machine"
specrag search -k 10 "connection"
```

---

## msearch

Multi-query search với RRF fusion.

```bash
specrag msearch "query1" "query2" [...] [OPTIONS]
```

| Option | Shortcut | Mô tả | Default |
|--------|----------|-------|---------|
| `--top-k` | `-k` | Số kết quả merged | 5 |
| `--hybrid` | `-hy` | BM25 + Vector | off |
| `--pic` | `-pic` | Images only | off |
| `--no-save` | | Không lưu logs | off |

```bash
# Examples
specrag msearch "reconnection" "link loss" "timeout"
specrag msearch -hy "Figure 4.1" "Media payload"
```

---

## list

Liệt kê documents đã index.

```bash
specrag list
```

---

## stats

Thống kê database.

```bash
specrag stats
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
specrag clean [OPTIONS]
```

| Option | Shortcut | Mô tả |
|--------|----------|-------|
| `--all` | | Bao gồm models |
| `--yes` | `-y` | Skip confirmation |

```bash
# Examples
specrag clean --yes
specrag clean --all --yes
```

---

## init

Khởi tạo thư mục cấu trúc.

```bash
specrag init
```

---

## addtag

Thêm tag vào document.

```bash
specrag addtag <doc_id> <tag>
```

```bash
# Examples
specrag addtag HID.pdf_p30 bluetooth
specrag addtag HID.pdf_p30 "security diagram"
```

---

## listtag

Xem tags của document.

```bash
specrag listtag <doc_id>
```

---

## removetag

Xóa user-added tag.

```bash
specrag removetag <doc_id> <tag>
```

---

## resettags

Reset về original tags.

```bash
specrag resettags <doc_id>
```

---

## addknowledge

Thêm knowledge (append).

```bash
specrag addknowledge <identifier> <knowledge_text>
```

```bash
# Examples
specrag addknowledge HID_p42 "State machine với 5 trạng thái"
```

---

## updateknowledge

Thay thế knowledge.

```bash
specrag updateknowledge <identifier> <knowledge_text>
```

---

## getknowledge

Xem knowledge.

```bash
specrag getknowledge <identifier>
```

---

## eval

Chạy retrieval evaluation.

```bash
specrag eval [OPTIONS]
```

| Option | Default |
|--------|---------|
| `--dataset` | `tests/data/golden_dataset.json` |
| `--top-k` | 5 |

---

## Help

```bash
specrag --help
specrag process --help
specrag search --help
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | CLI argument error |
