AWS REPRODUCTION — Business Decision Context Lab, review revision 2
6 October 2026

PUBLIC URL (unchanged)
https://gvk2rzatfezmfj5rk6givmxgue0vsrto.lambda-url.us-east-1.on.aws/

Current architecture
AWS HTTPS Function URL → Lambda gateway → frozen numeric tools/typed graph,
immutable actual Qwen recordings, and a closed display contract. The same
private VPC/DynamoDB gateway endpoint is retained. The dedicated Qwen EC2 host
is stopped; the legacy model Lambda has reserved concurrency zero. There are
no public model-server ports. Presets bypass generation quotas and model health.
Custom numeric predictions and code-composed summaries remain available.
Claude provider code is prepared, but account agreement is NOT_AVAILABLE;
no Claude runtime result is claimed. Enabling it requires AWS account access,
scoped Bedrock InvokeModel permission, and a managed-runtime network path.

Reproduce locally
python -m pytest -q
python evaluate_adversarial.py
python build_preset_cache.py
python reproduce_regression.py
python test_mcp_live.py

The adversarial suite contains 30 invalid/malicious output probes plus ten valid
structured controls. The separate 20-case Qwen report contains actual AWS
free-text generations with/without context across ten held-out rows. This is
not a matched Claude comparison. Legacy reports are retained and labeled history.
Model: Qwen/Qwen2.5-0.5B-Instruct, 494,032,768 frozen parameters, revision
7ae557604adf67be50417f59c2c2f167def9a775; no fine-tuning/adapter here.

Deployment update (existing account/deployment, authenticated CloudShell)
git clone https://github.com/ingyukoh/business-decision-context-lab.git /tmp/business-decision-lab
cd /tmp/business-decision-lab
python3 deploy/remediate.py
This verifies the exact project tag, preserves the existing URL/VPC, updates
assets/configuration, sets gateway concurrency to 20, and stops ONLY the named
Qwen instance. No subscription or account terms are accepted by the script.
For subsequent asset-only changes: python3 deploy/update_gateway.py
Do not rerun the original aws_deploy.py/ec2_deploy.py: they describe legacy
infrastructure and would restore the costly live CPU path.

Review boundary
Models supply only seven enumerated metadata fields in the prepared structured
path. Exact keys, enums, duplicates, trailing text and consistency with trusted
tool results are checked. Numbers, units and all displayed narrative are supplied
by code. Unstructured Qwen prose is always kept as an untrusted diagnostic.
The pass label covers schema/evidence consistency, not general factuality.
A public prediction still needs human applicability review and client validation.

Operational controls
Exact numeric inputs, 1 KiB JSON body, finite values 0–1000, same-origin POST,
strict CSP and safe DOM text rendering. Body size is checked after AWS upload
buffering: handler timing excludes the time taken to upload the request.
Live generation (when enabled) is limited to 5 attempts/day per source-IP daily
HMAC and a 100/day global fuse; hashed counters expire after two days. Shared
networks share a limit; distributed callers can exhaust the global fuse. Cached
examples remain available. Raw IPs, inputs and model text are excluded from logs.
Each response logs an allowlisted route, status, duration and request ID. Gateway
CloudWatch logs expire after seven days. Gateway concurrency 20 reduces collisions
for cached requests; AWS throttling can still occur, and the UI handles it clearly.

Optional Claude activation and matched evaluation
Enable the Anthropic model in AWS Bedrock after reviewing required terms/use-case.
Candidate: anthropic.claude-haiku-4-5-20251001-v1:0 (US profile may be required).
Use deploy/bedrock_provider.py with Bedrock Converse outputConfig.textFormat;
strict JSON schema plus independent application validation, maxTokens 220.
Initial schema compilation may take minutes; compile privately before enabling
public access. Restrict IAM to the selected model/profile and log token counts,
not prompt text. Provide Bedrock egress by moving this stateless public gateway
out of its now-unused model VPC; the stopped EC2 security groups remain intact.
Do this only as an explicitly reviewed deployment change, then record actual
same-prompt Qwen/Claude trials and latency before describing a comparison.
The provider unit test uses a stub and is not a Claude inference measurement.

Costs
The stopped EC2 instance incurs no instance-compute charge. Its 20 GiB gp3 disk
is approximately $1.60/month, and retained ECR image storage about $0.15/month;
rough retained storage estimate $1.75/month plus Lambda/DynamoDB/log/request use.
Previously the running t3a.large plus IPv4/storage was approximately $60/month.
AWS catalog estimates exclude credits/taxes and are not observed billing or an
account-wide cap. Managed Claude token charges depend on the eventual model.
Official pricing: https://aws.amazon.com/ec2/pricing/on-demand/
https://aws.amazon.com/ebs/pricing/ https://aws.amazon.com/ecr/pricing/
https://aws.amazon.com/lambda/pricing/ https://aws.amazon.com/bedrock/pricing/

Reversible cleanup/resumption
python3 deploy/cleanup.py --disable
Disables this gateway and keeps the Qwen host stopped. Storage remains billable.
python3 deploy/cleanup.py --resume
Resumes the cached gateway at concurrency 20, keeping the Qwen host stopped.
Direct host stop:
aws ec2 stop-instances --region us-east-1 --instance-ids i-0749d305b0448c253
No permanent deletion or other project's resources are touched.
