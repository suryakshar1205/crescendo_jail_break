"""
Unit tests for Phase 5 — Robustness & Generalization Framework.
Tests module imports, cross-phase integration, and Phase 5 benchmark parse_args.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPhase5ModuleImports(unittest.TestCase):
    """Tests that Phase 5 modules import correctly."""

    def test_threshold_stability_import(self):
        from src.phase5 import threshold_stability
        self.assertTrue(hasattr(threshold_stability, 'main'))

    def test_ablation_runner_import(self):
        from src.phase5 import ablation_runner
        self.assertTrue(hasattr(ablation_runner, 'main'))

    def test_phase5_benchmark_parse_args(self):
        from src.phase5.phase5_benchmark import parse_args
        self.assertTrue(callable(parse_args))

    def test_phase5_benchmark_response_cache(self):
        from src.phase5.phase5_benchmark import ResponseCache
        self.assertTrue(callable(ResponseCache))

    def test_phase5_evaluate_threshold(self):
        from src.phase5.phase5_benchmark import evaluate_threshold_phase5
        self.assertTrue(callable(evaluate_threshold_phase5))


class TestPhase5Integration(unittest.TestCase):
    """Tests that Phase 5 can access all upstream components."""

    def test_phase2_detector_accessible(self):
        from src.phase2.embedding_detector import EmbeddingDriftDetector
        self.assertTrue(callable(EmbeddingDriftDetector))

    def test_phase3_rule_detector_accessible(self):
        from src.phase3.rule_detector import BehavioralRuleDetector
        self.assertTrue(callable(BehavioralRuleDetector))

    def test_phase3_risk_fusion_accessible(self):
        from src.phase3.risk_fusion import fuse_risk
        self.assertTrue(callable(fuse_risk))

    def test_phase4_memory_accessible(self):
        from src.phase4.conversation_memory import ConversationMemoryEngine
        self.assertTrue(callable(ConversationMemoryEngine))

    def test_phase4_contextual_risk_accessible(self):
        from src.phase4.contextual_risk import compute_contextual_risk
        self.assertTrue(callable(compute_contextual_risk))

    def test_core_evaluator_accessible(self):
        from src.core.evaluator import get_evaluator
        self.assertTrue(callable(get_evaluator))

    def test_core_load_model_accessible(self):
        from src.core.load_model import load_model
        self.assertTrue(callable(load_model))


if __name__ == "__main__":
    unittest.main()
