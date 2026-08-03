# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Giáp Hoàng Thịnh
**Nhóm:** Nhà thám hiểm
**Ngày:** 03/08/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là hai vector embedding có hướng gần nhau, thường cho thấy hai văn bản có nội dung hoặc ý nghĩa ngữ nghĩa tương đồng. Giá trị càng gần 1 thì mức tương đồng càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: Người mua có thể yêu cầu trả hàng và hoàn tiền trên Shopee.
- Câu B: Khách hàng được gửi yêu cầu hoàn tiền khi muốn trả lại sản phẩm.
- Tại sao tương đồng: Hai câu diễn đạt cùng một ý về việc người mua yêu cầu trả hàng và nhận hoàn tiền, dù sử dụng từ ngữ khác nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Người bán phải đóng gói sản phẩm đúng quy định trước khi vận chuyển.
- Câu B: Hôm nay thời tiết có mưa lớn vào buổi chiều.
- Tại sao khác: Hai câu thuộc hai chủ đề không liên quan, một câu nói về quy định vận chuyển thương mại điện tử và câu còn lại nói về thời tiết.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine similarity tập trung vào hướng của vector nên phản ánh tốt hơn sự tương đồng ngữ nghĩa và ít bị ảnh hưởng bởi độ lớn vector. Khoảng cách Euclid phụ thuộc cả hướng lẫn độ lớn, vì vậy hai vector cùng nghĩa nhưng khác độ lớn vẫn có thể bị đánh giá là xa nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* Bước trượt là `500 - 50 = 450` ký tự. Số chunk là `ceil((10.000 - 500) / 450) + 1 = ceil(21,11) + 1 = 23`.
> *Đáp án:* 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100, bước trượt còn `500 - 100 = 400`, nên số chunk là `ceil((10.000 - 500) / 400) + 1 = 25`. Overlap lớn hơn giúp giữ ngữ cảnh ở ranh giới giữa hai chunk, nhưng làm tăng số vector, dung lượng lưu trữ và chi phí embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex `(?<=[.!?])\s+` để tách tại khoảng trắng ngay sau dấu `.`, `!` hoặc `?`, nhờ đó dấu câu vẫn nằm ở cuối câu trước. Sau khi tách, tôi `strip()` từng câu, bỏ phần rỗng rồi gom tối đa `max_sentences_per_chunk` câu bằng một dấu cách; text rỗng trả về `[]`.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử separator theo thứ tự ưu tiên đoạn `\n\n`, dòng `\n`, câu `. `, từ và cuối cùng là ký tự. Nếu một phần vẫn dài hơn `chunk_size`, `_split` gọi đệ quy với separator ưu tiên thấp hơn; hai base case là text đã đủ ngắn, hoặc đã hết separator/đến separator rỗng thì cắt fixed-size để bảo đảm kết thúc.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` biến mỗi `Document` thành một record gồm ID chunk duy nhất, content, bản sao metadata và embedding, sau đó lưu vào danh sách in-memory `_store`. `search` tạo query embedding đúng một lần, tính dot product với embedding của từng record, sắp xếp score giảm dần rồi trả tối đa `top_k` kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc record trước bằng cách yêu cầu mọi cặp key/value trong `metadata_filter` khớp metadata, sau đó mới xếp hạng tập ứng viên bằng `_search_records`. `delete_document` loại toàn bộ record có `metadata['doc_id']` bằng ID tài liệu gốc và trả `True` khi có ít nhất một record bị xóa, ngược lại trả `False`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `answer` gọi store để lấy top-k chunk, đánh số từng chunk dạng `[1]`, `[2]` và kèm `doc_id` cùng `source_url`/`source` để truy vết. Prompt gồm chỉ dẫn chỉ sử dụng context, yêu cầu nói rõ khi thiếu thông tin, phần `Context`, `Question` và nhãn `Answer:`; nếu store không trả kết quả thì agent thông báo ngay mà không gọi LLM.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
==================================================== test session starts ====================================================
platform win32 -- Python 3.12.0, pytest-9.1.1, pluggy-1.6.0 -- d:\K4-Day07-Data-Foundations-2A202601492-GiapHoangThinh\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\K4-Day07-Data-Foundations-2A202601492-GiapHoangThinh
plugins: anyio-4.14.2
collected 48 items                                                                                                           

tests/test_heading_chunker.py::test_splits_markdown_sections_and_keeps_headings PASSED                                 [  2%]
tests/test_heading_chunker.py::test_keeps_preamble_as_its_own_chunk PASSED                                             [  4%]
tests/test_heading_chunker.py::test_repeats_heading_context_when_section_is_too_long PASSED                            [  6%]
tests/test_heading_chunker.py::test_ignores_heading_syntax_inside_fenced_code PASSED                                   [  8%]
tests/test_heading_chunker.py::test_empty_text_returns_empty_list PASSED                                               [ 10%]
tests/test_heading_chunker.py::test_preserves_hash_inside_heading_title PASSED                                         [ 12%]
tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED                                  [ 14%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED                                           [ 16%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED                                    [ 18%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED                                     [ 20%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED                                          [ 22%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED                          [ 25%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED                                [ 27%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED                                 [ 29%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED                               [ 31%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED                                                 [ 33%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED                                 [ 35%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED                                            [ 37%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED                                        [ 39%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED                                                  [ 41%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED                         [ 43%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED                             [ 45%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED                       [ 47%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED                             [ 50%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED                                                 [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED                                   [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED                                     [ 56%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED                                           [ 58%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED                                [ 60%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED                                  [ 62%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED                      [ 64%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED                                   [ 66%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED                                            [ 68%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED                                           [ 70%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED                                      [ 72%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED                                  [ 75%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED                             [ 77%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED                                 [ 79%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED                                       [ 81%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED                                 [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED              [ 85%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED                            [ 87%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED                           [ 89%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED               [ 91%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED                          [ 93%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED                   [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED         [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED             [100%]

==================================================== 48 passed in 0.12s =====================================================
(.venv) PS D:\K4-Day07-Data-Foundations-2A202601492-GiapHoangThinh> 
```

