"""Reversible gateway stop/resume for the cached revision; no permanent deletion."""
import argparse,boto3
P='business-decision-lab-20261006';R='us-east-1';INSTANCE='i-0749d305b0448c253'
a=argparse.ArgumentParser();g=a.add_mutually_exclusive_group(required=True);g.add_argument('--disable',action='store_true');g.add_argument('--resume',action='store_true');args=a.parse_args()
e=boto3.client('ec2',region_name=R);l=boto3.client('lambda',region_name=R)
instance=e.describe_instances(InstanceIds=[INSTANCE])['Reservations'][0]['Instances'][0]
assert any(t['Key']=='Project' and t['Value']==P for t in instance['Tags'])
l.put_function_concurrency(FunctionName=P+'-model',ReservedConcurrentExecutions=0)
if args.disable:
 l.put_function_concurrency(FunctionName=P+'-gateway',ReservedConcurrentExecutions=0)
 if instance['State']['Name']=='running':e.stop_instances(InstanceIds=[INSTANCE])
 print('Gateway disabled; Qwen host stopped. EBS/ECR storage charges remain.')
else:
 l.put_function_concurrency(FunctionName=P+'-gateway',ReservedConcurrentExecutions=20)
 print('Cached gateway resumed; Qwen host stays stopped. Numeric tools/preset recordings are independent.')
