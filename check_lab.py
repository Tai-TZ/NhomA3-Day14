import json
import os


def validate_lab():
    print("🔍 Đang kiểm tra định dạng bài nộp...")

    required_files = [
        "reports/summary.json",
        "reports/benchmark_results.json",
        "analysis/failure_analysis.md",
    ]

    missing = []
    for f in required_files:
        if os.path.exists(f):
            print(f"✅ Tìm thấy: {f}")
        else:
            print(f"❌ Thiếu file: {f}")
            missing.append(f)

    if missing:
        print(f"\n❌ Thiếu {len(missing)} file. Hãy bổ sung trước khi nộp bài.")
        return

    try:
        with open("reports/summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ File reports/summary.json không phải JSON hợp lệ: {e}")
        return

    if "metrics" not in data or "metadata" not in data:
        print("❌ File summary.json thiếu trường 'metrics' hoặc 'metadata'.")
        return

    metrics = data["metrics"]
    total = data["metadata"].get("total", 0)

    print(f"\n--- Thống kê nhanh ---")
    print(f"Tổng số cases: {total}")
    print(f"Điểm trung bình: {metrics.get('avg_score', 0):.2f}")

    if total >= 50:
        print(f"✅ Dataset đủ 50+ cases ({total})")
    else:
        print(f"⚠️ CẢNH BÁO: Dataset chỉ có {total} cases (yêu cầu ≥50).")

    if "hit_rate" in metrics:
        print(f"✅ Retrieval Metrics — Hit Rate: {metrics['hit_rate']*100:.1f}%, MRR: {metrics.get('avg_mrr', 0):.3f}")
    else:
        print("⚠️ CẢNH BÁO: Thiếu Retrieval Metrics (hit_rate).")

    if "agreement_rate" in metrics:
        print(f"✅ Multi-Judge Metrics — Agreement Rate: {metrics['agreement_rate']*100:.1f}%")
    else:
        print("⚠️ CẢNH BÁO: Thiếu Multi-Judge Metrics (agreement_rate).")

    if data["metadata"].get("version"):
        print("✅ Regression Mode — có thông tin phiên bản Agent")

    if "regression" in data and "gate_result" in data["regression"]:
        decision = data["regression"]["gate_result"].get("decision", "N/A")
        print(f"✅ Release Gate — quyết định: {decision}")

    if metrics.get("estimated_cost_usd") is not None:
        print(f"✅ Cost Report — ${metrics['estimated_cost_usd']:.6f}, {metrics.get('total_tokens', 0)} tokens")

    duration = data["metadata"].get("benchmark_duration_sec", 0)
    if duration > 0 and total >= 50:
        if duration < 120:
            print(f"✅ Performance — {duration}s cho {total} cases (< 2 phút)")
        else:
            print(f"⚠️ Performance — {duration}s cho {total} cases (vượt 2 phút)")

    print("\n🚀 Bài lab đã sẵn sàng để chấm điểm!")


if __name__ == "__main__":
    validate_lab()
