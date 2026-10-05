"""Managed Claude adapter. Account access/terms must be enabled before deployment."""
import json,os,time
from lab import predict,reviewed_output
from structured_review import SCHEMA,structured_prompt

def invoke(payload, client=None):
    if not os.environ.get('BEDROCK_MODEL_ID'):raise RuntimeError('Claude account access pending')
    if client is None:
        import boto3
        from botocore.config import Config
        client=boto3.client('bedrock-runtime',region_name='us-east-1',config=Config(read_timeout=45,connect_timeout=3,retries={'max_attempts':0}))
    result=predict(payload['inputs']);began=time.perf_counter()
    r=client.converse(modelId=os.environ['BEDROCK_MODEL_ID'],
      messages=[{'role':'user','content':[{'text':structured_prompt(result,payload.get('include_context',True))}]}],
      inferenceConfig={'maxTokens':220,'temperature':0},
      outputConfig={'textFormat':{'type':'json_schema','structure':{'jsonSchema':{
        'schema':json.dumps(SCHEMA),'name':'business_review','description':'Read-only metadata decision; numeric display supplied by code'}}}})
    raw=''.join(c.get('text','') for c in r['output']['message']['content'])
    return {'status':'ok','prediction':result,**reviewed_output(raw,result,payload.get('include_context',True),structured=True),
            'model':os.environ['BEDROCK_MODEL_ID'],'compute_seconds':time.perf_counter()-began,
            'generation_mode':'Bedrock Converse, constrained JSON, 220-token cap',
            'usage':r.get('usage',{}),'stop_reason':r.get('stopReason')}