**Số lượng bài test vượt qua (pass):** __ / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Người mua có thể hủy đơn ở trạng thái Chờ xác nhận. | Đơn Chờ xác nhận có thể được người mua hủy ngay. | cao | 0,606197 | Đúng |
| 2 | Người mua gửi yêu cầu trả hàng và hoàn tiền. | Khách hàng đề nghị hoàn tiền khi trả lại sản phẩm. | cao | 0,492137 | Đúng |
| 3 | Người bán không được đăng bán sản phẩm bị cấm. | Hôm nay trời mưa lớn vào buổi chiều. | thấp | 0,439318 | Đúng |
| 4 | Phí xử lý giao dịch của người bán là 6%. | Tiền hoàn qua thẻ có thể mất 7–14 ngày làm việc. | thấp | 0,347335 | Đúng |
| 5 | Người bán phải đóng gói hàng đúng quy định. | Sản phẩm cần được người bán đóng gói phù hợp trước khi giao vận. | cao | 0,653520 | Đúng |

Các điểm thực tế được tính từ embedding 768 chiều của model `openai/text-embedding-3-small` qua OpenRouter. Vì cosine similarity không có một ngưỡng cao/thấp phổ quát, tôi đánh giá dự đoán theo thứ hạng tương đối: ba cặp dự đoán cao là ba điểm cao nhất và hai cặp dự đoán thấp là hai điểm thấp nhất.

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 4 bất ngờ nhất vì cả hai câu đều thuộc chính sách Shopee và đều chứa số liệu, nhưng điểm 0,347335 lại thấp hơn cả cặp ghép chính sách sản phẩm cấm với thời tiết. Điều này cho thấy embedding chú trọng quan hệ ngữ nghĩa cụ thể hơn việc hai câu chỉ cùng miền từ vựng; “phí giao dịch của người bán” và “thời gian hoàn tiền của người mua” là hai ý khác nhau. Các điểm cũng nên được so sánh tương đối trong cùng một model thay vì dùng một ngưỡng tuyệt đối cho mọi bài toán.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Người mua có thể hủy đơn hàng trên Shopee trong những trường hợp nào? | `shopee-buyer-cancel-order`, chunk 4: lưu ý chỉ được hủy một lần và không thể tiếp tục hủy nếu yêu cầu bị từ chối. | 0,792203 | Có liên quan, nhưng chưa chứa đầy đủ các trạng thái cho phép hủy. | Trả lời đúng trường hợp SPX Express và nêu việc hủy phụ thuộc trạng thái với đơn vị vận chuyển khác, nhưng thiếu chi tiết Chờ xác nhận/Chờ lấy hàng. |
| 2 | Phí xử lý giao dịch trên Shopee là bao nhiêu và được tính như thế nào cho người bán? | `shopee-seller-responsibilities-fees`, chunk 5: phí xử lý giao dịch được cấn trừ trước khi tiền vào số dư người bán và phụ thuộc phương thức thanh toán. | 0,743673 | Có liên quan, nhưng thiếu mức 6% và công thức. | Trả lời được cách cấn trừ, nhưng không nêu mức 6% và nhầm sang công thức Phí Cố Định nên chưa khớp gold answer. |
| 3 | Thời gian hoàn tiền khi người mua trả hàng trên Shopee là bao lâu tùy thuộc vào phương thức thanh toán? | `shopee-buyer-return-request`, chunk 4: thời gian xử lý yêu cầu trả hàng/hoàn tiền khoảng 3–5 ngày làm việc. | 0,719266 | Không; đây là thời gian xử lý yêu cầu, không phải thời gian tiền hoàn về theo phương thức thanh toán. | Nhờ chunk đúng xuất hiện ở hạng 3, agent vẫn liệt kê đúng thời gian hoàn tiền cho COD/QR, ngân hàng, ShopeePay, NAPAS, thẻ, Apple Pay, Google Pay và SPayLater. |
| 4 | Kể tên 5 nhóm sản phẩm bị cấm bán tiêu biểu trên Shopee và cho biết người bán có thể bị xử lý như thế nào khi vi phạm? | `shopee-seller-listing-rules`, chunk 31: các biện pháp xử lý khi người bán vi phạm quy định đăng bán. | 0,703287 | Liên quan một phần về xử lý vi phạm, nhưng sai tài liệu kỳ vọng và không chứa danh sách sản phẩm cấm. | Nêu đúng phần lớn biện pháp xử lý, nhưng 5 nhóm sản phẩm được liệt kê khác gold answer nên câu trả lời chỉ đúng một phần. |
| 5 | Người mua cần làm gì khi muốn gửi yêu cầu trả hàng/hoàn tiền trên Shopee? | `shopee-buyer-return-request`, chunk 3: quy trình gửi yêu cầu tại mục Trò Chuyện Với Shopee. | 0,843476 | Có, đúng tài liệu và đúng quy trình được hỏi. | Trả lời đúng hai cách gửi yêu cầu và các bước chính tại trang đơn hàng hoặc Trò Chuyện Với Shopee; chưa nhắc thời gian xử lý 3–5 ngày. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> *Viết 2-3 câu:*

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | / 5 |
| Hướng tiếp cận của tôi (My Approach) | / 10 |
| Hoàn thiện code (Core Implementation — tests) | / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | / 5 |
| Kết quả truy xuất của tôi (Competition Results) | / 10 |
| **Tổng phần cá nhân** | **/ 60** |
