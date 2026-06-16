from typing import Dict, Any, Optional


class ReleaseGate:
    """
    Regression Release Gate — tự động quyết định APPROVE / BLOCK dựa trên
    chất lượng, retrieval, chi phí và hiệu năng.
    """

    DEFAULT_THRESHOLDS = {
        "min_avg_score": 3.0,
        "min_hit_rate": 0.65,
        "min_mrr": 0.45,
        "min_agreement_rate": 0.5,
        "max_cost_increase_pct": 0.25,
        "max_latency_increase_pct": 0.30,
        "min_score_delta": 0.0,
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

    @staticmethod
    def _pct_change(old: float, new: float) -> float:
        if old == 0:
            return 0.0 if new == 0 else 1.0
        return (new - old) / old

    def evaluate(self, v1_summary: Dict, v2_summary: Dict) -> Dict[str, Any]:
        v1m = v1_summary["metrics"]
        v2m = v2_summary["metrics"]
        t = self.thresholds

        checks = []

        score_delta = v2m["avg_score"] - v1m["avg_score"]
        checks.append({
            "name": "score_delta",
            "passed": score_delta >= t["min_score_delta"],
            "value": round(score_delta, 3),
            "threshold": t["min_score_delta"],
        })

        checks.append({
            "name": "min_avg_score",
            "passed": v2m["avg_score"] >= t["min_avg_score"],
            "value": round(v2m["avg_score"], 3),
            "threshold": t["min_avg_score"],
        })

        checks.append({
            "name": "min_hit_rate",
            "passed": v2m["hit_rate"] >= t["min_hit_rate"],
            "value": round(v2m["hit_rate"], 3),
            "threshold": t["min_hit_rate"],
        })

        checks.append({
            "name": "min_mrr",
            "passed": v2m.get("avg_mrr", 0) >= t["min_mrr"],
            "value": round(v2m.get("avg_mrr", 0), 3),
            "threshold": t["min_mrr"],
        })

        checks.append({
            "name": "min_agreement_rate",
            "passed": v2m["agreement_rate"] >= t["min_agreement_rate"],
            "value": round(v2m["agreement_rate"], 3),
            "threshold": t["min_agreement_rate"],
        })

        cost_change = self._pct_change(
            v1m.get("estimated_cost_usd", 0),
            v2m.get("estimated_cost_usd", 0),
        )
        checks.append({
            "name": "max_cost_increase",
            "passed": cost_change <= t["max_cost_increase_pct"],
            "value": round(cost_change, 3),
            "threshold": t["max_cost_increase_pct"],
        })

        v1_dur = v1_summary["metadata"].get("benchmark_duration_sec", 0)
        v2_dur = v2_summary["metadata"].get("benchmark_duration_sec", 0)
        latency_change = self._pct_change(v1_dur, v2_dur)
        checks.append({
            "name": "max_latency_increase",
            "passed": latency_change <= t["max_latency_increase_pct"],
            "value": round(latency_change, 3),
            "threshold": t["max_latency_increase_pct"],
        })

        all_passed = all(c["passed"] for c in checks)
        failed = [c["name"] for c in checks if not c["passed"]]

        return {
            "decision": "APPROVE" if all_passed else "BLOCK",
            "score_delta": round(score_delta, 3),
            "checks": checks,
            "failed_checks": failed,
            "v1_version": v1_summary["metadata"]["version"],
            "v2_version": v2_summary["metadata"]["version"],
        }
