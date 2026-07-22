import unittest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.phase9.optimize_judge_prompts import run_prompt_optimization
from src.phase9.simulate_adaptive_attacks import run_adaptive_adversary_simulation
from src.phase9.interactive_fpr_auditor import run_auditor

class TestPhase9Harness(unittest.TestCase):
    """Tests the Phase 9 Cross-Model harness configuration and integrity."""

    def test_phase9_config_loading(self):
        config_path = os.path.join("configs", "phase9_config.json")
        self.assertTrue(os.path.exists(config_path), "configs/phase9_config.json does not exist.")
        
        with open(config_path, "r") as f:
            config = json.load(f)
            
        self.assertIn("phase_name", config)
        self.assertIn("models", config)
        self.assertTrue(isinstance(config["models"], list))
        self.assertEqual(len(config["models"]), 3)
        self.assertEqual(config["models"][0], "meta-llama/Llama-3.2-3B-Instruct")

    def test_prompt_optimizer_runs(self):
        output_path = "results/phase9/test_prompt_optimization_metrics.json"
        res = run_prompt_optimization(
            results_json="results/json/baseline_results.json",
            output_path=output_path
        )
        self.assertIn("standard", res)
        self.assertIn("few_shot", res)
        self.assertTrue(os.path.exists(output_path))
        if os.path.exists(output_path):
            os.remove(output_path)

    def test_adaptive_evasion_runs(self):
        output_path = "results/phase9/test_adaptive_attack_solver_results.json"
        res = run_adaptive_adversary_simulation(output_path=output_path)
        self.assertTrue(len(res) > 0)
        self.assertIn("min_safe_filler_turns_required", res[0])
        self.assertTrue(os.path.exists(output_path))
        if os.path.exists(output_path):
            os.remove(output_path)

    def test_auditor_auto_runs(self):
        output_path = "results/phase9/test_human_audit_feedback.json"
        res = run_auditor(
            cache_path="results/json/phase5_inference_cache.json",
            output_path=output_path,
            auto_mode=True
        )
        self.assertTrue(len(res) > 0)
        self.assertIn("human_verdict", res[0])
        self.assertTrue(os.path.exists(output_path))
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == "__main__":
    unittest.main()
