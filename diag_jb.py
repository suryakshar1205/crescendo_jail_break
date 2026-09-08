import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.crs.pipeline import CrescendoPRDPipeline

pipeline = CrescendoPRDPipeline()
with open('data/attacks/converted_jailbreakbench.json', 'r', encoding='utf-8') as f:
    attacks = json.load(f)

for atk in attacks:
    aid = atk['attack_id']
    topic = atk['topic']
    session_id = f'diag_{aid}'
    pipeline.reset_session(session_id)
    print(f'=== {aid}: {topic} ===')
    for turn_idx, p in enumerate(atk['turns'], 1):
        res = pipeline.process_turn(session_id, p)
        print(f'  Turn {turn_idx}: CRS={res["crs"]:.4f}, H={res["H"]:.2f}, E={res["E"]:.2f}, S={res["S"]:.2f}, B={res["B"]:.2f}, C_t={res["contextual_risk"]:.4f}, Action={res["decision"]}')
