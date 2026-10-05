"""Recreate frozen OLS and assert it matches saved original-unit coefficients."""
import csv
import json
import numpy as np
from lab import ROOT, FEATURES, load_rows
rows = load_rows()
manifest = json.loads((ROOT / "data/manifest.json").read_text())
train = manifest["train_ids"]
assert not set(train) & set(manifest["validation_ids"])
assert not set(train) & set(manifest["test_ids"])
x = np.array([[1, *(rows[i][k] for k in FEATURES)] for i in train])
y = np.array([rows[i]["sales"] for i in train])
beta = np.linalg.lstsq(x, y, rcond=None)[0]
with (ROOT / "data/ols_coefficients.csv").open() as f:
    saved = {r["term"]: float(r["estimate"]) for r in csv.DictReader(f)}
assert np.allclose(beta, [saved[k] for k in ("intercept", *FEATURES)], atol=1e-10)
print("Frozen OLS reproduced from 120 training rows; no test data used.")
