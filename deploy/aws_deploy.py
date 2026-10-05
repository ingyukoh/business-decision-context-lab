"""Run in authenticated AWS CloudShell. Creates isolated, tagged demo resources.
No access keys are exported. Logs exclude payloads. Default no idle compute cost.
"""
import boto3, json, time, subprocess, pathlib, base64, zipfile, io
from botocore.exceptions import ClientError
R='us-east-1'; NAME='business-decision-lab-20261006'; ROOT=pathlib.Path(__file__).resolve().parents[1]
ACCOUNT=boto3.client('sts').get_caller_identity()['Account']
ecr=boto3.client('ecr',region_name=R); iam=boto3.client('iam'); lam=boto3.client('lambda',region_name=R); logs=boto3.client('logs',region_name=R)
TAGS={'Project':NAME,'Purpose':'Independent public numeric work sample'}
def role(name,policy=None):
    try:r=iam.get_role(RoleName=name)['Role']
    except ClientError as e:
        if e.response['Error']['Code']!='NoSuchEntity':raise
        r=iam.create_role(RoleName=name,AssumeRolePolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'lambda.amazonaws.com'},'Action':'sts:AssumeRole'}]}),Tags=[{'Key':k,'Value':v} for k,v in TAGS.items()])['Role']
    statements=[{'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],'Resource':f'arn:aws:logs:{R}:{ACCOUNT}:log-group:/aws/lambda/{name.removesuffix("-role")}:*'}]
    if policy:statements.extend(policy)
    iam.put_role_policy(RoleName=name,PolicyName='scoped-demo-runtime',PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':statements}))
    return r['Arn']
modelname=NAME+'-model'; gatewayname=NAME+'-gateway'
for n in [modelname,gatewayname]:
    try:logs.create_log_group(logGroupName='/aws/lambda/'+n,tags=TAGS)
    except logs.exceptions.ResourceAlreadyExistsException:pass
    logs.put_retention_policy(logGroupName='/aws/lambda/'+n,retentionInDays=7)
quota=NAME+'-quota'; ddb=boto3.client('dynamodb',region_name=R)
try:
    ddb.create_table(TableName=quota,KeySchema=[{'AttributeName':'day','KeyType':'HASH'}],AttributeDefinitions=[{'AttributeName':'day','AttributeType':'S'}],BillingMode='PAY_PER_REQUEST',Tags=[{'Key':k,'Value':v} for k,v in TAGS.items()])
    ddb.get_waiter('table_exists').wait(TableName=quota)
    ddb.update_time_to_live(TableName=quota,TimeToLiveSpecification={'Enabled':True,'AttributeName':'expires_at'})
except ddb.exceptions.ResourceInUseException:pass
mr=role(modelname+'-role'); gr=role(gatewayname+'-role',[
    {'Effect':'Allow','Action':'lambda:InvokeFunction','Resource':f'arn:aws:lambda:{R}:{ACCOUNT}:function:{modelname}'},
    {'Effect':'Allow','Action':'dynamodb:UpdateItem','Resource':f'arn:aws:dynamodb:{R}:{ACCOUNT}:table/{quota}'}])
try:ecr.create_repository(repositoryName=NAME,imageScanningConfiguration={'scanOnPush':True},tags=[{'Key':k,'Value':v} for k,v in TAGS.items()])
except ecr.exceptions.RepositoryAlreadyExistsException:pass
registry=f'{ACCOUNT}.dkr.ecr.{R}.amazonaws.com'; uri=registry+'/'+NAME+':20261006'
auth=ecr.get_authorization_token()['authorizationData'][0]; user,password=base64.b64decode(auth['authorizationToken']).decode().split(':',1)
subprocess.run(['docker','login','--username',user,'--password-stdin',registry],input=password.encode(),check=True)
subprocess.run(['docker','build','--platform','linux/amd64','-f','deploy/Dockerfile','-t',uri,'.'],cwd=ROOT,check=True)
subprocess.run(['docker','push',uri],check=True)
print('IMAGE_PUSHED',flush=True)
def deploy(n,args):
    try:lam.get_function(FunctionName=n)
    except lam.exceptions.ResourceNotFoundException:
        for attempt in range(6):
            try:lam.create_function(FunctionName=n,Tags=TAGS,**args);break
            except lam.exceptions.InvalidParameterValueException:
                if attempt==5:raise
                time.sleep(10)
        lam.get_waiter('function_active_v2').wait(FunctionName=n)
    else:
        lam.update_function_code(FunctionName=n,**args['Code']);lam.get_waiter('function_updated_v2').wait(FunctionName=n)
        conf={k:v for k,v in args.items() if k not in ('Code','PackageType','Architectures')}
        lam.update_function_configuration(FunctionName=n,**conf);lam.get_waiter('function_updated_v2').wait(FunctionName=n)
    lam.put_function_concurrency(FunctionName=n,ReservedConcurrentExecutions=1 if n==modelname else 2)
deploy(modelname,dict(PackageType='Image',Code={'ImageUri':uri},Role=mr,MemorySize=4096,Timeout=100,Architectures=['x86_64'],EphemeralStorage={'Size':512}))
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
    for p in [ROOT/'lab.py',ROOT/'deploy/gateway.py']:
        z.write(p,p.name)
    for folder in ['data','results','docs']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.csv','.json','.html','.js','.css'): z.write(p,str(p.relative_to(ROOT)))
deploy(gatewayname,dict(PackageType='Zip',Code={'ZipFile':buf.getvalue()},Role=gr,Runtime='python3.12',Handler='gateway.handler',MemorySize=256,Timeout=110,Environment={'Variables':{'MODEL_FUNCTION':modelname,'QUOTA_TABLE':quota}}))
try:url=lam.create_function_url_config(FunctionName=gatewayname,AuthType='NONE',InvokeMode='BUFFERED')['FunctionUrl']
except lam.exceptions.ResourceConflictException:url=lam.get_function_url_config(FunctionName=gatewayname)['FunctionUrl']
# Current Function URLs require both URL and function invoke grants, limited to this URL.
for sid,action,kw in [('public-demo-url','lambda:InvokeFunctionUrl',{'FunctionUrlAuthType':'NONE'}),('public-demo-url-invoke','lambda:InvokeFunction',{'InvokedViaFunctionUrl':True})]:
    try:lam.add_permission(FunctionName=gatewayname,StatementId=sid,Action=action,Principal='*',**kw)
    except lam.exceptions.ResourceConflictException:pass
state={'region':R,'project':NAME,'gateway':gatewayname,'model':modelname,'image':uri,'url':url,'model_memory_mb':4096,'model_reserved_concurrency':1,'gateway_reserved_concurrency':2,'log_retention_days':7,'quota_table':quota,'daily_generation_limit':100}
(ROOT/'results/aws-resource-state.json').write_text(json.dumps(state,indent=2))
print('DEPLOYMENT_COMPLETE '+json.dumps(state),flush=True)
