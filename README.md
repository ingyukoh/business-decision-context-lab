# Business Decision Context Lab

Independent portfolio work, 6 October 2026, created with AI assistance.
Reuses frozen regression developed on 4 October; adds a typed semantic layer,
actual local LLM generation, output checks, human-review fallback and FastAPI.
This is recent implementation evidence, not a prior enterprise deployment.

## Why combine ML and an LLM?

OLS computes a numerical sales prediction from structured advertising inputs.
The LLM summarizes the result for a reviewer; it cannot change the prediction or
execute external actions. SQLite typed relationships connect the metric to units,
model, dataset provenance and limitations. Recursive traversal supplies context.
This is a small hand-defined semantic layer, not an enterprise ontology.

## Actual results

Public ISL Advertising data: 200 cross-sectional observations. SHA256 and disjoint
120/40/40 train/validation/test row IDs are in data/manifest.json.
OLS test RMSE is 1.9761, versus 5.8287 for the training-mean baseline
on 40 test rows, in thousands of units. This is not time-series or causal ROI.

Revision 2 fixes a failed review boundary: the retired keyword validator accepted
15 crafted harmful instructions that contained the expected number, unit and a
caveat keyword. The new policy rejects arbitrary prose for the main display.
Numbers, units and narrative come from code; raw model output stays untrusted.
Structured metadata must match an exact seven-field schema and trusted tools.

The fixed adversarial suite rejects all 30 invalid/malicious probes and accepts
all ten valid controls. This measures the closed display policy, not general
model safety. Twenty actual AWS Qwen generations across ten held-out rows are
reported separately in results/remediation-report.json. The original four local
generations and old check results remain in results/report.json as history.
Claude on Bedrock is prepared but account activation is pending; there are zero
measured Claude cases and no model comparison claim.

The dataset is cross-sectional and training ranges are marginal. A real client
forecast needs temporal validation and its own accepted business metric.

## Reproduce and serve

Use Python 3.11 in a virtual environment. Install requirements.txt, then run:

    python reproduce_regression.py
    pytest -q
    uvicorn api:app --host 127.0.0.1 --port 8520

Open http://127.0.0.1:8520/ or /docs. POST /predict accepts exactly TV,
radio and newspaper as finite nonnegative numbers. /recorded-examples explicitly
returns recorded LLM generations, not fresh inference.

To reproduce actual LLM generation, download the official Hugging Face
Qwen/Qwen2.5-0.5B-Instruct base checkpoint into a local model directory, then:

    python evaluate.py --model-path ./model

Weights are not redistributed here. Apache 2.0 checkpoint license and model card:
https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct
Dataset origin: https://www.statlearning.com/s/Advertising.csv
The training-mean and OLS metrics can be reproduced without model weights.

## Five-minute walkthrough

1. Inspect the source, row split and regression reproduction.
2. Predict sales for TV=80.2, radio=0, newspaper=9.2.
3. Traverse sales → OLS → Advertising; inspect units and source.
4. Inspect recorded wrong-unit generation and flagged fallback.
5. Show rejection of unknown schema, negative inputs and unknown metrics.

## Client implementation proposal

Agree on a real business target and acceptance criteria with stakeholders;
connect approved Databricks tables through read-only tools; fit a temporal
baseline; define metric/unit/ownership semantics; evaluate frontier-model
summaries and tool trajectories on held-out business cases; deliver prediction
API, source-linked explanations, review gates and reproducible evaluation.
Databricks-specific prior implementation: none established in inspected record.

## AWS live demonstration

Public, no access code: https://gvk2rzatfezmfj5rk6givmxgue0vsrto.lambda-url.us-east-1.on.aws/


The gateway serves three cached actual Qwen examples, including a deliberately
wrong-unit fallback case. Cached recordings bypass model quotas and busy states.
Custom inputs get fresh numeric predictions and code-composed summaries; the
idle Qwen EC2 host is stopped. Claude structured generation awaits AWS account
activation, scoped access and a managed-runtime network path.

This uses a small typed graph and fixed read-only orchestration. The separate
MCP server has two genuine stdio tools (`python test_mcp_live.py`). An autonomous
agent loop and enterprise Databricks integration remain implementation gaps.
Qwen base revision: 7ae557604adf67be50417f59c2c2f167def9a775; frozen, no adapter.
Cached compute times are historical; current browser timings measure retrieval.

Deploy/stop/resume and cost controls: [deploy/README.txt](deploy/README.txt).
Run `python evaluate_adversarial.py`, `python build_preset_cache.py`, and tests
before `python deploy/remediate.py` in the existing authenticated AWS account.
The remediation preserves the public URL, stops only this model host and avoids
accepting any new model-provider agreement. Retained EBS/ECR storage is estimated
at about $1.75/month plus request/log use, compared with about $60/month running.
Live provider calls, once enabled, use a five/day source-network quota and
100/day global fuse; presets and numeric tools remain independent. App logs
exclude inputs/model text. A 1 KiB request-body limit applies after AWS receives
an upload, rather than controlling client upload time.
