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

## Ghi chú thiết kế: collection và document facets

Không dùng cơ chế tag hiện tại của chunk để thay cho collection. Tag hiện tại
gắn với từng chunk/image, được trộn vào nội dung embedding và mỗi thay đổi đều
phải re-embed item; vì vậy nó không phù hợp để phân loại cả document hoặc làm
bộ lọc chính xác.

Hướng đề xuất là tách ba lớp metadata:

- `collection`: phạm vi quản trị/lifecycle ổn định và có thể để tùy chọn, ví dụ
  project, team hoặc knowledge base.
- `facets`: nhãn nhiều chiều ở cấp document, ví dụ `domain:wifi`,
  `topic:p2p`, `topic:hotspot`, `document_type:requirement`.
- Tag/knowledge hiện tại: enrichment cục bộ cho một chunk hoặc image nhằm cải
  thiện retrieval, không dùng làm taxonomy của document.

Document facets nên nằm trong catalog riêng (đề xuất `catalog.sqlite` dưới data
volume), liên kết chunk qua `document_id`. Thay đổi facet không re-embed và
không reindex nội dung. Search dùng facets/source để chọn candidate trước khi
FAISS và BM25 xếp hạng.

Quy ước filter đề xuất:

- Giữa các facet là `AND`.
- Nhiều giá trị trong cùng facet mặc định là `OR`; có tùy chọn `all` nếu cần.
- Vẫn hỗ trợ lọc chính xác theo `source` và `max_per_source`.

API dự kiến:

- `GET /api/v1/facets`: liệt kê facet cùng số document/chunk.
- `GET /api/v1/documents/{id}`: metadata của document.
- `PUT /api/v1/documents/{id}/facets`: cập nhật facet không re-embed.
- Upload nhận collection/facets và tạo record trong catalog.
- Search nhận collection/facets/source, trả source statistics.

Workflow của agent skill: lấy facets -> chọn phạm vi -> scoped search -> xem
source statistics -> thu hẹp vào một file khi cần.

### Ràng buộc deployment

Theo `docs/deployment/portainer.md`, mọi state phải nằm trong host folder mount
vào `/specrag`. `catalog.sqlite` vì vậy phải được lưu dưới data volume, không
nằm trong image. Giữ mô hình một RAG writer; không chạy nhiều replica dùng
chung FAISS/catalog. Thay đổi facets không cần build image hoặc reindex, còn
thay đổi backend vẫn phải phát hành prebuilt image mới cho Portainer.

## Ghi chú thiết kế: image và diagram pipeline

Hiện tại image pipeline chỉ phát hiện các trang PDF có khả năng chứa nội dung
trực quan rồi render toàn trang ở 150 DPI. Việc phát hiện dựa trên heuristic:
embedded image đủ lớn, vector drawing, caption `Figure`/`Table`/`Hình`/`Bảng`
hoặc nhiều line/rectangle. Hệ thống chưa crop riêng figure/table và chưa xử lý
ảnh nhúng trong DOCX/PPTX.

Bitmap không được embedding trực tiếp. Image item được tìm bằng caption, tag và
tối đa 10.000 ký tự text lấy từ trang PDF. `image_path`, `source_file`, page và
metadata được trả về để vision-capable agent tự xem ảnh. Gauss vision analysis
chỉ là script enrichment tùy chọn, không nằm trong ingestion/API hoặc Docker
production mặc định.

Các vấn đề cần xử lý:

- Agent gọi server từ xa không đọc được container-local `image_path`; cần API
  trả image bytes/URL có authentication, MIME type và cache headers.
- `image_id` chỉ gồm filename và page nên hai document cùng tên có thể collision.
  Chuyển sang stable `document_id` và lưu dưới
  `extracted_images/{document_id}/page-NNNN.png`.
- Delete/re-ingest cần cleanup extracted image; hiện có thể để lại orphan files.
- Image-only search đang lấy candidate toàn kho rồi mới post-filter; phải lọc
  `content_type=image` trước khi semantic/BM25 ranking.
- Extraction failure hiện bị chuyển thành danh sách rỗng; job cần báo trạng thái
  text/image riêng thay vì thành công im lặng.
- Bổ sung test cho page detection, caption/metadata, collision, cleanup,
  image-only prefilter và image serving.

Hướng triển khai:

1. Làm chắc lifecycle: stable ID, scoped storage, image endpoint, cleanup,
   prefilter và test.
2. Cải thiện CPU pipeline: liên kết caption/clause/page, crop figure/table nhưng
   giữ full-page context, OCR tùy chọn cho scanned PDF, index caption/OCR bằng
   FTS5.
3. Để agent vision xem 1-3 ảnh top đầu qua API và chỉ ghi knowledge sau khi xác
   minh. Giữ vision analysis thành optional enrichment worker; không đưa vision
   model nặng vào RAG container mặc định.

Mọi image asset và metadata bền vững phải nằm dưới `/specrag` theo layout
Portainer. Không lưu state trong Docker image/container filesystem.

## P0: NUMA affinity cho server dual-socket

Server production dùng 2 x Intel Xeon E5-2690 v2. Cấu hình hiện tại chỉ đặt
`cpus: 4` cho embedding và `cpus: 2` cho RAG; đây là CPU quota, không pin process
vào logical CPU/socket cụ thể. Không có `cpuset`, NUMA binding hoặc cấu hình
OpenMP/MKL affinity trong image/Compose. Vì vậy embedding threads có thể chạy
trên cả hai socket và phát sinh remote-NUMA memory traffic.

Việc cần làm trước khi sửa Compose:

1. Lấy topology thật trên production bằng
   `lscpu -e=CPU,NODE,SOCKET,CORE,ONLINE` và `numactl --hardware`; không giả định
   CPU ID liên tục hoặc giống máy development.
2. Chọn các physical core thuộc cùng một NUMA node, tránh chọn hai hyper-thread
   sibling nếu mục tiêu là bốn core vật lý.
3. Thêm `cpuset` cho embedding trong Portainer Compose; cân nhắc pin RAG/FAISS
   vào socket còn lại để tránh tranh chấp.
4. Đặt rõ số tokenizer/runtime threads phù hợp với cpuset; benchmark trước/sau
   bằng cùng batch/query corpus.
5. Xác minh container thực tế qua `docker inspect`,
   `/proc/1/status` (`Cpus_allowed_list`, `Mems_allowed_list`) và cgroup
   `cpuset.cpus.effective`/`cpuset.mems.effective`.

Nếu cần bind memory node nghiêm ngặt, chỉ `cpuset` CPU là chưa đủ: dùng
`--cpuset-mems` ở Docker Engine hoặc một derived embedding image/entrypoint có
`numactl --cpunodebind --membind`. Portainer Compose hỗ trợ `cpuset` cho CPU;
không hard-code phương án memory binding trước khi xác nhận khả năng của phiên
bản Docker/Portainer đang deploy.
