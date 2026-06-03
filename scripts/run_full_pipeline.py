#!/usr/bin/env python3
"""
Full Pipeline Runner — Executes all 5 phases sequentially.
Usage:
    python scripts/run_full_pipeline.py                  # Full Llama inference
    python scripts/run_full_pipeline.py --mock_inference  # Mock mode for logic validation (<2s total)
"""
import subprocess
import sys
import os
import time

PHASES = [
    ("Phase 1 — Baseline Benchmarking", ["-m", "src.phase1.benchmark", "--experiment_id", "G0_baseline"]),
    ("Phase 2 — Semantic Drift Detection", ["-m", "src.phase2.phase2_benchmark"]),
    ("Phase 3 — Hybrid Risk Fusion", ["-m", "src.phase3.phase3_benchmark"]),
    ("Phase 4 — Adaptive Contextual Memory", ["-m", "src.phase4.phase4_benchmark"]),
    ("Phase 5 — Robustness & Generalization", ["-m", "src.phase5.phase5_benchmark"]),
]


def main():
    project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    os.chdir(project_root)

    mock = "--mock_inference" in sys.argv
    mode_label = "MOCK" if mock else "FULL"
    
    print("=" * 70)
    print(f"  CRESCENDO JAILBREAK DEFENSE — FULL PIPELINE ({mode_label} MODE)")
    print("=" * 70)
    
    overall_start = time.time()
    results = []

    for phase_name, module_args in PHASES:
        print(f"\n{'-' * 60}")
        print(f"  > {phase_name}")
        print(f"{'-' * 60}")
        
        cmd = [sys.executable] + module_args
        if mock:
            cmd.append("--mock_inference")
        
        phase_start = time.time()
        result = subprocess.run(cmd, cwd=os.getcwd())
        elapsed = time.time() - phase_start
        
        status = "PASS" if result.returncode == 0 else "FAIL"
        results.append((phase_name, status, elapsed))
        
        print(f"  [+] {phase_name}: {status} ({elapsed:.1f}s)")
        
        if result.returncode != 0:
            print(f"\n  [-] {phase_name} FAILED with exit code {result.returncode}")
            print(f"    Stopping pipeline.")
            break
    
    total_time = time.time() - overall_start
    
    print(f"\n{'=' * 70}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'=' * 70}")
    for name, status, elapsed in results:
        icon = "[+]" if status == "PASS" else "[-]"
        print(f"  {icon} {name}: {status} ({elapsed:.1f}s)")
    print(f"\n  Total time: {total_time:.1f}s")
    
    failed = any(s == "FAIL" for _, s, _ in results)
    if failed:
        print("  [!] Pipeline completed with FAILURES.")
        sys.exit(1)
    else:
        print("  [+] All phases completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
