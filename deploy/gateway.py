"""Public bounded numeric work sample; private model invocation through scoped IAM."""
import base64, json, os, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from lab import ROOT, predict, context, reviewed_output
HEADERS = {'content-type': 'application/json', 'cache-control': 'no-store',
 'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer',
 'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"}

def response(status, data, mime='application/json'):
    h = {**HEADERS, 'content-type': mime}
    return {'statusCode': status, 'headers': h, 'body': json.dumps(data, allow_nan=False) if mime=='application/json' else data}

def model_invoke(payload):
    import boto3
    from botocore.config import Config
    c = boto3.client('lambda', config=Config(read_timeout=190, retries={'max_attempts': 0}))
    r = c.invoke(FunctionName=os.environ['MODEL_FUNCTION'], Payload=json.dumps(payload).encode())
    if r.get('FunctionError'):
        raise RuntimeError('Private model error')
    return json.load(r['Payload'])

def claim_generation_slot():
    """Atomic global daily quota; stores UTC day/count only, never user identity."""
    if not os.environ.get('QUOTA_TABLE'): return True  # local tests only
    import boto3
    from botocore.exceptions import ClientError
    day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    try:
        boto3.client('dynamodb').update_item(TableName=os.environ['QUOTA_TABLE'],
            Key={'day':{'S':day}},
            UpdateExpression='SET expires_at = if_not_exists(expires_at, :expiry) ADD #n :one',
            ConditionExpression='attribute_not_exists(#n) OR #n < :limit',
            ExpressionAttributeNames={'#n':'calls'},
            ExpressionAttributeValues={':one':{'N':'1'},':limit':{'N':'100'},':expiry':{'N':str(int(time.time())+259200)}})
        return True
    except ClientError as e:
        if e.response['Error']['Code']=='ConditionalCheckFailedException': return False
        raise

def handler(event, lambda_context):
    began = time.perf_counter()
    req = event.get('requestContext', {}).get('http', {})
    method = req.get('method', 'GET'); path = event.get('rawPath', '/')
    if method=='GET':
        if path=='/': return response(200, (ROOT/'docs/aws.html').read_text(), 'text/html; charset=utf-8')
        if path=='/app.js': return response(200, (ROOT/'docs/app.js').read_text(), 'text/javascript; charset=utf-8')
        if path=='/style.css': return response(200, (ROOT/'docs/style.css').read_text(), 'text/css; charset=utf-8')
        if path=='/health': return response(200, {'status':'ok', 'mode':'independent read-only prototype', 'model_readiness':'checked by /api/analyze; gateway health does not establish model health'})
        if path=='/api/report': return response(200, json.loads((ROOT/'results/report.json').read_text()))
        if path=='/api/examples': return response(200, [{'label':'Held-out row 176: within marginal ranges','inputs':{'TV':276.9,'radio':48.9,'newspaper':41.8}}, {'label':'Held-out row 128: zero radio, review required','inputs':{'TV':80.2,'radio':0,'newspaper':9.2}}, {'label':'Illustrative out-of-range scenario','inputs':{'TV':500,'radio':80,'newspaper':100}}])
        return response(404, {'error':'Not found'})
    if method!='POST' or path not in ('/api/predict','/api/analyze'):
        return response(405, {'error':'Method not allowed'})
    headers = {k.lower():v for k,v in event.get('headers', {}).items()}
    origin = headers.get('origin')
    domain = event.get('requestContext', {}).get('domainName')
    if origin and origin != 'https://' + str(domain):
        return response(403, {'error':'Cross-origin browser request rejected'})
    if not headers.get('content-type','').startswith('application/json'):
        return response(415, {'error':'JSON required'})
    try:
        raw = event.get('body') or ''
        if event.get('isBase64Encoded'): raw = base64.b64decode(raw, validate=True).decode()
        if len(raw.encode())>1024: return response(413, {'error':'Payload exceeds 1024 bytes'})
        payload = json.loads(raw)
        if not isinstance(payload,dict) or set(payload) - {'inputs','include_context'} or 'inputs' not in payload:
            raise ValueError('Exact inputs/include_context schema required')
        if type(payload.get('include_context',True)) is not bool:
            raise ValueError('include_context must be boolean')
        p = predict(payload['inputs'])
        if any(x>1000 for x in payload['inputs'].values()): raise ValueError('Demo budget per channel limited to 1000 thousand dollars')
    except (ValueError, TypeError, KeyError, AttributeError, AssertionError):
        return response(422, {'error':'Require TV/radio/newspaper finite numbers between 0 and 1000; no text or extra fields'})
    trace = [{'tool':'predict_sales','result':p}, {'tool':'metric_context','result':context()}]
    if path=='/api/predict': return response(200, {'prediction':p,'semantic_context':context(),'tool_trace':trace})
    try:
        if not claim_generation_slot():
            return response(429, {'status':'unavailable','error':'Shared demo daily generation limit reached. Numeric prediction remains available.',
                'prediction':p, **reviewed_output('',p), 'tool_trace':trace})
        result = model_invoke(payload)
        if result.get('status')!='ok': raise RuntimeError('Unavailable')
        trace.append({'tool':'private_qwen_generation','status':'completed','context_in_prompt':payload.get('include_context',True)})
        status = 200
    except Exception:
        result = {'status':'unavailable', 'error':'Live LLM unavailable or busy. Numeric prediction remains available; retry later.',
                  'prediction':p, **reviewed_output('',p)}
        trace.append({'tool':'private_qwen_generation','status':'unavailable'})
        status = 503
    result.update({'semantic_context':context(), 'tool_trace':trace,
                   'gateway_seconds':time.perf_counter()-began, 'workflow':'fixed read-only orchestration, not autonomous tool selection'})
    print(json.dumps({'request_id':getattr(lambda_context,'aws_request_id',str(uuid.uuid4())), 'route':path, 'status':status,'elapsed_ms':round((time.perf_counter()-began)*1000)}))
    return response(status, result)
