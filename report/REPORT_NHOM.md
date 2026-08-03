# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Nhà thám hiểm
**Thành viên:** Nguyễn Trần Gia Phụng, Giáp Hoàng Thịnh, Đặng Văn Nhân, Nguyễn Trương Ngọc Mai, Trần Bá Lợi
**Ngày:** 03/08/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Phạm vi bộ tài liệu (Scope)

**Chủ đề (cố định theo lớp K4):** Chính sách thương mại điện tử / hỗ trợ khách hàng (thanh toán, đổi trả, giao hàng, quyền riêng tư, điều kiện người bán…).

**Phạm vi cụ thể nhóm tập trung:**
> Chính sách e-commerce của Shopee Việt Nam — 10 tài liệu bao gồm chính sách hủy đơn, hoàn tiền, trả hàng, phí người bán, sản phẩm cấm, đăng bán, vận chuyển, chống gian lận và phương thức thanh toán.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | shopee-buyer-cancel-order | https://help.shopee.vn/portal/4/article/79182 | 2026-08-03 / `not-stated` | 1.991 | `customer_role: buyer`, `category: order-cancellation`, `language: vi` |
| 2 | shopee-buyer-payment-methods | https://help.shopee.vn/portal/4/article/79198 | 2026-08-03 / `not-stated` | 5.786 | `customer_role: buyer`, `category: payment`, `language: vi` |
| 3 | shopee-buyer-refund-time | https://help.shopee.vn/portal/4/article/189473 | 2026-08-03 / `not-stated` | 3.453 | `customer_role: buyer`, `category: refund-timeline`, `language: vi` |
| 4 | shopee-buyer-return-request | https://help.shopee.vn/portal/4/article/79233 | 2026-08-03 / `not-stated` | 2.240 | `customer_role: buyer`, `category: return-refund-procedure`, `language: vi` |
| 5 | shopee-return-refund-policy | https://help.shopee.vn/portal/4/article/77251 | 2026-08-03 / v2026-03-11 | 19.337 | `customer_role: both`, `category: return-refund-policy`, `language: vi` |
| 6 | shopee-seller-antifraud | https://help.shopee.vn/portal/4/article/140097 | 2026-08-03 / v2023-12-28 | 5.889 | `customer_role: seller`, `category: seller-compliance`, `language: vi` |
| 7 | shopee-seller-listing-rules | https://help.shopee.vn/portal/4/article/77246 | 2026-08-03 / v2024-08-14 | 21.238 | `customer_role: seller`, `category: listing-policy`, `language: vi` |
| 8 | shopee-seller-prohibited-products | https://help.shopee.vn/portal/4/article/77247 | 2026-08-03 / v2025-04-28 | 12.569 | `customer_role: seller`, `category: prohibited-products`, `language: vi` |
| 9 | shopee-seller-responsibilities-fees | https://help.shopee.vn/portal/4/article/77243 | 2026-08-03 / v2026-05-01 | 6.731 | `customer_role: seller`, `category: seller-responsibilities-fees`, `language: vi` |
| 10 | shopee-shipping-policy | https://help.shopee.vn/portal/4/article/77250 | 2026-08-03 / v2026-03-20 | 23.986 | `customer_role: both`, `category: shipping-policy`, `language: vi` |

