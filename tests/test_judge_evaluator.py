import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.judge_evaluator import LLMJudgeEvaluator

class TestLLMJudgeEvaluator(unittest.TestCase):
    """Tests for the LLMJudgeEvaluator class."""

    def setUp(self):
        # Force mock mode to guarantee local compatibility without downloading weights
        self.evaluator = LLMJudgeEvaluator(mock=True)

    def test_mock_fallback_refusal(self):
        # In mock fallback mode, it uses RuleBasedEvaluator which should detect this refusal and return False
        result = self.evaluator.evaluate("harmful query", "I cannot assist with that request.")
        self.assertFalse(result, "Refusal should be detected and return False")

    def test_mock_fallback_compliance(self):
        # Compliance response should not trigger any refusal and return True
        result = self.evaluator.evaluate("harmful query", "Here are the step-by-step instructions to proceed...")
        self.assertTrue(result, "Compliance should not trigger refusal and return True")

    def test_empty_response(self):
        # Empty response should return False (refusal classification)
        result = self.evaluator.evaluate("query", "")
        self.assertFalse(result, "Empty response should be treated as refusal (False)")

    def test_lazy_init_flag(self):
        # Ensure lazy initialization works and sets mock flag appropriately
        evaluator = LLMJudgeEvaluator(mock=False)
        self.assertFalse(evaluator.mock)
        # Call evaluate to trigger lazy initialization
        evaluator.evaluate("query", "test")
        # Should auto-detect mock since HF token is not configured or we are in a test env
        self.assertTrue(evaluator.mock or evaluator.classifier is not None)

if __name__ == "__main__":
    unittest.main()
