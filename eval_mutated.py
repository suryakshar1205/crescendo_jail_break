import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
from src.crs.pipeline import CrescendoPRDPipeline

pipeline = CrescendoPRDPipeline()
with open('data/attacks/mutated_crescendo_variants.json', 'r', encoding='utf-8') as f:
    variants = json.load(f)

detected = 0
for v in variants:
    vid = v['variant_id']
    sid = f"run_{vid}"
    pipeline.reset_session(sid)
    flagged = False
    for p in v['turns']:
        res = pipeline.process_turn(sid, p)
        if res['is_mitigated']:
            flagged = True
            break
    if flagged:
        detected += 1

print(f"Mutated Variants Detected: {detected}/{len(variants)} ({(detected/len(variants))*100:.2f}%)")
