#!/usr/bin/env python3
"""
Generates standalone and web HTML dossiers from final_verified_results_dossier.md.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(PROJECT_ROOT, "results", "final_verified_results_dossier.md")
HEADER_PATH = os.path.join(PROJECT_ROOT, "web", "dossier_header.html")
FOOTER_PATH = os.path.join(PROJECT_ROOT, "web", "dossier_footer.html")
OUT_HTML_RESULTS = os.path.join(PROJECT_ROOT, "results", "final_verified_results_dossier.html")
OUT_HTML_WEB = os.path.join(PROJECT_ROOT, "web", "results_dossier.html")


def generate():
    if not os.path.exists(MD_PATH):
        print(f"Error: {MD_PATH} not found.")
        return 1
    if not os.path.exists(HEADER_PATH) or not os.path.exists(FOOTER_PATH):
        print("Error: header or footer template not found.")
        return 1

    with open(HEADER_PATH, "r", encoding="utf-8") as f:
        header = f.read()
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md = f.read()
    with open(FOOTER_PATH, "r", encoding="utf-8") as f:
        footer = f.read()

    # Results version
    full_html = f"{header}\n{md}\n{footer}"
    with open(OUT_HTML_RESULTS, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"Created: {OUT_HTML_RESULTS}")

    # Web version
    web_header = header.replace('href="../web/index.html"', 'href="/"')
    web_html = f"{web_header}\n{md}\n{footer}"
    with open(OUT_HTML_WEB, "w", encoding="utf-8") as f:
        f.write(web_html)
    print(f"Created: {OUT_HTML_WEB}")
    return 0


if __name__ == "__main__":
    sys.exit(generate())
