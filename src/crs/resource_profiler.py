"""
Hardware, Memory, and Token Overhead Profiler for the Crescendo Defense Pipeline.
Tracks CPU/GPU memory footprint, processing latency, and token overhead percentage.
"""
import os
import psutil
try:
    import torch
    HAS_TORCH = True
except Exception:
    torch = None
    HAS_TORCH = False

from typing import Dict, Any, Optional

class ResourceProfiler:
    """
    Monitors host RAM, GPU VRAM, and prompt/response token overhead.
    """
    def __init__(self, baseline_token_estimator: Optional[Any] = None):
        self.process = psutil.Process(os.getpid())
        self.has_cuda = HAS_TORCH and torch.cuda.is_available()

    def get_hardware_snapshot(self) -> Dict[str, Any]:
        """Captures instantaneous process RAM and CUDA VRAM usage."""
        ram_info = self.process.memory_info()
        ram_mb = ram_info.rss / (1024 * 1024)
        vram_mb = 0.0
        vram_allocated_mb = 0.0

        if self.has_cuda:
            vram_allocated_mb = torch.cuda.memory_allocated() / (1024 * 1024)
            vram_mb = torch.cuda.memory_reserved() / (1024 * 1024)

        return {
            "ram_rss_mb": round(ram_mb, 2),
            "ram_vms_mb": round(ram_info.vms / (1024 * 1024), 2),
            "vram_allocated_mb": round(vram_allocated_mb, 2),
            "vram_reserved_mb": round(vram_mb, 2),
            "has_gpu": self.has_cuda,
            "cpu_percent": self.process.cpu_percent(interval=None)
        }

    @staticmethod
    def estimate_token_count(text: str) -> int:
        """
        Heuristic fast token count (~4 chars per token average in English/code).
        Avoids requiring heavy tokenizer initialization in fast defense loops.
        """
        if not text:
            return 0
        return max(1, len(text.split()))

    def calculate_token_overhead(
        self,
        user_prompt: str,
        intervention_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates token overhead added by the defense intervention or reasoning wrappers.
        If prompt is allowed cleanly, overhead is 0%.
        If intervened/blocked, overhead reflects the safety directive tokens relative to baseline.
        """
        baseline_prompt_tokens = self.estimate_token_count(user_prompt)
        intervention_tokens = self.estimate_token_count(intervention_message) if intervention_message else 0
        
        # Total tokens emitted/processed under defense
        defended_tokens = baseline_prompt_tokens + intervention_tokens
        token_overhead_ratio = (intervention_tokens / baseline_prompt_tokens) if baseline_prompt_tokens > 0 else 0.0

        return {
            "baseline_prompt_tokens": baseline_prompt_tokens,
            "intervention_tokens": intervention_tokens,
            "total_tokens_defended": defended_tokens,
            "token_overhead_percent": round(token_overhead_ratio * 100.0, 2)
        }
