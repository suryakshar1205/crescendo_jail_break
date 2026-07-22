import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DynamicThresholdCalibrator:
    """
    Calibrates the defense threshold dynamically based on the semantic domain of the conversation's first turn.
    Helps maintain utility (low FPR) on technical tasks (e.g., coding) while keeping high security (low ASR) on others.
    """
    def __init__(self, base_threshold: float = 0.92, domain_offsets: Dict[str, float] = None):
        self.base_threshold = base_threshold
        # Predefined domain category anchors representing common user intents
        self.domain_anchors = {
            "programming": "write code, implement function, software script, programming solution, coding design patterns",
            "creative_writing": "tell me a creative story, pretend you are a character, roleplay as, write fictional screenplay",
            "academic_research": "explain historical facts, scientific theory overview, mathematical theorem explanation",
            "general": "standard conversation help, general question answer session, help assistant"
        }
        # Offsets adjustment to base threshold
        # Positive offset makes the system less sensitive (higher threshold = lower FPR on safe coding tasks)
        # Negative offset makes the system more sensitive (lower threshold = higher security on creative/pretend tasks)
        self.domain_offsets = domain_offsets or {
            "programming": 0.03,
            "creative_writing": -0.02,
            "academic_research": 0.00,
            "general": 0.00
        }
        self.anchor_embeddings = {}

    def _lazy_init_anchors(self, drift_detector):
        """
        Computes and caches embeddings for the domain anchors.
        """
        if not self.anchor_embeddings:
            logger.info("Computing embeddings for domain anchors...")
            for domain, anchor_text in self.domain_anchors.items():
                self.anchor_embeddings[domain] = drift_detector.get_embedding(anchor_text)

    def calibrate_threshold(self, first_turn_prompt: str, drift_detector) -> Dict[str, Any]:
        """
        Analyzes the first turn of a conversation to classify its domain,
        applies the domain-specific offset, and returns the calibrated threshold.
        """
        if not first_turn_prompt:
            return {
                "calibrated_threshold": self.base_threshold,
                "classified_domain": "general",
                "max_similarity": 1.0,
                "offset": 0.0
            }

        self._lazy_init_anchors(drift_detector)
        
        # Get embedding of the first turn prompt
        prompt_embedding = drift_detector.get_embedding(first_turn_prompt)
        
        # Compute cosine similarity with each domain anchor
        similarities = {}
        for domain, anchor_emb in self.anchor_embeddings.items():
            sim = drift_detector.cosine_similarity(prompt_embedding, anchor_emb)
            similarities[domain] = sim
            
        # Classify as the domain with the highest similarity
        classified_domain = max(similarities, key=similarities.get)
        max_similarity = similarities[classified_domain]
        
        offset = self.domain_offsets.get(classified_domain, 0.0)
        calibrated_threshold = float(np.clip(self.base_threshold + offset, 0.30, 0.98))
        
        logger.info(
            f"First turn domain classification: '{classified_domain}' (sim: {max_similarity:.4f}). "
            f"Offset applied: {offset:+.2f} -> Calibrated Threshold: {calibrated_threshold:.4f}"
        )
        
        return {
            "calibrated_threshold": round(calibrated_threshold, 4),
            "classified_domain": classified_domain,
            "max_similarity": round(max_similarity, 4),
            "offset": offset
        }
