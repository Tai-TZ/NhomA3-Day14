# Báo cáo Cá nhân — Ngô Thị Ánh (2A202600979)

## 1. Vai trò & Phân công trong nhóm
- **Module phụ trách:** Multi-Judge Consensus Engine, Judge Calibration (Cohen's Kappa), Position Bias detection
- **Thời gian đóng góp:** ~2 giờ — Giai đoạn 2 (90') phát triển Eval Engine & Giai đoạn 4 (45') hoàn thiện báo cáo cá nhân

## 2. Đóng góp Kỹ thuật (Engineering Contribution)
- **File/Module đã triển khai:**
  - `engine/llm_judge.py` — `MultiModelJudge`: 2 Judge (GPT-4o accuracy + Claude tone), Agreement Rate, conflict resolution khi lệch > 1 điểm, `check_position_bias()`
  - `engine/judge_calibration.py` — **Module mới:** Cohen's Kappa, batch agreement analytics, tổng hợp calibration sau benchmark
  - `main.py` — tích hợp `JudgeCalibration.summarize()` vào summary metrics (`cohens_kappa`, `conflict_rate`)
- **Commit liên quan:** `feat(anh): add judge calibration with Cohen's Kappa and integrate into benchmark summary`
- **Giải trình kỹ thuật:**

  **Multi-Judge Consensus (`MultiModelJudge`):**
  - Judge A (GPT-4o) chấm theo **accuracy** — đo recall token overlap giữa answer và ground truth.
  - Judge B (Claude) chấm theo **tone** — đo mức chuyên nghiệp qua professional markers.
  - **Agreement Rate** per-case: lệch 0 → 1.0, ≤0.5 → 0.85, ≤1.0 → 0.6, >1.0 → 0.3.
  - **Conflict resolution** khi `|score_a - score_b| > 1.0`:
    - Nếu answer thiếu keywords ground truth (recall < 0.2) → lấy **min score** (conservative, tránh over-score).
    - Ngược lại → **weighted average** 60% accuracy judge + 40% tone judge.

  **Judge Calibration (`judge_calibration.py`):**
  - Tính **Cohen's Kappa** trên toàn bộ 50 cases: đo đồng thuận vượt trên mức ngẫu nhiên (κ > 0.6 = substantial agreement).
  - Trade-off: dùng heuristic judge (không gọi API) để tiết kiệm chi phí trong lab, nhưng vẫn giữ đủ logic consensus thực tế.

## 3. Chiều sâu Kỹ thuật (Technical Depth)

- **MRR là gì? Tại sao MRR quan trọng hơn Hit Rate trong một số trường hợp?**

  **MRR (Mean Reciprocal Rank)** = trung bình của `1/rank`, trong đó `rank` là vị trí (1-indexed) của tài liệu đúng đầu tiên trong danh sách retrieved.

  Ví dụ: expected doc ở vị trí 1 → RR = 1.0; vị trí 3 → RR = 0.33; không tìm thấy → RR = 0.

  **Hit Rate @ top_k** chỉ trả lời câu hỏi nhị phân: "Có tài liệu đúng trong top_k không?" — không phân biệt doc đúng ở vị trí 1 hay vị trí k.

  MRR quan trọng hơn khi:
  - Agent chỉ dùng **top-1 hoặc top-2 context** để generate → doc ở vị trí 3 gần như vô dụng dù Hit Rate vẫn = 1.
  - Cần **ranking quality** — RAG pipeline càng đưa doc đúng lên cao, generation càng ít hallucination.
  - Benchmark nhóm đạt Hit Rate 92% nhưng MRR 0.886 — cho thấy phần lớn doc đúng ở top đầu, không chỉ "có mặt" trong top-3.

- **Cohen's Kappa / Agreement Rate:** Hệ thống Multi-Judge của nhóm tính độ đồng thuận như thế nào?

  Nhóm dùng **2 lớp metrics**:

  1. **Agreement Rate (per-case)** — trong `MultiModelJudge._agreement_rate()`: đo mức gần nhau của 2 điểm từng case, trung bình hóa qua 50 cases.
  2. **Cohen's Kappa (batch)** — trong `judge_calibration.cohens_kappa()`: chuẩn hóa điểm về thang 1–5, tính:
     - `P_o` = tỷ lệ 2 judge cho cùng category
     - `P_e` = xác suất đồng thuận do ngẫu nhiên
     - `κ = (P_o - P_e) / (1 - P_e)`

  Kappa bổ sung Agreement Rate vì loại bỏ **agreement by chance** — 2 judge cùng cho điểm cao liên tục có thể có Agreement Rate cao nhưng κ thấp nếu cả hai đều bias về một phía.

  Kết quả benchmark thực tế: κ = 0.0, Agreement Rate = 58.5% — phản ánh 2 judge dùng rubric khác nhau (accuracy vs tone) nên hiếm khi cho cùng category 1–5, dù vẫn có consensus qua weighted average.

- **Position Bias:** Judge LLM có thể thiên vị vị trí câu trả lời không? Nhóm xử lý ra sao?

  **Có.** Nhiều nghiên cứu cho thấy LLM-as-Judge thường **ưu tiên response xuất hiện trước** (primacy bias) hoặc response dài hơn.

  Nhóm triển khai `MultiModelJudge.check_position_bias()`:
  - Chấm cặp (A, B) theo thứ tự AB.
  - Đổi chỗ thành (B, A) và chấm lại.
  - `bias_score = |Δ_AB - Δ_BA| / 2` — càng gần 0 càng ít thiên vị.
  - Nếu `bias_score > 0.5` → `position_bias_detected = True`.

  **Mitigation trong production:** randomize thứ tự response, chấm 2 lần rồi lấy trung bình, hoặc dùng pairwise comparison thay vì listwise ranking.

- **Trade-off Chi phí vs Chất lượng:** Đề xuất giảm ~30% chi phí eval mà không giảm độ chính xác?

  Benchmark V2: **$0.001093** (7358 tokens) vs V1: **$0.001221** (8144 tokens) — đã giảm ~10.5% chi phí.

  Đề xuất giảm thêm ~30% tổng chi phí eval:

  | Chiến lược | Tiết kiệm | Impact chất lượng |
  |------------|-----------|-------------------|
  | **Tiered judging:** heuristic pre-filter, chỉ gọi LLM Judge khi heuristic score nằm trong vùng xám (2.5–3.5) | ~40% judge calls | Thấp — case rõ ràng pass/fail không cần LLM |
  | **Batch async** (đã có, batch_size=10) | Giảm overhead | Không ảnh hưởng |
  | **Cache judge results** theo hash(question+answer) | ~15% trên re-run | Không ảnh hưởng regression cùng dataset |
  | **RAGAS heuristic fallback** khi không có API key | 100% RAGAS cost | Chấp nhận được cho CI/CD; dùng RAGAS thật cho release gate |

  Kết hợp tiered judging + cache → ước tính giảm ~30% mà giữ nguyên accuracy trên edge cases.

## 4. Giải quyết Vấn đề (Problem Solving)

- **Vấn đề gặp phải:**
  1. Sau merge `main`, `MultiModelJudge` chỉ có Agreement Rate per-case, thiếu metric calibration chuẩn (Cohen's Kappa) mà rubric yêu cầu.
  2. Khi 2 Judge lệch > 1 điểm, cần quyết định lấy điểm nào — trung bình đơn giản có thể over-score câu trả lời sai nội dung nhưng đúng tone.
  3. Không có API key OpenAI trong môi trường lab → không thể gọi LLM Judge thật.

- **Cách xử lý:**
  1. Tạo module `judge_calibration.py` tách biệt, tính Kappa sau benchmark từ `individual_scores` đã có — không cần thay đổi runner.
  2. Conflict resolution dùng **conservative min** khi recall ground truth < 0.2, **weighted avg** khi answer có nội dung đúng — ưu tiên accuracy hơn tone.
  3. Dùng heuristic scoring (token overlap + tone markers) mô phỏng 2 model khác rubric, giữ nguyên architecture Multi-Judge để swap sang API thật sau.

- **Bài học rút ra:**
  - Evaluation pipeline nên **tách calibration analytics** khỏi scoring logic — dễ test và mở rộng.
  - Multi-Judge không chỉ là "2 model chấm rồi lấy TB" — cần **conflict policy** rõ ràng và metrics như Kappa để đo độ tin cậy.
  - Trong lab thiếu API, heuristic judge vẫn hữu ích để validate **architecture và data flow** trước khi deploy production.

## 5. Tự đánh giá
| Tiêu chí | Mức tự đánh giá (1-5) | Ghi chú |
|----------|:---------------------:|---------|
| Engineering Contribution | 4 | Triển khai Multi-Judge + Judge Calibration, tích hợp vào pipeline |
| Technical Depth | 4 | Giải thích MRR, Kappa, Position Bias, cost trade-off dựa trên code thực tế |
| Problem Solving | 4 | Xử lý conflict resolution và thiếu API key bằng heuristic fallback |
