"""Immutable actual generation recordings; never fabricate a missing model output."""
import json
from pathlib import Path
from deploy.gateway import cache_key
entries={}
x=json.loads(Path('results/aws-verification.json').read_text())
for c in x['inference']:
 p={'inputs':c['inputs'],'include_context':c['context']}
 entries[cache_key(p)]={**c['result'],'recorded_at':x['verified_at_utc'],'recording_source':'results/aws-verification.json'}
f=Path('results/qwen-20-case-2026-10-06.json')
if f.exists():
 for c in json.loads(f.read_text())['cases']:
  if c.get('response',{}).get('raw_model_output'):entries[cache_key(c['payload'])]={**c['response'],'recorded_at':'2026-10-06','recording_source':str(f)}
f=Path('results/qwen-out-of-range-2026-10-06.json')
if f.exists():
 for c in json.loads(f.read_text())['cases']:
  if c.get('response',{}).get('raw_model_output'):entries[cache_key(c['payload'])]={**c['response'],'recorded_at':'2026-10-06','recording_source':str(f)}
# Keep only actual raw/model/timing provenance; gateway re-computes display/review.
keep=('raw_model_output','model','parameters','model_revision','fine_tuned','compute_seconds','recorded_at','recording_source')
entries={k:{n:v for n,v in r.items() if n in keep} for k,r in entries.items()}
Path('results/preset-cache.json').write_text(json.dumps({'policy':'Immutable cached actual generation; gateway revalidates and recomputes display.','entries':entries},indent=2))
print('CACHED_RECORDINGS',len(entries))
