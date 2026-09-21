"""
Jailbreak Similarity Analyzer Module (S Score).

Produces a normalized semantic similarity score S in [0, 1] comparing the current
conversation context against a vector database / FAISS index of known Crescendo and
adversarial jailbreak attack patterns.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

from src.phase2.embedding_detector import EmbeddingDriftDetector

logger = logging.getLogger(__name__)

# Attempt to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss package not found. JailbreakSimilarityAnalyzer will use NumPy cosine fallback.")


class JailbreakSimilarityAnalyzer:
    """
    Evaluates semantic proximity of user prompts/dialogue turns to known jailbreak attacks.
    Indexes historical attack datasets and computes top-k similarity vectors.

    Produces normalized score S in [0, 1].
    """

    def __init__(
        self,
        drift_detector: Optional[EmbeddingDriftDetector] = None,
        dataset_path: Union[str, List[str]] = "data/attacks/crescendo_attacks.json",
        similarity_threshold: float = 0.50,
        cache_dir: Optional[str] = "data/cache"
    ):
        self.drift_detector = drift_detector or EmbeddingDriftDetector()
        self.dataset_path = dataset_path
        self.similarity_threshold = similarity_threshold
        self.cache_dir = cache_dir
        self.indexed_texts: List[str] = []
        self.indexed_metadata: List[Dict[str, Any]] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.faiss_index: Any = None
        self.dimension = 384  # all-MiniLM-L6-v2 embedding dimension
        self.backend = "faiss" if FAISS_AVAILABLE else "numpy"

        # Attempt to load pre-built index or build fresh from dataset paths
        if isinstance(dataset_path, list):
            self.build_index_from_sources(dataset_path)
        elif os.path.isdir(dataset_path):
            sources = [
                os.path.join(dataset_path, f)
                for f in os.listdir(dataset_path)
                if f.endswith(".json")
            ]
            self.build_index_from_sources(sources)
        elif os.path.exists(dataset_path):
            self.build_index(dataset_path)

    def build_index_from_sources(self, source_paths: List[str]) -> int:
        """
        Aggregates attack vectors from multiple dataset files and indexes them.
        """
        all_items = []
        for src in source_paths:
            if os.path.exists(src):
                try:
                    with open(src, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        all_items.extend(data)
                    elif isinstance(data, dict):
                        # Some formats contain datasets under keys
                        attacks = data.get("attacks") or data.get("conversations") or []
                        all_items.extend(attacks)
                except Exception as e:
                    logger.warning(f"Error reading source dataset {src}: {e}")
        return self._index_items(all_items)

    def build_index(self, dataset_path: str) -> int:
        """
        Loads attack vectors from a single dataset JSON and builds the FAISS / vector index.

        Args:
            dataset_path: Path to attacks JSON file.

        Returns:
            int: Number of attack vector turns indexed.
        """
        self.dataset_path = dataset_path
        if not os.path.exists(dataset_path):
            logger.warning(f"Attack dataset not found at {dataset_path}. Index is empty.")
            return 0

        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = data.get("attacks") or data.get("conversations") or []

        return self._index_items(data)

    def _index_items(self, items: List[Dict[str, Any]]) -> int:
        """Helper to index a list of attack turn objects."""
        self.indexed_texts = []
        self.indexed_metadata = []
        vectors = []

        logger.info(f"Building jailbreak similarity index from {len(items)} attack records...")
        for item in items:
            attack_id = item.get("attack_id", item.get("id", "unknown"))
            category = item.get("category", "general")
            turns = item.get("turns", [])
            # Support single-prompt or multi-turn
            if not turns and "prompt" in item:
                turns = [item["prompt"]]

            for turn_idx, turn_text in enumerate(turns):
                if not isinstance(turn_text, str) or not turn_text.strip():
                    continue
                emb = self.drift_detector.get_embedding(turn_text)
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm

                vectors.append(emb)
                self.indexed_texts.append(turn_text)
                self.indexed_metadata.append({
                    "attack_id": attack_id,
                    "category": category,
                    "turn_number": turn_idx + 1,
                    "is_final_payload": (turn_idx == len(turns) - 1),
                    "text": turn_text
                })

        if vectors:
            self.embeddings_matrix = np.array(vectors, dtype=np.float32)
            if FAISS_AVAILABLE:
                self.faiss_index = faiss.IndexFlatIP(self.dimension)
                getattr(self.faiss_index, "add")(self.embeddings_matrix)
                self.backend = "faiss"
                logger.info(f"Built FAISS IndexFlatIP with {self.faiss_index.ntotal} vectors.")
            else:
                self.backend = "numpy"
                logger.info(f"Built NumPy matrix index with {len(vectors)} vectors.")

        return len(self.indexed_texts)

    def save_index(self, index_file: str, metadata_file: str) -> bool:
        """
        Serializes the vector index and metadata to disk for instant loading.
        """
        try:
            os.makedirs(os.path.dirname(index_file) or ".", exist_ok=True)
            os.makedirs(os.path.dirname(metadata_file) or ".", exist_ok=True)

            if FAISS_AVAILABLE and self.faiss_index is not None:
                faiss.write_index(self.faiss_index, index_file)
            elif self.embeddings_matrix is not None:
                np.save(index_file, self.embeddings_matrix)

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump({
                    "texts": self.indexed_texts,
                    "metadata": self.indexed_metadata,
                    "dimension": self.dimension,
                    "backend": self.backend
                }, f, indent=2)
            logger.info(f"Successfully saved vector index ({len(self.indexed_texts)} vectors) to {index_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save vector index: {e}")
            return False

    def load_index(self, index_file: str, metadata_file: str) -> bool:
        """
        Loads pre-compiled vector index and metadata from disk in <5ms.
        """
        if not os.path.exists(index_file) or not os.path.exists(metadata_file):
            logger.warning(f"Index or metadata file does not exist: {index_file}, {metadata_file}")
            return False

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            self.indexed_texts = meta.get("texts", [])
            self.indexed_metadata = meta.get("metadata", [])
            self.dimension = meta.get("dimension", 384)

            if FAISS_AVAILABLE and index_file.endswith((".bin", ".index", ".faiss")):
                self.faiss_index = faiss.read_index(index_file)
                self.backend = "faiss"
                logger.info(f"Loaded FAISS index with {self.faiss_index.ntotal} vectors from {index_file}")
            else:
                self.embeddings_matrix = np.load(index_file if index_file.endswith(".npy") else f"{index_file}.npy")
                self.backend = "numpy"
                logger.info(f"Loaded NumPy matrix with {len(self.embeddings_matrix)} vectors.")
            return True
        except Exception as e:
            logger.error(f"Failed to load vector index: {e}")
            return False

    def query(
        self,
        query_text: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Queries the indexed attack database for top-k semantically nearest attack turns.

        Args:
            query_text: Prompt text to search.
            top_k: Number of nearest matches to return.

        Returns:
            List of matching records with similarity score and metadata.
        """
        if not self.indexed_texts or (self.faiss_index is None and self.embeddings_matrix is None):
            return []

        emb = self.drift_detector.get_embedding(query_text).astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        emb_2d = np.expand_dims(emb, axis=0)

        results = []
        k = min(top_k, len(self.indexed_texts))

        if FAISS_AVAILABLE and self.faiss_index is not None:
            distances, indices = self.faiss_index.search(emb_2d, k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx >= 0 and idx < len(self.indexed_metadata):
                    meta = dict(self.indexed_metadata[idx])
                    # Cosine distance in IndexFlatIP is in [-1, 1], map to [0, 1]
                    sim = float(np.clip(dist, 0.0, 1.0))
                    meta["similarity"] = round(sim, 4)
                    results.append(meta)
        elif self.embeddings_matrix is not None:
            # NumPy cosine similarity fallback
            sims = np.dot(self.embeddings_matrix, emb)
            top_indices = np.argsort(sims)[::-1][:k]
            for idx in top_indices:
                meta = dict(self.indexed_metadata[idx])
                sim = float(np.clip(sims[idx], 0.0, 1.0))
                meta["similarity"] = round(sim, 4)
                results.append(meta)

        return results

    def score(
        self,
        prompts: Union[str, List[str]],
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Computes the normalized S score in [0, 1] for a prompt or conversation history.

        Args:
            prompts: Single prompt string or list of conversation prompts.
            top_k: Top-k nearest neighbors to consider.

        Returns:
            Dict containing:
                - jailbreak_similarity_score (S): float in [0, 1]
                - max_similarity: float in [0, 1]
                - top_matches: List of match dicts
        """
        if isinstance(prompts, str):
            history = [prompts] if prompts.strip() else []
        else:
            history = [p for p in prompts if p and p.strip()]

        if not history or not self.indexed_texts:
            return {
                "jailbreak_similarity_score": 0.0,
                "max_similarity": 0.0,
                "top_matches": [],
                "explanation": "No prompts or empty attack index: S = 0.0"
            }

        # Analyze current prompt as primary probe, with context from recent turns
        current_prompt = history[-1]
        matches = self.query(current_prompt, top_k=top_k)

        if not matches:
            return {
                "jailbreak_similarity_score": 0.0,
                "max_similarity": 0.0,
                "top_matches": [],
                "explanation": "No index matches found: S = 0.0"
            }

        max_sim = matches[0]["similarity"]
        avg_top_sim = float(np.mean([m["similarity"] for m in matches]))

        # Final payload attack turns receive elevated weighting
        has_final_payload_match = any(m.get("is_final_payload", False) and m["similarity"] > 0.60 for m in matches)

        # Baseline S calculation: 0.70 * max_sim + 0.30 * avg_top_sim
        raw_s = 0.70 * max_sim + 0.30 * avg_top_sim
        if has_final_payload_match:
            raw_s += 0.10

        s_score = float(np.clip(raw_s, 0.0, 1.0))

        return {
            "jailbreak_similarity_score": round(s_score, 4),
            "max_similarity": round(float(max_sim), 4),
            "avg_top_similarity": round(float(avg_top_sim), 4),
            "top_matches": matches,
            "has_final_payload_match": has_final_payload_match,
            "explanation": f"Jailbreak Similarity Score S={s_score:.4f} (MaxSim={max_sim:.2f}, TopCat={matches[0].get('category', 'unknown')})"
        }
