"""
Regression Test: Jittering Attacks and Decision Hysteresis.

Verifies that the AdaptiveDecisionEngine maintains hysteresis and prevents
decision oscillation when an attacker alternates high-risk and low-risk turns.
"""
import unittest
from src.crs.decision_engine import AdaptiveDecisionEngine
from src.crs.types import DecisionAction


class TestJitterHysteresis(unittest.TestCase):
    """Validates dual-threshold hysteresis behavior under jittering attacks."""

    def setUp(self):
        self.engine = AdaptiveDecisionEngine(
            allow_threshold=0.40,
            warn_threshold=0.60,
            restrict_threshold=0.75,
            release_margin=0.15,
            use_dynamic_mode=False
        )
        self.session_id = "test_jitter_session"
        self.engine.reset_session(self.session_id)

    def test_jitter_oscillation_prevention(self):
        """
        Tests that when a session enters BLOCK (CRS=0.82), a subsequent turn with
        moderate risk (CRS=0.72) is NOT immediately released to ALLOW/WARN, but
        remains in BLOCK because it has not breached the release threshold (0.60).
        """
        # Turn 1: Benign setup
        t1 = self.engine.decide(crs=0.20, session_id=self.session_id)
        self.assertEqual(t1["decision"], DecisionAction.ALLOW.value)

        # Turn 2: Escalating
        t2 = self.engine.decide(crs=0.55, session_id=self.session_id)
        self.assertEqual(t2["decision"], DecisionAction.WARN.value)

        # Turn 3: High-risk attack -> Trigger BLOCK
        t3 = self.engine.decide(crs=0.82, session_id=self.session_id)
        self.assertEqual(t3["decision"], DecisionAction.BLOCK.value)
        self.assertTrue(t3["is_blocked"])

        # Turn 4: Adversary sends jittered filler query (CRS=0.72, which normally would be RESTRICT)
        # Hysteresis must keep it in BLOCK because 0.72 >= 0.60 (release threshold)
        t4 = self.engine.decide(crs=0.72, session_id=self.session_id)
        self.assertEqual(t4["decision"], DecisionAction.BLOCK.value)
        self.assertTrue(t4["hysteresis_applied"])

        # Turn 5: Adversary continues with mild query (CRS=0.62)
        # Still above release threshold (0.60)
        t5 = self.engine.decide(crs=0.62, session_id=self.session_id)
        self.assertEqual(t5["decision"], DecisionAction.BLOCK.value)

        # Turn 6: Truly safe de-escalation (CRS=0.30 < 0.40)
        # Dropped below release threshold -> Released to ALLOW
        t6 = self.engine.decide(crs=0.30, session_id=self.session_id)
        self.assertEqual(t6["decision"], DecisionAction.ALLOW.value)
        self.assertFalse(t6["is_blocked"])


if __name__ == "__main__":
    unittest.main()
