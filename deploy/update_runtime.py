"""Update only this demo's model allocation and gateway code; no image rebuild."""
import boto3,json,io,zipfile,pathlib
P='business-decision-lab-20261006';root=pathlib.Path(__file__).resolve().parents[1]
l=boto3.client('lambda',region_name='us-east-1')
l.update_function_configuration(FunctionName=P+'-model',MemorySize=6144,Timeout=180)
l.get_waiter('function_updated_v2').wait(FunctionName=P+'-model')
b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
    for p in [root/'lab.py',root/'deploy/gateway.py']:z.write(p,p.name)
    for folder in ['docs','data','results']:
        for p in (root/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.json','.csv','.html','.js','.css'):z.write(p,str(p.relative_to(root)))
l.update_function_code(FunctionName=P+'-gateway',ZipFile=b.getvalue());l.get_waiter('function_updated_v2').wait(FunctionName=P+'-gateway')
l.update_function_configuration(FunctionName=P+'-gateway',Timeout=200);l.get_waiter('function_updated_v2').wait(FunctionName=P+'-gateway')
print('RUNTIME_UPDATED 6144 MB / 180s model / 200s gateway',flush=True)
