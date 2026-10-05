"""Isolated warm model host behind the SAME public Lambda URL.
No SSH ingress, no peering with existing projects, no domain purchase.
Run in authenticated CloudShell. On-demand t3a.large; stop to end instance compute charges.
"""
import boto3,json,time,pathlib,base64,io,zipfile,urllib.request
from botocore.exceptions import ClientError
R='us-east-1';P='business-decision-lab-20261006';ROOT=pathlib.Path(__file__).resolve().parents[1]
A=boto3.client('sts').get_caller_identity()['Account'];e=boto3.client('ec2',region_name=R);i=boto3.client('iam');ssm=boto3.client('ssm',region_name=R);l=boto3.client('lambda',region_name=R)
TAG=[{'Key':'Project','Value':P},{'Key':'Purpose','Value':'Independent public numeric demo'}]
def tag(x):e.create_tags(Resources=[x],Tags=TAG);return x
def role(name,statements):
    try:r=i.get_role(RoleName=name)['Role']
    except i.exceptions.NoSuchEntityException:r=i.create_role(RoleName=name,AssumeRolePolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'ec2.amazonaws.com'},'Action':'sts:AssumeRole'}]}),Tags=TAG)['Role']
    i.put_role_policy(RoleName=name,PolicyName='scoped-demo-host',PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':statements}))
    try:i.create_instance_profile(InstanceProfileName=name);i.add_role_to_instance_profile(InstanceProfileName=name,RoleName=name)
    except i.exceptions.EntityAlreadyExistsException:pass
    return name
statefile=ROOT/'results/aws-ec2-state.json'
if statefile.exists():
    state=json.loads(statefile.read_text());vid=state['vpc_id'];sub=state['subnet_id'];sgm=state['model_sg'];sgl=state['lambda_sg'];instance=state['instance_id'];rt=state['route_table_id'];igw=state['igw_id'];endpoint=state['ddb_endpoint']
else:
    vid=tag(e.create_vpc(CidrBlock='10.42.0.0/24')['Vpc']['VpcId']);e.modify_vpc_attribute(VpcId=vid,EnableDnsSupport={'Value':True});e.modify_vpc_attribute(VpcId=vid,EnableDnsHostnames={'Value':True})
    az=e.describe_availability_zones(Filters=[{'Name':'state','Values':['available']}])['AvailabilityZones'][0]['ZoneName']
    sub=tag(e.create_subnet(VpcId=vid,CidrBlock='10.42.0.0/26',AvailabilityZone=az)['Subnet']['SubnetId'])
    igw=tag(e.create_internet_gateway()['InternetGateway']['InternetGatewayId']);e.attach_internet_gateway(InternetGatewayId=igw,VpcId=vid)
    rt=tag(e.create_route_table(VpcId=vid)['RouteTable']['RouteTableId']);e.associate_route_table(RouteTableId=rt,SubnetId=sub);e.create_route(RouteTableId=rt,DestinationCidrBlock='0.0.0.0/0',GatewayId=igw)
    sgm=tag(e.create_security_group(GroupName=P+'-model',Description='Private model RPC from demo gateway only',VpcId=vid)['GroupId']);sgl=tag(e.create_security_group(GroupName=P+'-gateway',Description='Only model RPC and DynamoDB egress',VpcId=vid)['GroupId'])
    e.authorize_security_group_ingress(GroupId=sgm,IpPermissions=[{'IpProtocol':'tcp','FromPort':8080,'ToPort':8080,'UserIdGroupPairs':[{'GroupId':sgl}]}])
    for sg in [sgm,sgl]:e.revoke_security_group_egress(GroupId=sg,IpPermissions=[{'IpProtocol':'-1','IpRanges':[{'CidrIp':'0.0.0.0/0'}]}])
    e.authorize_security_group_egress(GroupId=sgm,IpPermissions=[{'IpProtocol':'tcp','FromPort':port,'ToPort':port,'IpRanges':[{'CidrIp':'0.0.0.0/0'}]} for port in (80,443)])
    prefix=e.describe_managed_prefix_lists(Filters=[{'Name':'prefix-list-name','Values':['com.amazonaws.us-east-1.dynamodb']}])['PrefixLists'][0]['PrefixListId']
    e.authorize_security_group_egress(GroupId=sgl,IpPermissions=[{'IpProtocol':'tcp','FromPort':8080,'ToPort':8080,'UserIdGroupPairs':[{'GroupId':sgm}]},{'IpProtocol':'tcp','FromPort':443,'ToPort':443,'PrefixListIds':[{'PrefixListId':prefix}]}])
    endpoint=e.create_vpc_endpoint(VpcId=vid,VpcEndpointType='Gateway',ServiceName='com.amazonaws.us-east-1.dynamodb',RouteTableIds=[rt],TagSpecifications=[{'ResourceType':'vpc-endpoint','Tags':TAG}])['VpcEndpoint']['VpcEndpointId']
    profile=role(P+'-host-role',[
        {'Effect':'Allow','Action':['ssm:UpdateInstanceInformation','ssm:ListInstanceAssociations'],'Resource':'*'},
        {'Effect':'Allow','Action':['ssmmessages:CreateControlChannel','ssmmessages:CreateDataChannel','ssmmessages:OpenControlChannel','ssmmessages:OpenDataChannel'],'Resource':'*'},
        {'Effect':'Allow','Action':['ec2messages:AcknowledgeMessage','ec2messages:DeleteMessage','ec2messages:FailMessage','ec2messages:GetEndpoint','ec2messages:GetMessages','ec2messages:SendReply'],'Resource':'*'},
        {'Effect':'Allow','Action':'ecr:GetAuthorizationToken','Resource':'*'},
        {'Effect':'Allow','Action':['ecr:BatchGetImage','ecr:GetDownloadUrlForLayer','ecr:BatchCheckLayerAvailability'],'Resource':f'arn:aws:ecr:{R}:{A}:repository/{P}'}])
    service=(ROOT/'deploy/ec2_service.py').read_bytes();digest='sha256:b53a42ef76434e431e1c7edb3ae44673c6de6bb64127d86a4485106f8a49031c'
    dockerfile=f'FROM {A}.dkr.ecr.{R}.amazonaws.com/{P}@{digest}\nRUN pip install --no-cache-dir fastapi==0.142.2 uvicorn==0.54.0\nCOPY service.py /var/task/service.py\nENTRYPOINT ["python3", "-m", "uvicorn"]\nCMD ["service:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--limit-concurrency", "16"]\n'
    user=f'''#!/bin/bash
set -eu
mkdir -p /opt/business-model
cd /opt/business-model
dnf install -y docker
systemctl enable --now docker
systemctl enable --now amazon-ssm-agent
printf '%s' '{base64.b64encode(service).decode()}' | base64 -d > service.py
printf '%s' '{base64.b64encode(dockerfile.encode()).decode()}' | base64 -d > Dockerfile
export DOCKER_CONFIG=/tmp/business-docker-auth
mkdir -m 700 -p "$DOCKER_CONFIG"
aws ecr get-login-password --region {R} | docker login --username AWS --password-stdin {A}.dkr.ecr.{R}.amazonaws.com
docker build -t business-decision-service:20261006 .
docker logout {A}.dkr.ecr.{R}.amazonaws.com
docker run -d --name business-decision-model --restart unless-stopped --memory 6g --cpus 2 --read-only --tmpfs /tmp:rw,size=256m --log-opt max-size=10m --log-opt max-file=3 -p 8080:8080 business-decision-service:20261006
'''
    ami=ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')['Parameter']['Value']
    time.sleep(15)
    ins=e.run_instances(ImageId=ami,InstanceType='t3a.large',MinCount=1,MaxCount=1,IamInstanceProfile={'Name':profile},MetadataOptions={'HttpTokens':'required','HttpPutResponseHopLimit':1},BlockDeviceMappings=[{'DeviceName':'/dev/xvda','Ebs':{'VolumeSize':20,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}],NetworkInterfaces=[{'DeviceIndex':0,'SubnetId':sub,'Groups':[sgm],'AssociatePublicIpAddress':True}],UserData=user,TagSpecifications=[{'ResourceType':'instance','Tags':TAG},{'ResourceType':'volume','Tags':TAG}])['Instances'][0]
    instance=ins['InstanceId'];state={'region':R,'project':P,'vpc_id':vid,'subnet_id':sub,'route_table_id':rt,'igw_id':igw,'model_sg':sgm,'lambda_sg':sgl,'ddb_endpoint':endpoint,'instance_id':instance,'instance_type':'t3a.large','instance_memory_gib':8,'container_limit_gib':6,'image_digest':digest}
    statefile.write_text(json.dumps(state,indent=2));print('MODEL_HOST_CREATED '+instance,flush=True)
e.get_waiter('instance_running').wait(InstanceIds=[instance]);ins=e.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0];ip=ins['PrivateIpAddress'];state['private_rpc']=f'http://{ip}:8080';statefile.write_text(json.dumps(state,indent=2))
# Lambda-service ENI access. Explicitly deny these EC2 actions to function code.
actions=['ec2:CreateNetworkInterface','ec2:DescribeNetworkInterfaces','ec2:DescribeSubnets','ec2:DeleteNetworkInterface','ec2:AssignPrivateIpAddresses','ec2:UnassignPrivateIpAddresses']
i.put_role_policy(RoleName=P+'-gateway-role',PolicyName='scoped-demo-runtime',PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],'Resource':f'arn:aws:logs:{R}:{A}:log-group:/aws/lambda/{P}-gateway:*'},{'Effect':'Allow','Action':'dynamodb:UpdateItem','Resource':f'arn:aws:dynamodb:{R}:{A}:table/{P}-quota'}]}))
i.put_role_policy(RoleName=P+'-gateway-role',PolicyName='isolated-vpc-service',PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':actions,'Resource':'*'},{'Effect':'Deny','Action':actions,'Resource':'*','Condition':{'ArnEquals':{'lambda:SourceFunctionArn':f'arn:aws:lambda:{R}:{A}:function:{P}-gateway'}}}]}))
b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
    for p in [ROOT/'lab.py',ROOT/'deploy/gateway.py']:z.write(p,p.name)
    for folder in ['docs','data','results']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.json','.csv','.html','.js','.css') and not p.name.endswith('state.json'):z.write(p,str(p.relative_to(ROOT)))
l.update_function_code(FunctionName=P+'-gateway',ZipFile=b.getvalue());l.get_waiter('function_updated_v2').wait(FunctionName=P+'-gateway')
l.update_function_configuration(FunctionName=P+'-gateway',Timeout=100,VpcConfig={'SubnetIds':[sub],'SecurityGroupIds':[sgl]},Environment={'Variables':{'MODEL_HTTP_URL':state['private_rpc'],'QUOTA_TABLE':P+'-quota'}});l.get_waiter('function_updated_v2').wait(FunctionName=P+'-gateway')
l.put_function_concurrency(FunctionName=P+'-model',ReservedConcurrentExecutions=0)
state['public_url']=l.get_function_url_config(FunctionName=P+'-gateway')['FunctionUrl'];statefile.write_text(json.dumps(state,indent=2))
print('GATEWAY_CONNECTED '+state['public_url'],flush=True)
# Public catalog price, not a billing commitment.
try:
    prices=boto3.client('pricing',region_name=R).get_products(ServiceCode='AmazonEC2',Filters=[{'Type':'TERM_MATCH','Field':k,'Value':v} for k,v in {'instanceType':'t3a.large','regionCode':R,'operatingSystem':'Linux','tenancy':'Shared','preInstalledSw':'NA','capacitystatus':'Used'}.items()])['PriceList']
    rates=[float(d['pricePerUnit']['USD']) for p in prices for t in json.loads(p)['terms']['OnDemand'].values() for d in t['priceDimensions'].values() if d['unit']=='Hrs']
    state['catalog_instance_usd_per_hour']=rates[0];statefile.write_text(json.dumps(state,indent=2));print('PRICE_PER_HOUR '+str(rates[0]),flush=True)
except Exception as exc:print('PRICE_LOOKUP_UNAVAILABLE '+type(exc).__name__,flush=True)
print('EC2_DEPLOYMENT_COMPLETE',flush=True)
