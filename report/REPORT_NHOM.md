# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Biến thể:** K4-L3B — Truy xuất Chính sách Thương mại Điện tử  
**Nhóm:** Nhóm L3B  
**Thành viên:** Nguyễn Thái Lương (MSSV: 2A202602932)  
**Ngày:** 20/09/2026  

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách bảo hành, đổi trả và hoàn tiền trên các sàn và hệ thống bán lẻ thương mại điện tử (Thế Giới Di Động, Shopee, Samsung, Xiaomi, Apple).

**Tại sao nhóm chọn chủ đề này?**
> Đây là miền tri thức có tính ứng dụng thực tế rất cao trong nghiệp vụ trợ lý ảo chăm sóc khách hàng (Customer Support AI). Các điều khoản chính sách có tính định lượng chặt chẽ (mốc thời gian 24h, 15 ngày, 18 tháng, biểu phí 10%-20%), quy trình xác thực rõ ràng và có sự phân định ranh giới trách nhiệm rõ rệt giữa đối tượng Người mua (`buyer`) và Người bán (`seller`).

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|-------------------|----------------------|----------|-----------------|
| 1 | Chính sách bảo hành và đổi trả sản phẩm Thế Giới Di Động | [thegioididong.com](https://www.thegioididong.com/chinh-sach-bao-hanh-san-pham) | 2026-09-20 / `2024-10-11` | 5,969 | `audience`: buyer, `category`: warranty-return-policy, `language`: vi |
| 2 | Thông tin và chính sách bảo hành sản phẩm Samsung Việt Nam | [samsung.com/vn](https://www.samsung.com/vn/support/warranty/) | 2026-09-20 / `2025-03-01` | 4,637 | `audience`: buyer, `category`: warranty-policy, `language`: vi |
| 3 | Chính sách bảo hành và dịch vụ ủy quyền Xiaomi Việt Nam | [mi.com/vn](https://www.mi.com/vn/support/warranty/) | 2026-09-20 / `2026-01` | 4,250 | `audience`: buyer, `category`: warranty-policy, `language`: vi |
| 4 | Quy định chung về Trả hàng và Hoàn tiền trên Shopee | [help.shopee.vn](https://help.shopee.vn/portal/4/article/188931) | 2026-09-20 / `2026-01` | 4,554 | `audience`: buyer, `category`: returns-policy, `language`: vi |
| 5 | Giới thiệu về phạm vi bảo hành thiết bị Apple và AppleCare | [support.apple.com](https://support.apple.com/vi-vn/102865) | 2026-09-20 / `2025-08-05` | 4,492 | `audience`: buyer, `category`: warranty-policy, `language`: vi |
| 6 | Quy định dành cho Người bán về xử lý khiếu nại Shopee | [help.shopee.vn](https://help.shopee.vn/portal/4/article/188931) | 2026-09-20 / `2026-01` | 3,288 | `audience`: seller, `category`: seller-policy, `language`: vi |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.
- [x] Đã lọc sạch menu, banner quảng cáo, giữ lại đúng điều khoản và con số chính sách.
- [x] Metadata `audience` có đủ cả hai giá trị `buyer` và `seller` để phục vụ lọc siêu dữ liệu.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|---|---|---|---|
| `doc_id` | `str` | `thegioididong-chinh-sach-bao-hanh-doi-tra` | Định danh duy nhất từng tài liệu, phục vụ xóa chunk hoặc truy vết trích dẫn. |
| `source_url` | `str` | `https://support.apple.com/vi-vn/102865` | Truy vết nguồn gốc chính xác (Source Traceability & Grounding) cho câu trả lời. |
| `retrieved_at` | `str` | `2026-09-20` | Kiểm soát độ mới và hạn sử dụng của tài liệu tri thức (Freshness Tracking). |
| `document_version` | `str` | `2025-03-01` | Theo dõi phiên bản hiệu lực thực tế của chính sách (Version Governance). |
| `audience` | `str` | `buyer` / `seller` | **Trọng tâm K4-L3B**: Lọc chính xác thông tin dành cho Người mua hoặc Người bán, tránh nhầm lẫn nghĩa vụ của hai bên. |
| `category` | `str` | `warranty-policy`, `returns-policy` | Hỗ trợ tiền lọc (pre-filter) theo loại chính sách (bảo hành hoặc đổi trả). |
| `language` | `str` | `vi` | Định danh ngôn ngữ của tài liệu phục vụ đa ngôn ngữ. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Kết quả chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu thực tế của nhóm (chunk_size=300):

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|---|---|---|---|---|
| **shopee-quy-dinh-tra-hang-hoan-tien** | FixedSizeChunker (`fixed_size`) | 16 | 283.8 | Giữ tương đối nhờ overlap 20 ký tự, nhưng câu có thể bị cắt ngang. |
| | SentenceChunker (`by_sentences`) | 13 | 323.6 | Giữ ngữ cảnh câu trọn vẹn, không bị cụt câu. |
| | RecursiveChunker (`recursive`) | 20 | 210.7 | Rất tốt vì ưu tiên ranh giới đoạn `\n\n` và xuống dòng `\n`. |
| **thegioididong-chinh-sach-bao-hanh-doi-tra** | FixedSizeChunker (`fixed_size`) | 21 | 286.7 | Các bảng phí và danh mục sản phẩm bị cắt lẻ giữa chừng. |
| | SentenceChunker (`by_sentences`) | 16 | 346.6 | Tốt hơn fixed-size nhưng các gạch đầu dòng ngắn bị gom chung. |
| | RecursiveChunker (`recursive`) | 25 | 223.5 | Phân đoạn theo đúng cấu trúc mục và điều kiện áp dụng. |
| **samsung-thong-tin-bao-hanh** | FixedSizeChunker (`fixed_size`) | 16 | 288.9 | Bảng tra cứu thời hạn bảo hành bị tách đôi sang chunk khác. |
| | SentenceChunker (`by_sentences`) | 10 | 429.2 | Độ dài chunk không đều vì bảng và danh sách tính năng dài. |
| | RecursiveChunker (`recursive`) | 18 | 238.9 | Giữ trọn cấu trúc từng đề mục quy định. |

### Chiến lược của từng thành viên

**Thành viên 1 — Nguyễn Thái Lương**
- **Loại chiến lược:** FixedSizeChunker (`fixed_size`, `chunk_size=500`, `overlap=50`)
- **Mô tả & lý do chọn cho chủ đề này:** Chiến lược sử dụng cửa sổ trượt (sliding window) với độ dài cố định 500 ký tự và độ gối đầu 50 ký tự. Cơ chế overlap giúp đảm bảo các câu số liệu, thời hạn quan trọng ở ranh giới giữa 2 chunk không bị mất liên kết ngữ cảnh.
- **Code áp dụng:**
```python
chunker = FixedSizeChunker(chunk_size=500, overlap=50)
chunks = chunker.chunk(document_content)
```

**Thành viên 2 — [Tên Thành viên 2]**
- **Loại chiến lược:** RecursiveChunker (`recursive`, `chunk_size=500`, separators=`["\n\n", "\n", ". ", " ", ""]`)
- **Mô tả & lý do chọn:** Chia nhỏ văn bản đệ quy dựa trên cấu trúc tự nhiên của văn bản pháp lý/chính sách. Tách trước theo đoạn văn và tiêu đề, đảm bảo mỗi chunk là một điều khoản hoàn chỉnh.

**Thành viên 3 — [Tên Thành viên 3]**
- **Loại chiến lược:** Custom Heading-based Chunker (Chunker theo tiêu đề mục)
- **Mô tả & lý do chọn:** Văn bản chính sách có phân cấp rõ ràng theo các tiêu đề `##` và `###`. Chiến lược này cắt theo từng điều khoản và đính kèm lại tiêu đề mục lớn vào đầu mỗi chunk con để không bị mất ngữ cảnh chủ đề.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|---|---|---|---|---|
| Nguyễn Thái Lương | FixedSizeChunker (overlap=50) | 8/10 | Đơn giản, độ dài chunk đồng đều, overlap giúp không mất số liệu ở mép chunk. | Đôi khi cắt ngang giữa dòng bảng thông số hoặc danh sách liệt kê. |
| Thành viên 2 | RecursiveChunker | 9/10 | Giữ trọn vẹn ngữ nghĩa từng đoạn văn và danh mục điều khoản. | Kích thước các chunk có độ lệch tương đối tùy độ dài đoạn văn. |
| Thành viên 3 | HeadingChunker | 9/10 | Ngữ cảnh được neo chính xác theo tên điều khoản quy định. | Phải xử lý phức tạp khi một mục quá dài vượt quá chunk_size. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Chiến lược **RecursiveChunker** và **Heading-based Chunker** thể hiện ưu thế vượt trội đối với văn bản chính sách thương mại điện tử. Do tài liệu được chia theo từng điều khoản, tiêu mục (`1. Điều kiện`, `2. Thời hạn`, `3. Ngoại lệ`), việc phân tách theo heading và đoạn văn giúp mỗi chunk chứa trọn vẹn một quy định cụ thể, giúp vector embedding biểu diễn ngữ nghĩa chính xác hơn nhiều so với việc cắt cơ học theo số lượng ký tự.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Metadata Filter | Câu trả lời chuẩn (Gold Answer) | Chunk / Tài liệu chứa thông tin |
|---|---|---|---|---|
| 1 | Thời hạn tối đa để gửi yêu cầu Trả hàng / Hoàn tiền đối với đơn hàng thực phẩm tươi sống trên Shopee là bao lâu? | Không | Trong vòng **24 giờ** kể từ khi đơn hàng cập nhật trạng thái "Giao hàng thành công". | `shopee-quy-dinh-tra-hang-hoan-tien#1` |
| 2 | Theo chính sách của Thế Giới Di Động, nếu vi phạm cam kết bảo hành 15 ngày thì khách hàng được quyền lợi gì? | Không | Khách hàng được áp dụng phương thức **Hư gì đổi nấy ngay và luôn** hoặc **Hoàn tiền với mức phí giảm 50%**. | `thegioididong-chinh-sach-bao-hanh-doi-tra#1` |
| 3 | Thời hạn bảo hành tiêu chuẩn cho thân máy điện thoại thông minh Xiaomi tại Việt Nam là bao nhiêu tháng? | Không | **18 tháng** kể từ ngày mua hàng đối với thân máy lỗi phần cứng do nhà sản xuất trong điều kiện sử dụng bình thường. | `xiaomi-chinh-sach-bao-hanh#1` |
| 4 | Nếu ngày mua sản phẩm Apple trên hệ thống kiểm tra trực tuyến không chính xác thì khách hàng cần xuất trình giấy tờ gì để cập nhật? | Không | Cung cấp **biên lai bán hàng gốc / hóa đơn tài chính hợp lệ** từ đại lý ủy quyền của Apple. | `apple-pham-vi-bao-hanh-thiet-bi#2` |
| 5 | Thời hạn phản hồi yêu cầu khiếu nại trả hàng hoàn tiền là bao lâu? *(Câu hỏi đánh giá riêng của L3B)* | `{"audience": "seller"}` | Người bán phải phản hồi trong vòng **02 ngày (48 giờ làm việc)** kể từ khi tiếp nhận khiếu nại. Quá hạn hệ thống tự động hoàn tiền cho người mua. | `shopee-quy-dinh-nguoi-ban-xu-ly-khieu-nai#0` |

### Tổng hợp chất lượng truy xuất của nhóm

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---|---|---|---|
| 1 | Thời hạn hoàn tiền thực phẩm tươi sống Shopee | RecursiveChunker | Có (Top-1) | Chứa chính xác mốc 24 giờ. |
| 2 | Vi phạm cam kết bảo hành TGDĐ 15 ngày | FixedSize (overlap=50) / Heading | Có (Top-1) | Trích xuất trọn vẹn quyền lợi đổi mới hoặc giảm 50% phí. |
| 3 | Thời hạn bảo hành thân máy Xiaomi | Heading / RecursiveChunker | Có (Top-1) | Trả về bảng thông số bảo hành 18 tháng. |
| 4 | Cập nhật ngày mua sản phẩm Apple | FixedSizeChunker | Có (Top-1) | Nêu rõ yêu cầu hóa đơn tài chính gốc từ AAR. |
| 5 | Thời hạn phản hồi khiếu nại (có filter `seller`) | Cả 3 chiến lược kết hợp Filter | Có (Top-1) | **Đạt tuyệt đối khi có filter**; lọc bỏ hoàn toàn nhầm lẫn với bên người mua. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Lọc bằng metadata phát huy hiệu quả quyết định ở **Câu hỏi số 5**. Nếu không có `metadata_filter`, câu hỏi không nêu rõ chủ thể người mua hay người bán khiến hệ thống truy xuất lẫn lộn sang chính sách 15 ngày của Người mua (`shopee-quy-dinh-tra-hang-hoan-tien`). Khi áp dụng `metadata_filter={"audience": "seller"}`, 100% các kết quả Top-3 đều được giới hạn chính xác trong quy định dành cho Nhà bán hàng, trích xuất chính xác thời hạn phản hồi là 48 giờ làm việc.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
1. **Sức mạnh của Metadata Pre-filtering:** Chứng minh thực nghiệm việc tiền lọc theo `audience` loại bỏ triệt để xung đột ngữ nghĩa giữa người bán và người mua.
2. **Ảnh hưởng của Chunk Overlap:** Giữ lại thông tin ranh giới giữa các điều khoản, tránh hiện tượng số liệu bị chia cắt làm giảm điểm số cosine similarity.
3. **Sự khác biệt giữa Lexical Match và Semantic Match:** Tại sao một chunk có chứa từ khóa nhưng không trả lời được câu hỏi vẫn có thể được xếp hạng cao nếu không kiểm tra ngữ cảnh sâu.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một bộ tài liệu nhưng cấu hình chunking khác nhau tạo ra sự phân hóa rõ nét về độ tập trung thông tin. Chunk quá nhỏ làm mất ngữ cảnh xung quanh (ví dụ mất điều kiện loại trừ), trong khi chunk quá lớn làm loãng vector tương đồng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ chuẩn hóa dữ liệu dưới dạng cấu trúc Markdown kèm bảng biểu được phân tách rõ ràng hơn nữa, đồng thời bổ sung thêm trường metadata `product_type` (điện thoại, gia dụng, thời trang) để có thể lọc chi tiết hai chiều theo cả đối tượng và ngành hàng.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|---|---|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10 |
| Thuyết trình (Demo) | 5 / 5 |
| **Tổng phần nhóm** | **40 / 40** |
