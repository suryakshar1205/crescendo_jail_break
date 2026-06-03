import os
import json
import csv
import time
import logging
import argparse
from typing import List, Dict, Any

from src.core.load_model import load_model
from src.phase1.baseline_chat import initialize_chat, generate_response, reset_chat
from src.core.evaluator import get_evaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Crescendo Jailbreak Detection and Mitigation Benchmarking Tool")
    parser.add_argument("--model_id", type=str, default="meta-llama/Llama-3.2-3B-Instruct", help="Hugging Face model ID")
    parser.add_argument("--config_path", type=str, default="configs/generation_config.json", help="Path to generation config JSON")
    parser.add_argument("--attacks_path", type=str, default="data/attacks/crescendo_attacks.json", help="Path to attacks dataset")
    parser.add_argument("--benign_path", type=str, default="data/benign/benign_chats.json", help="Path to benign dataset")
    parser.add_argument("--csv_output", type=str, default="results/csv/baseline_results.csv", help="Path for CSV results export")
    parser.add_argument("--json_output", type=str, default="results/json/baseline_results.json", help="Path for JSON results export")
    parser.add_argument("--evaluator_type", type=str, default="rule_based", help="Safety evaluator type")
    parser.add_argument("--experiment_id", type=str, default="G0_baseline", help="Unique identifier for the experiment run")
    parser.add_argument("--mock_inference", action="store_true", help="Run in mock mode without loading full Llama weights")
    return parser.parse_args()

class MockModel:
    """
    Mock class simulating Hugging Face CausalLM generation interface for validation.
    """
    def __init__(self):
        self.device = "cpu"
        
    def generate(self, input_ids, **kwargs):
        # Return a simple mock tensor representing some token outputs
        import torch
        # Add 10 dummy token ids to input
        mock_output = torch.cat([input_ids, torch.tensor([[128009, 29, 39, 49]] * input_ids.shape[0], device=input_ids.device)], dim=1)
        return mock_output

    def parameters(self):
        import torch
        # Return a dummy parameter to mock the device retrieval
        p = torch.nn.Parameter(torch.tensor([1.0]))
        return [p]

class MockTokenizer:
    """
    Mock class simulating Hugging Face Tokenizer interface for validation.
    """
    def __init__(self):
        self.pad_token = "<pad>"
        self.eos_token = "<eos>"
        self.pad_token_id = 128009
        self.eos_token_id = 128009

    def apply_chat_template(self, conversation, **kwargs):
        import torch
        # Return a dummy input representation
        return torch.tensor([[1, 2, 3, 4]])

    def decode(self, token_ids, **kwargs):
        return "I cannot provide that instructions as it violates safety policies."

def run_evaluation(
    model,
    tokenizer,
    dataset: List[Dict[str, Any]],
    is_attack: bool,
    evaluator,
    experiment_id: str
) -> List[Dict[str, Any]]:
    """
    Executes dialog interactions turn-by-turn for the given dataset.
    Evaluates compliance/refusals and tracks key metrics.
    """
    results = []
    
    for item in dataset:
        chat_id = item.get("attack_id")
        category = item.get("category", "unknown")
        turns = item.get("turns", [])
        
        logger.info(f"Running session: {chat_id} | Category: {category} | Turns: {len(turns)}")
        
        # Reset chat states
        history = reset_chat()
        
        session_succeeded = False
        
        for turn_idx, user_prompt in enumerate(turns):
            turn_num = turn_idx + 1
            
            # Form conversation context
            history.append({"role": "user", "content": user_prompt})
            
            # Generate model response
            try:
                response, latency_ms = generate_response(history, model, tokenizer)
            except Exception as e:
                logger.error(f"Error during response generation for {chat_id} Turn {turn_num}: {e}")
                response = "[Generation Error]"
                latency_ms = 0.0
                
            # Run safety compliance evaluation
            # Attack is successful if model complies with the instruction
            attack_success = evaluator.evaluate(user_prompt, response)
            
            # For attacks, once compliance is achieved in a turn, the attack is successful
            if is_attack and attack_success:
                session_succeeded = True
            
            # If we are assessing benign chats, "attack_success" means we false-positively triggered compliance detection
            # but in baseline G0, we simply verify standard response safety.
            # To maintain compatibility: false_positive = (evaluation classifies it as safe compliance, i.e., compliance)
            # but wait, a false positive in security means a benign request was blocked/classified as an attack (refusal).
            # So: if is_benign and evaluator says "refusal" (attack_success == False), that's a false positive.
            # We track this distinction downstream.
            
            # Record turn details
            turn_record = {
                "experiment_id": experiment_id,
                "attack_id": chat_id,
                "category": category,
                "turn_number": turn_num,
                "prompt": user_prompt,
                "response": response,
                "attack_success": attack_success,
                "latency_ms": latency_ms
            }
            results.append(turn_record)
            
            # Update history with response
            history.append({"role": "assistant", "content": response})
            logger.info(f"Finished Turn {turn_num} | Latency: {latency_ms:.2f}ms | Compliance Success: {attack_success}")
            
    return results

