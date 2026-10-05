AWS REPRODUCTION — Business Decision Context Lab
6 October 2026

Architecture
Public HTTPS Lambda Function URL → Python gateway → privately invoked model Lambda.
Prediction and semantic context use frozen OLS and SQLite typed relationships.
The model container includes the exact Qwen2.5-0.5B-Instruct base revision
7ae557604adf67be50417f59c2c2f167def9a775. No legal adapter is loaded.
Python 3.12, CPU torch 2.14.1, Transformers 4.57.6; greedy 110-token cap.
On-demand x86 model: 4096 MB, 100-second timeout, reserved concurrency 1.
Gateway: 256 MB, 110-second timeout, reserved concurrency 2.
No provisioned concurrency or always-on EC2 for this demo.

Reproduce
In authenticated AWS CloudShell (us-east-1) with Docker and sufficient temporary disk:
  git clone https://github.com/ingyukoh/business-decision-context-lab.git /tmp/business-decision-lab
  cd /tmp/business-decision-lab
  python3 -u deploy/aws_deploy.py
This creates isolated project-tagged ECR, Lambda, scoped IAM roles, log groups,
and a DynamoDB daily counter table. The model container has no model-function URL
and no business-data permissions. Its role can write only its own log stream.
The gateway can invoke only this model and update only the daily quota counter.
A generated URL and resource names are saved to results/aws-resource-state.json.
No credentials are embedded in the repository or exported from CloudShell.

Controls
JSON-only 1024-byte payload, exact numeric schema, channel values 0–1000,
no arbitrary user prompt or upload. Cross-origin browser POST rejected.
Same-origin script/style Content Security Policy; no cross-origin CORS grants.
Daily global 100 generation attempts (UTC), atomic counter with 3-day expiry;
no IP or user identity is stored. Prediction remains available after the LLM cap.
Only route/status/timing/request ID is logged by application code, with 7-day retention.
Model concurrency and token/time limits bound execution; gateway health is separate
from model readiness. These are prototype controls, not SOC 2 certification.

Verification
  python -m pytest -q
  python reproduce_regression.py
  python test_mcp_live.py
Use /health, /api/report, /api/examples, POST /api/predict and POST /api/analyze.
The separate MCP stdio server is mcp_tools.py; it is not the HTTP orchestration transport.
No autonomous tool choice or business write action is claimed by the web service.

Cleanup
Run in authenticated AWS CloudShell:
  python deploy/cleanup.py --disable
This reversibly sets both functions' concurrency to zero, preserving all artifacts.
For explicit permanent resource cleanup:
  python deploy/cleanup.py --delete
This removes only this demo's Lambda functions, ECR repository/images, quota table
and scoped IAM roles. It preserves the source, local evaluations and 7-day logs.
Restore a disabled deployment by rerunning deploy/aws_deploy.py.

Costs
No idle Lambda compute cost; ECR model storage continues to incur storage charges.
Estimate using actual measured Lambda billed duration, not browser latency.
x86 on-demand example at $0.0000166667/GB-second: 4 GB × 15 seconds × 1000
model invocations = about $1.00 before gateway duration, initialization, requests,
logs, ECR storage and free-tier eligibility. 100/day is a generation-attempt cap,
not a universal AWS spending cap; page/predict requests remain public.
Official sources checked 6 October 2026:
https://aws.amazon.com/lambda/pricing/
https://aws.amazon.com/ecr/pricing/