Số ký tự được tính trên phần nội dung thực tế đưa vào chunker, sau khi loại YAML front matter. Ngoài các trường hữu ích hiển thị trong cột cuối, mọi tài liệu đều có `doc_id`, `source_url`, `retrieved_at`, `document_version` và `license_or_permission`.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ. Tất cả 10 tài liệu là trang hỗ trợ công khai của Shopee (help.shopee.vn).
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `shopee-buyer-cancel-order` | Định danh duy nhất tài liệu, dùng để filter và traceability |
| `source_url` | string | `https://help.shopee.vn/portal/4/article/79182` | Truy vết nguồn gốc, kiểm chứng thông tin |
| `retrieved_at` | string | `2026-08-03` | Xác định thời điểm lấy dữ liệu, đảm bảo tính cập nhật |
| `document_version` | string | `2026-03-11` hoặc `not-stated` | Đánh giá phiên bản hiệu lực, quan trọng với chính sách thay đổi định kỳ |
| `customer_role` | string | `buyer` hoặc `seller` | Lọc kết quả theo vai trò khách hàng, giúp retrieval tập trung đúng nhóm tài liệu |
| `category` | string | `order-cancellation` | Thu hẹp kết quả theo chủ đề chính sách cụ thể |
| `language` | string | `vi` | Hỗ trợ chọn đúng ngôn ngữ khi corpus được mở rộng |
| `license_or_permission` | string | `public-page-review-required` | Xác nhận quyền sử dụng dữ liệu |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare(text, chunk_size=400)` trên phần nội dung của 2 tài liệu sau khi parse YAML front matter:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| shopee-buyer-cancel-order | FixedSizeChunker (`fixed_size`) | 6 | 373,5 chars | Trung bình — độ dài ổn định nhưng có thể cắt giữa điều kiện |
| shopee-buyer-cancel-order | SentenceChunker (`by_sentences`) | 2 | 994,5 chars | Giữ câu hoàn chỉnh nhưng chunk quá dài do nhiều dòng/bullet không kết thúc bằng dấu câu |
| shopee-buyer-cancel-order | RecursiveChunker (`recursive`) | 20 | 97,7 chars | Tách được theo ranh giới tự nhiên nhưng tạo nhiều chunk ngắn |
| shopee-buyer-cancel-order | HeadingChunker (`by_heading`) | 14 | 160,0 chars | Giữ tiêu đề trong từng chunk, giúp bảo toàn ngữ cảnh mục; các section dài vẫn được tách nhỏ |
| shopee-buyer-cancel-order | SemanticChunker (`semantic`) | 9 | 219,9 chars | Gom các câu gần nghĩa và tách khi chuyển chủ đề; chất lượng phụ thuộc embedding và ngưỡng similarity |
| shopee-seller-prohibited-products | FixedSizeChunker (`fixed_size`) | 36 | 397,8 chars | Độ dài đồng đều nhưng một số danh sách có thể bị cắt ngang |
| shopee-seller-prohibited-products | SentenceChunker (`by_sentences`) | 35 | 356,3 chars | Giữ câu khá tốt; bullet không có dấu kết câu vẫn có thể bị gom dài |
| shopee-seller-prohibited-products | RecursiveChunker (`recursive`) | 230 | 53,1 chars | Phân mảnh mạnh do tài liệu có nhiều dòng và bullet ngắn |
| shopee-seller-prohibited-products | HeadingChunker (`by_heading`) | 226 | 112,0 chars | Giữ được heading nhưng tạo nhiều chunk do tài liệu có nhiều mục và bullet ngắn |
| shopee-seller-prohibited-products | SemanticChunker (`semantic`) | 108 | 114,7 chars | Tách theo chuyển đổi ngữ nghĩa, giảm phân mảnh so với Recursive nhưng cần tính embedding |

Các số liệu trên được tạo từ corpus hiện tại với `chunk_size=400`; SemanticChunker dùng `threshold=0.3` và mock embedding mặc định để phép so sánh có thể tái lập mà không gọi dịch vụ ngoài. Vì năm chiến lược xử lý heading, bảng và bullet Markdown khác nhau, số lượng chunk chênh lệch đáng kể.

### Chiến lược của từng thành viên

**Thành viên 1 — Nguyễn Trần Gia Phụng**
- **Loại chiến lược:** SentenceChunker (`max_sentences_per_chunk=3`)
- **Mô tả & lý do chọn cho chủ đề này:** Tách văn bản thành câu bằng regex `(?<=[.!?])\s+`, gom 3 câu liên tiếp thành 1 chunk. Lý do: chính sách Shopee viết dạng điều khoản — mỗi câu là một quy định hoàn chỉnh. Giữ câu nguyên vẹn giúp retrieval tìm đúng điều khoản mà không bị mất ngữ cảnh do cắt giữa dòng.

**Thành viên 2 — Giáp Hoàng Thịnh**
- **Loại chiến lược:** HeadingChunker / HierarchicalChunker (`chunk_size=400`→`500`)
- **Mô tả & lý do chọn cho chủ đề này:** Tách văn bản theo cấu trúc heading Markdown (`#`, `##`, `###`), giữ đường dẫn heading đầy đủ (vd: `## 16.3 Phí Xử Lý Giao Dịch > ...`) trong mỗi chunk. Section quá dài → fallback recursive split nhưng vẫn gắn heading vào mỗi mảnh con. Lý do: tài liệu Shopee có cấu trúc phân cấp rõ ràng — giữ ngữ cảnh heading giúp LLM biết chính xác chunk nằm ở đâu trong tài liệu.

