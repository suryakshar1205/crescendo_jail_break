import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.dynamic_threshold import DynamicThresholdCalibrator

class MockDriftDetector:
    """
    Mocks EmbeddingDriftDetector for offline testing.
    Returns deterministic mock embeddings based on text search.
    """
    def get_embedding(self, text: str) -> np.ndarray:
        # Return a simple mock vector (dimension 4) representing domain clustering
        text_lower = text.lower()
        if "code" in text_lower or "program" in text_lower or "script" in text_lower:
            return np.array([1.0, 0.0, 0.0, 0.0])  # Programming cluster
        elif "story" in text_lower or "roleplay" in text_lower or "pretend" in text_lower:
            return np.array([0.0, 1.0, 0.0, 0.0])  # Creative writing cluster
        elif "scientific" in text_lower or "research" in text_lower or "physics" in text_lower:
            return np.array([0.0, 0.0, 1.0, 0.0])  # Academic research cluster
        else:
            return np.array([0.0, 0.0, 0.0, 1.0])  # General cluster

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        # Standard cosine similarity for 1D arrays
        n1 = np.linalg.norm(emb1)
        n2 = np.linalg.norm(emb2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (n1 * n2))

class TestDynamicThresholdCalibrator(unittest.TestCase):
    """Tests for the DynamicThresholdCalibrator class."""

    def setUp(self):
        self.calibrator = DynamicThresholdCalibrator(base_threshold=0.92)
        self.mock_detector = MockDriftDetector()

    def test_programming_domain_calibration(self):
        res = self.calibrator.calibrate_threshold("Write a python script to parse logs", self.mock_detector)
        self.assertEqual(res["classified_domain"], "programming")
        self.assertAlmostEqual(res["calibrated_threshold"], 0.95, places=4)
        self.assertEqual(res["offset"], 0.03)

    def test_creative_writing_domain_calibration(self):
        res = self.calibrator.calibrate_threshold("Pretend you are a character in a story", self.mock_detector)
        self.assertEqual(res["classified_domain"], "creative_writing")
        self.assertAlmostEqual(res["calibrated_threshold"], 0.90, places=4)
        self.assertEqual(res["offset"], -0.02)

    def test_general_domain_calibration(self):
        res = self.calibrator.calibrate_threshold("Hello! Can you help me?", self.mock_detector)
        self.assertEqual(res["classified_domain"], "general")
        self.assertAlmostEqual(res["calibrated_threshold"], 0.92, places=4)
        self.assertEqual(res["offset"], 0.00)

    def test_empty_prompt_handling(self):
        res = self.calibrator.calibrate_threshold("", self.mock_detector)
        self.assertEqual(res["classified_domain"], "general")
        self.assertAlmostEqual(res["calibrated_threshold"], 0.92, places=4)

if __name__ == "__main__":
    unittest.main()
