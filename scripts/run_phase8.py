#!/usr/bin/env python3
"""
Phase 8 Runner — Adaptive Adversary Simulation.
Usage:
    python scripts/run_phase8.py
"""
import subprocess
import sys
import os

def main():
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [
        sys.executable, "-m", "src.phase8.phase8_benchmark",
    ]
    print(f"[Phase 8] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
