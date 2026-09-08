"""
Visualization Suite for PRD CRS Architecture.

Generates high-resolution publication-quality plots:
1. Multi-turn CRS Trajectory (CRS vs Turn across dialogues)
2. Component Dynamics (H, E, S, B vs Turn)
3. Decision States vs Turn
4. Confusion Matrix heatmap
5. Component Ablation Comparison bar chart
"""
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np

# Set matplotlib backend to Agg to allow headless rendering
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def plot_crs_trajectory(
    conversation_records: List[Dict[str, Any]],
    output_path: str = "results/plots/crs_trajectory.png",
    title: str = "Multi-Turn Conversation Risk Score (CRS) Trajectory"
):
    """
    Plots the turn-by-turn CRS trajectory along with decision tier threshold zones.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    turns = [r["turn_number"] for r in conversation_records]
    crs_scores = [r["crs"] for r in conversation_records]
    h_scores = [r["H"] for r in conversation_records]
    e_scores = [r["E"] for r in conversation_records]
    s_scores = [r["S"] for r in conversation_records]
    b_scores = [r["B"] for r in conversation_records]

    # Plot threshold regions
    ax.axhspan(0.00, 0.40, color="#d4edda", alpha=0.5, label="ALLOW Zone (CRS < 0.40)")
    ax.axhspan(0.40, 0.60, color="#fff3cd", alpha=0.5, label="WARN Zone (0.40 ≤ CRS < 0.60)")
    ax.axhspan(0.60, 0.75, color="#ffeeba", alpha=0.5, label="RESTRICT Zone (0.60 ≤ CRS < 0.75)")
    ax.axhspan(0.75, 1.00, color="#f8d7da", alpha=0.5, label="BLOCK Zone (CRS ≥ 0.75)")

    # Plot component lines
    ax.plot(turns, h_scores, "o--", color="#e74c3c", alpha=0.7, label="Harmfulness (H)")
    ax.plot(turns, e_scores, "s--", color="#3498db", alpha=0.7, label="Intent Escalation (E)")
    ax.plot(turns, s_scores, "^--", color="#9b59b6", alpha=0.7, label="Jailbreak Similarity (S)")
    ax.plot(turns, b_scores, "d--", color="#e67e22", alpha=0.7, label="Refusal Bypass (B)")

    # Plot final CRS line
    ax.plot(turns, crs_scores, "o-", color="#2c3e50", linewidth=2.8, markersize=8, label="Final CRS (0.40H + 0.30E + 0.20S + 0.10B)")

    # Annotate decision on each turn
    for r in conversation_records:
        t = r["turn_number"]
        c = r["crs"]
        dec = r["decision"]
        ax.annotate(
            f"T{t}: {dec}\n({c:.2f})",
            (t, c),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="#2c3e50")
        )

    ax.set_xlabel("Conversation Turn", fontsize=12, fontweight="bold")
    ax.set_ylabel("Normalized Risk Score [0.0 - 1.0]", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xticks(turns)
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    logger.info(f"Saved CRS trajectory plot to {output_path}")


def plot_confusion_matrix(
    cm_dict: Dict[str, int],
    output_path: str = "results/plots/confusion_matrix.png",
    title: str = "Defense Classification Confusion Matrix"
):
    """
    Plots a 2x2 confusion matrix heatmap.
    cm_dict: {"TP": int, "FP": int, "TN": int, "FN": int}
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.8, 5.5), dpi=300)

    tp = cm_dict.get("TP", 0)
    fp = cm_dict.get("FP", 0)
    tn = cm_dict.get("TN", 0)
    fn = cm_dict.get("FN", 0)

    matrix = np.array([[tn, fp], [fn, tp]])
    labels = np.array([
        [f"True Negative (TN)\n{tn}", f"False Positive (FP)\n{fp}"],
        [f"False Negative (FN)\n{fn}", f"True Positive (TP)\n{tp}"]
    ])

    im = ax.imshow(matrix, cmap="Blues", interpolation="nearest")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    # Set tick labels
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Passed / Allowed", "Mitigated / Blocked"], fontsize=10, fontweight="bold")
    ax.set_yticklabels(["Benign", "Adversarial Attack"], fontsize=10, fontweight="bold")
    ax.set_xlabel("Predicted Outcome", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Ground Truth Class", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=14)

    # Annotate matrix text
    for i in range(2):
        for j in range(2):
            text_color = "white" if matrix[i, j] > np.max(matrix) / 2 else "black"
            ax.text(j, i, labels[i, j], ha="center", va="center", color=text_color, fontweight="bold", fontsize=10)

    plt.subplots_adjust(left=0.22, right=0.92, top=0.90, bottom=0.15)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved confusion matrix plot to {output_path}")


def plot_prd_ablation_comparison(
    ablation_results: List[Dict[str, Any]],
    output_path: str = "results/plots/prd_ablation_comparison.png",
    title: str = "PRD Component Ablation Study (ASR & DDR Comparison)"
):
    """
    Plots comparative bar charts showing Attack Success Rate (ASR) and Drift Detection Rate (DDR)
    across component ablations.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=300)

    configs = [r["configuration"] for r in ablation_results]
    asr_values = [r["asr"] * 100.0 for r in ablation_results]
    ddr_values = [r["ddr"] * 100.0 for r in ablation_results]

    x = np.arange(len(configs))
    width = 0.35

    rects1 = ax1.bar(x - width/2, asr_values, width, label="ASR (%) [Lower is Better]", color="#e74c3c", alpha=0.85)
    rects2 = ax1.bar(x + width/2, ddr_values, width, label="DDR (%) [Higher is Better]", color="#2ecc71", alpha=0.85)

    ax1.set_ylabel("Percentage (%)", fontsize=11, fontweight="bold")
    ax1.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(configs, rotation=15, ha="right", fontsize=9, fontweight="bold")
    ax1.set_ylim(0, 115)
    ax1.grid(True, linestyle="--", alpha=0.4, axis="y")
    ax1.legend(loc="upper right", framealpha=0.9)

    # Value labels
    for rect in rects1:
        height = rect.get_height()
        ax1.annotate(f"{height:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
    for rect in rects2:
        height = rect.get_height()
        ax1.annotate(f"{height:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    logger.info(f"Saved PRD ablation plot to {output_path}")
