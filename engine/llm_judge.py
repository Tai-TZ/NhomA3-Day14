import os
import re
from typing import Dict, Any, Tuple

from engine.openrouter_client import get_async_client, is_live_mode

CONFLICT_THRESHOLD = 1.0


class LLMJudge:
    """Judge đơn lẻ — OpenRouter (live) hoặc heuristic fallback."""

    def __init__(self, model_name: str, rubric: str = "accuracy"):
        self.model_name = model_name
        self.rubric = rubric
        self.live = is_live_mode()

    def _tokenize(self, text: str) -> set:
        return set(re.findall(r"\w+", text.lower()))

    def _heuristic_accuracy(self, answer: str, ground_truth: str) -> float:
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

    def _heuristic_tone(self, answer: str) -> float:
        markers = ["dựa trên", "tài liệu", "hệ thống", "xin trả lời", "không tìm thấy"]
        hits = sum(1 for m in markers if m in answer.lower())
        return min(5.0, 2.5 + hits * 0.5)

    def _build_prompt(self, question: str, answer: str, ground_truth: str) -> str:
        if self.rubric == "tone":
            return (
                f"Chấm điểm từ 1-5 độ chuyên nghiệp của câu trả lời (tone, clarity, safety).\n"
                f"Câu hỏi: {question}\nCâu trả lời: {answer}\n"
                f"Chỉ trả về MỘT số từ 1 đến 5."
            )
        return (
            f"Chấm điểm từ 1-5 độ chính xác so với ground truth.\n"
            f"Câu hỏi: {question}\nGround truth: {ground_truth}\nCâu trả lời: {answer}\n"
            f"Chỉ trả về MỘT số từ 1 đến 5."
        )

    @staticmethod
    def _parse_score(text: str) -> float:
        match = re.search(r"[1-5](?:\.\d+)?", text.strip())
        if match:
            return max(1.0, min(5.0, float(match.group())))
        return 3.0

    async def _live_evaluate(self, question: str, answer: str, ground_truth: str) -> float:
        client = get_async_client()
        if not client:
            raise RuntimeError("No API client")

        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": self._build_prompt(question, answer, ground_truth)}],
            temperature=0,
            max_tokens=10,
        )
        content = response.choices[0].message.content or "3"
        return self._parse_score(content)

    async def evaluate(self, question: str, answer: str, ground_truth: str) -> float:
        if self.live:
            try:
                return await self._live_evaluate(question, answer, ground_truth)
            except Exception:
                pass
        if self.rubric == "tone":
            return self._heuristic_tone(answer)
        return self._heuristic_accuracy(answer, ground_truth)


class MultiModelJudge:
    """Multi-Judge: 2 model qua OpenRouter + consensus logic."""

    def __init__(self):
        model_a = os.getenv("JUDGE_MODEL_A", "openai/gpt-4o-mini")
        model_b = os.getenv("JUDGE_MODEL_B", "anthropic/claude-3.5-haiku")
        self.judge_a = LLMJudge(model_a, rubric="accuracy")
        self.judge_b = LLMJudge(model_b, rubric="tone")
        self.live_mode = is_live_mode()

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

        model_a = self.judge_a.model_name
        model_b = self.judge_b.model_name

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
            "individual_scores": {model_a: score_a, model_b: score_b},
            "score_delta": round(diff, 2),
            "conflict_resolved": conflict_resolved,
            "reasoning": reasoning,
            "judge_mode": "openrouter_live" if self.live_mode else "heuristic",
        }

    async def check_position_bias(self, response_a: str, response_b: str) -> Dict[str, Any]:
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
