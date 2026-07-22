#!/usr/bin/env python3
"""
Phase 7 Runner — Turn 1 Dynamic Thresholding & Calibration.
Usage:
    python scripts/run_phase7.py
    python scripts/run_phase7.py --mock_inference
"""
import subprocess
import sys
import os

def main():
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    cmd = [
        sys.executable, "-m", "src.phase7.phase7_benchmark",
    ]
    if "--mock_inference" in sys.argv:
        cmd.append("--mock_inference")
    print(f"[Phase 7] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.getcwd())
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
