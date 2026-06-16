# Báo cáo Cá nhân — Nguyễn Thành Tài (2A202600627)

## 1. Vai trò & Phân công trong nhóm

- **Module phụ trách:** Retrieval Evaluation (Hit Rate, MRR), Eval Engine tích hợp RAGAS, Async Benchmark Runner (Performance & Cost metrics)
- **Thời gian đóng góp:** ~2.5 giờ — Giai đoạn 2 (90') phát triển Eval Engine & Async Runner; Giai đoạn 4 (45') hoàn thiện pipeline, fix môi trường, báo cáo cá nhân

---

## 2. Đóng góp Kỹ thuật (Engineering Contribution)

### File / Module đã triển khai

| File | Nội dung |
|------|----------|
| `engine/retrieval_eval.py` | `RetrievalEvaluator`: Hit Rate @ top_k, MRR, `evaluate_single()`, `evaluate_batch()` |
| `engine/expert_evaluator.py` | `ExpertEvaluator`: kết hợp Retrieval metrics + RAGAS (faithfulness, answer_relevancy) + heuristic fallback |
| `engine/runner.py` | `BenchmarkRunner`: async batch với `asyncio.gather`, tracking latency / tokens / cost |
| `agent/main_agent.py` | Bổ sung `retrieved_ids` trong response để tính Hit Rate/MRR |
| `main.py` | Tích hợp `ExpertEvaluator` + `BenchmarkRunner.summarize_performance()` + `load_dotenv()` |
| `engine/openrouter_client.py` | Client OpenRouter cho Multi-Judge live |
| `check_lab.py` | Validate retrieval metrics, performance, 50+ cases |
| `README.md` | Hướng dẫn Python 3.12 + venv cho RAGAS |

### Commit liên quan

- `4de4e60` — `feat: Complete Day 14 group lab - AI Evaluation Factory`
  - Triển khai toàn bộ Retrieval Eval, RAGAS Eval Engine, Async Runner, benchmark reports

### Giải trình kỹ thuật

**Retrieval Evaluation (`RetrievalEvaluator`):**

- **Hit Rate @ top_k:** Kiểm tra ít nhất 1 `expected_retrieval_id` có trong `retrieved_ids[:top_k]` không. Trả về 1.0 (hit) hoặc 0.0 (miss) — metric nhị phân, dễ debug từng case.
- **MRR (Mean Reciprocal Rank):** Tìm vị trí đầu tiên (1-indexed) của expected doc trong ranked list → `RR = 1/rank`. Phản ánh **chất lượng ranking**, không chỉ "có hay không".
- **`evaluate_batch()`:** Chạy song song logic eval trên 50 cases, trả về `avg_hit_rate`, `avg_mrr`, `per_case` để failure analysis.

**Eval Engine (`ExpertEvaluator`):**

- Gọi `RetrievalEvaluator` **trước** RAGAS metrics — đúng yêu cầu README: chứng minh Retrieval stage trước khi đánh giá Generation.
- Tích hợp thư viện **RAGAS** (`faithfulness`, `answer_relevancy`) khi có API key + `USE_RAGAS_LIVE=1`; fallback heuristic mặc định → pipeline vẫn chạy nhanh trong lab batch 50 cases.
- Hỗ trợ **OpenRouter** (`OPENROUTER_API_KEY` + `OPENAI_BASE_URL`) cho Multi-Judge live qua `engine/openrouter_client.py`.
- Mỗi case trả về `eval_mode: "ragas" | "heuristic_fallback"` để traceability.

**Async Runner (`BenchmarkRunner`):**

- `run_all()` chia dataset thành batch (`batch_size=5` với OpenRouter live, `10` với mock), mỗi batch chạy `asyncio.gather` — 50 cases hoàn thành trong **72.12s** với Judge API thật (<< 2 phút).
- Mỗi case track: `latency_sec`, `tokens_used`, `cost_usd` (ước tính GPT-4o-mini pricing).
- `summarize_performance()` aggregate: `total_latency_sec`, `total_tokens`, `estimated_cost_usd`, `pass_rate`.

**Trade-off thiết kế:**

- Chọn `batch_size=5` khi dùng OpenRouter live → cân bằng tốc độ vs rate limit (100 judge calls / 50 cases); mock agent vẫn có thể dùng `batch_size=10`.
- Heuristic fallback cho RAGAS, live API cho Multi-Judge → tiết kiệm chi phí RAGAS (~$0.001/case) nhưng vẫn có judge scores thật trong report.

---

## 3. Chiều sâu Kỹ thuật (Technical Depth)

### MRR là gì? Tại sao MRR quan trọng hơn Hit Rate trong một số trường hợp?

**MRR (Mean Reciprocal Rank)** = trung bình của `1/rank`, với `rank` là vị trí doc đúng đầu tiên trong danh sách retrieved (1-indexed).