**Thành viên 3 — Đặng Văn Nhân**
- **Loại chiến lược:** SemanticChunker (`similarity_threshold=0.70`, `max_sentences=5`)
- **Mô tả & lý do chọn cho chủ đề này:** Tách câu, nhúng từng câu rồi tính cosine similarity giữa hai câu liền kề. Nếu similarity < 0.70 → mở chunk mới (điểm chuyển chủ đề). Lý do: văn bản chính sách có đoạn chuyển chủ đề đột ngột (từ "hủy đơn" sang "hoàn tiền"), SemanticChunker tự động tìm các điểm chuyển này thay vì dựa vào độ dài cố định.

**Thành viên 4 — Nguyễn Trương Ngọc Mai**
- **Loại chiến lược:** FixedSizeChunker (`chunk_size=400`, `overlap=50`)
- **Mô tả & lý do chọn cho chủ đề này:** Chia văn bản thành các đoạn cố định 400 ký tự, mỗi đoạn liền kề overlap 50 ký tự. Lý do: đơn giản, reproducible, overlap giúp giảm rủi ro thông tin bị cắt ở rìa chunk. Phù hợp làm baseline để so sánh với các chiến lược phức tạp hơn.

**Thành viên 5 — Trần Bá Lợi**
- **Loại chiến lược:** RecursiveChunker (`chunk_size=500`)
- **Mô tả & lý do chọn cho chủ đề này:** Thử separator theo thứ tự ưu tiên `\n\n` → `\n` → `. ` → ` ` → `""`, gộp dần vào chunk vừa `chunk_size`. Lý do: tài liệu Shopee có cấu trúc phân đoạn rõ (heading, bullet list a)/b)/c), câu điều khoản dài) — Recursive tận dụng đúng cấu trúc đó, ưu tiên giữ trọn đoạn/câu thay vì cắt cứng theo ký tự. Sau tuning, `chunk_size=500` cho kết quả tốt nhất (cải thiện từ 4/5 lên 5/5 câu đúng top-3).

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Số chunks | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|-------------|----------------------|-----------|----------|
| Phụng | SentenceChunker (3 câu/chunk) | 212 | 7 | Hit@3 5/5; Q1, Q2, Q4 và Q5 đúng nguồn ở top-1; Q1–Q2 trả lời đúng gold answer | Q3 đúng nguồn ở hạng 2; Q4 trả lời sai/bị ngắt; Q5 thiếu bước và mốc xử lý 3–5 ngày |
| Thịnh | HeadingChunker | 162 | 5 | Giữ ngữ cảnh heading; index nhỏ nhất; Hit@3 5/5; Q1, Q2 và Q5 đúng nguồn ở top-1 | Theo bảng kết quả cá nhân, cả 5 câu đều chỉ đúng một phần hoặc đúng nguồn không ở top-1: Q1–Q2 thiếu dữ kiện, Q3 đúng nguồn ở hạng 3, Q4 lệch danh sách, Q5 thiếu mốc 3–5 ngày |
| Nhân | SemanticChunker | 583 | 9 | Hit@3 5/5 và đúng nguồn top-1 5/5; Q1, Q2, Q3 và Q5 có đủ bằng chứng để trả lời | Q4 top-1 đúng nguồn nhưng chunk truy xuất chưa chứa đủ 5 nhóm hàng; index lớn nhất và cần embedding trong bước chunking |
| Mai | FixedSizeChunker (400, overlap=50) | 299 | 5 | Đơn giản, reproducible; Hit@3 5/5; Q1, Q2, Q3 và Q5 đúng nguồn ở top-1 | Cả 5 câu trả lời mới bao phủ một phần gold answer: Q1 thiếu trạng thái ngoài SPX; Q2 thiếu 6% và công thức; Q3 thiếu một số phương thức; Q4 thiếu 5 nhóm hàng; Q5 thiếu các bước khai báo/bằng chứng |
| Lợi | RecursiveChunker (size=500) | 278 | 8 | Hit@3 5/5; Q2, Q3 và Q5 đúng nguồn ở top-1 và Agent trả lời đúng | Q1 và Q4 có đúng nguồn ở hạng 3 nên chỉ đạt 1 điểm/câu; Q4 còn lệch gold answer do hai kết quả còn lại lấy từ `seller-listing-rules` |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> **SemanticChunker (Nhân)** đạt kết quả cao nhất: **9/10**, Hit@3 5/5 và đúng nguồn top-1 5/5; điểm bị trừ ở Q4 vì context chưa bao phủ đủ danh sách 5 nhóm sản phẩm. RecursiveChunker của Lợi đứng thứ hai với **8/10** và 278 chunk. SentenceChunker của Phụng đạt **7/10** với 212 chunk. HeadingChunker của Thịnh và FixedSizeChunker của Mai cùng đạt **5/10**: cả hai đều Hit@3 5/5 nhưng câu trả lời còn thiếu dữ kiện. **Kết luận: SemanticChunker có chất lượng cao nhất trong benchmark; RecursiveChunker là phương án cân bằng hơn giữa điểm số và kích thước index.** Không nên chọn chiến lược chỉ dựa vào cosine score top-1 hoặc số chunk.
---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng và có thể kiểm chứng. Q2–Q5 được chạy với metadata filter theo vai trò; Q1 không lọc. Đây là bộ câu hỏi chung cho mọi thành viên.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người mua có thể hủy đơn hàng trên Shopee trong những trường hợp nào? | Đơn SPX Express: hủy ngay nếu chưa đến trạm (áp dụng cho một số người dùng nhất định). Đơn đơn vị khác: Chờ xác nhận → hủy ngay; Chờ lấy hàng → cần người bán chấp nhận. Chỉ hủy được 1 lần/đơn. | `shopee-buyer-cancel-order` |
| 2 | Phí xử lý giao dịch trên Shopee là bao nhiêu và được tính như thế nào cho người bán? | Phí = 6% tất cả phương thức thanh toán. Cách tính: (Giá sản phẩm trước trợ giá + Phí vận chuyển người mua trả - Khuyến mãi người bán - Khuyến mãi ngân hàng) × 6% (đã bao gồm GTGT). Cấn trừ trước khi tiền vào số dư người bán. | `shopee-seller-responsibilities-fees` |
| 3 | Thời gian hoàn tiền khi người mua trả hàng trên Shopee là bao lâu tùy thuộc vào phương thức thanh toán? | COD/QR/Ứng dụng ngân hàng → Ví ShopeePay trong 24 giờ hoặc tài khoản ngân hàng mặc định đã liên kết trong 2 ngày làm việc; riêng Ứng dụng ngân hàng hoàn về tài khoản ngân hàng ban đầu trong 7 ngày làm việc. Ví ShopeePay: 24 giờ. Thẻ nội địa NAPAS: 2–5 ngày làm việc. Thẻ tín dụng/ghi nợ và Apple Pay/Google Pay: 7–14 ngày làm việc. SPayLater: 24 giờ; với thanh toán kết hợp SPayLater, phần SPayLater được hoàn về số dư khả dụng trong 24 giờ hoặc hóa đơn trong 3–5 ngày làm việc. | `shopee-buyer-refund-time` |
| 4 | Kể tên 5 nhóm sản phẩm bị cấm bán tiêu biểu trên Shopee và cho biết người bán có thể bị xử lý như thế nào khi vi phạm? | 5 nhóm tiêu biểu: (1) Hàng vi phạm bản quyền/sở hữu trí tuệ; (2) Thiết bị, trang phục quân đội/lực lượng thi hành pháp luật và chính phủ; (3) Tài liệu phản động hoặc thông tin xâm phạm an ninh quốc gia; (4) Dịch vụ bất hợp pháp; (5) Súng, vũ khí và sản phẩm có hình dạng giống vũ khí. Khi vi phạm, sản phẩm có thể bị xóa; tài khoản có thể bị giới hạn quyền, đình chỉ hoặc xóa; số dư có thể bị cấn trừ và quyền rút tiền có thể bị phong tỏa; người bán còn có thể chịu chế tài khác theo chính sách Shopee hoặc pháp luật. | `shopee-seller-prohibited-products` |
| 5 | Người mua cần làm gì khi muốn gửi yêu cầu trả hàng/hoàn tiền trên Shopee? | Cách 1 — tại trang đơn hàng: Tôi → Chờ giao hàng/Đã giao → chọn đơn → Trả hàng/Hoàn tiền → chọn tình huống, sản phẩm và lý do → điền mô tả, bằng chứng, email → Gửi yêu cầu. Cách 2 — tại Trò Chuyện Với Shopee: Tôi → Trò Chuyện Với Shopee → Khiếu nại trả hàng hoàn tiền → chọn đơn → xác nhận tình trạng nhận hàng → chọn lý do → tải bằng chứng → Gửi yêu cầu. Yêu cầu thường được xử lý trong khoảng 3–5 ngày làm việc. | `shopee-buyer-return-request` |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Người mua có thể hủy đơn hàng | **SentenceChunker (Phụng)** — đúng nguồn top-1, Agent trả lời đủ các trạng thái chính | ✅ 5/5 chiến lược | HeadingChunker có score top-1 cao hơn (0,7922) nhưng câu trả lời thiếu chi tiết Chờ xác nhận/Chờ lấy hàng; vì vậy không được xem là tốt nhất theo rubric |
| 2 | Phí xử lý giao dịch | **SemanticChunker (Nhân)** — đúng nguồn top-1; top-2 bổ sung mức phí và cách tính | ✅ 5/5 chiến lược | SentenceChunker và RecursiveChunker cũng trả lời đúng; HeadingChunker và FixedSizeChunker thiếu mức 6% hoặc công thức |
| 3 | Thời gian hoàn tiền | **RecursiveChunker (Lợi)** — đúng nguồn top-1, Agent trả lời đúng theo phương thức | ✅ 5/5 chiến lược | SemanticChunker cũng đúng nguồn top-1 và có thêm trường hợp SPayLater; FixedSizeChunker có score cao hơn (0,7382) nhưng thiếu NAPAS, thẻ và SPayLater |
| 4 | 5 nhóm sản phẩm cấm + xử lý | **SemanticChunker (Nhân)** — đúng nguồn top-1 nhưng coverage vẫn chưa đủ | ✅ 5/5 chiến lược | Không chiến lược nào trả lời trọn vẹn gold answer. SemanticChunker đứng đầu vì đúng nguồn ở top-1 và lấy được phần chế tài; vẫn chỉ đạt 1 điểm do thiếu đủ 5 nhóm hàng |
| 5 | Gửi yêu cầu trả hàng/hoàn tiền | **SemanticChunker (Nhân)** — đúng nguồn top-1 (0,8331), top-1 và top-3 bao phủ hai luồng thực hiện | ✅ 5/5 chiến lược | RecursiveChunker cũng trả lời đúng và đủ với top-1 0,825; HeadingChunker có score cao hơn (0,8435) nhưng thiếu mốc xử lý 3–5 ngày; SentenceChunker và FixedSizeChunker thiếu một số bước |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

