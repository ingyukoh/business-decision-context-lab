"""Public bounded numeric work sample; private model invocation through scoped IAM."""
import base64, json, os, time, uuid, hashlib, hmac
import http.client
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path
from lab import ROOT, predict, context, reviewed_output
HEADERS = {'content-type': 'application/json', 'cache-control': 'no-store',
 'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer',
 'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"}

_log_context={}

def response(status, data, mime='application/json'):
    if _log_context:print(json.dumps({**_log_context,'status':status,'elapsed_ms':round((time.perf_counter()-_began)*1000,3)}))
    h = {**HEADERS, 'content-type': mime}
    return {'statusCode': status, 'headers': h, 'body': json.dumps(data, allow_nan=False) if mime=='application/json' else data}

def private_http(path, payload=None):
    u=urlsplit(os.environ['MODEL_HTTP_URL'])
    if u.scheme!='http' or not u.hostname.startswith('10.42.0.') or u.port!=8080:
        raise RuntimeError('Only isolated private model address is allowed')
    c=http.client.HTTPConnection(u.hostname,u.port,timeout=3)
    try:
        c.connect();c.sock.settimeout(70)
        body=json.dumps(payload).encode() if payload is not None else None
        c.request('POST' if body else 'GET',path,body=body,headers={'Content-Type':'application/json'})
        r=c.getresponse()
        if r.status!=200:raise RuntimeError('Private model unavailable')
        b=r.read(32769)
        if len(b)>32768:raise RuntimeError('Private response exceeds limit')
        return json.loads(b)
    finally:c.close()

def model_invoke(payload):
    if payload.get('provider')=='claude':
        try: from deploy.bedrock_provider import invoke
        except ImportError: from bedrock_provider import invoke
        return invoke(payload)
    if os.environ.get('MODEL_HTTP_URL'):return private_http('/analyze',payload)
    import boto3
    from botocore.config import Config
    c = boto3.client('lambda', config=Config(read_timeout=190, retries={'max_attempts': 0}))
    r = c.invoke(FunctionName=os.environ['MODEL_FUNCTION'], Payload=json.dumps(payload).encode())
    if r.get('FunctionError'):
        raise RuntimeError('Private model error')
    return json.load(r['Payload'])

def cache_key(payload):
    return json.dumps([payload.get('provider','qwen'),[float(payload['inputs'][k]) for k in ('TV','radio','newspaper')],payload.get('include_context',True)],separators=(',',':'))

def cached_result(payload):
    file=ROOT/'results/preset-cache.json'
    if not file.exists():return None
    return json.loads(file.read_text()).get('entries',{}).get(cache_key(payload))

def claim_generation_slot(source_ip=None):
    """5 attempts per daily HMAC of source IP, then global 100/day fuse.
    Shared NATs share a limit. Distributed callers can still exhaust the fuse;
    recorded examples and numeric predictions remain available independently.
    """
    if not os.environ.get('QUOTA_TABLE'): return True
    import boto3
    from botocore.exceptions import ClientError
    day=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    def claim(key,limit):
        try:
            boto3.client('dynamodb').update_item(TableName=os.environ['QUOTA_TABLE'],
              Key={'day':{'S':key}},UpdateExpression='SET expires_at = if_not_exists(expires_at, :expiry) ADD #n :one',
              ConditionExpression='attribute_not_exists(#n) OR #n < :limit',ExpressionAttributeNames={'#n':'calls'},
              ExpressionAttributeValues={':one':{'N':'1'},':limit':{'N':str(limit)},':expiry':{'N':str(int(time.time())+172800)}})
            return True
        except ClientError as e:
            if e.response['Error']['Code']=='ConditionalCheckFailedException':return False
            raise
    salt=os.environ.get('QUOTA_HMAC_SALT')
    if not salt or not source_ip:return False
    digest=hmac.new(salt.encode(),(day+'|'+source_ip).encode(),hashlib.sha256).hexdigest()
    return claim('visitor|'+day+'|'+digest,5) and claim(day,100)


def handler(event, lambda_context):
    global _began,_log_context
    began = time.perf_counter();_began=began
    req = event.get('requestContext', {}).get('http', {})
    method = req.get('method', 'GET'); path = event.get('rawPath', '/')
    _log_context={'request_id':getattr(lambda_context,'aws_request_id','local'),'route':path if path in ('/','/app.js','/style.css','/health','/api/model-health','/api/report','/api/remediation','/api/aws-verification','/api/examples','/api/analyze','/api/predict') else 'unknown'}
    if method=='GET':
        if path=='/': return response(200, (ROOT/'docs/aws.html').read_text(), 'text/html; charset=utf-8')
        if path=='/app.js': return response(200, (ROOT/'docs/app.js').read_text(), 'text/javascript; charset=utf-8')
        if path=='/style.css': return response(200, (ROOT/'docs/style.css').read_text(), 'text/css; charset=utf-8')
        if path=='/health': return response(200, {'status':'ok', 'mode':'independent read-only prototype', 'model_readiness':'checked by /api/analyze; gateway health does not establish model health'})
        if path=='/api/model-health':
            return response(200,{'gateway':'ok','qwen':'recorded examples available; live CPU backend retired' if os.environ.get('QWEN_LIVE_ENABLED')=='0' else 'private backend configured',
              'claude':'configured; inference establishes readiness' if os.environ.get('BEDROCK_MODEL_ID') else 'pending AWS account agreement; no Claude results claimed',
              'numeric_prediction':'available independently'})
        if path=='/api/remediation':return response(200,json.loads((ROOT/'results/remediation-report.json').read_text()))
        if path=='/api/report': return response(200, {'report_status':'historical_only; keyword validation retired',**json.loads((ROOT/'results/report.json').read_text())})
        if path=='/api/aws-verification':return response(200,json.loads((ROOT/'results/aws-remediation-verification.json').read_text()))
        if path=='/api/examples': return response(200, [{'label':'Held-out row 176: within marginal ranges','inputs':{'TV':276.9,'radio':48.9,'newspaper':41.8}}, {'label':'Row 128: deliberate wrong-unit fallback demonstration','inputs':{'TV':80.2,'radio':0,'newspaper':9.2}}, {'label':'Illustrative out-of-range scenario','inputs':{'TV':500,'radio':80,'newspaper':100}}])
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
        if not isinstance(payload,dict) or set(payload) - {'inputs','include_context','provider'} or 'inputs' not in payload:
            raise ValueError('Exact inputs/include_context schema required')
        if type(payload.get('include_context',True)) is not bool:
            raise ValueError('include_context must be boolean')
        if payload.get('provider','qwen') not in ('qwen','claude'):raise ValueError('Unknown provider')
        p = predict(payload['inputs'])
        if any(x>1000 for x in payload['inputs'].values()): raise ValueError('Demo budget per channel limited to 1000 thousand dollars')
    except (ValueError, TypeError, KeyError, AttributeError, AssertionError):
        return response(422, {'error':'Require TV/radio/newspaper finite numbers between 0 and 1000; no text or extra fields'})
    trace = [{'tool':'predict_sales','result':p}, {'tool':'metric_context','result':context()}]
    if path=='/api/predict': return response(200, {'prediction':p,'semantic_context':context(),'tool_trace':trace})
    try:
        cached=cached_result(payload)
        if cached:
            result=dict(cached)
            result.update({'status':'ok','cache_hit':True,'generation_mode':'Recorded actual generation; no live model call or quota consumed'})
        elif payload.get('provider','qwen')=='qwen' and os.environ.get('QWEN_LIVE_ENABLED')=='0':
            result={'status':'unavailable','error':'Qwen live CPU server retired. Custom prediction and code-composed summary remain available.', 'cache_hit':False}
        elif payload.get('provider')=='claude' and not os.environ.get('BEDROCK_MODEL_ID'):
            result={'status':'unavailable','error':'Claude account access pending; no Claude generation was performed.','cache_hit':False}
        else:
            if not claim_generation_slot(req.get('sourceIp')):
                return response(429, {'status':'unavailable','error':'Live generation limit reached (5/day per source network, 100/day globally). Presets and numeric prediction remain available.',
                    'prediction':p, **reviewed_output('',p), 'tool_trace':trace})
            result=model_invoke(payload)
            if result.get('status')!='ok':raise RuntimeError('Unavailable')
        raw=result.get('raw_model_output','')
        result.update(reviewed_output(raw,p,payload.get('include_context',True),structured=payload.get('provider')=='claude'))
        result['prediction']=p
        trace.append({'tool':'model_metadata_or_draft','provider':payload.get('provider','qwen'),'status':result['status'],'cache_hit':result.get('cache_hit',False)})
        status=200
    except Exception:
        result = {'status':'unavailable', 'error':'Live model unavailable; trusted numeric summary remains available. Recorded examples are independent.',
                  'prediction':p, **reviewed_output('',p)}
        trace.append({'tool':'private_qwen_generation','status':'unavailable'})
        status = 200
    result.update({'semantic_context':context(), 'tool_trace':trace,
                   'gateway_seconds':time.perf_counter()-began, 'workflow':'read-only tools plus a closed display contract; no business write actions'})

    return response(status, result)
