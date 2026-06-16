import asyncio
import time
from typing import List, Dict, Any

# GPT-4o-mini: ~$0.15 / 1M input tokens
COST_PER_TOKEN_USD = 0.00000015


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge, batch_size: int = 5):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge
        self.batch_size = batch_size

    @staticmethod
    def _estimate_cost(tokens: int) -> float:
        return round(tokens * COST_PER_TOKEN_USD, 6)

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        response = await self.agent.query(test_case["question"])
        latency = round(time.perf_counter() - start_time, 4)

        ragas_scores = await self.evaluator.score(test_case, response)

        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"],
        )

        tokens_used = response.get("metadata", {}).get("tokens_used", 0)

        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "retrieved_ids": response.get("retrieved_ids", []),
            "latency_sec": latency,
            "tokens_used": tokens_used,
            "cost_usd": self._estimate_cost(tokens_used),
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass",
        }

    async def run_all(self, dataset: List[Dict]) -> List[Dict]:
        """
        Chạy song song bằng asyncio.gather với giới hạn batch_size để tránh Rate Limit.
        """
        results = []
        total_batches = (len(dataset) + self.batch_size - 1) // self.batch_size

        for batch_idx, i in enumerate(range(0, len(dataset), self.batch_size), start=1):
            batch = dataset[i : i + self.batch_size]
            batch_start = time.perf_counter()
            tasks = [self.run_single_test(case) for case in batch]
            batch_results = await asyncio.gather(*tasks)
            batch_elapsed = round(time.perf_counter() - batch_start, 3)
            print(f"  Batch {batch_idx}/{total_batches}: {len(batch)} cases in {batch_elapsed}s")
            results.extend(batch_results)

        return results

    @staticmethod
    def summarize_performance(results: List[Dict]) -> Dict[str, Any]:
        if not results:
            return {
                "total_latency_sec": 0.0,
                "avg_latency_sec": 0.0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "pass_rate": 0.0,
            }

        total_latency = sum(r["latency_sec"] for r in results)
        total_tokens = sum(r["tokens_used"] for r in results)
        total_cost = sum(r["cost_usd"] for r in results)
        passed = sum(1 for r in results if r["status"] == "pass")

        return {
            "total_latency_sec": round(total_latency, 3),
            "avg_latency_sec": round(total_latency / len(results), 4),
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(total_cost, 6),
            "pass_rate": round(passed / len(results), 4),
        }
