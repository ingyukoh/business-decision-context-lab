"""Reversible stop/start for this isolated demo. No permanent deletion."""
import argparse,json,pathlib,boto3
P='business-decision-lab-20261006';R='us-east-1'
a=argparse.ArgumentParser();g=a.add_mutually_exclusive_group(required=True);g.add_argument('--disable',action='store_true');g.add_argument('--resume',action='store_true');args=a.parse_args()
e=boto3.client('ec2',region_name=R);l=boto3.client('lambda',region_name=R)
s=json.loads((pathlib.Path(__file__).resolve().parents[1]/'results/aws-ec2-state.json').read_text())
assert s['project']==P
instance=e.describe_instances(InstanceIds=[s['instance_id']])['Reservations'][0]['Instances'][0]
assert any(t['Key']=='Project' and t['Value']==P for t in instance['Tags'])
if args.disable:
    for suffix in ['-gateway','-model']:l.put_function_concurrency(FunctionName=P+suffix,ReservedConcurrentExecutions=0)
    e.stop_instances(InstanceIds=[s['instance_id']]);print('Stopped demo compute. EBS/ECR storage charges remain.')
else:
    e.start_instances(InstanceIds=[s['instance_id']]);e.get_waiter('instance_running').wait(InstanceIds=[s['instance_id']])
    l.put_function_concurrency(FunctionName=P+'-gateway',ReservedConcurrentExecutions=2)
    print('Gateway resumed; wait for /api/model-health ready. Old model Lambda stays disabled.')
