# Báo cáo Cá nhân — Nguyễn Trọng Nguyên (2A202600548)

## 1. Vai trò & Phân công trong nhóm
- **Module phụ trách:**
  - **Golden Dataset & SDG** (`data/synthetic_gen.py`, `data/knowledge_base.py`): Thiết kế knowledge base 10 documents, sinh ≥50 test cases với `expected_retrieval_ids`, bao gồm red-teaming (adversarial, out-of-context, ambiguous).
  - **Failure Analysis** (`analysis/failure_analysis.md`): Phân cụm lỗi, phân tích 5 Whys cho 3 case tệ nhất, kết nối retrieval metrics với answer quality.
  - **Mock Agent V1/V2** (`agent/main_agent.py`): Hỗ trợ triển khai keyword retrieval mock và V2 synonym expansion để có baseline/regression rõ ràng.
- **Thời gian đóng góp:** ~2 giờ — Giai đoạn 1 (45') SDG & Golden Dataset; Giai đoạn 3 (60') Failure Clustering & 5 Whys; Giai đoạn 4 (45') hoàn thiện báo cáo nhóm và cá nhân.

## 2. Đóng góp Kỹ thuật (Engineering Contribution)
- **File/Module đã triển khai:**
  - `data/knowledge_base.py` — `DOC_CATALOG`: 10 tài liệu với title, keywords, content; là nguồn chung cho SDG và mock retrieval.
  - `data/synthetic_gen.py` — `BASE_CASES`, `RED_TEAM_CASES`, `_generate_variations()`, `build_golden_dataset()`: đảm bảo ≥50 cases unique, mỗi case có ground truth IDs để tính Hit Rate/MRR.
  - `analysis/failure_analysis.md` — Bảng so sánh V1/V2, failure clustering 4 nhóm, 3 case 5 Whys (goal hijacking, prompt injection, out-of-context), action plan cải tiến.
  - `agent/main_agent.py` — `MainAgent` (V1) và `MainAgentV2` (synonym expansion) trả về `retrieved_ids` phục vụ retrieval eval.
- **Commit liên quan:** `4de4e60` — `feat: Complete Day 14 group lab - AI Evaluation Factory` (SDG, knowledge base, failure analysis, agent mock)
- **Giải trình kỹ thuật:**
  - **SDG:** Mỗi case trong golden set phải có `expected_retrieval_ids` — không có mapping này thì Hit Rate/MRR không tính được. Tôi thiết kế 3 lớp: base fact-check/how-to (10 cases), red-team hard cases (8 cases), và variations sinh từ `DOC_CATALOG` để đạt 50+ mà vẫn đa dạng difficulty/type.
  - **Failure Analysis:** Không dừng ở pass/fail — nhóm lỗi theo metadata (`adversarial`, `out-of-context`, judge conflict) rồi đào sâu 5 Whys để chỉ root cause (Safety Guard, Prompting, Retrieval threshold) thay vì chỉ blame LLM generation.
  - **Trade-off:** Variations từ template có thể trùng semantic — dùng `seen_questions` dedupe; red-team cases cố ý không match retrieval dễ để kiểm tra agent safety.

## 3. Chiều sâu Kỹ thuật (Technical Depth)

- **MRR là gì? Tại sao MRR quan trọng hơn Hit Rate trong một số trường hợp?**
  - **MRR** = trung bình `1/rank` của document đúng đầu tiên trong kết quả retrieval. Rank 1 → 1.0; rank 3 → 0.33; miss → 0.
  - **Hit Rate @ top-k** chỉ trả lời “có trong top-k không?” (0/1), không phân biệt doc đúng ở vị trí 1 hay k.
  - Quan trọng hơn khi agent chỉ inject **top-1 hoặc top-2** chunk vào prompt (tiết kiệm token). Hit Rate @3 = 100% nhưng doc đúng ở rank 3 vẫn khiến LLM không thấy context đúng → hallucination. MRR phản ánh **ranking quality** thực tế.

- **Cohen's Kappa / Agreement Rate:** Hệ thống Multi-Judge của nhóm tính độ đồng thuận như thế nào?
  - **Agreement Rate (per-case):** Map độ lệch điểm 2 judge → tỷ lệ đồng thuận (lệch 0 → 100%, lệch >1 → 30%).
  - **Cohen's Kappa (batch):** `κ = (P_o - P_e) / (1 - P_e)` trên toàn bộ 50 cases — loại bỏ đồng thuận “giả” do cả hai judge cùng bias.
  - Khi phân tích failure, tôi dùng cả hai: Agreement Rate để tìm case conflict trong benchmark_results; Kappa thấp (~0.05) cho thấy 2 rubric (accuracy vs tone) đo các khía cạnh khác nhau — cần conflict resolution policy, không chỉ lấy trung bình.

- **Position Bias:** Judge LLM có thể thiên vị vị trí câu trả lời không? Nhóm xử lý ra sao?
  - **Có** — primacy/recency bias khi so sánh nhiều câu trả lời trong một prompt.
  - Nhóm có `check_position_bias()` trong `llm_judge.py`: chấm AB rồi hoán đổi BA, tính `bias_score`. Trong failure analysis, các case judge conflict thường do một judge ưu tiên tone chuyên nghiệp trong khi answer sai nội dung — conservative min score khi recall ground truth thấp là cách giảm over-score.

- **Trade-off Chi phí vs Chất lượng:** Đề xuất giảm ~30% chi phí eval mà không giảm độ chính xác?
  1. **Stratified eval:** Chạy full 50 cases mỗi release; giữa các release chỉ re-eval subset red-team + cases fail trước đó (~15 cases) — tiết kiệm ~70% run thường ngày, vẫn bảo vệ safety.
  2. **Dataset dedup & cache:** Hash `(question, answer)` — case không đổi giữa V1/V2 regression không gọi lại judge.
  3. **Heuristic pre-screen trên SDG:** Cases `type=generated` dễ (high token overlap) có thể skip LLM judge — tập trung budget vào adversarial/out-of-context do tôi thiết kế trong RED_TEAM_CASES.

## 4. Giải quyết Vấn đề (Problem Solving)
- **Vấn đề gặp phải:**
  1. Ban đầu golden set chỉ ~18 cases thủ công — không đủ 50+ và thiếu adversarial coverage.
  2. Red-team cases (goal hijacking) vẫn trigger retrieval nhầm vì keyword “tài liệu”, “instructions” — khó phân biệt lỗi retrieval vs generation trong báo cáo.
  3. Số liệu trong `failure_analysis.md` dễ lệch với `reports/summary.json` nếu cập nhật tay sau benchmark.

- **Cách xử lý:**
  1. Thêm `_generate_variations()` duyệt `DOC_CATALOG` + dedupe `seen_questions` → 50 cases với metadata `type`, `difficulty`, `source_doc`.
  2. Failure clustering tách 4 nhóm; 5 Whys gắn `subtype` (goal-hijacking, prompt-injection) từ metadata SDG → root cause rõ ở Safety/Prompting layer.
  3. Đồng bộ báo cáo: chạy `python main.py` trước khi nộp, lấy metrics từ `summary.json` (pass_rate, agreement_rate, conflicts_resolved, duration).

- **Bài học rút ra:**
  - Golden dataset tốt = nền tảng mọi metric — thiếu `expected_retrieval_ids` thì cả pipeline eval vô nghĩa.
  - Failure analysis phải **traceable** từ benchmark JSON, không viết số “ước lượng”.
  - Adversarial cases là phần giá trị nhất của SDG — chứng minh agent fail ở safety dù Hit Rate tổng vẫn cao.

## 5. Tự đánh giá
| Tiêu chí | Mức tự đánh giá (1-5) | Ghi chú |
|----------|:---------------------:|---------|
| Engineering Contribution | 4 | SDG 50+ cases, knowledge base, failure analysis, agent mock baseline |
| Technical Depth | 4 | Hiểu MRR vs Hit Rate, Kappa vs Agreement Rate, liên kết SDG metadata với root cause |
| Problem Solving | 4 | Mở rộng dataset, phân cụm lỗi có cấu trúc, đồng bộ báo cáo với reports |
