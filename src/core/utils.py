import logging
import random
import numpy as np
import torch
import psutil

logger = logging.getLogger(__name__)

def set_seed(seed: int = 42):
    """
    Sets the random seed for reproducibility across random, numpy, and torch.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    logger.info(f"Reproducible seed set to {seed}")

def log_memory(step: str = ""):
    """
    Detailed logging of memory before/after every step.
    """
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    proc = psutil.Process()
    rss = proc.memory_info().rss / (1024**3)
    vms = proc.memory_info().vms / (1024**3)
    logger.info(
        f"[Memory - {step}] "
        f"RAM Avail: {vm.available/(1024**3):.2f}GB/Used {vm.percent}%, "
        f"Swap Free: {swap.free/(1024**3):.2f}GB/Total {swap.total/(1024**3):.2f}GB, "
        f"Process RSS: {rss:.3f}GB, VMS: {vms:.3f}GB"
    )
