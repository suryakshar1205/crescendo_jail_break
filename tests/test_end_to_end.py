"""
End-to-End Integration Tests — Validates the full pipeline wiring.
Tests that all phase modules resolve imports correctly and can be
invoked via their parse_args interface.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCoreImports(unittest.TestCase):
    """Validates all core module imports."""

    def test_evaluator_import(self):
        from src.core.evaluator import RuleBasedEvaluator, get_evaluator
        self.assertTrue(callable(get_evaluator))

    def test_load_model_import(self):
        from src.core.load_model import load_model
        self.assertTrue(callable(load_model))

    def test_utils_import(self):
        from src.core.utils import set_seed, log_memory
        self.assertTrue(callable(set_seed))
        self.assertTrue(callable(log_memory))


class TestPhaseModuleImports(unittest.TestCase):
    """Validates all phase benchmark module imports."""

    def test_phase1_benchmark_import(self):
        from src.phase1.benchmark import MockModel, MockTokenizer
        m = MockModel()
        t = MockTokenizer()
        self.assertIsNotNone(m)
        self.assertIsNotNone(t)

    def test_phase2_benchmark_import(self):
        from src.phase2.phase2_benchmark import parse_args
        self.assertTrue(callable(parse_args))

    def test_phase3_benchmark_import(self):
        from src.phase3.phase3_benchmark import parse_args
        self.assertTrue(callable(parse_args))

    def test_phase4_benchmark_import(self):
        from src.phase4.phase4_benchmark import parse_args
        self.assertTrue(callable(parse_args))

    def test_phase5_benchmark_import(self):
        from src.phase5.phase5_benchmark import parse_args
        self.assertTrue(callable(parse_args))


class TestMockModelInterface(unittest.TestCase):
    """Tests the MockModel and MockTokenizer interface used by --mock_inference."""

    def setUp(self):
        from src.phase1.benchmark import MockModel, MockTokenizer
        self.model = MockModel()
        self.tokenizer = MockTokenizer()

    def test_tokenizer_apply_chat_template(self):
        result = self.tokenizer.apply_chat_template([{"role": "user", "content": "test"}])
        self.assertIsNotNone(result)

    def test_tokenizer_decode(self):
        decoded = self.tokenizer.decode([1, 2, 3], skip_special_tokens=True)
        self.assertIsInstance(decoded, str)
        self.assertGreater(len(decoded), 0)

    def test_model_generate(self):
        import torch
        input_ids = torch.tensor([[1, 2, 3]])
        output = self.model.generate(input_ids=input_ids, max_new_tokens=10)
        self.assertIsNotNone(output)


class TestDefenseComponentIntegration(unittest.TestCase):
    """Tests that defense components from different phases interact correctly."""

    def test_phase2_detector_feeds_phase3_fusion(self):
        from src.phase2.embedding_detector import EmbeddingDriftDetector
        from src.phase3.risk_fusion import fuse_risk

        detector = EmbeddingDriftDetector(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            similarity_metric="cosine",
            window_size=3,
            weights={"anchor_drift": 0.60, "local_drift": 0.25, "velocity": 0.15}
        )
        prompts = ["What is cybersecurity?", "How do hackers break into systems?"]
        verdict = detector.evaluate_turn(prompts, 0.5)

        config = {"risk_levels": {"safe": 0.40, "medium": 0.65, "high": 0.80}}
        result = fuse_risk(verdict["risk_score"], 0.10, 0.80, config)
        self.assertIn("risk_level", result)
        self.assertIn("flagged", result)

    def test_phase3_feeds_phase4_memory(self):
        from src.phase4.conversation_memory import ConversationMemoryEngine

        engine = ConversationMemoryEngine(memory_decay=0.80, history_window=5)
        engine.reset_session("integration_test")

        # Simulate 3 turns of escalating risk
        for risk in [0.1, 0.3, 0.6]:
            signals = engine.add_turn("integration_test", "test prompt", risk, safe_threshold=0.40)

        self.assertGreater(signals["historical_risk"], 0.0)
        self.assertGreater(signals["trend_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
