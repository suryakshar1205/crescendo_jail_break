#!/usr/bin/env python3
import os
import sys

LEGACY_FILES = [
    "src/core/judge_evaluator.py",
    "src/core/dynamic_threshold.py",
    "scripts/evaluate_judge_agreement.py",
    "scripts/run_cross_model_benchmark.py",
    "tests/test_judge_evaluator.py",
    "tests/test_dynamic_threshold.py",
    "tests/test_adaptive_adversary.py",
    "scripts/optimize_judge_prompts.py",
    "scripts/simulate_adaptive_attacks.py",
    "scripts/interactive_fpr_auditor.py"
]

def main():
    project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    os.chdir(project_root)
    
    print("Starting cleanup of legacy transient files...")
    removed_count = 0
    for rel_path in LEGACY_FILES:
        abs_path = os.path.abspath(rel_path)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
                print(f"  [x] Removed legacy file: {rel_path}")
                removed_count += 1
            except Exception as e:
                print(f"  [-] Failed to remove {rel_path}: {e}")
        else:
            print(f"  [-] Legacy file not present (already cleaned): {rel_path}")
            
    print(f"Cleanup complete. Total {removed_count} files removed.")

if __name__ == "__main__":
    main()
