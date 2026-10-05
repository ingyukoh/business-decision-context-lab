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

Four actual CPU generations used frozen Qwen/Qwen2.5-0.5B-Instruct,
494,032,768 parameters, greedy decoding, no fine-tuning here.
The first two predefined test rows each ran with and without semantic context.
One contextual output said "6.64 million units" instead of thousands: it fails
validation and the displayed result falls back to exact numeric facts.
The other contextual output passed narrow number/unit/caveat checks.
Neither output without context passed. Two examples per condition do not
establish general improvement. Raw outputs, prompts and 4.42–12.12 second local
generation times remain in results/report.json. A validator revision accepted
"thousand units" as synonymous; no generation was changed or retried.

Passing checks is not complete semantic certification. Every response requires
human review. Training bounds are marginal only; they do not establish joint
support. No Claude/GPT runtime, Databricks deployment, client data, production
users or commercial impact is established by this lab.

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

The dedicated AWS deployment uses a public HTTPS Lambda Function URL, a small
numeric gateway, and a preloaded CPU model container on an isolated EC2 host. The browser page
supports three examples and bounded custom numeric scenarios, actual Qwen
generation, raw output inspection, semantic relationships, checks and fallback.
It is a fixed read-only workflow; the standalone MCP server is a separate stdio
integration, not an autonomous HTTP agent. Run `python test_mcp_live.py` to inspect
the actual MCP protocol connection and calls.

The model base revision is pinned to
7ae557604adf67be50417f59c2c2f167def9a775. No adapter is used here.
Runtime parameter count and process peak memory are measured in the model
service. Browser round-trip timing is distinct from model compute timing.
There is no calibrated confidence or commercial ROI claim.

Deployment, scoped permissions, quota, costs and cleanup:
[deploy/README.txt](deploy/README.txt). The public page serves external
JavaScript/CSS with a same-origin CSP and accepts no user text or arbitrary prompts.
The quota is 100 generation attempts per UTC day for all visitors together;
it is not a comprehensive account-wide spending limit.

Meaningful local checks now include gateway input/origin/payload validation,
quota fallback, model-unavailable responses, cold/warm cache behavior and retention
of failed raw generations. Mocked model tests do not constitute AWS inference;
live measurements are recorded separately after deployment.
