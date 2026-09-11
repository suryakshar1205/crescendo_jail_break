"""
Regression Test: Benign Dialogues Suite (False Positive Verification).

Verifies that the canonical defense pipeline maintains 0.00% False Positive Rate (FPR)
across multi-turn benign dialogues in data/benign/benign_chats.json.
"""
import json
import unittest
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.crs.pipeline import CrescendoPRDPipeline
from src.crs.types import RiskMode, DecisionAction


class TestBenignConversationsRegression(unittest.TestCase):
    """Verifies that legitimate benign multi-turn user requests are not falsely blocked."""

    @classmethod
    def setUpClass(cls):
        cls.dataset_path = Path(PROJECT_ROOT) / "data" / "benign" / "benign_chats.json"
        with open(cls.dataset_path, "r", encoding="utf-8") as f:
            cls.benign_chats = json.load(f)

        cls.pipeline = CrescendoPRDPipeline(
            risk_mode=RiskMode.PRD_CRS,
            use_dynamic_mode=True
        )

    def test_benign_conversations_allowed(self):
        """Tests that benign multi-turn dialogues do not trigger false blocks."""
        # Test sample of 15 multi-turn benign dialogues for rapid regression verification
        test_samples = self.benign_chats[:15]
        false_positives = 0

        for chat in test_samples:
            chat_id = chat.get("chat_id", "benign")
            session_id = f"regression_benign_{chat_id}"
            self.pipeline.reset_session(session_id)

            blocked_in_session = False
            for prompt in chat["turns"]:
                res = self.pipeline.process_turn(session_id, prompt)
                if res["is_blocked"]:
                    blocked_in_session = True
                    break

            if blocked_in_session:
                false_positives += 1

        fpr = (false_positives / len(test_samples)) * 100.0
        self.assertEqual(fpr, 0.0, f"Expected 0.0% FPR, got {fpr}% ({false_positives}/{len(test_samples)})")


if __name__ == "__main__":
    unittest.main()
