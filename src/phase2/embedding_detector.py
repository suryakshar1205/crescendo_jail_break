import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["USE_TF"] = "0"

import sys
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EmbeddingDriftDetector:
    """
    Refined Sentence-Transformer embedding based semantic drift detector.
    Combines Anchor Drift, Local Drift, and Escalation Velocity with weighted risk scoring.
    """
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_metric: str = "cosine",
        window_size: int = 3,
        weights: Dict[str, float] = None
    ):
        self.model_name = model_name
        self.similarity_metric = similarity_metric
        self.window_size = window_size
        self.weights = weights or {"anchor_drift": 0.60, "local_drift": 0.25, "velocity": 0.15}
        self.model = None
        self.embedding_cache = {}

    def _lazy_init(self):
        """
        Lazily initializes the sentence-transformers model.
        """
        if self.model is None:
            logger.info(f"Initializing SentenceTransformer model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = SentenceTransformer(self.model_name, device=device)
            logger.info(f"SentenceTransformer loaded on device: {device}")

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Gets embedding for text and caches it.
        """
        self._lazy_init()
        if text not in self.embedding_cache:
            emb = self.model.encode(text, convert_to_numpy=True)
            self.embedding_cache[text] = emb
        return self.embedding_cache[text]

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Computes cosine similarity between two 1D numpy arrays.
        """
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    def calculate_drift(self, prompts: List[str]) -> float:
        """
        Calculates local consecutive semantic drift score in a sliding window.
        drift_score = 1 - average cosine similarity.
        """
        if len(prompts) <= 1:
            return 0.0

        max_turns = self.window_size + 1
        recent_prompts = prompts[-max_turns:]
        
        embeddings = [self.get_embedding(p) for p in recent_prompts]
        
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self.cosine_similarity(embeddings[i], embeddings[i+1])
            similarities.append(sim)
            
        if not similarities:
            return 0.0
            
        avg_similarity = sum(similarities) / len(similarities)
        drift_score = 1.0 - avg_similarity
        return drift_score

    def evaluate_turn(self, prompts: List[str], threshold: float) -> Dict[str, Any]:
        """
        Evaluates prompt history with multi-signal score and returns safety verdict.
        """
        if not prompts:
            return {
                "anchor_drift": 0.0,
                "local_drift": 0.0,
                "velocity": 0.0,
                "risk_score": 0.0,
                "flagged": False,
                "threshold": threshold
            }
            
        # 1. Anchor Drift (compared to first turn origin)
        cur_emb = self.get_embedding(prompts[-1])
        first_emb = self.get_embedding(prompts[0])
        anchor_drift = 1.0 - self.cosine_similarity(cur_emb, first_emb)
        
        # 2. Local Drift (average consecutive drift in window)
        local_drift = self.calculate_drift(prompts)
        
        # 3. Escalation Velocity (rate of change of anchor drift)
        if len(prompts) <= 1:
            velocity = 0.0
        else:
            prev_emb = self.get_embedding(prompts[-2])
            prev_anchor_drift = 1.0 - self.cosine_similarity(prev_emb, first_emb)
            if prev_anchor_drift > 0.0:
                velocity = float(np.clip(anchor_drift / prev_anchor_drift, 0.0, 1.0))
            else:
                velocity = 1.0 if anchor_drift > 0.0 else 0.0
                
        # 4. Final Risk Score calculation
        w_anchor = self.weights.get("anchor_drift", 0.60)
        w_local = self.weights.get("local_drift", 0.25)
        w_velocity = self.weights.get("velocity", 0.15)
        
        risk_score = w_anchor * anchor_drift + w_local * local_drift + w_velocity * velocity
        flagged = risk_score > threshold
        
        return {
            "anchor_drift": anchor_drift,
            "local_drift": local_drift,
            "velocity": velocity,
            "risk_score": risk_score,
            "flagged": flagged,
            "threshold": threshold
        }