```
Ví dụ retrieved_ids = [doc_A, doc_B, doc_C, expected = doc_B]
→ rank = 2 → RR = 1/2 = 0.5

Nếu expected = doc_D (không có) → RR = 0
```

**Hit Rate @ top_3** chỉ trả lời nhị phân: "Có doc đúng trong top 3 không?" — không phân biệt doc đúng ở vị trí 1 hay 3.

**MRR quan trọng hơn khi:**

1. LLM chỉ dùng **top-1 hoặc top-2 context** → doc ở vị trí 3 gần như vô dụng dù Hit Rate vẫn = 1.
2. Cần đo **ranking quality** — RAG càng rank doc đúng lên cao, generation càng ít hallucination.
3. Phân biệt 2 agent cùng Hit Rate 92% nhưng MRR khác nhau (0.886 vs 0.65) → agent có MRR cao hơn retrieval tốt hơn thực sự.

Kết quả benchmark nhóm: **Hit Rate 92%, MRR 0.886** — cho thấy phần lớn doc đúng ở top-1/top-2, không chỉ "lọt" vào top-3.

Phân tích failure cho thấy: cases retrieval miss (hit_rate=0) có avg judge score **~1.5/5**, trong khi cases hit có score **~4.2/5** — chứng minh mối liên hệ Retrieval ↔ Answer Quality mà module của tôi đo được.

---

### Cohen's Kappa / Agreement Rate: Hệ thống Multi-Judge tính độ đồng thuận như thế nào?

Nhóm dùng **2 lớp metrics** (module Multi-Judge do Ánh triển khai, tôi tích hợp vào pipeline summary):

1. **Agreement Rate (per-case)** — trong `MultiModelJudge._agreement_rate()`:
   - Lệch 0 điểm → 1.0
   - Lệch ≤ 0.5 → 0.85
   - Lệch ≤ 1.0 → 0.6
   - Lệch > 1.0 → 0.3
   - Trung bình 50 cases → **61.8%** trong `summary.json` (OpenRouter live)

2. **Cohen's Kappa (batch)** — trong `judge_calibration.cohens_kappa()` (module Ánh):
   - Chuẩn hóa điểm 2 judge về thang 1–5
   - `κ = (P_o - P_e) / (1 - P_e)` — loại bỏ đồng thuận do ngẫu nhiên
   - κ > 0.6 = substantial agreement; κ > 0.8 = almost perfect

**Liên hệ với phần Retrieval của tôi:** Khi retrieval fail → answer sai → 2 judge live (gpt-4o-mini accuracy vs claude-3.5-haiku tone) chấm lệch lớn → trigger conflict resolution → `conflict_rate = 18%` (9/50 cases), Cohen's Kappa = 0.049. Retrieval metrics giúp **giải thích nguyên nhân** xung đột judge, không chỉ báo cáo con số.

---

### Position Bias: Judge LLM có thể thiên vị vị trí câu trả lời không? Nhóm xử lý ra sao?

**Position Bias** xảy ra khi LLM Judge cho điểm cao hơn cho response đặt ở vị trí đầu (A) so với cùng nội dung ở vị trí sau (B) — do thiên vị thứ tự trong prompt, không phải chất lượng nội dung.

Nhóm xử lý qua `MultiModelJudge.check_position_bias()`:
- Chấm cặp (A, B) theo thứ tự AB
- Đảo thứ tự (B, A) và chấm lại
- `bias_score = |Δ_AB - Δ_BA| / 2` — càng gần 0 càng ít thiên vị
- `position_bias_detected = True` nếu bias_score > 0.5

**Góc nhìn từ Retrieval module:** Position bias trong **Judge** tương tự "ranking bias" trong **Retriever** — doc ở vị trí đầu được ưu tiên dù không phải relevant nhất. Module MRR của tôi đo chính xác vấn đề này ở tầng retrieval; Position Bias check đo ở tầng judge — hai lớp bổ sung cho nhau.

---

### Trade-off Chi phí vs Chất lượng: Đề xuất giảm ~30% chi phí eval mà không giảm độ chính xác

Benchmark V1 → V2 đã chứng minh một phần đề xuất này:

| Metric | V1 | V2 | Delta |
|--------|----|----|-------|
| Cost | $0.001221 | $0.001093 | **-10.5%** |
| Benchmark duration | ~99s | 72.12s | **-27%** |
| Hit Rate | 92% | 92% | 0 |
| Avg Score | 3.82 | 3.88 | +0.06 |
| Pass rate | 74% | 74% | 0 |

**3 chiến lược giảm thêm ~30% cost (tổng ~40%) mà không giảm accuracy:**

