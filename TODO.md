Hai vấn đề này nên giải quyết bằng **cùng một cơ chế**: chia tài liệu thành các **collection** theo thư mục, và cho search lọc theo collection hoặc file **trước khi xếp hạng**. Cơ chế này cũng trả lời luôn câu hỏi trước về "tìm trong một file chỉ định".

## Vấn đề 2: chia theo thư mục (p2p, bluetooth…)

**Đề xuất:** collection = thư mục con đầu tiên trong `documents/`.

```text
documents/p2p/WiFi_Direct_Spec.pdf        → collection "p2p"
documents/bluetooth/Core_v5.4.pdf          → collection "bluetooth"
```

- Ingest đã quét đệ quy (`rglob`), nên thư mục con đã được hỗ trợ sẵn.
- Collection suy ra được từ `source_file` đã lưu trong metadata, nên **không cần reindex** các file đã đúng thư mục. Chỉ khi chuyển file sang thư mục khác thì phải ingest lại file đó, vì đường dẫn nằm trong chunk id.

**Về URL, tôi khuyên không dùng `/api/v1/p2p/...`.** Tên collection sẽ dùng chung không gian URL với các route sẵn có, nên một collection tên `graph`, `tables`, `documents` hay `search` sẽ đụng route. Có hai cách an toàn:

| Cách | Ví dụ | Nhận xét |
|---|---|---|
| **Tham số trong body** (khuyên dùng) | `POST /api/v1/search {"query": …, "filters": {"collection": "p2p"}}` | Một endpoint duy nhất. SKILL chỉ cần mô tả thêm một trường. Tìm trên nhiều collection cùng lúc rất tự nhiên. |
| Đường dẫn có namespace | `POST /api/v1/collections/p2p/search` | Đúng kiểu REST, không đụng route. Nhưng mỗi API (graph, tables) đều phải nhân đôi route. |

Thêm `GET /api/v1/collections` để agent biết có những collection nào và mỗi cái có bao nhiêu file.

## Vấn đề 1: nhiều file thì output bị loãng

Nên giải quyết theo ba lớp, từ gốc đến ngọn:

1. **Thu hẹp phạm vi (giải quyết gốc rễ).** Thêm `filters.collection` và `filters.source` vào search, và lọc **trước khi xếp hạng**: chỉ chấm điểm các chunk trong phạm vi, ở cả FAISS lẫn BM25. Khi đó top_k là top của riêng phạm vi đó. Cách tạm "lấy nhiều rồi lọc" không đáng tin, vì file cần tìm có thể bị lấn át và không lọt vào top.
2. **Cho agent biết kết quả đến từ đâu.** Response có thêm thống kê theo file, ví dụ `sources: [{file, hits, best_score}]`. Agent thấy ngay file nào liên quan nhất rồi tìm tiếp trong file đó, thay vì đọc một danh sách trộn lẫn.
3. **Giới hạn số chunk mỗi file** (tuỳ chọn, ví dụ `max_per_source`). Một tài liệu khổng lồ như 802.11 (42k chunk) sẽ không chiếm hết top_k khi tìm trên nhiều file.

Cập nhật SKILL theo quy trình: gọi `collections` → chọn collection → search có phạm vi → xem `sources` → thu hẹp vào một file nếu cần.

## Tách mỗi collection thành một index riêng?

Để giai đoạn sau, chỉ làm khi thật sự cần:

- **Có lợi khi:** reindex một collection mất quá lâu (hiện cả kho là khoảng 4 giờ), hoặc RAM vượt `mem_limit` 10g vì phải nạp toàn bộ index.
- **Cái giá:** mỗi collection cần staged reindex, writer lease và fingerprint riêng. Tìm trên nhiều collection thì phải trộn kết quả giữa các index.

Với số lượng tài liệu hiện tại, một index chung có bộ lọc là đủ và ít rủi ro hơn nhiều.

## Đề xuất thực hiện

Giai đoạn 1 gồm:
- `filters.collection` và `filters.source`, lọc trước khi xếp hạng.
- `GET /api/v1/collections`.
- Thống kê `sources` trong response.
- Upload nhận tham số `collection` để lưu vào đúng thư mục.
- Cập nhật SKILL.

Cần sửa backend và có test đi kèm. Tôi chưa kiểm tra chi tiết cách `FaissVectorStore` ánh xạ ID, nên việc lọc trước trong FAISS sẽ được xác nhận khi bắt tay làm. Bạn muốn tôi bắt đầu không?