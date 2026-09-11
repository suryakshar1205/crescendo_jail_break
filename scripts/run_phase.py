#!/usr/bin/env python3
"""
Master Unified Research Phase Runner.

Consolidates the 9 historical phase milestones into a single, standardized entrypoint:
    Phase 1: Baseline Llama-3.2-3B Vulnerability Benchmarking
    Phase 2: Embedding Drift Detection Layer
    Phase 3: Behavioral Rule Detection & Multi-Signal Risk Fusion
    Phase 4: Multi-Turn Conversation Memory Engine
    Phase 5: Component Ablation & Threshold Stability
    Phase 6: LLM-as-a-Judge Agreement Analysis
    Phase 7: Dynamic Threshold Calibration
    Phase 8: Hardware Resource & Latency Profiling
    Phase 9: Adaptive Adversary Simulation & Prompt Hardening

Usage:
    python scripts/run_phase.py --phase 1
    python scripts/run_phase.py --phase 1 --mock_inference
    python scripts/run_phase.py --all --mock_inference
"""
import os
os.environ["MPLBACKEND"] = "Agg"
import sys
import argparse
import subprocess
from typing import List

PHASE_MODULES = {
    1: "src.phase1.benchmark",
    2: "src.phase2.phase2_benchmark",
    3: "src.phase3.phase3_benchmark",
    4: "src.phase4.phase4_benchmark",
    5: "src.phase5.phase5_benchmark",
    6: "src.phase6.phase6_benchmark",
    7: "src.phase7.phase7_benchmark",
    8: "src.phase8.phase8_benchmark",
    9: "src.phase9.phase9_benchmark",
}


def run_single_phase(phase: int, extra_args: List[str]) -> int:
    """Executes a single phase benchmark module."""
    if phase not in PHASE_MODULES:
        print(f"[!] Error: Invalid phase {phase}. Must be between 1 and 9.")
        return 1

    module_name = PHASE_MODULES[phase]
    cmd = [sys.executable, "-m", module_name]

    # Filter flags not recognized by specific phases
    phase_args = list(extra_args)
    if phase in (7, 8) and "--mock_inference" in phase_args:
        phase_args.remove("--mock_inference")

    if phase == 1 and "--experiment_id" not in phase_args:
        cmd.extend(["--experiment_id", "G0_baseline"])

    cmd.extend(phase_args)

    print("=" * 70)
    print(f"RUNNING RESEARCH MILESTONE -- PHASE {phase}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 70)

    result = subprocess.run(cmd, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return result.returncode


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Unified Research Phase Runner for Crescendo Defense Milestones."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--phase", type=int, choices=range(1, 10), help="Phase number to run (1-9)")
    group.add_argument("--all", action="store_true", help="Sequentially run all phases (1-9)")
    parser.add_argument("--mock_inference", action="store_true", help="Run in mock mode for fast execution")

    args, unknown = parser.parse_known_args()

    forward_args = list(unknown)
    if args.mock_inference and "--mock_inference" not in forward_args:
        forward_args.append("--mock_inference")

    if args.phase:
        code = run_single_phase(args.phase, forward_args)
        sys.exit(code)

    if args.all:
        print("\n" + "=" * 70)
        print("EXECUTING ALL RESEARCH PHASES (1 through 9)")
        print("=" * 70)
        for p in range(1, 10):
            code = run_single_phase(p, forward_args)
            if code != 0:
                print(f"[!] Phase {p} failed with exit code {code}. Aborting remaining phases.")
                sys.exit(code)
        print("\n[+] All 9 phases completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
