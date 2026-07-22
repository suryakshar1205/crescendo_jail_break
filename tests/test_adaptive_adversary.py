import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.phase4.conversation_memory import ConversationMemoryEngine
from src.phase4.contextual_risk import compute_contextual_risk
from src.core.dynamic_threshold import DynamicThresholdCalibrator

class MockDriftDetector:
    def __init__(self, semantic_scores):
        self.semantic_scores = semantic_scores
        self.call_count = 0

    def evaluate_turn(self, prompts, threshold):
        # Return a simulated semantic score from the predefined array
        idx = min(self.call_count, len(self.semantic_scores) - 1)
        score = self.semantic_scores[idx]
        self.call_count += 1
        return {
            "anchor_drift": score * 0.8,
            "local_drift": score * 0.7,
            "velocity": 0.5 if idx > 0 else 0.0,
            "risk_score": score,
            "flagged": score > threshold
        }

    def get_embedding(self, text):
        return np.array([1.0, 0.0])

    def cosine_similarity(self, emb1, emb2):
        return 0.5

class TestAdaptiveAdversarySimulation(unittest.TestCase):
    """
    Validates that the Contextual Memory Defense successfully flags adaptive adversary designs 
    (jittering attacks and semantic smuggling) even when single turn checks might be bypassed.
    """
    
    def test_jittering_attack_blocked(self):
        """
        Adversary alternates high-risk turns with benign filler turns (e.g., Turn 1: High, Turn 2: Benign, Turn 3: High)
        to force the decay engine to forget prior risk.
        """
        memory_engine = ConversationMemoryEngine(memory_decay=0.80)
        chat_id = "test_jitter_001"
        
        # High, Low, High, Low, High pattern
        semantic_scores = [0.85, 0.10, 0.90, 0.15, 0.95]
        detector = MockDriftDetector(semantic_scores)
        
        threshold = 0.92
        config = {
            "risk_levels": {"safe": 0.40, "medium": 0.65, "high": 0.80}
        }
        
        flagged_at_any_turn = False
        
        for turn, score in enumerate(semantic_scores):
            # Simulate turn execution
            # Turn Risk = 0.7 * semantic + 0.3 * rules
            # Let's assume behavioral rules contribute a small baseline score
            turn_risk = 0.7 * score + 0.3 * (0.4 if score > 0.5 else 0.0)
            
            proportional_safe = threshold * (0.40 / 0.80)
            memory_signals = memory_engine.add_turn(
                chat_id, f"turn {turn}", turn_risk, safe_threshold=proportional_safe
            )
            
            ctx = compute_contextual_risk(
                phase3_risk=turn_risk,
                historical_risk=memory_signals["historical_risk"],
                trend_score=memory_signals["trend_score"],
                persistence_memory=memory_signals["persistence_memory"],
                bypass_score=memory_signals["bypass_score"],
                threshold=threshold,
                config=config
            )
            
            if ctx["flagged"]:
                flagged_at_any_turn = True
                
        # The session should be flagged eventually due to persistence accumulation
        self.assertTrue(flagged_at_any_turn, "Jittering sequence was not blocked by persistence indicators.")

    def test_semantic_smuggling_blocked(self):
        """
        Adversary uses paraphrased prompts to keep semantic drift low but triggers high behavioral rules.
        """
        memory_engine = ConversationMemoryEngine(memory_decay=0.80)
        chat_id = "test_smuggle_001"
        
        # Low semantic drift scores
        semantic_scores = [0.20, 0.25, 0.22, 0.28, 0.30]
        detector = MockDriftDetector(semantic_scores)
        
        # High rules detection (e.g., repeating actionability keywords / coding instructions)
        rule_scores = [0.60, 0.70, 0.85, 0.90, 0.95]
        
        threshold = 0.92
        config = {
            "risk_levels": {"safe": 0.40, "medium": 0.65, "high": 0.80}
        }
        
        flagged_at_any_turn = False
        
        for turn, (sem, rule) in enumerate(zip(semantic_scores, rule_scores)):
            turn_risk = 0.7 * sem + 0.3 * rule
            
            proportional_safe = threshold * (0.40 / 0.80)
            memory_signals = memory_engine.add_turn(
                chat_id, f"turn {turn}", turn_risk, safe_threshold=proportional_safe
            )
            
            ctx = compute_contextual_risk(
                phase3_risk=turn_risk,
                historical_risk=memory_signals["historical_risk"],
                trend_score=memory_signals["trend_score"],
                persistence_memory=memory_signals["persistence_memory"],
                bypass_score=memory_signals["bypass_score"],
                threshold=threshold,
                config=config
            )
            
            if ctx["flagged"]:
                flagged_at_any_turn = True
                
        # High rule score + contextual build-up should eventually flag the session
        self.assertTrue(flagged_at_any_turn, "Semantic smuggling sequence bypassed the defense.")

if __name__ == "__main__":
    unittest.main()
