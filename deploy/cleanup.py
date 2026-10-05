"""Explicit cleanup for only the isolated Oct 6 business demo.
Disable access without deleting evidence: python cleanup.py --disable
Delete deployment resources: python cleanup.py --delete
Local/GitHub project and evaluation artifacts remain intact.
"""
import argparse,boto3
P='business-decision-lab-20261006';R='us-east-1'
a=argparse.ArgumentParser();a.add_argument('--disable',action='store_true');a.add_argument('--delete',action='store_true');args=a.parse_args()
if args.disable==args.delete:a.error('Choose exactly --disable or --delete')
l=boto3.client('lambda',region_name=R)
for n in [P+'-gateway',P+'-model']:
    if args.disable:l.put_function_concurrency(FunctionName=n,ReservedConcurrentExecutions=0)
    else:l.delete_function(FunctionName=n)
if args.delete:
    # Only this project's registry, daily counters and runtime roles. Keep log groups.
    boto3.client('ecr',region_name=R).delete_repository(repositoryName=P,force=True)
    boto3.client('dynamodb',region_name=R).delete_table(TableName=P+'-quota')
    i=boto3.client('iam')
    for n in [P+'-gateway-role',P+'-model-role']:
        i.delete_role_policy(RoleName=n,PolicyName='scoped-demo-runtime');i.delete_role(RoleName=n)
print('Business demo disabled' if args.disable else 'Business deployment resources deleted; 7-day logs preserved')
