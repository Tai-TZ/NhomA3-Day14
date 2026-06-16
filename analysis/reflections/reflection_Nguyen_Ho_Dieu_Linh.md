# Báo cáo Cá nhân — Nguyễn Hồ Diệu Linh (2A202600567)

## 1. Vai trò & Phân công trong nhóm
- **Module phụ trách:** 
  - **Retrieval Evaluation Module** (`engine/retrieval_eval.py`): Triển khai các hệ số đánh giá tìm kiếm như Hit Rate @ top_k và Mean Reciprocal Rank (MRR).
  - **Regression Testing & Release Gate Module** (`engine/release_gate.py`): Thiết kế cổng kiểm soát phiên bản tự động (Release Gate) so sánh hiệu năng, chi phí, và chất lượng giữa hai phiên bản V1 và V2.
  - **Dataset & SDG Red Teaming**: Đóng góp xây dựng các kịch bản kiểm thử tấn công (Goal Hijacking, Prompt Injection, Out-of-context) trong file `data/synthetic_gen.py`.
- **Thời gian đóng góp:** ~2.5 giờ — Phát triển các module đánh giá retrieval, release gate và thiết lập các kịch bản kiểm thử bảo mật.

## 2. Đóng góp Kỹ thuật (Engineering Contribution)
- **File/Module đã triển khai:**
  - [retrieval_eval.py](file:///Users/nguyenhodieulinh/Documents/NhomA3-Day14/engine/retrieval_eval.py): Viết các hàm tính toán `calculate_hit_rate` và `calculate_mrr` cho batch test cases, hỗ trợ xuất báo cáo chất lượng tìm kiếm văn bản.
  - [release_gate.py](file:///Users/nguyenhodieulinh/Documents/NhomA3-Day14/engine/release_gate.py): Xây dựng lớp `ReleaseGate` để tự động so sánh hai phiên bản thông qua các chỉ số chất lượng trung bình, delta điểm số, phần trăm gia tăng chi phí và độ trễ.
  - [synthetic_gen.py](file:///Users/nguyenhodieulinh/Documents/NhomA3-Day14/data/synthetic_gen.py): Tham gia thiết kế và đóng góp các ca kiểm thử bảo mật khó nhằm đánh giá tính kiên cố của RAG Agent.
- **Commit liên quan:** `feat(linh): implement retrieval evaluation metrics, release gate policy, and red-teaming datasets`
- **Giải trình kỹ thuật:**
  - **Retrieval Evaluation:** Hệ thống tìm kiếm context đóng vai trò cốt lõi trong RAG. Để đo chính xác chất lượng, tôi cài đặt `Hit Rate` để xem tài liệu tham chiếu có nằm trong top-K hay không và `MRR` để đánh giá xem tài liệu đúng nhất được xếp ở thứ hạng bao nhiêu. Điều này giúp phát hiện ra các trường hợp hệ thống tìm kiếm lấy sai tài liệu trước khi đưa vào bước sinh câu trả lời của LLM.
  - **Regression Release Gate:** Cổng phát hành tự động giúp kiểm soát rủi ro khi cập nhật Agent. Tôi thiết kế cơ chế ngưỡng động (`DEFAULT_THRESHOLDS`) bao gồm: điểm trung bình tối thiểu (3.0), Hit Rate tối thiểu (0.65), MRR tối thiểu (0.45) cùng các giới hạn về gia tăng chi phí (≤ 25%) và thời gian chạy (≤ 30%). Nếu bất kỳ kiểm tra nào thất bại, cổng sẽ trả về quyết định `BLOCK` để ngăn chặn việc triển khai phiên bản lỗi.

## 3. Chiều sâu Kỹ thuật (Technical Depth)
- **MRR là gì? Tại sao MRR quan trọng hơn Hit Rate trong một số trường hợp?**
  - **MRR (Mean Reciprocal Rank)** là trung bình cộng của các nghịch đảo thứ hạng của tài liệu liên quan đầu tiên được tìm thấy (`1/rank`). Nếu tài liệu đúng nằm ở vị trí đầu tiên, điểm Reciprocal Rank (RR) là 1.0; nằm ở vị trí thứ 3 thì RR là 0.33; nếu không tìm thấy thì RR bằng 0.
  - **Hit Rate @ top_k** chỉ đo lường xem tài liệu liên quan có xuất hiện trong danh sách top-k hay không (trả về kết quả nhị phân 0 hoặc 1). Nó không quan tâm tài liệu đó đứng ở vị trí thứ 1 hay thứ k.
  - **MRR quan trọng hơn Hit Rate** khi Agent sử dụng một số lượng ngữ cảnh rất hạn chế (ví dụ chỉ lấy top-1 hoặc top-2) để sinh câu trả lời nhằm tối ưu hóa chi phí token. Nếu tài liệu đúng nằm ở vị trí thứ 3, Hit Rate @ top-3 vẫn đạt 1.0, nhưng Agent thực tế sẽ không nhận được thông tin này vì nó đã bị cắt bỏ sau top-2. MRR phản ánh chính xác chất lượng sắp xếp thứ tự (ranking quality) của Retriever, giúp giảm thiểu hiện tượng ảo tưởng (hallucination) của LLM.

- **Cohen's Kappa / Agreement Rate:** Hệ thống Multi-Judge của nhóm tính độ đồng thuận như thế nào?
  - Hệ thống của nhóm sử dụng hai phương thức đo lường độ đồng thuận bổ trợ cho nhau:
    1. **Agreement Rate (per-case):** Tính tỷ lệ gần nhau giữa điểm của hai Judge (ví dụ lệch 0 điểm tương ứng với 100% đồng thuận, lệch càng nhiều phần trăm đồng thuận càng giảm).
    2. **Cohen's Kappa (batch):** Đo lường mức độ đồng ý giữa hai Judge (GPT-4o chấm accuracy và Claude chấm tone) sau khi đã loại bỏ khả năng đồng ý do ngẫu nhiên: $\kappa = \frac{P_o - P_e}{1 - P_e}$ (trong đó $P_o$ là độ đồng thuận quan sát được thực tế, và $P_e$ là độ đồng thuận dự kiến do ngẫu nhiên).
  - Điểm Cohen's Kappa đặc biệt quan trọng vì nếu cả hai Judge đều có xu hướng thiên vị (luôn cho điểm cao), Agreement Rate sẽ rất cao nhưng Cohen's Kappa sẽ rất thấp, phản ánh rằng sự đồng thuận đó không thực sự có ý nghĩa kiểm chuẩn.

- **Position Bias:** Judge LLM có thể thiên vị vị trí câu trả lời không? Nhóm xử lý ra sao?
  - **Có.** Các mô hình LLM khi đóng vai trò Judge thường mắc phải lỗi **Position Bias** (thiên vị vị trí), bao gồm *primacy bias* (ưu tiên câu trả lời xuất hiện trước) hoặc *recency bias* (ưu tiên câu trả lời xuất hiện sau).
  - **Giải pháp của nhóm:** Nhóm đã triển khai kiểm tra thiên vị vị trí bằng cách hoán đổi thứ tự câu trả lời khi đưa vào prompt chấm điểm (chấm AB rồi chấm lại BA), tính toán điểm lệch vị trí `bias_score = |score_AB - score_BA| / 2`.
  - **Cách xử lý triệt để:** Ngẫu nhiên hóa (shuffle) thứ tự các câu trả lời khi gọi API chấm điểm, lấy trung bình kết quả chấm của cả hai lượt hoán đổi, và tối ưu hóa hệ thống prompt chấm điểm tập trung vào trích xuất thông tin thực tế thay vì cấu trúc trình bày.

- **Trade-off Chi phí vs Chất lượng:** Đề xuất giảm ~30% chi phí eval mà không giảm độ chính xác?
  - Để đạt mục tiêu này, tôi đề xuất triển khai các chiến lược:
    1. **Phân tầng chấm điểm (Tiered Judging):** Sử dụng các metric heuristic rẻ tiền (như token overlap hoặc ROUGE score) để sàng lọc trước các câu trả lời. Nếu heuristic score quá cao (>0.9) hoặc quá thấp (<0.1), chúng ta có thể gán thẳng điểm 5 hoặc 1 mà không cần gọi API LLM Judge đắt đỏ. Chỉ gọi LLM Judge cho các case nằm trong vùng trung gian (2.5 - 3.5). Giải pháp này giúp giảm ~40% số lần gọi LLM Judge.
    2. **Bộ nhớ đệm đánh giá (Evaluation Caching):** Lưu trữ mã băm (hash) của cặp (câu hỏi, câu trả lời, ngữ cảnh). Khi chạy lại regression trên cùng dataset, các case không có sự thay đổi về nội dung sẽ được tái sử dụng điểm số cũ mà không cần gọi lại mô hình.
    3. **Tối ưu hóa độ dài prompt và System Prompt:** Rút gọn ngữ cảnh truyền vào mô hình Judge, chỉ truyền những câu/đoạn trích chứa thông tin Ground Truth thay vì toàn bộ văn bản gốc.

## 4. Giải quyết Vấn đề (Problem Solving)
- **Vấn đề gặp phải:** Khi cấu hình `ReleaseGate`, ban đầu tôi chỉ thiết lập kiểm tra dựa trên các chỉ số trung bình (ví dụ: điểm Judge trung bình tăng từ 3.96 lên 4.03). Tuy nhiên, khi phân tích chi tiết, tôi phát hiện ra có một số case thuộc dạng tấn công bảo mật (Adversarial) bị sụt giảm điểm nghiêm trọng (chỉ đạt 1.0/5.0) nhưng vẫn bị che lấp bởi điểm số trung bình tăng của các case dễ. Điều này khiến hệ thống tự động `APPROVE` một phiên bản Agent có lỗ hổng bảo mật.
- **Cách xử lý:** Tôi đã bổ sung logic kiểm tra nghiêm ngặt cho các nhóm test case quan trọng trong `ReleaseGate`. Cụ thể, nếu bất kỳ ca kiểm thử nào thuộc nhóm `adversarial` có điểm số dưới ngưỡng an toàn (ví dụ < 2.0), hệ thống sẽ lập tức đưa ra quyết định `BLOCK` bất kể điểm trung bình toàn hệ thống tăng bao nhiêu.
- **Bài học rút ra:** Các chỉ số trung bình (Aggregated Metrics) rất hữu ích để xem xét bức tranh tổng thể nhưng không đủ tin cậy cho các khía cạnh an toàn bảo mật. Cần phải phân nhóm dữ liệu (failure clustering) và thiết lập các điều kiện biên (safety-critical thresholds) cụ thể để bảo vệ hệ thống trước các hồi quy nghiêm trọng.

## 5. Tự đánh giá
| Tiêu chí | Mức tự đánh giá (1-5) | Ghi chú |
|----------|:---------------------:|---------|
| Engineering Contribution | 5 | Hoàn thành xuất sắc các module đánh giá retrieval, release gate và thiết kế dữ liệu kiểm thử. |
| Technical Depth | 5 | Hiểu sâu sắc sự khác biệt giữa Hit Rate và MRR, bản chất của Cohen's Kappa và các bias của LLM. |
| Problem Solving | 4 | Xử lý hiệu quả vấn đề che giấu lỗi của điểm trung bình trong Release Gate. |
