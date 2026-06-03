import os
import json
import time
import logging
import torch
from typing import List, Dict, Any, Tuple
from src.core.load_model import set_seed

logger = logging.getLogger(__name__)

# Module-level globals to cache the model, tokenizer, and config
_model = None
_tokenizer = None
_config = None

def load_config(config_path: str = "configs/generation_config.json") -> Dict[str, Any]:
    """
    Loads the frozen generation configuration. Falls back to defaults if not found.
    """
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found at {config_path}. Using fallback default configuration.")
        return {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_new_tokens": 256,
            "do_sample": True,
            "seed": 42
        }
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            logger.info(f"Loaded generation configuration from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to parse configuration file: {e}. Using fallback defaults.")
        return {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_new_tokens": 256,
            "do_sample": True,
            "seed": 42
        }

def initialize_chat(model=None, tokenizer=None, config_path: str = "configs/generation_config.json") -> List[Dict[str, str]]:
    """
    Initializes the baseline chat environment. Caches the model and tokenizer 
    globally if provided, and loads the frozen generation config.
    Returns an empty conversation history.
    """
    global _model, _tokenizer, _config
    
    _config = load_config(config_path)
    
    if model is not None:
        _model = model
    if tokenizer is not None:
        _tokenizer = tokenizer
        
    logger.info("Baseline chat initialized.")
    return []

def reset_chat() -> List[Dict[str, str]]:
    """
    Resets the conversation history by returning a clean, empty list.
    """
    logger.info("Conversation history reset.")
    return []

def generate_response(
    conversation_history: List[Dict[str, str]],
    model=None,
    tokenizer=None
) -> Tuple[str, float]:
    """
    Generates a response from the model based on the conversation history.
    Maintains reproducibility by re-applying the frozen seed before generation.
    Returns a tuple of (response_text, latency_ms).
    """
    global _model, _tokenizer, _config
    
    active_model = model if model is not None else _model
    active_tokenizer = tokenizer if tokenizer is not None else _tokenizer
    
    if active_model is None or active_tokenizer is None:
        logger.error("Attempted to generate response before model and tokenizer were loaded.")
        raise ValueError("Model and tokenizer must be initialized/cached before generating a response.")
        
    if _config is None:
        _config = load_config()
        
    # Re-apply seed for deterministic/reproducible generation runs
    set_seed(_config.get("seed", 42))
    
    try:
        # Construct chat format using model template
        inputs_formatted = active_tokenizer.apply_chat_template(
            conversation_history,
            add_generation_prompt=True,
            return_tensors="pt"
        )
        
        # Shift inputs to the active model device
        device = next(iter(active_model.parameters())).device
        inputs_formatted = inputs_formatted.to(device)
        
        # Generation parameters matching the frozen configuration
        gen_params = {
            "temperature": _config.get("temperature", 0.7),
            "top_p": _config.get("top_p", 0.9),
            "max_new_tokens": _config.get("max_new_tokens", 256),
            "do_sample": _config.get("do_sample", True),
            "pad_token_id": active_tokenizer.pad_token_id,
            "eos_token_id": active_tokenizer.eos_token_id
        }
        
        # Record wall-clock time
        start_time = time.perf_counter()
        
        with torch.no_grad():
            outputs = active_model.generate(
                inputs_formatted,
                **gen_params
            )
            
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Decode only the newly generated response slice
        input_len = inputs_formatted.shape[1]
        response_tokens = outputs[0][input_len:]
        response_text = active_tokenizer.decode(response_tokens, skip_special_tokens=True).strip()
        
        return response_text, latency_ms
        
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        raise e

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Baseline Chat Test Runner")
    parser.add_argument("--mock_inference", action="store_true", help="Run with mock model/tokenizer")
    args = parser.parse_args()
    
    # Define Mock classes if mock is requested
    if args.mock_inference:
        class MockModel:
            def __init__(self):
                self.device = "cpu"
            def generate(self, input_ids, **kwargs):
                import torch
                # Append dummy token IDs
                return torch.cat([input_ids, torch.tensor([[128009, 29, 39, 49]], device=input_ids.device)], dim=1)
            def parameters(self):
                import torch
                return [torch.nn.Parameter(torch.tensor([1.0]))]
        
        class MockTokenizer:
            def __init__(self):
                self.pad_token = "<pad>"
                self.eos_token = "<eos>"
                self.pad_token_id = 128009
                self.eos_token_id = 128009
            def apply_chat_template(self, conversation, **kwargs):
                import torch
                return torch.tensor([[1, 2, 3, 4]])
            def decode(self, token_ids, **kwargs):
                # Return context-aware responses to verify multi-turn behavior
                # The last prompt in conversation determines the response
                return "Mock response: Phishing is a social engineering attack used to steal user data."

        logger.info("Initializing mock environment for baseline chat...")
        model = MockModel()
        tokenizer = MockTokenizer()
    else:
        logger.info("Loading real Llama model...")
        from src.core.load_model import load_model
        try:
            model, tokenizer = load_model()
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            print("\n[ALERT] Gated repo error or CUDA OOM. Try running with: python src/baseline_chat.py --mock_inference")
            exit(1)
            
    history = initialize_chat(model, tokenizer)
    
    # Run test conversations: "hello" and "What is phishing?"
    prompts = ["hello", "What is phishing?"]
    for prompt in prompts:
        print(f"\nUser: {prompt}")
        history.append({"role": "user", "content": prompt})
        try:
            response, latency = generate_response(history, model, tokenizer)
            history.append({"role": "assistant", "content": response})
            print(f"Assistant: {response}")
            print(f"Latency: {latency:.2f}ms")
        except Exception as e:
            print(f"Error during response generation: {e}")
            
    # Test reset behavior
    history = reset_chat()
    print(f"\nAfter reset, history length: {len(history)}")

