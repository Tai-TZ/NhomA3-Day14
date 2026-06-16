import asyncio
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

from engine.runner import BenchmarkRunner
from engine.expert_evaluator import ExpertEvaluator
from engine.llm_judge import MultiModelJudge
from engine.judge_calibration import JudgeCalibration
from engine.release_gate import ReleaseGate
from agent.main_agent import MainAgent, MainAgentV2


async def run_benchmark_with_results(agent, agent_version: str):
    print(f"🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    print(f"  Dataset: {len(dataset)} cases")

    runner = BenchmarkRunner(
        agent,
        ExpertEvaluator(top_k=3),
        MultiModelJudge(),
        batch_size=5,
    )

    bench_start = time.perf_counter()
    results = await runner.run_all(dataset)
    bench_elapsed = round(time.perf_counter() - bench_start, 3)

    total = len(results)
    performance = BenchmarkRunner.summarize_performance(results)
    calibration = JudgeCalibration.summarize(results)

    summary = {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "benchmark_duration_sec": bench_elapsed,
        },
        "metrics": {
            "avg_score": round(sum(r["judge"]["final_score"] for r in results) / total, 3),
            "hit_rate": round(sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total, 4),
            "avg_mrr": round(sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total, 4),
            "agreement_rate": round(sum(r["judge"]["agreement_rate"] for r in results) / total, 4),
            "avg_faithfulness": round(sum(r["ragas"]["faithfulness"] for r in results) / total, 4),
            "avg_relevancy": round(sum(r["ragas"]["relevancy"] for r in results) / total, 4),
            "conflicts_resolved": sum(1 for r in results if r["judge"].get("conflict_resolved")),
            "cohens_kappa": calibration["cohens_kappa"],
            "conflict_rate": calibration["conflict_rate"],
            **performance,
        },
        "judge_calibration": calibration,
    }
    return results, summary


async def run_benchmark(agent, version: str):
    _, summary = await run_benchmark_with_results(agent, version)
    return summary


async def main():
    v1_summary = await run_benchmark(MainAgent(version="v1"), "Agent_V1_Base")
    v2_results, v2_summary = await run_benchmark_with_results(
        MainAgentV2(), "Agent_V2_Optimized"
    )

    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    gate = ReleaseGate()
    gate_result = gate.evaluate(v1_summary, v2_summary)

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION) ---")
    print(f"V1 Score:       {v1_summary['metrics']['avg_score']:.2f}")
    print(f"V2 Score:       {v2_summary['metrics']['avg_score']:.2f}")
    print(f"Hit Rate:       {v2_summary['metrics']['hit_rate']*100:.1f}%")
    print(f"Avg MRR:        {v2_summary['metrics']['avg_mrr']:.3f}")
    print(f"Agreement Rate: {v2_summary['metrics']['agreement_rate']*100:.1f}%")
    print(f"Cohen's Kappa:  {v2_summary['metrics'].get('cohens_kappa', 0):.3f}")
    print(f"Latency:        {v2_summary['metadata']['benchmark_duration_sec']}s total")
    print(f"Cost:           ${v2_summary['metrics']['estimated_cost_usd']:.6f}")
    print(f"Delta Score:    {'+' if gate_result['score_delta'] >= 0 else ''}{gate_result['score_delta']:.2f}")

    print("\n🚦 --- RELEASE GATE ---")
    for check in gate_result["checks"]:
        icon = "✅" if check["passed"] else "❌"
        print(f"  {icon} {check['name']}: {check['value']} (ngưỡng: {check['threshold']})")

    decision = gate_result["decision"]
    if decision == "APPROVE":
        print("\n✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
    else:
        print(f"\n❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK) — failed: {gate_result['failed_checks']}")

    os.makedirs("reports", exist_ok=True)

    v2_summary["regression"] = {
        "v1": v1_summary["metrics"],
        "gate_result": gate_result,
    }

    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Reports saved to reports/")


if __name__ == "__main__":
    asyncio.run(main())
