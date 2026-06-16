"""Unit tests for judge calibration — Ngô Thị Ánh."""
import unittest

from engine.judge_calibration import cohens_kappa, agreement_rate_batch, JudgeCalibration


class TestJudgeCalibration(unittest.TestCase):
    def test_perfect_agreement_kappa(self):
        scores = [4.0, 5.0, 3.0, 4.0, 5.0]
        self.assertEqual(cohens_kappa(scores, scores), 1.0)

    def test_disagreement_kappa_below_one(self):
        a = [5.0, 5.0, 5.0, 5.0, 5.0]
        b = [1.0, 1.0, 1.0, 1.0, 1.0]
        self.assertLessEqual(cohens_kappa(a, b), 0.0)

    def test_agreement_rate_batch(self):
        a = [4.0, 4.0, 5.0]
        b = [4.0, 3.5, 3.0]
        rate = agreement_rate_batch(a, b)
        self.assertGreater(rate, 0.5)
        self.assertLessEqual(rate, 1.0)

    def test_summarize_from_results(self):
        results = [
            {
                "judge": {
                    "individual_scores": {"gpt-4o": 4.0, "claude-3-5-sonnet": 4.0},
                    "score_delta": 0.0,
                    "conflict_resolved": False,
                }
            },
            {
                "judge": {
                    "individual_scores": {"gpt-4o": 5.0, "claude-3-5-sonnet": 2.0},
                    "score_delta": 3.0,
                    "conflict_resolved": True,
                }
            },
        ]
        summary = JudgeCalibration.summarize(results)
        self.assertIn("cohens_kappa", summary)
        self.assertEqual(summary["conflict_count"], 1)


if __name__ == "__main__":
    unittest.main()
