"""
Judge Calibration — Cohen's Kappa & Agreement analytics.
Module phụ trách: Ngô Thị Ánh (Multi-Judge Consensus).
"""
from typing import Dict, Any, List, Tuple


def _to_categories(scores: List[float], num_categories: int = 5) -> List[int]:
    return [max(1, min(num_categories, round(s))) for s in scores]


def cohens_kappa(
    scores_a: List[float],
    scores_b: List[float],
    num_categories: int = 5,
) -> float:
    """
    Cohen's Kappa — đo mức đồng thuận giữa 2 Judge vượt trên ngẫu nhiên.
    κ ≈ 1: đồng thuận hoàn hảo; κ ≈ 0: ngẫu nhiên; κ < 0: tệ hơn ngẫu nhiên.
    """
    if not scores_a or not scores_b or len(scores_a) != len(scores_b):
        return 0.0

    n = len(scores_a)
    cats_a = _to_categories(scores_a, num_categories)
    cats_b = _to_categories(scores_b, num_categories)

    po = sum(1 for i in range(n) if cats_a[i] == cats_b[i]) / n

    pe = 0.0
    for cat in range(1, num_categories + 1):
        pa = sum(1 for x in cats_a if x == cat) / n
        pb = sum(1 for x in cats_b if x == cat) / n
        pe += pa * pb

    if abs(1.0 - pe) < 1e-9:
        return 1.0 if po == 1.0 else 0.0

    return round((po - pe) / (1.0 - pe), 4)


def agreement_rate_batch(scores_a: List[float], scores_b: List[float]) -> float:
    """Agreement Rate trung bình theo từng cặp điểm (per-case)."""
    if not scores_a or len(scores_a) != len(scores_b):
        return 0.0

    rates = []
    for a, b in zip(scores_a, scores_b):
        diff = abs(a - b)
        if diff == 0:
            rates.append(1.0)
        elif diff <= 0.5:
            rates.append(0.85)
        elif diff <= 1.0:
            rates.append(0.6)
        else:
            rates.append(0.3)

    return round(sum(rates) / len(rates), 4)


def extract_judge_scores(results: List[Dict]) -> Tuple[List[float], List[float]]:
    """Trích điểm từng Judge từ benchmark results."""
    scores_a, scores_b = [], []
    for r in results:
        individual = r.get("judge", {}).get("individual_scores", {})
        if not individual:
            continue
        keys = list(individual.keys())
        if len(keys) >= 2:
            scores_a.append(individual[keys[0]])
            scores_b.append(individual[keys[1]])
    return scores_a, scores_b


class JudgeCalibration:
    """Tổng hợp metrics calibration sau benchmark."""

    @staticmethod
    def summarize(results: List[Dict]) -> Dict[str, Any]:
        scores_a, scores_b = extract_judge_scores(results)

        if not scores_a:
            return {
                "cohens_kappa": 0.0,
                "agreement_rate": 0.0,
                "conflict_count": 0,
                "conflict_rate": 0.0,
                "avg_score_delta": 0.0,
                "judge_a_mean": 0.0,
                "judge_b_mean": 0.0,
            }

        conflicts = sum(1 for r in results if r.get("judge", {}).get("conflict_resolved"))
        deltas = [r.get("judge", {}).get("score_delta", 0) for r in results]

        return {
            "cohens_kappa": cohens_kappa(scores_a, scores_b),
            "agreement_rate": agreement_rate_batch(scores_a, scores_b),
            "conflict_count": conflicts,
            "conflict_rate": round(conflicts / len(results), 4),
            "avg_score_delta": round(sum(deltas) / len(deltas), 4),
            "judge_a_mean": round(sum(scores_a) / len(scores_a), 3),
            "judge_b_mean": round(sum(scores_b) / len(scores_b), 3),
        }
