"""Update only existing public gateway code/assets; preserve VPC, roles and quota."""
import boto3,io,zipfile,pathlib
P='business-decision-lab-20261006';ROOT=pathlib.Path(__file__).resolve().parents[1]
b=io.BytesIO()
with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
    for p in [ROOT/'lab.py',ROOT/'deploy/gateway.py']:z.write(p,p.name)
    for folder in ['docs','data','results']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.json','.csv','.html','.js','.css') and not p.name.endswith('state.json'):z.write(p,str(p.relative_to(ROOT)))
l=boto3.client('lambda',region_name='us-east-1')
l.update_function_code(FunctionName=P+'-gateway',ZipFile=b.getvalue())
l.get_waiter('function_updated_v2').wait(FunctionName=P+'-gateway')
print('GATEWAY_ASSETS_UPDATED; configuration unchanged')
