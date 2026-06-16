import os
from typing import Dict, Any, Optional

from engine.retrieval_eval import RetrievalEvaluator

# RAGAS — Giai đoạn 2 README: Eval Engine (RAGAS, Custom Judge)
try:
    from datasets import Dataset
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import faithfulness, answer_relevancy

    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False


class ExpertEvaluator:
    """
    Eval Engine kết hợp:
    - Retrieval metrics (Hit Rate, MRR) — custom
    - RAGAS metrics (faithfulness, answer_relevancy) — khi có OPENAI_API_KEY
    - Heuristic fallback — khi không có API key
    """

    def __init__(self, top_k: int = 3, use_ragas: bool = True):
        self.retrieval = RetrievalEvaluator()
        self.top_k = top_k
        has_api = bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"))
        self.use_ragas = use_ragas and RAGAS_AVAILABLE and has_api and os.getenv("USE_RAGAS_LIVE") == "1"

    def _heuristic_faithfulness(self, answer: str, contexts: list) -> float:
        if not answer or not contexts:
            return 0.0
        answer_words = set(answer.lower().split())
        context_text = " ".join(c for c in contexts if c).lower()
        context_words = set(context_text.split())
        if not answer_words:
            return 0.0
        overlap = len(answer_words & context_words) / len(answer_words)
        return round(min(1.0, 0.5 + overlap * 0.5), 4)

    def _heuristic_relevancy(self, question: str, answer: str) -> float:
        if not question or not answer:
            return 0.0
        q_words = set(question.lower().split())
        a_words = set(answer.lower().split())
        if not q_words:
            return 0.0
        overlap = len(q_words & a_words) / len(q_words)
        return round(min(1.0, 0.4 + overlap * 0.6), 4)

    def _ragas_score(
        self, question: str, answer: str, contexts: list, ground_truth: str
    ) -> Optional[Dict[str, float]]:
        if not self.use_ragas:
            return None

        try:
            ctx_list = [c for c in contexts if c] or [""]
            dataset = Dataset.from_dict(
                {
                    "question": [question],
                    "answer": [answer],
                    "contexts": [ctx_list],
                    "ground_truth": [ground_truth or answer],
                }
            )
            result = ragas_evaluate(dataset, metrics=[faithfulness, answer_relevancy])
            scores = result.to_pandas().iloc[0]
            return {
                "faithfulness": round(float(scores.get("faithfulness", 0) or 0), 4),
                "relevancy": round(float(scores.get("answer_relevancy", 0) or 0), 4),
            }
        except Exception:
            return None

    async def score(self, case: Dict, response: Dict) -> Dict[str, Any]:
        expected = case.get("expected_retrieval_ids", [])
        retrieved = response.get("retrieved_ids", [])
        retrieval_scores = self.retrieval.evaluate_single(expected, retrieved, self.top_k)

        contexts = response.get("contexts", [])
        answer = response.get("answer", "")
        question = case.get("question", "")
        ground_truth = case.get("expected_answer", "")

        ragas_scores = self._ragas_score(question, answer, contexts, ground_truth)
        if ragas_scores:
            eval_mode = "ragas"
            faithfulness_score = ragas_scores["faithfulness"]
            relevancy_score = ragas_scores["relevancy"]
        else:
            eval_mode = "heuristic_fallback"
            faithfulness_score = self._heuristic_faithfulness(answer, contexts)
            relevancy_score = self._heuristic_relevancy(question, answer)

        return {
            "faithfulness": faithfulness_score,
            "relevancy": relevancy_score,
            "retrieval": retrieval_scores,
            "eval_mode": eval_mode,
            "ragas_available": RAGAS_AVAILABLE,
        }