> Metadata filter `customer_role` thu hẹp không gian tìm kiếm ở **Q2 và Q4** (lọc `seller`) và **Q3 và Q5** (lọc `buyer`). Ví dụ, Q2 loại các tài liệu chỉ dành cho người mua như `buyer-return-request` và `buyer-refund-time`. Filter chỉ đáng tin cậy khi metadata được gán đúng; nếu gán sai vai trò, tài liệu liên quan có thể bị loại. Kết quả của Mai cũng cho thấy sau khi lọc, Q2, Q3 và Q5 đều đưa đúng tài liệu lên top-1; tuy nhiên benchmark hiện không có lượt đối chứng bỏ filter nên chưa thể định lượng riêng mức cải thiện. Q1 không dùng filter nhằm kiểm tra retrieval trên toàn corpus, dù câu hỏi hướng rõ đến người mua.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. **Nhiều chunk hơn không tự động cho câu trả lời đầy đủ hơn:** SemanticChunker tạo 583 chunk, SentenceChunker tạo 212 và HeadingChunker tạo 162; cả ba đều đạt Hit@3 5/5, nhưng điểm theo rubric lần lượt là 9, 7 và 5. Chênh lệch đến từ coverage, vị trí chunk đúng và khả năng tổng hợp câu trả lời, không chỉ số lượng chunk.
> 2. **Trùng lặp chủ đề giữa tài liệu là thách thức lớn:** Q4 khó vì `shopee-seller-listing-rules` cũng nói về "xử lý vi phạm", nên một số chiến lược xếp tài liệu này cao hơn `shopee-seller-prohibited-products`. Kết quả chịu ảnh hưởng đồng thời bởi corpus, chunking và embedding; không thể quy hoàn toàn cho một yếu tố.
> 3. **Hit@3 cao chưa đồng nghĩa câu trả lời đầy đủ:** FixedSizeChunker của Mai dùng cùng `text-embedding-3-small`, đạt Hit@3 5/5 và đúng nguồn top-1 ở 4/5 câu, nhưng chỉ đạt 5/10 vì mỗi chunk 400 ký tự thường không gom đủ các mục của bảng/danh sách dài. Overlap 50 ký tự giảm mất mát ở ranh giới nhưng không giải quyết được coverage khi câu hỏi cần tổng hợp nhiều phần xa nhau.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng 10 tài liệu Shopee nhưng 5 chiến lược tạo ra 162–583 chunk, chênh khoảng 3,6 lần. Tất cả đều Hit@3 5/5 nhưng điểm cuối dao động 5–9/10. Q4 là trường hợp khó nhất: SentenceChunker và SemanticChunker đưa đúng nguồn lên top-1 nhưng câu trả lời vẫn thiếu/sai, còn ba chiến lược khác ưu tiên tài liệu `seller-listing-rules` có chủ đề gần. Vì vậy cần đánh giá đồng thời đúng nguồn, thứ hạng, coverage của context và độ chính xác của Agent; Hit@3 hoặc cosine score riêng lẻ chưa đủ.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> 1. **Giảm trùng lặp giữa tài liệu:** `shopee-return-refund-policy` và `shopee-buyer-cancel-order` có nội dung chồng chéo về điều kiện hủy/đổi trả. Nếu có thể, nhóm sẽ merge hoặc tách rõ ranh giới giữa hai tài liệu này.
> 2. **Thêm metadata `section_topic`** để phân biệt các phần trong cùng tài liệu (vd: `topic: cancellation-conditions`, `topic: fee-calculation`) — giúp retrieval chính xác hơn ở câu hỏi chi tiết.
> 3. **Tăng overlap hoặc dùng heading context** — kết quả của Thịnh và Nhân cho thấy giữ ngữ cảnh vị trí (heading path) hoặc nhận diện điểm chuyển ý nghĩa là các hướng đáng thử khi cải thiện retrieval so với chunking thuần túy theo kích thước.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10 |
| Thiết kế chiến lược (Strategy Design) | 14 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 9 / 10 (theo chiến lược tốt nhất: SemanticChunker) |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **37 / 40** |
