import argparse
import json
import math
import time
from lab import ROOT, FEATURES, load_rows, predict, prompt_for, validate_summary, LocalLLM

p = argparse.ArgumentParser()
p.add_argument('--model-path', required=True)
a = p.parse_args()
rows = load_rows()
manifest = json.loads((ROOT / 'data/manifest.json').read_text())
train_mean = sum(rows[i]['sales'] for i in manifest['train_ids']) / len(manifest['train_ids'])
test = manifest['test_ids']
rmse = lambda values: math.sqrt(sum(v*v for v in values) / len(values))
report = {'created': '2026-10-06', 'dataset': manifest['source'], 'test_n': len(test),
          'baseline_rmse': rmse([train_mean-rows[i]['sales'] for i in test]),
          'ols_rmse': rmse([predict({k: rows[i][k] for k in FEATURES})['prediction']-rows[i]['sales'] for i in test]),
          'base_model': 'Qwen/Qwen2.5-0.5B-Instruct', 'fine_tuned_in_this_lab': False,
          'generation': 'Actual local CPU causal-LM generation; greedy decoding',
          'semantic_layer': 'SQLite typed triples with recursive source/metric/model traversal',
          'actions': 'Read-only analysis; human review before any external action', 'cases': []}
llm = LocalLLM(a.model_path)
report['parameter_count'] = sum(p.numel() for p in llm.model.parameters())
for row_id in test[:2]:
    inputs = {k: rows[row_id][k] for k in FEATURES}
    for has_context in [False, True]:
        prompt, result = prompt_for(inputs, has_context)
        t = time.perf_counter()
        text = llm.generate(prompt)
        case = {'row_id': row_id, 'context': has_context, 'prompt': prompt,
                'prediction': result, 'output': text, 'latency_seconds': time.perf_counter()-t,
                'checks': validate_summary(text, result)}
        report['cases'].append(case)
        print(json.dumps(case), flush=True)
report['context_check_passes'] = sum(c['checks']['checks_passed'] for c in report['cases'] if c['context'])
report['no_context_check_passes'] = sum(c['checks']['checks_passed'] for c in report['cases'] if not c['context'])
report['limits'] = ['Two examples per generation condition; no general quality or enterprise-scale conclusion.',
                   'Public textbook advertising data, not pet/garden customer data.',
                   'Frozen regression reused from 4 October lab; no causal ROI or time-series performance claimed.',
                   'Small hand-defined semantic layer, not Neo4j, GraphRAG, Databricks or enterprise ontology delivery.',
                   'No GPT/Claude runtime or production users established in this work sample.']
(ROOT / 'results/report.json').write_text(json.dumps(report, indent=2))
print('REPORT_SAVED', ROOT / 'results/report.json', flush=True)

