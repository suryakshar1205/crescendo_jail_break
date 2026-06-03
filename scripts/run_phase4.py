#!/usr/bin/env python3
"""
Phase 4 Runner — Adaptive Contextual Memory Defense Benchmarking.
Usage:
    python scripts/run_phase4.py                  # Full Llama inference
    python scripts/run_phase4.py --mock_inference  # Mock mode for logic validation
"""
import subprocess
import sys
import os

def main():
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [
        sys.executable, "-m", "src.phase4.phase4_benchmark",
    ]
    if "--mock_inference" in sys.argv:
        cmd.append("--mock_inference")
    print(f"[Phase 4] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
