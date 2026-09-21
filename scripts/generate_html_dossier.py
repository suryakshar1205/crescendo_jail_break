#!/usr/bin/env python3
"""
Generates standalone and web HTML dossiers from:
1. final_verified_results_dossier.md -> results/final_verified_results_dossier.html & web/results_dossier.html
2. master_architecture_report.md     -> results/master_architecture_report.html & web/master_architecture_report.html
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER_PATH = os.path.join(PROJECT_ROOT, "web", "dossier_header.html")
FOOTER_PATH = os.path.join(PROJECT_ROOT, "web", "dossier_footer.html")

RESULTS_MD = os.path.join(PROJECT_ROOT, "results", "final_verified_results_dossier.md")
ARCH_MD = os.path.join(PROJECT_ROOT, "results", "master_architecture_report.md")


def generate():
    if not os.path.exists(HEADER_PATH) or not os.path.exists(FOOTER_PATH):
        print("Error: header or footer template not found.")
        return 1

    with open(HEADER_PATH, "r", encoding="utf-8") as f:
        base_header = f.read()
    with open(FOOTER_PATH, "r", encoding="utf-8") as f:
        footer = f.read()

    # =========================================================================
    # 1. Generate Results Dossier
    # =========================================================================
    if os.path.exists(RESULTS_MD):
        with open(RESULTS_MD, "r", encoding="utf-8") as f:
            results_md = f.read()

        # Custom nav action adding link to Architecture Blueprint
        nav_action_results = """      <a href="master_architecture_report.html" class="btn-action" title="Open Master Architectural Blueprint">
        <span>🏛️</span> Architecture Blueprint
      </a>
      <button class="btn-action" onclick="window.print()">
        <span>🖨️</span> Print / Save PDF
      </button>
      <a href="../web/index.html" class="btn-action" title="Open Interactive Web Testbench">
        <span>🌐</span> Open Testbench
      </a>"""

        results_header = base_header.replace(
            """      <button class="btn-action" onclick="window.print()">
        <span>🖨️</span> Print / Save PDF
      </button>
      <a href="../web/index.html" class="btn-action" title="Open Interactive Web Testbench">
        <span>🌐</span> Open Testbench
      </a>""",
            nav_action_results
        )

        out_results_standalone = os.path.join(PROJECT_ROOT, "results", "final_verified_results_dossier.html")
        with open(out_results_standalone, "w", encoding="utf-8") as f:
            f.write(f"{results_header}\n{results_md}\n{footer}")
        print(f"Created: {out_results_standalone}")

        # Web version
        web_nav_action_results = nav_action_results.replace('href="master_architecture_report.html"', 'href="/master_architecture_report.html"').replace('href="../web/index.html"', 'href="/"')
        web_results_header = base_header.replace(
            """      <button class="btn-action" onclick="window.print()">
        <span>🖨️</span> Print / Save PDF
      </button>
      <a href="../web/index.html" class="btn-action" title="Open Interactive Web Testbench">
        <span>🌐</span> Open Testbench
      </a>""",
            web_nav_action_results
        ).replace('href="../web/index.html"', 'href="/"')

        out_results_web = os.path.join(PROJECT_ROOT, "web", "results_dossier.html")
        with open(out_results_web, "w", encoding="utf-8") as f:
            f.write(f"{web_results_header}\n{results_md}\n{footer}")
        print(f"Created: {out_results_web}")
    else:
        print(f"Warning: {RESULTS_MD} not found, skipping results dossier generation.")

    # =========================================================================
    # 2. Generate Master Architecture Report
    # =========================================================================
    if os.path.exists(ARCH_MD):
        with open(ARCH_MD, "r", encoding="utf-8") as f:
            arch_md = f.read()

        # Customize header for Architecture Blueprint
        arch_header = base_header.replace(
            "<title>Crescendo Multi-Turn Jailbreak Defense — Master Verified Results Dossier</title>",
            "<title>Crescendo Multi-Turn Jailbreak Defense — Master Architectural Blueprint</title>"
        ).replace(
            "<h1>CRESCENDO DEFENSE LAB — MASTER RESULTS DOSSIER</h1>",
            "<h1>CRESCENDO DEFENSE LAB — MASTER ARCHITECTURAL BLUEPRINT</h1>"
        ).replace(
            "<p>Inference-Time Multi-Turn Jailbreak Defense & Empirical Benchmark Audit</p>",
            "<p>Stateful Inference-Time Multi-Turn Jailbreak Defense & Systems Blueprint</p>"
        ).replace(
            """      <span class="badge-chip badge-emerald">● 34/34 Tests Passing</span>
      <span class="badge-chip badge-emerald">● ASR: 0.00%</span>
      <span class="badge-chip badge-emerald">● DDR: 100.00%</span>
      <span class="badge-chip badge-cyan">● Latency: 7.2ms</span>""",
            """      <span class="badge-chip badge-cyan">● Decoupled Proxy</span>
      <span class="badge-chip badge-emerald">● Zero Token Overhead</span>
      <span class="badge-chip badge-emerald">● 7.2ms CPU Latency</span>
      <span class="badge-chip badge-indigo">● FAISS Vector Store</span>"""
        )

        nav_action_arch = """      <a href="final_verified_results_dossier.html" class="btn-action" title="Open Master Verified Results Dossier">
        <span>📊</span> Results Dossier
      </a>
      <button class="btn-action" onclick="window.print()">
        <span>🖨️</span> Print / Save PDF
      </button>
      <a href="../web/index.html" class="btn-action" title="Open Interactive Web Testbench">
        <span>🌐</span> Open Testbench
      </a>"""

        arch_header_standalone = arch_header.replace(
            """      <button class="btn-action" onclick="window.print()">
        <span>🖨️</span> Print / Save PDF
      </button>
      <a href="../web/index.html" class="btn-action" title="Open Interactive Web Testbench">
        <span>🌐</span> Open Testbench
      </a>""",
            nav_action_arch
        )

        out_arch_standalone = os.path.join(PROJECT_ROOT, "results", "master_architecture_report.html")
        with open(out_arch_standalone, "w", encoding="utf-8") as f:
            f.write(f"{arch_header_standalone}\n{arch_md}\n{footer}")
        print(f"Created: {out_arch_standalone}")

        # Web version
        web_nav_action_arch = nav_action_arch.replace('href="final_verified_results_dossier.html"', 'href="/results_dossier.html"').replace('href="../web/index.html"', 'href="/"')
        arch_header_web = arch_header.replace(
            """      <button class="btn-action" onclick="window.print()">
        <span>🖨️</span> Print / Save PDF
      </button>
      <a href="../web/index.html" class="btn-action" title="Open Interactive Web Testbench">
        <span>🌐</span> Open Testbench
      </a>""",
            web_nav_action_arch
        ).replace('href="../web/index.html"', 'href="/"')

        out_arch_web = os.path.join(PROJECT_ROOT, "web", "master_architecture_report.html")
        with open(out_arch_web, "w", encoding="utf-8") as f:
            f.write(f"{arch_header_web}\n{arch_md}\n{footer}")
        print(f"Created: {out_arch_web}")
    else:
        print(f"Warning: {ARCH_MD} not found, skipping architecture report generation.")

    return 0


if __name__ == "__main__":
    sys.exit(generate())
