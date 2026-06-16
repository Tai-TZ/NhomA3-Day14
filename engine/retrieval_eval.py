from typing import List, Dict, Any


class RetrievalEvaluator:
    """Đánh giá chất lượng Retrieval: Hit Rate @ top_k và MRR."""

    def calculate_hit_rate(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
        top_k: int = 3,
    ) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0

        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0

        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    def evaluate_single(
        self,
        expected_ids: List[str],
        retrieved_ids: List[str],
        top_k: int = 3,
    ) -> Dict[str, float]:
        hit_rate = self.calculate_hit_rate(expected_ids, retrieved_ids, top_k)
        mrr = self.calculate_mrr(expected_ids, retrieved_ids)
        return {"hit_rate": hit_rate, "mrr": round(mrr, 4)}

    async def evaluate_batch(
        self,
        dataset: List[Dict],
        responses: List[Dict],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Chạy eval cho toàn bộ bộ dữ liệu.
        Dataset cần trường 'expected_retrieval_ids', response cần 'retrieved_ids'.
        """
        if len(dataset) != len(responses):
            raise ValueError("dataset và responses phải có cùng số lượng phần tử")

        per_case = []
        for case, resp in zip(dataset, responses):
            expected = case.get("expected_retrieval_ids", [])
            retrieved = resp.get("retrieved_ids", [])
            scores = self.evaluate_single(expected, retrieved, top_k)
            per_case.append(
                {
                    "question": case.get("question", ""),
                    "expected_retrieval_ids": expected,
                    "retrieved_ids": retrieved[:top_k],
                    **scores,
                }
            )

        if not per_case:
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0, "total": 0, "per_case": []}

        avg_hit_rate = sum(c["hit_rate"] for c in per_case) / len(per_case)
        avg_mrr = sum(c["mrr"] for c in per_case) / len(per_case)

        return {
            "avg_hit_rate": round(avg_hit_rate, 4),
            "avg_mrr": round(avg_mrr, 4),
            "total": len(per_case),
            "per_case": per_case,
        }
