"""Recent independent ML + semantic-context + local LLM work sample."""
import csv
import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
FEATURES = ('TV', 'radio', 'newspaper')
SOURCE = 'https://www.statlearning.com/s/Advertising.csv'
TRIPLES = [
    ('sales', 'unit', 'thousands of units'),
    ('sales', 'source', SOURCE),
    ('sales', 'predicted_by', 'ols'),
    ('ols', 'trained_on', 'advertising'),
    ('ols', 'limitation', 'Association only; no causal ROI or optimal budget established.'),
    ('advertising', 'structure', 'Cross-sectional observations; not time-series forecasting.'),
    ('advertising', 'source', SOURCE),
    ('TV', 'unit', 'thousands of dollars'),
    ('radio', 'unit', 'thousands of dollars'),
    ('newspaper', 'unit', 'thousands of dollars'),
]


def context(metric='sales'):
    """Traverse a small typed relationship layer; not a learned graph model."""
    db = sqlite3.connect(':memory:')
    db.execute('CREATE TABLE edges(subject TEXT, relation TEXT, object TEXT)')
    db.executemany('INSERT INTO edges VALUES(?,?,?)', TRIPLES)
    rows = db.execute('''WITH RECURSIVE nodes(n) AS (
        SELECT ? UNION SELECT object FROM edges JOIN nodes ON subject=nodes.n
        WHERE relation IN ('predicted_by','trained_on'))
        SELECT subject,relation,object FROM edges WHERE subject IN (SELECT n FROM nodes)
        ORDER BY subject,relation,object''', (metric,)).fetchall()
    db.close()
    if not rows:
        raise ValueError('Unknown metric; do not infer a definition')
    return [dict(zip(('subject', 'relation', 'object'), row)) for row in rows]


def load_rows():
    p = ROOT / 'data/Advertising.csv'
    manifest = json.loads((ROOT / 'data/manifest.json').read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest() == manifest['sha256']
    with p.open() as f:
        return {int(r['']): {k: float(r[k]) for k in (*FEATURES, 'sales')}
                for r in csv.DictReader(f)}


def predict(inputs):
    if set(inputs) != set(FEATURES):
        raise ValueError('Exact TV/radio/newspaper schema required')
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) or v < 0 for v in inputs.values()):
        raise ValueError('Finite nonnegative numeric inputs required')
    with (ROOT / 'data/ols_coefficients.csv').open() as f:
        beta = {r['term']: float(r['estimate']) for r in csv.DictReader(f)}
    rows = load_rows()
    manifest = json.loads((ROOT / 'data/manifest.json').read_text())
    train = [rows[i] for i in manifest['train_ids']]
    support = all(min(r[k] for r in train) <= inputs[k] <= max(r[k] for r in train)
                  for k in FEATURES)
    return {'prediction': beta['intercept'] + sum(beta[k] * inputs[k] for k in FEATURES),
            'metric': 'sales', 'unit': 'thousands of units',
            'within_marginal_training_bounds': support,
            'review_required': True,
            'limitation': 'Marginal ranges are not joint support or causal evidence.'}


def prompt_for(inputs, include_context=True):
    result = predict(inputs)
    facts = {'inputs': inputs, 'prediction': round(result['prediction'], 2)}
    if include_context:
        facts['semantic_context'] = context()
    prompt = ('Write two sentences for a business reviewer using only these facts. '
              'Include the exact prediction number. Do not recommend spending or claim causation. '
              'When definitions or units are absent, say they are unavailable. '
              'Describe any stated limitations. Facts: ' + json.dumps(facts))
    return prompt, result


def validate_summary(text, result):
    # Narrow deterministic checks; passing is not proof of complete factuality.
    failures = []
    if f"{result['prediction']:.2f}" not in text:
        failures.append('prediction_number_missing')
    number = re.escape(f"{result['prediction']:.2f}")
    if not re.search(r'(?<![\d.])' + number + r'\s+(?:thousand units|thousands of units)\b', text.lower()):
        failures.append('sales_unit_missing')
    if not any(s in text.lower() for s in ('association', 'associational', 'causal', 'causation')):
        failures.append('association_limitation_missing')
    return {'checks_passed': not failures, 'failures': failures, 'human_review_required': True,
            'scope': 'Exact-number, unit, and caveat presence only; not semantic certification.'}


def reviewed_output(raw, result):
    checks = validate_summary(raw, result)
    fallback = (f"Predicted sales: {result['prediction']:.2f} thousands of units. "
                "Association only; no causal ROI or optimal budget established.")
    return {'raw_model_output': raw, 'checks': checks,
            'displayed_summary': raw if checks['checks_passed'] else fallback,
            'fallback_used': not checks['checks_passed'], 'human_review_required': True}


class LocalLLM:
    def __init__(self, path):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        torch.set_num_threads(4)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True,
                                                        torch_dtype=torch.float32)
        self.model.eval()

    def generate(self, prompt):
        messages = [{'role': 'system', 'content': 'Summarize evidence faithfully. Never perform external actions.'},
                    {'role': 'user', 'content': prompt}]
        s = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        x = self.tokenizer(s, return_tensors='pt')
        with self.torch.inference_mode():
            y = self.model.generate(**x, do_sample=False, max_new_tokens=110,
                                    pad_token_id=self.tokenizer.eos_token_id)
        return self.tokenizer.decode(y[0, x['input_ids'].shape[1]:], skip_special_tokens=True)
