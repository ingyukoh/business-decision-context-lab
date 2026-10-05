"""Managed image build avoids CloudShell's 16 GB nested-Docker disk limit."""
import boto3,json,time,pathlib
from botocore.exceptions import ClientError
R='us-east-1';P='business-decision-lab-20261006';A=boto3.client('sts').get_caller_identity()['Account']
i=boto3.client('iam');c=boto3.client('codebuild',region_name=R);logs=boto3.client('logs',region_name=R)
role=P+'-build-role';group='/aws/codebuild/'+P
try:arn=i.get_role(RoleName=role)['Role']['Arn']
except i.exceptions.NoSuchEntityException:
    arn=i.create_role(RoleName=role,AssumeRolePolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'codebuild.amazonaws.com'},'Action':'sts:AssumeRole'}]}),Tags=[{'Key':'Project','Value':P}])['Role']['Arn']
policy={'Version':'2012-10-17','Statement':[
 {'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],'Resource':f'arn:aws:logs:{R}:{A}:log-group:{group}:*'},
 {'Effect':'Allow','Action':'ecr:GetAuthorizationToken','Resource':'*'},
 {'Effect':'Allow','Action':['ecr:BatchCheckLayerAvailability','ecr:InitiateLayerUpload','ecr:UploadLayerPart','ecr:CompleteLayerUpload','ecr:PutImage','ecr:BatchGetImage','ecr:GetDownloadUrlForLayer'],'Resource':f'arn:aws:ecr:{R}:{A}:repository/{P}'}]}
i.put_role_policy(RoleName=role,PolicyName='build-only-scoped-ecr',PolicyDocument=json.dumps(policy))
try:logs.create_log_group(logGroupName=group,tags={'Project':P})
except logs.exceptions.ResourceAlreadyExistsException:pass
logs.put_retention_policy(logGroupName=group,retentionInDays=7)
uri=f'{A}.dkr.ecr.{R}.amazonaws.com/{P}:20261006';registry=f'{A}.dkr.ecr.{R}.amazonaws.com'
spec={'version':0.2,'phases':{'build':{'commands':[
 'git clone --depth 1 https://github.com/ingyukoh/business-decision-context-lab.git source',
 'cd source',f'aws ecr get-login-password --region {R} | docker login --username AWS --password-stdin {registry}',
 f'docker build --platform linux/amd64 -f deploy/Dockerfile -t {uri} .',f'docker push {uri}',
 'git rev-parse HEAD']}}}
args=dict(name=P,source={'type':'NO_SOURCE','buildspec':json.dumps(spec)},artifacts={'type':'NO_ARTIFACTS'},environment={'type':'LINUX_CONTAINER','image':'aws/codebuild/standard:7.0','computeType':'BUILD_GENERAL1_SMALL','privilegedMode':True},serviceRole=arn,timeoutInMinutes=20,queuedTimeoutInMinutes=15,logsConfig={'cloudWatchLogs':{'status':'ENABLED','groupName':group}},tags=[{'key':'Project','value':P}])
if c.batch_get_projects(names=[P])['projects']:
    args.pop('tags');c.update_project(**args)
else:c.create_project(**args)
time.sleep(10)
b=c.start_build(projectName=P)['build'];bid=b['id'];print('BUILD_STARTED '+bid,flush=True)
last=None
while True:
    b=c.batch_get_builds(ids=[bid])['builds'][0]
    if b['currentPhase']!=last: print(b['currentPhase']+' '+b['buildStatus'],flush=True);last=b['currentPhase']
    if b['buildComplete']:
        print('BUILD_FINAL '+json.dumps({'id':bid,'status':b['buildStatus'],'image':uri,'logs':b.get('logs',{})}),flush=True)
        if b['buildStatus']!='SUCCEEDED':
            print(json.dumps(b.get('phases',[])),flush=True);raise RuntimeError('Managed image build failed')
        break
    time.sleep(15)
