#!/usr/bin/env python3
"""
Phase 9 Runner — Cross-Model Harness.
Usage:
    python scripts/run_phase9.py
    python scripts/run_phase9.py --mock_inference
"""
import subprocess
import sys
import os

def main():
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [
        sys.executable, "-m", "src.phase9.phase9_benchmark",
    ]
    if "--mock_inference" in sys.argv:
        cmd.append("--mock_inference")
    print(f"[Phase 9] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
