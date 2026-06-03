#!/usr/bin/env python3
"""
Phase 1 Runner — Baseline Benchmarking.
Usage:
    python scripts/run_phase1.py                  # Full Llama inference (CPU ~60-80s/turn)
    python scripts/run_phase1.py --mock_inference  # Mock mode for logic validation (<2s)
"""
import subprocess
import sys
import os

def main():
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [
        sys.executable, "-m", "src.phase1.benchmark",
        "--experiment_id", "G0_baseline",
    ]
    # Forward --mock_inference if present
    if "--mock_inference" in sys.argv:
        cmd.append("--mock_inference")
    print(f"[Phase 1] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
