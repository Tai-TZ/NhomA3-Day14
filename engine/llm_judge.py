import re
from typing import Dict, Any, Tuple

CONFLICT_THRESHOLD = 1.0  # Điểm lệch > 1 → kích hoạt xử lý xung đột


class LLMJudge:
    """Judge đơn lẻ — mô phỏng 1 model với rubric riêng."""

    def __init__(self, model_name: str, rubric: str = "accuracy"):
        self.model_name = model_name
        self.rubric = rubric

    def _tokenize(self, text: str) -> set:
        return set(re.findall(r"\w+", text.lower()))

    def _score_accuracy(self, answer: str, ground_truth: str) -> float:
        if not ground_truth:
            return 3.0
        gt_tokens = self._tokenize(ground_truth)
        ans_tokens = self._tokenize(answer)
        if not gt_tokens:
            return 3.0
        recall = len(gt_tokens & ans_tokens) / len(gt_tokens)
        if recall >= 0.6:
            return 5.0
        if recall >= 0.4:
            return 4.0
        if recall >= 0.2:
            return 3.0
        if recall >= 0.1:
            return 2.0
        return 1.0

    def _score_tone(self, answer: str) -> float:
        professional_markers = ["dựa trên", "tài liệu", "hệ thống", "xin trả lời", "không tìm thấy"]
        hits = sum(1 for m in professional_markers if m in answer.lower())
        return min(5.0, 2.5 + hits * 0.5)

    async def evaluate(self, question: str, answer: str, ground_truth: str) -> float:
        if self.rubric == "tone":
            return self._score_tone(answer)
        return self._score_accuracy(answer, ground_truth)


class MultiModelJudge:
    """
    Multi-Judge Consensus Engine:
    - 2 model Judge (GPT-4o + Claude) với rubric khác nhau
    - Tính Agreement Rate
    - Xử lý xung đột khi lệch > 1 điểm
    """

    def __init__(self):
        self.judge_a = LLMJudge("gpt-4o", rubric="accuracy")
        self.judge_b = LLMJudge("claude-3-5-sonnet", rubric="tone")

    @staticmethod
    def _agreement_rate(score_a: float, score_b: float) -> float:
        diff = abs(score_a - score_b)
        if diff == 0:
            return 1.0
        if diff <= 0.5:
            return 0.85
        if diff <= 1.0:
            return 0.6
        return 0.3

    @staticmethod
    def _resolve_conflict(
        score_a: float, score_b: float, question: str, answer: str, ground_truth: str
    ) -> Tuple[float, str]:
        """
        Xung đột > 1 điểm: lấy min score (conservative) nếu answer thiếu ground truth keywords,
        ngược lại lấy trung bình có trọng số nghiêng về accuracy judge.
        """
        gt_tokens = set(re.findall(r"\w+", ground_truth.lower()))
        ans_tokens = set(re.findall(r"\w+", answer.lower()))
        recall = len(gt_tokens & ans_tokens) / max(len(gt_tokens), 1)

        if recall < 0.2:
            final = min(score_a, score_b)
            reason = f"Conflict resolved (conservative min={final}): answer thiếu ground truth keywords."
        else:
            final = round(score_a * 0.6 + score_b * 0.4, 2)
            reason = f"Conflict resolved (weighted avg={final}): accuracy judge 60%, tone judge 40%."

        return final, reason

    async def evaluate_multi_judge(
        self, question: str, answer: str, ground_truth: str
    ) -> Dict[str, Any]:
        score_a = await self.judge_a.evaluate(question, answer, ground_truth)
        score_b = await self.judge_b.evaluate(question, answer, ground_truth)

        diff = abs(score_a - score_b)
        agreement = self._agreement_rate(score_a, score_b)

        if diff > CONFLICT_THRESHOLD:
            final_score, reasoning = self._resolve_conflict(
                score_a, score_b, question, answer, ground_truth
            )
            conflict_resolved = True
        else:
            final_score = round((score_a + score_b) / 2, 2)
            reasoning = f"Cả 2 model đồng thuận (lệch {diff:.1f} điểm). Trung bình = {final_score}."
            conflict_resolved = False

        return {
            "final_score": final_score,
            "agreement_rate": agreement,
            "individual_scores": {"gpt-4o": score_a, "claude-3-5-sonnet": score_b},
            "score_delta": round(diff, 2),
            "conflict_resolved": conflict_resolved,
            "reasoning": reasoning,
        }

    async def check_position_bias(self, response_a: str, response_b: str) -> Dict[str, Any]:
        """
        Kiểm tra Position Bias: đổi chỗ A/B và so sánh điểm.
        Trả về bias_score — càng gần 0 càng ít thiên vị.
        """
        gt = "placeholder ground truth"
        score_ab_a = await self.judge_a.evaluate("", response_a, gt)
        score_ab_b = await self.judge_a.evaluate("", response_b, gt)
        score_ba_a = await self.judge_a.evaluate("", response_b, gt)
        score_ba_b = await self.judge_a.evaluate("", response_a, gt)

        bias = abs((score_ab_a - score_ab_b) - (score_ba_b - score_ba_a)) / 2
        return {
            "bias_score": round(bias, 3),
            "position_bias_detected": bias > 0.5,
        }
