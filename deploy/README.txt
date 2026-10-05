AWS REPRODUCTION — Business Decision Context Lab
6 October 2026

Public demo:
https://gvk2rzatfezmfj5rk6givmxgue0vsrto.lambda-url.us-east-1.on.aws/

Architecture
Public AWS-managed HTTPS Lambda Function URL → bounded Python gateway →
private HTTP RPC restricted by security groups → preloaded FastAPI model container
on a dedicated t3a.large (8 GiB) in a new isolated VPC. No peering, public model
ingress or SSH. TLS terminates at AWS Lambda; the isolated private RPC uses HTTP.
This is a single-host demonstration, not a highly available production service.
Numeric predictions and semantic context use frozen OLS and SQLite typed triples.
Model: Qwen/Qwen2.5-0.5B-Instruct revision
7ae557604adf67be50417f59c2c2f167def9a775, 494,032,768 parameters.
Frozen causal LM; no fine-tuning or legal adapter in this project.
CPU torch 2.14.1 / Transformers 4.57.6 / Python 3.12; greedy 110-token cap.
The original private model Lambda cold-load attempts timed out at 100 and 180
seconds. Their failure history is retained. Its concurrency is now zero.

Reproduce in authenticated us-east-1 CloudShell
  git clone https://github.com/ingyukoh/business-decision-context-lab.git /tmp/business-decision-lab
  cd /tmp/business-decision-lab
  python3 -u deploy/aws_deploy.py
  python3 -u deploy/ec2_deploy.py
The first script creates registry, gateway, quota table and the initial private model.
The second creates the preloaded EC2 backend and reconnects the SAME Function URL.
Initial image construction needs several GB free disk. If CloudShell is too small,
use deploy/codebuild_image.py with its generated CodeBuild project instead, then
SKIP_BUILD=1 python3 deploy/aws_deploy.py. CodeBuild was not used in this deployment.
The EC2 wrapper pins the exact existing registry image digest. For another account
or a rebuilt image, change ec2_deploy.py's digest to the ECR output for that build.
Infrastructure state stays in ignored results/aws-ec2-state.json. Preserve that file.
A resumed ec2_deploy.py reuses the saved EC2 and VPC. Do not remove state and rerun
against an existing deployment. IAM propagation/network attachment may take minutes.

Controls
JSON-only 1024-byte body; exact numeric schema; finite nonnegative channel values
up to 1000; no arbitrary prompts, uploads, or business write actions.
Same-origin POST and Content Security Policy. No cross-origin CORS grants.
Atomic global quota of 100 generation attempts per UTC day, TTL 3 days.
Gateway reserved concurrency 2; model admits one generation, bounded token budget.
A failed/busy model yields a flagged numeric fallback; /health and /api/model-health
separate gateway availability from model readiness.
The container has 6 GiB memory limit, 2 CPUs, readonly root, tmpfs, rotated logs,
and restarts unless stopped. No submitted values/prompts/outputs in application logs.
Gateway CloudWatch logs expire after 7 days; container logs rotate 10 MB × 3.
These are scoped prototype controls, not SOC 2 certification or enterprise history.
MCP stdio transport is separately runnable via mcp_tools.py; the web workflow is fixed.

Verification
  python -m pytest -q
  python reproduce_regression.py
  python test_mcp_live.py
Inspect results/aws-verification.json for actual live measurements and failed attempts.
GET /api/model-health must return ready before assessing generation.
POST /api/predict works independently. POST /api/analyze performs real generation.

Reversible cleanup / resumption (authenticated CloudShell)
  python deploy/cleanup.py --disable
Stops the EC2 instance and sets gateway/model concurrency to zero. EBS/ECR storage
charges remain. Original source/evaluations remain unchanged.
  python deploy/cleanup.py --resume
Starts the existing EC2 instance and restores gateway concurrency 2; wait for model
readiness. The replaced model Lambda stays disabled. This avoids a second instance.
For direct emergency stop of THIS deployment:
  aws ec2 stop-instances --region us-east-1 --instance-ids i-0749d305b0448c253
Permanent teardown needs Lambda deletion before removing their network interfaces,
followed by this project's EC2, endpoint, security groups, routes/VPC and roles.
No permanent deletion is performed by cleanup.py.

Costs (estimate, no free-tier or credits assumed)
t3a.large Linux on-demand approximately $0.0752/hour × 730 = $54.90/month.
One running public IPv4 approximately $0.005/hour × 730 = $3.65/month.
20 GiB gp3 approximately $1.60/month; ECR about $0.10/GB/month.
Rough idle running total $60/month, plus gateway/log/request use and possible
burstable CPU surplus credits. A daily inference cap is not an AWS account spend cap.
Stopped instance compute ends; EBS and ECR storage remain. Auto public IPv4 releases.
Catalog price is read by ec2_deploy.py and saved privately when available.
Official pricing: https://aws.amazon.com/ec2/pricing/on-demand/
https://aws.amazon.com/vpc/pricing/
https://aws.amazon.com/ebs/pricing/
https://aws.amazon.com/lambda/pricing/
https://aws.amazon.com/ecr/pricing/