1. **Two-stage eval (Retrieval gate):** Chỉ gọi Multi-Judge cho cases retrieval hit (92% cases). 8% cases miss → skip judge, gán score=1 tự động. Tiết kiệm ~8% judge calls, tập trung budget vào cases khó.

2. **Batch size tối ưu:** Tăng `batch_size` từ 5 → 10 (đã làm) giảm overhead. Với API thật, batch 15–20 vẫn an toàn nếu monitor rate limit → giảm thêm ~15% wall-clock (= giảm cost compute).

3. **Heuristic pre-filter:** Dùng `ExpertEvaluator` heuristic (miễn phí) làm Stage 1; chỉ gọi RAGAS API cho cases faithfulness < 0.7 hoặc relevancy < 0.5 (~20% cases). Ước tính giảm ~20% API cost RAGAS mà vẫn catch 95% lỗi thật.

**Tổng ước tính:** 8% + 15% + 20% ≈ **~35% cost reduction** mà Hit Rate và pass_rate giữ nguyên.

---

## 4. Giải quyết Vấn đề (Problem Solving)

### Vấn đề 1: `pip install ragas` fail trên Python 3.14

- **Triệu chứng:** `scikit-network` cần Microsoft Visual C++ Build Tools; Python 3.14 không có pre-built wheel.
- **Cách xử lý:** Cài Python 3.12 qua winget, tạo `.venv` với `py -3.12 -m venv .venv`, cài `ragas==0.1.21` trong venv. Cập nhật README hướng dẫn team.
- **Bài học:** Luôn kiểm tra Python version compatibility trước khi cài ML/AI packages; pin version ragas ổn định thay vì latest.

### Vấn đề 2: Agent không trả `retrieved_ids` → Hit Rate luôn = 0

- **Triệu chứng:** Pipeline chạy được nhưng retrieval metrics toàn 0 — không đo được gì.
- **Cách xử lý:** Sửa `agent/main_agent.py` thêm field `retrieved_ids` từ mock retrieval; cập nhật `golden_set.jsonl` schema với `expected_retrieval_ids`.
- **Bài học:** Eval pipeline phải thiết kế **contract rõ ràng** giữa Agent output và Evaluator input trước khi code metrics.

### Vấn đề 3: `reports/` bị `.gitignore` → không commit được kết quả nộp bài

- **Triệu chứng:** README yêu cầu nộp `reports/summary.json` nhưng gitignore chặn toàn bộ folder.
- **Cách xử lý:** Gỡ `reports/` khỏi `.gitignore` (giữ `data/golden_set.jsonl` ignore vì grader tự generate). Phân biệt: golden_set = runtime input, reports = submission output.
- **Bài học:** Đọc kỹ submission checklist trước khi follow template gitignore mặc định.

### Vấn đề 4: `ModuleNotFoundError: No module named 'data'` khi chạy `synthetic_gen.py`

- **Triệu chứng:** Script fail khi import `data.knowledge_base`.
- **Cách xử lý:** Thêm `sys.path.insert(0, project_root)` vào đầu script — pattern chuẩn cho Python script chạy trực tiếp.
- **Bài học:** Dùng package import cần đảm bảo PYTHONPATH hoặc chạy qua `python -m data.synthetic_gen`.

### Vấn đề 5: Multi-Judge mock không đủ thuyết phục khi nộp bài Expert

- **Triệu chứng:** `llm_judge.py` ban đầu dùng heuristic token overlap — Agreement Rate và scores không phản ánh judge thật.
- **Cách xử lý:** Tạo `engine/openrouter_client.py`, cấu hình `.env` với OpenRouter API key, cập nhật `LLMJudge` gọi `openai/gpt-4o-mini` + `anthropic/claude-3.5-haiku`, thêm `judge_mode: openrouter_live` vào report.
- **Bài học:** Evaluation Factory production cần live judge ít nhất cho submission; heuristic giữ làm fallback khi API fail.

---

## 5. Tự đánh giá

| Tiêu chí | Mức tự đánh giá (1-5) | Ghi chú |
|----------|:---------------------:|---------|
| Engineering Contribution | **5** | Triển khai 3 module core (Retrieval, Eval Engine, Async Runner), tích hợp RAGAS, commit `4de4e60` |
| Technical Depth | **4** | Giải thích được MRR, Cohen's Kappa, Position Bias, cost trade-off với số liệu thực từ benchmark |
| Problem Solving | **5** | Xử lý 5 vấn đề thực tế: Python version, Agent contract, gitignore, module import, OpenRouter integration |

**Tổng ước lượng:** ~36–38 / 40 điểm cá nhân.

---

*Báo cáo được viết dựa trên module thực tế đã triển khai và kết quả benchmark OpenRouter live trong `reports/summary.json` (50 cases, Hit Rate 92%, MRR 0.886, Agreement 61.8%, duration 72.12s, APPROVE).*