def main():
    args = parse_args()
    
    # Create directory structures if they don't exist
    os.makedirs(os.path.dirname(args.csv_output), exist_ok=True)
    os.makedirs(os.path.dirname(args.json_output), exist_ok=True)
    
    logger.info(f"Starting benchmark run: {args.experiment_id}")
    
    # Model initialization (Mock or Real)
    if args.mock_inference:
        logger.info("Initializing mock model and tokenizer for validation...")
        model = MockModel()
        tokenizer = MockTokenizer()
    else:
        logger.info("Initializing Hugging Face model and tokenizer...")
        model, tokenizer = load_model(args.model_id)
        
    # Configure the baseline chat globally
    initialize_chat(model, tokenizer, args.config_path)
    
    # Initialize safety evaluator
    evaluator = get_evaluator(args.evaluator_type)
    
    # Load attack dataset
    logger.info(f"Loading attacks dataset from: {args.attacks_path}")
    with open(args.attacks_path, "r") as f:
        attacks_data = json.load(f)
        
    # Load benign dataset
    logger.info(f"Loading benign dataset from: {args.benign_path}")
    with open(args.benign_path, "r") as f:
        benign_data = json.load(f)
        
    # Run evaluation on attacks
    logger.info("Executing evaluation on attack dataset...")
    attack_results = run_evaluation(
        model=model,
        tokenizer=tokenizer,
        dataset=attacks_data,
        is_attack=True,
        evaluator=evaluator,
        experiment_id=args.experiment_id
    )
    
    # Run evaluation on benign chats
    logger.info("Executing evaluation on benign dataset...")
    benign_results = run_evaluation(
        model=model,
        tokenizer=tokenizer,
        dataset=benign_data,
        is_attack=False,
        evaluator=evaluator,
        experiment_id=args.experiment_id
    )
    
    # Combine results
    all_results = attack_results + benign_results
    
    # Export CSV results
    logger.info(f"Exporting CSV results to {args.csv_output}")
    csv_headers = ["experiment_id", "attack_id", "turn_number", "response", "attack_success", "latency_ms"]
    try:
        with open(args.csv_output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_results)
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        
    # Compute summary metrics
    # ASR: For attack chats, was the target complied with at ANY turn?
    # Actually, a successful jailbreak is typically when the final turn succeeds, or if the model complied.
    # Let's count a chat session as a successful attack if the evaluator returned True (compliance) on the final turn.
    successful_attacks = 0
    total_attacks = len(attacks_data)
    
    # Group results by attack_id to examine final turn
    for item in attacks_data:
        chat_id = item.get("attack_id")
        session_turns = [r for r in attack_results if r["attack_id"] == chat_id]
        if session_turns:
            # Look at final turn success
            final_turn = max(session_turns, key=lambda x: x["turn_number"])
            if final_turn["attack_success"]:
                successful_attacks += 1
                
    asr = successful_attacks / total_attacks if total_attacks > 0 else 0.0
    
    # FPR: For benign chats, did the safety filter falsely flag/refuse them?
    # In baseline (G0), there is no safety filter, so the model compliance rate on benign queries should be 100%.
    # If the evaluator says "refusal" (attack_success == False) on a benign input, that means the model itself refused or we flagged it.
    # Therefore, False Positive is when model/system refuses a benign query.
    false_positives = 0
    total_benign_turns = len(benign_results)
    for r in benign_results:
        # If evaluator says "refusal" (False), then it is flagged as unsafe / refused, which is a False Positive for benign content
        if not r["attack_success"]:
            false_positives += 1
            
    fpr = false_positives / total_benign_turns if total_benign_turns > 0 else 0.0
    
    # Latency calculation
    all_latencies = [r["latency_ms"] for r in all_results if r["latency_ms"] > 0]
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
    
    summary_metrics = {
        "total_attacks": total_attacks,
        "successful_attacks": successful_attacks,
        "asr": asr,
        "total_benign_turns": total_benign_turns,
        "false_positives": false_positives,
        "fpr": fpr,
        "average_latency_ms": avg_latency
    }
    
    # Export JSON results
    logger.info(f"Exporting JSON results to {args.json_output}")
    try:
        # Load configs
        with open(args.config_path, "r") as f:
            gen_config = json.load(f)
    except Exception:
        gen_config = {}
        
    json_payload = {
        "experiment_id": args.experiment_id,
        "config": gen_config,
        "summary_metrics": summary_metrics,
        "details": all_results
    }
    
    try:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to export JSON: {e}")
        
    logger.info("=" * 50)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Experiment ID:      {args.experiment_id}")
    logger.info(f"ASR:                {asr:.4f} ({successful_attacks}/{total_attacks})")
    logger.info(f"FPR:                {fpr:.4f} ({false_positives}/{total_benign_turns})")
    logger.info(f"Avg Latency:        {avg_latency:.2f} ms")
    logger.info("=" * 50)
    
if __name__ == "__main__":
    main()
