"""Update this deployment only; preserve URL/isolation, retire idle Qwen host.
Run from authenticated CloudShell after tests and recorded evaluations finish.
"""
import boto3,secrets,json,importlib.util
from pathlib import Path
P='business-decision-lab-20261006';R='us-east-1';INSTANCE='i-0749d305b0448c253'
l=boto3.client('lambda',region_name=R);e=boto3.client('ec2',region_name=R)
c=l.get_function_configuration(FunctionName=P+'-gateway')
assert c['FunctionName']==P+'-gateway'
ins=e.describe_instances(InstanceIds=[INSTANCE])['Reservations'][0]['Instances'][0]
assert any(t['Key']=='Project' and t['Value']==P for t in ins['Tags'])
env=c['Environment']['Variables'];env['QWEN_LIVE_ENABLED']='0';env.setdefault('QUOTA_HMAC_SALT',secrets.token_hex(32))
# No Bedrock permission or account terms are changed by this remediation.
l.update_function_configuration(FunctionName=P+'-gateway',Timeout=55,Environment={'Variables':env})
l.get_waiter('function_updated_v2').wait(FunctionName=P+'-gateway')
spec=importlib.util.spec_from_file_location('update_gateway',Path(__file__).with_name('update_gateway.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
l.put_function_concurrency(FunctionName=P+'-gateway',ReservedConcurrentExecutions=20)
l.put_function_concurrency(FunctionName=P+'-model',ReservedConcurrentExecutions=0)
e.stop_instances(InstanceIds=[INSTANCE])
print('UPDATED_PUBLIC_URL',l.get_function_url_config(FunctionName=P+'-gateway')['FunctionUrl'])
print('MODEL_INSTANCE_STOP_REQUESTED',INSTANCE)
print('Gateway isolation preserved; cached examples/numeric tools stay live. Claude account access pending.')
