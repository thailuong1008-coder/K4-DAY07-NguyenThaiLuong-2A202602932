# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Thái Lương  
**MSSV:** 2A202602932  
**Biến thể:** K4-L3B — Truy xuất Chính sách Thương mại Điện tử  
**Nhóm:** Nhóm L3B  
**Ngày:** 20/09/2026  

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao (tiến gần về 1.0) thể hiện góc giữa hai vector embedding trong không gian đa chiều là rất nhỏ, nghĩa là hai đoạn văn bản có sự tương đồng cao về mặt ý nghĩa ngữ nghĩa (semantic similarity), bất kể độ dài hay số lượng từ của hai đoạn văn đó có chênh lệch nhau.

**Ví dụ có độ tương tự CAO:**
- **Câu A:** "Khách hàng có quyền gửi yêu cầu đổi trả sản phẩm trong vòng 15 ngày."
- **Câu B:** "Thời hạn để người mua khiếu nại hoàn trả hàng hóa là 15 ngày."
- **Tại sao tương đồng:** Cả hai câu cùng truyền tải một nội dung quy định chính sách thương mại điện tử với mốc thời gian và hành động đổi trả tương đương nhau, sử dụng các từ ngữ đồng nghĩa.

**Ví dụ có độ tương tự THẤP:**
- **Câu A:** "Khách hàng có quyền gửi yêu cầu đổi trả sản phẩm trong vòng 15 ngày."
- **Câu B:** "Dự báo thời tiết hôm nay trời nhiều mây và có mưa rào rải rác."
- **Tại sao khác:** Hai câu thuộc về hai miền chủ đề hoàn toàn độc lập (chính sách thương mại vs khí tượng học), không chia sẻ ngữ cảnh hay khái niệm chung.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid bị phụ thuộc nặng nề vào độ dài (magnitude) của vector. Một đoạn văn ngắn và một bài viết dài dù cùng nói về một chủ đề nhưng vector của bài viết dài sẽ có độ lớn lớn hơn nhiều, dẫn đến khoảng cách Euclid giữa chúng rất xa. Ngược lại, Cosine Similarity chỉ tính góc giữa hai hướng vector (đã chuẩn hóa độ dài), giúp đánh giá chính xác sự tương đồng ngữ nghĩa mà không bị thiên vị bởi độ dài văn bản.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> - Công thức: `số lượng chunk = ceil((độ_dài - overlap) / (chunk_size - overlap))`
> - Phép tính: `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> - **Đáp án:** **23 chunks**.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> - Khi `overlap = 100`: `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25` chunks (tăng thêm 2 chunks).
> - **Lý do muốn độ chồng chéo nhiều hơn:** Việc tăng overlap giúp đảm bảo các câu văn, mệnh đề số liệu hoặc các điều kiện ngoại lệ nằm ngay tại ranh giới cắt không bị đứt đoạn, giúp các chunk giữ được ngữ cảnh liền mạch cho bộ tìm kiếm vector.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Sử dụng regex lookbehind `r"(?<=[.!?])\s+|\.\n+"` để nhận diện ranh giới kết thúc câu mà không làm mất dấu câu gốc. Xử lý triệt để các trường hợp chuỗi rỗng hoặc chỉ toàn khoảng trắng bằng `strip()`, sau đó gom các câu thành từng nhóm không vượt quá `max_sentences_per_chunk` câu bằng `" ".join()`.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Triển khai thuật toán đệ quy với danh sách phân cách ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Trường hợp cơ sở (base case) là khi đoạn văn có độ dài `len(text) <= chunk_size` hoặc đã hết danh sách phân cách (fallback sang cắt ký tự). Ở mỗi bước, hàm tách text theo dấu phân cách hiện tại, đệ quy chia nhỏ các phần vượt kích thước, và cuối cùng duyệt gộp các đoạn con liền kề sao cho tổng độ dài nhỏ hơn hoặc bằng `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Lưu trữ các bản ghi trong danh sách `self._store` ở bộ nhớ RAM. Mỗi bản ghi được chuẩn hóa gồm `id`, `content`, `metadata` và vector nhúng `embedding`. Khi tìm kiếm, hàm `search` gọi `_search_records` để nhúng câu truy vấn, tính tích vô hướng (dot product) với từng bản ghi, sắp xếp điểm số giảm dần và trả về đúng `top_k` kết quả (loại bỏ vector raw để làm sạch đầu ra).

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Thực hiện lọc trước (**pre-filtering**): duyệt `self._store` và lọc ra các bản ghi thỏa mãn toàn bộ cặp key-value trong `metadata_filter` trước, sau đó mới thực hiện tìm kiếm tương đồng trên tập ứng viên này để tránh mất kết quả đúng. Hàm `delete_document` lọc bỏ mọi bản ghi có `doc_id` trùng với `metadata['doc_id']` hoặc `id`, trả về `True` nếu kích thước store giảm đi.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Gọi `store.search(question, top_k)` để lấy các chunk liên quan nhất. Định dạng các chunk thành khối ngữ cảnh có đánh số thứ tự kèm nguồn `[1] Nguồn: ...` giúp LLM dễ dàng trích dẫn nguồn (Source Traceability). Bọc trong prompt chỉ thị chặt chẽ: chỉ trả lời dựa trên ngữ cảnh được cấp và báo không tìm thấy nếu dữ liệu bị thiếu.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\AI DAY 2 -1\K4-DAY07-NguyenThaiLuong-2A202602932
plugins: anyio-4.14.1
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.12s ==============================
```

**Số lượng bài test vượt qua (pass):** **42 / 42**

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán ngữ nghĩa | Điểm thực tế (MockEmbedder) | Đúng kỳ vọng ngữ nghĩa? |
|---|---|---|---|---|---|
| 1 | "Chính sách đổi trả sản phẩm trong 15 ngày." | "Khách hàng có thể trả hàng trong vòng 15 ngày." | Cao (đồng nghĩa) | 0.0741 | Không (do MockEmbedder) |
| 2 | "Thời hạn bảo hành điện thoại là 12 tháng." | "Bảo hành máy tính bảng trong 1 năm." | Cao (đồng nghĩa) | -0.2616 | Không (do MockEmbedder) |
| 3 | "Quy định đổi trả hàng tươi sống." | "Thủ tục hoàn tiền cho đơn hàng người bán tự giao." | Trung bình (cùng sàn) | 0.0859 | Ngẫu nhiên |
| 4 | "Thời gian làm việc của tổng đài là 8h đến 21h." | "Hôm nay thời tiết Hà Nội nắng đẹp." | Thấp (khác chủ đề) | 0.0705 | Ngẫu nhiên |
| 5 | "Sản phẩm bị lỗi kỹ thuật của nhà sản xuất." | "Sản phẩm hoàn toàn bình thường không có lỗi gì." | Thấp (ngược nghĩa) | 0.0143 | Ngẫu nhiên |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là Cặp 2 mang ý nghĩa gần như trùng khớp nhưng điểm cosine lại âm (-0.2616), trong khi Cặp 4 hoàn toàn không liên quan lại có điểm dương (0.0705). Điều này phản ánh rõ bản chất của `MockEmbedder`: nó chỉ sinh vector ngẫu nhiên dựa trên mã băm MD5 của chuỗi ký tự thô chứ không hề có không gian ngữ nghĩa (semantic latent space). Trong các bài toán RAG thực tế, bắt buộc phải dùng pre-trained embedding models (như paraphrase-multilingual hay text-embedding) để ánh xạ các khái niệm tương đồng về vị trí gần nhau trong không gian vector.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên chiến lược `FixedSizeChunker(chunk_size=500, overlap=50)`:

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|---|---|---|---|---|
| 1 | Thời hạn tối đa gửi yêu cầu đổi trả thực phẩm tươi sống Shopee? | `apple-pham-vi-bao-hanh-thiet-bi#5` | 0.2258 | Chưa liên quan | Trích xuất điều khoản loại trừ của Apple (do nhiễu mock embed). |
| 2 | TGDĐ vi phạm cam kết bảo hành 15 ngày được quyền lợi gì? | `shopee-quy-dinh-tra-hang-hoan-tien#2` | 0.2134 | Chưa liên quan | Trích xuất các lý do trả hàng của Shopee. |
| 3 | Thời hạn bảo hành thân máy điện thoại Xiaomi tại VN? | `thegioididong-chinh-sach-bao-hanh-doi-tra#4` | 0.2130 | Chưa liên quan | Trích xuất phí mất hộp và phụ kiện TGDĐ. |
| 4 | Cập nhật ngày mua Apple trên hệ thống trực tuyến cần giấy tờ gì? | `apple-pham-vi-bao-hanh-thiet-bi#2` | 0.2610 | **Có (Chính xác)** | Trích xuất yêu cầu xuất trình biên lai bán hàng gốc / hóa đơn tài chính hợp lệ từ AAR. |
| 5 | Thời hạn phản hồi khiếu nại trả hàng hoàn tiền? *(Có Filter `audience: seller`)* | `shopee-quy-dinh-nguoi-ban-xu-ly-khieu-nai#0` | 0.0870 | **Có (Chính xác)** | Người bán phải phản hồi trong vòng 02 ngày (48 giờ làm việc) kể từ khi tiếp nhận. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **2 / 5** (Khi kết hợp với `metadata_filter`, câu hỏi phân định vai trò đạt độ chính xác 100%).

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Nhận thấy rõ hạn chế của việc cắt cố định ký tự (`FixedSizeChunker`): nó có thể chém ngang một bảng biểu hoặc câu quy định. Các bạn dùng `RecursiveChunker` hoặc `HeadingChunker` giữ được trọn vẹn ngữ cảnh từng điều khoản nguyên vẹn hơn. Đặc biệt, việc áp dụng `metadata_filter` trước khi tìm kiếm là giải pháp cực kỳ hiệu quả để giải quyết bài toán nhập nhằng giữa các đối tượng khác nhau trên cùng nền tảng.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|---|---|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
