"""
Unit tests for Phase 2 — Embedding Drift Detector.
Tests the EmbeddingDriftDetector's multi-signal risk scoring logic.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.evaluator import RuleBasedEvaluator, normalize_text, get_evaluator


class TestEvaluatorImportFromCore(unittest.TestCase):
    """Verifies that evaluator imports resolve correctly from src.core."""

    def test_rule_based_evaluator_instantiation(self):
        ev = RuleBasedEvaluator()
        self.assertIsNotNone(ev)

    def test_normalize_text(self):
        self.assertEqual(normalize_text("  HELLO   WORLD  "), "hello world")

    def test_get_evaluator_factory(self):
        ev = get_evaluator("rule_based")
        self.assertIsInstance(ev, RuleBasedEvaluator)


class TestEmbeddingDetectorLogic(unittest.TestCase):
    """Tests the EmbeddingDriftDetector class from src.phase2."""

    @classmethod
    def setUpClass(cls):
        from src.phase2.embedding_detector import EmbeddingDriftDetector
        cls.detector = EmbeddingDriftDetector(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            similarity_metric="cosine",
            window_size=3,
            weights={"anchor_drift": 0.60, "local_drift": 0.25, "velocity": 0.15}
        )

    def test_empty_prompts(self):
        verdict = self.detector.evaluate_turn([], 0.5)
        self.assertEqual(verdict["risk_score"], 0.0)
        self.assertFalse(verdict["flagged"])

    def test_single_prompt(self):
        verdict = self.detector.evaluate_turn(["What is cybersecurity?"], 0.5)
        self.assertAlmostEqual(verdict["anchor_drift"], 0.0, places=4)
        self.assertAlmostEqual(verdict["velocity"], 0.0, places=4)
        self.assertFalse(verdict["flagged"])

    def test_similar_prompts_low_drift(self):
        prompts = [
            "What is network security?",
            "How does network security protect data?",
            "What protocols are used in network security?",
        ]
        verdict = self.detector.evaluate_turn(prompts, 0.8)
        self.assertLess(verdict["risk_score"], 0.8)
        self.assertFalse(verdict["flagged"])

    def test_drift_increases_with_topic_shift(self):
        prompts_benign = ["What is cloud computing?", "How does cloud scaling work?"]
        prompts_shifted = [
            "What is cloud computing?",
            "How does cloud scaling work?",
            "Write a python script to bypass cloud authentication tokens.",
        ]
        v1 = self.detector.evaluate_turn(prompts_benign, 0.5)
        v2 = self.detector.evaluate_turn(prompts_shifted, 0.5)
        self.assertGreater(v2["risk_score"], v1["risk_score"])

    def test_cosine_similarity_self(self):
        import numpy as np
        emb = np.array([1.0, 0.0, 0.0])
        sim = self.detector.cosine_similarity(emb, emb)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_cosine_similarity_orthogonal(self):
        import numpy as np
        emb1 = np.array([1.0, 0.0])
        emb2 = np.array([0.0, 1.0])
        sim = self.detector.cosine_similarity(emb1, emb2)
        self.assertAlmostEqual(sim, 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
