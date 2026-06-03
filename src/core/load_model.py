import os
import gc
import random
import logging
import psutil
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def log_memory(step=""):
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

def load_model(model_id: str = "meta-llama/Llama-3.2-3B-Instruct", seed: int = 42):
    """
    Loads the tokenizer and the model with aggressive memory optimizations.
    Uses local sharded model folder to execute efficiently on CPU without OOM.
    """
    # 15. Disable gradients globally for inference-only mode
    torch.set_grad_enabled(False)
    
    # Optimize CPU threads for inference speed (avoid hyperthreading overhead)
    if not torch.cuda.is_available():
        torch.set_num_threads(6)
        logger.info("Set PyTorch CPU threads to 6 (physical cores count).")
    
    # 5. Garbage collection before model load
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    log_memory("Before Seed Set")
    set_seed(seed)
    
    # Check if we should redirect Llama-3.2-3B-Instruct to our sharded local folder
    sharded_dir = "models/Llama-3.2-3B-Instruct-sharded"
    if "Llama-3.2-3B-Instruct" in model_id:
        if os.path.exists(sharded_dir):
            logger.info(f"Redirecting model path from '{model_id}' to local sharded path '{sharded_dir}'")
            model_id = sharded_dir
        else:
            logger.warning(f"Sharded directory {sharded_dir} not found. Proceeding with {model_id}")

    logger.info(f"Initializing tokenizer for model: {model_id}")
    # Get HuggingFace token from environment if available
    hf_token = os.environ.get("HF_TOKEN", None)
    
    # 18. Reduce tokenizer cache duplication & optimize loading
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        token=hf_token,
        use_fast=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        logger.info("Pad token set to EOS token.")
    
    log_memory("After Tokenizer load")
    
    # 3. Memory-safe dtype logic try order
    dtypes_to_try = [torch.float16, torch.bfloat16, torch.float32]
    
    # If we are CPU-only, float16 operations are unsupported/unstable during generation,
    # so we prioritize bfloat16 over float16 on CPU.
    if not torch.cuda.is_available():
        dtypes_to_try = [torch.bfloat16, torch.float16, torch.float32]
        
    model = None
    last_error = None
    
    for dtype in dtypes_to_try:
        logger.info(f"Attempting to load model weights with dtype: {dtype}")
        gc.collect()
        
        try:
            # 1. low_cpu_mem_usage=True
            # 2. device_map="cpu" (or "auto" if CUDA is available)
            # 10. streaming-safe shard loading (handled by local 500MB shards)
            device_map = "auto" if torch.cuda.is_available() else "cpu"
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                dtype=dtype,
                device_map=device_map,
                low_cpu_mem_usage=True,
                token=hf_token
            )
            logger.info(f"Successfully loaded model with dtype: {dtype}")
            break
        except Exception as e:
            logger.warning(f"Failed to load model with dtype {dtype}: {e}")
            last_error = e
            # Cleanup resources before fallback attempt
            model = None
            gc.collect()
            
    if model is None:
        logger.error("Failed to load model with all attempted dtypes.")
        raise last_error if last_error else RuntimeError("Model loading failed.")
        
    # 17. Enforce eval mode
    model.eval()
    
    # 16. Inference-only mode optimization
    for param in model.parameters():
        param.requires_grad = False
        
    log_memory("After Model load")
    return model, tokenizer

if __name__ == "__main__":
    try:
        model, tokenizer = load_model()
        print("Model loading test passed successfully.")
    except Exception as e:
        logger.error(f"Error during model loading test: {e}")
