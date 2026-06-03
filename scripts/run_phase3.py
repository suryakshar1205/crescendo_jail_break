#!/usr/bin/env python3
"""
Phase 3 Runner — Hybrid Behavioral + Semantic Risk Fusion Benchmarking.
Usage:
    python scripts/run_phase3.py                  # Full Llama inference
    python scripts/run_phase3.py --mock_inference  # Mock mode for logic validation
"""
import subprocess
import sys
import os

def main():
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [
        sys.executable, "-m", "src.phase3.phase3_benchmark",
    ]
    if "--mock_inference" in sys.argv:
        cmd.append("--mock_inference")
    print(f"[Phase 3] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
