import os
import json
import csv
import numpy as np
import matplotlib.pyplot as plt

def main():
    os.makedirs("results/plots", exist_ok=True)
    
    # Set style for premium aesthetic
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.size'] = 10
    
    # ----------------------------------------------------
    # Load Data
    # ----------------------------------------------------
    # 1. Stability Data
    thresholds = []
    asr_list = []
    fpr_list = []
    ddr_list = []
    mitigation_rates = []
    avg_det_turns = []
    latencies = []
    
    with open("results/phase5/threshold_stability.csv", "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            thresholds.append(float(r["threshold"]))
            asr_list.append(float(r["asr"]))
            fpr_list.append(float(r["fpr"]))
            ddr_list.append(float(r["ddr"]))
            mitigation_rates.append(float(r["mitigation_rate"]))
            avg_det_turns.append(float(r["avg_detection_turn"]))
            latencies.append(float(r["avg_latency_ms"]))
            
    # 2. Ablation Data
    ablation_configs = []
    ablation_asr = []
    ablation_ddr = []
    ablation_perf_drop = []
    with open("results/phase5/ablation_results.csv", "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ablation_configs.append(r["configuration"])
            ablation_asr.append(float(r["asr"]))
            ablation_ddr.append(float(r["ddr"]))
            ablation_perf_drop.append(float(r["perf_drop_pct"]))
            
    # 3. Phase 5 Details (JSON)
    with open("results/phase5/phase5_results.json", "r") as f:
        p5_json = json.load(f)
    details = p5_json["details"]
    
    # Group details by attack_id
    sessions = {}
    for r in details:
        aid = r["attack_id"]
        if aid not in sessions:
            sessions[aid] = []
        sessions[aid].append(r)
        
    # Analyze by category
    categories_attacks = ["delayed_persuasion", "roleplay_escalation", "mitigation_bypass", "indirect_social_engineering", "long_horizon_crescendo", "reframed_instruction"]
    
    det_turns_by_cat = {c: [] for c in categories_attacks}
    bypass_int_by_cat = {c: 0 for c in categories_attacks}
    total_turns_by_cat = {c: 0 for c in categories_attacks}
    blocked_by_cat = {c: 0 for c in categories_attacks}
    leaked_by_cat = {c: 0 for c in categories_attacks}
    
    for aid, turns in sessions.items():
        # Get category
        cat = turns[0]["category"]
        if cat == "education" or cat == "unknown":
            continue
        if cat not in det_turns_by_cat:
            det_turns_by_cat[cat] = []
            bypass_int_by_cat[cat] = 0
            total_turns_by_cat[cat] = 0
            blocked_by_cat[cat] = 0
            leaked_by_cat[cat] = 0
            
        total_turns_by_cat[cat] += len(turns)
        
        # Check if flagged and find detection turn
        flagged_turns = [t["turn_number"] for t in turns if t["detector_flagged"]]
        if flagged_turns:
            det_turns_by_cat[cat].append(min(flagged_turns))
            blocked_by_cat[cat] += 1
        else:
            # Check final turn success
            final_turn = max(turns, key=lambda x: x["turn_number"])
            if final_turn["attack_success"]:
                leaked_by_cat[cat] += 1
            else:
                blocked_by_cat[cat] += 1  # Blocked by Llama model refusal
                
        # Count bypass interceptions
        for t in turns:
            if t["bypass_score"] > 0.25 and t["detector_flagged"]:
                bypass_int_by_cat[cat] += 1

    # ----------------------------------------------------
    # Plot 1: Holdout ASR vs threshold
    # ----------------------------------------------------
    plt.figure(figsize=(6, 4))
    plt.plot(thresholds, asr_list, marker='o', color='#E53935', linewidth=2.5, markersize=8)
    plt.title("Holdout Attack Success Rate (ASR) vs Threshold", fontsize=11, fontweight='bold', pad=10)
    plt.xlabel("Threshold (T)", fontsize=10)
    plt.ylabel("ASR", fontsize=10)
    plt.ylim(-0.05, 1.05)
    plt.xticks(thresholds)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig("results/plots/holdout_asr_vs_threshold.png", dpi=300)
    plt.close()
    
    # ----------------------------------------------------
    # Plot 2: Threshold stability curve
    # ----------------------------------------------------
    plt.figure(figsize=(7, 4.5))
    plt.plot(thresholds, asr_list, marker='o', color='#E53935', label='ASR', linewidth=2)
    plt.plot(thresholds, fpr_list, marker='s', color='#1E88E5', label='FPR', linewidth=2)
    plt.plot(thresholds, ddr_list, marker='^', color='#4CAF50', label='DDR', linewidth=2)
    plt.plot(thresholds, mitigation_rates, marker='d', color='#FFB300', label='Mitigation Rate', linewidth=1.5, linestyle='--')
    plt.title("Defense Metrics Stability Curve across Threshold Window", fontsize=11, fontweight='bold', pad=10)
    plt.xlabel("Threshold (T)", fontsize=10)
    plt.ylabel("Metric Value", fontsize=10)
    plt.ylim(-0.05, 1.05)
    plt.xticks(thresholds)
    plt.legend(loc='best', frameon=True)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig("results/plots/threshold_stability_curve.png", dpi=300)
    plt.close()
    
    # ----------------------------------------------------
    # Plot 3: Component ablation comparison
    # ----------------------------------------------------
    plt.figure(figsize=(8, 4.5))
    x = np.arange(len(ablation_configs))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(8, 4.5))
    rects1 = ax.bar(x - width/2, ablation_asr, width, label='ASR', color='#E53935')
    rects2 = ax.bar(x + width/2, ablation_ddr, width, label='DDR', color='#4CAF50')
    
    ax.set_ylabel('Metric Value')
    ax.set_title('Component Ablation Study on Holdout Dataset', fontsize=11, fontweight='bold', pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(ablation_configs, rotation=15, ha='right')
    ax.set_ylim(0, 1.1)
    ax.legend(frameon=True)
    ax.grid(True, linestyle='--', alpha=0.4)
    
    # Add values on top of bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)
            
    autolabel(rects1)
    autolabel(rects2)
    plt.tight_layout()
    plt.savefig("results/plots/component_ablation_comparison.png", dpi=300)
    plt.close()
    
    # ----------------------------------------------------
    # Plot 4: Seen vs unseen robustness
    # ----------------------------------------------------
    # Seen (Phase 4) vs Unseen (Phase 5 Holdout) at T = 0.92
    metrics_lbls = ['ASR', 'FPR', 'DDR']
    seen_vals = [0.00, 0.00, 1.00]
    unseen_vals = [0.00, 0.00, 1.00]
    
    x = np.arange(len(metrics_lbls))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(6, 4))
    rects1 = ax.bar(x - width/2, seen_vals, width, label='Seen (Phase 4)', color='#7E57C2')
    rects2 = ax.bar(x + width/2, unseen_vals, width, label='Unseen Holdout (Phase 5)', color='#26A69A')
    
    ax.set_ylabel('Value')
    ax.set_title('Generalization: Seen vs Unseen Robustness Comparison', fontsize=11, fontweight='bold', pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics_lbls)
    ax.set_ylim(0, 1.2)
    ax.legend(frameon=True)
    ax.grid(True, linestyle='--', alpha=0.5)
    
    autolabel(rects1)
    autolabel(rects2)
    plt.tight_layout()
    plt.savefig("results/plots/seen_vs_unseen_robustness.png", dpi=300)
    plt.close()
    
    # ----------------------------------------------------
    # Plot 5: Failure distribution
    # ----------------------------------------------------
    # For holdout attacks at T=0.92: all 30 were successfully defended (0 jailbreaks, 0 false positives).
    # We will show the session outcome distribution by category.
    categories_clean = [c.replace('_', ' ').title() for c in categories_attacks]
    blocked_counts = [blocked_by_cat[c] for c in categories_attacks]
    leaked_counts = [leaked_by_cat[c] for c in categories_attacks]
    
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(categories_clean, blocked_counts, label='Successfully Defended (Blocked)', color='#4CAF50')
    ax.bar(categories_clean, leaked_counts, bottom=blocked_counts, label='Failed (Jailbroken)', color='#E53935')
    
    ax.set_ylabel('Number of Session Outcomes')
    ax.set_title('Robustness Failure/Success Distribution by Attack Category (T=0.92)', fontsize=11, fontweight='bold', pad=10)
    ax.set_xticklabels(categories_clean, rotation=15, ha='right')
    ax.legend(frameon=True)
    ax.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()
    plt.savefig("results/plots/failure_distribution.png", dpi=300)
    plt.close()
    
    # ----------------------------------------------------
    # Plot 6: Latency comparison across phases
    # ----------------------------------------------------
    phases = ['Phase 1\nBaseline', 'Phase 2\nSemantic', 'Phase 3\nHybrid', 'Phase 4\nMemory', 'Phase 5\nHoldout']
    latencies_sec = [45.54, 29.87, 25.08, 20.37, 156.48]
    
    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(phases, latencies_sec, color=['#B0BEC5', '#90CAF9', '#64B5F6', '#1E88E5', '#D32F2F'], width=0.55)
    plt.ylabel('Average Turn Latency (seconds)')
    plt.title('Performance: Latency Comparison across Evolution Phases', fontsize=11, fontweight='bold', pad=10)
    plt.ylim(0, 180)
    plt.grid(True, linestyle='--', alpha=0.4, axis='y')
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 3, f'{yval:.2f}s', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
    plt.tight_layout()
    plt.savefig("results/plots/latency_comparison_across_phases.png", dpi=300)
    plt.close()
    
    # ----------------------------------------------------
    # Plot 7: Detection robustness distribution
    # ----------------------------------------------------
    # Average detection turn by category
    avg_det_turn_by_cat = []
    for c in categories_attacks:
        turns_list = det_turns_by_cat[c]
        avg_det_turn_by_cat.append(np.mean(turns_list) if turns_list else 0.0)
        
    plt.figure(figsize=(8, 4))
    bars = plt.bar(categories_clean, avg_det_turn_by_cat, color='#26C6DA', width=0.55)
    plt.ylabel('Average Detection Turn')
    plt.title('Detection Robustness: Average Interception Turn by Attack Category', fontsize=11, fontweight='bold', pad=10)
    plt.ylim(0, 6)
    plt.xticks(rotation=15, ha='right')
    plt.grid(True, linestyle='--', alpha=0.4, axis='y')
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.1, f'{yval:.2f}', ha='center', va='bottom', fontsize=9)
        
    plt.tight_layout()
    plt.savefig("results/plots/detection_robustness_distribution.png", dpi=300)
    plt.close()
    
    # ----------------------------------------------------
    # Plot 8: Bypass interception distribution
    # ----------------------------------------------------
    bypass_counts = [bypass_int_by_cat[c] for c in categories_attacks]
    
    plt.figure(figsize=(8, 4))
    bars = plt.bar(categories_clean, bypass_counts, color='#FF7043', width=0.55)
    plt.ylabel('Total Intercepted Bypass Actions')
    plt.title('Bypass Protection: Intercepted Evasion Turns by Category (T=0.92)', fontsize=11, fontweight='bold', pad=10)
    plt.ylim(0, max(bypass_counts) + 3 if bypass_counts else 10)
    plt.xticks(rotation=15, ha='right')
    plt.grid(True, linestyle='--', alpha=0.4, axis='y')
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.3, f'{int(yval)}', ha='center', va='bottom', fontweight='bold', fontsize=9)
        
    plt.tight_layout()
    plt.savefig("results/plots/bypass_interception_distribution.png", dpi=300)
    plt.close()
    
    print("Successfully generated all 8 Phase 5 plots under results/plots/")

if __name__ == "__main__":
    main()
