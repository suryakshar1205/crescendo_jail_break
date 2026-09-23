import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

import sys
import numpy as np
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class EmbeddingDriftDetector:
    """
    Refined Sentence-Transformer embedding based semantic drift detector.
    Combines Anchor Drift, Local Drift, and Escalation Velocity with weighted risk scoring.
    """
    _SHARED_MODEL = None
    _SHARED_FALLBACK = False
    _INIT_ATTEMPTED = False

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_metric: str = "cosine",
        window_size: int = 3,
        weights: Optional[Dict[str, float]] = None
    ):
        self.model_name = model_name
        self.similarity_metric = similarity_metric
        self.window_size = window_size
        self.weights = weights or {"anchor_drift": 0.60, "local_drift": 0.25, "velocity": 0.15}
        self.model = EmbeddingDriftDetector._SHARED_MODEL
        self.embedding_cache = {}
        self._fallback_mode = EmbeddingDriftDetector._SHARED_FALLBACK

    def _deterministic_embedding(self, text: str) -> np.ndarray:
        """Generates deterministic unit-normalized 384-d vector when model weights cannot load."""
        import hashlib
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        vec = rng.randn(384).astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _lazy_init(self):
        """
        Lazily initializes the sentence-transformers model with graceful fallback on memory exhaustion.
        Reuses class-level shared model or fallback across instances.
        """
        if os.environ.get("USE_DETERMINISTIC_EMBEDDING", "0") == "1":
            EmbeddingDriftDetector._SHARED_MODEL = None
            EmbeddingDriftDetector._SHARED_FALLBACK = True
            EmbeddingDriftDetector._INIT_ATTEMPTED = True
            self.model = None
            self._fallback_mode = True
            return

        if EmbeddingDriftDetector._INIT_ATTEMPTED:
            self.model = EmbeddingDriftDetector._SHARED_MODEL
            self._fallback_mode = EmbeddingDriftDetector._SHARED_FALLBACK
            return

        EmbeddingDriftDetector._INIT_ATTEMPTED = True
        try:
            logger.info(f"Initializing SentenceTransformer model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            import torch
            device = "cpu"
            self.model = SentenceTransformer(self.model_name, device=device)
            EmbeddingDriftDetector._SHARED_MODEL = self.model
            EmbeddingDriftDetector._SHARED_FALLBACK = False
            self._fallback_mode = False
            logger.info(f"SentenceTransformer loaded on device: {device}")
        except Exception as e:
            logger.warning(f"SentenceTransformer load failed ({e}). Using deterministic embedding fallback.")
            EmbeddingDriftDetector._SHARED_MODEL = None
            EmbeddingDriftDetector._SHARED_FALLBACK = True
            self.model = None
            self._fallback_mode = True

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Gets embedding for text and caches it.
        """
        self._lazy_init()
        if text not in self.embedding_cache:
            if self.model is not None and not self._fallback_mode:
                try:
                    emb = self.model.encode(text, convert_to_numpy=True)
                except Exception as e:
                    logger.warning(f"Model encode failed ({e}); falling back to deterministic embedding.")
                    emb = self._deterministic_embedding(text)
            else:
                emb = self._deterministic_embedding(text)
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
