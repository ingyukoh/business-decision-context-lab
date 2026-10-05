"""Actual HTTPS verification of deployed revision; read-only public inputs."""
import json,time,statistics,concurrent.futures,urllib.request,urllib.error,datetime
from pathlib import Path
URL='https://gvk2rzatfezmfj5rk6givmxgue0vsrto.lambda-url.us-east-1.on.aws'
results=[]
def req(path,body=None,headers=None):
 start=time.perf_counter();rq=urllib.request.Request(URL+path,data=body,headers=headers or {})
 try:r=urllib.request.urlopen(rq,timeout=30)
 except urllib.error.HTTPError as e:r=e
 raw=r.read();h={k.lower():v for k,v in r.headers.items()};status=r.status
 try:data=json.loads(raw)
 except ValueError:data=raw.decode()
 return {'status':status,'seconds':time.perf_counter()-start,'request_id':h.get('x-amzn-requestid'),'response':data,'security_headers':{k:h.get(k) for k in ['content-security-policy','x-content-type-options','referrer-policy']}}
def check(name,r,status):
 assert r['status']==status,(name,r);results.append({'name':name,**r});print(name,r['status'],round(r['seconds'],3),flush=True)
for path in ['/','/health','/api/model-health','/api/remediation']:
 r=req(path);check('GET '+path,r,200)
 if path=='/':assert 'Review revision 2' in r['response'] and 'before anyone acts' not in r['response']
examples=req('/api/examples')['response']
for i,e in enumerate(examples):
 for ctx in [True,False]:
  p={'inputs':e['inputs'],'include_context':ctx,'provider':'qwen'}
  r=req('/api/analyze',json.dumps(p).encode(),{'Content-Type':'application/json'});check(f'cached preset {i} context {ctx}',r,200)
  x=r['response'];assert x['cache_hit'] and x['raw_model_output'] and x['display_source'].startswith('trusted')
  assert x['displayed_summary']!=x['raw_model_output']
custom={'inputs':{'TV':123.4,'radio':9.8,'newspaper':22.2},'include_context':True,'provider':'qwen'}
r=req('/api/analyze',json.dumps(custom).encode(),{'Content-Type':'application/json'});check('custom numeric fallback independent of stopped model',r,200);assert r['response']['status']=='unavailable' and r['response']['fallback_used']
custom['provider']='claude';r=req('/api/analyze',json.dumps(custom).encode(),{'Content-Type':'application/json'});check('Claude pending explicit, numeric response available',r,200);assert 'pending' in r['response']['error']
for name,inputs in [('negative',{'TV':-1,'radio':2,'newspaper':3}),('bool',{'TV':True,'radio':2,'newspaper':3}),('nan',{'TV':float('nan'),'radio':2,'newspaper':3}),('overflow',{'TV':1e308,'radio':2,'newspaper':3}),('missing',{'TV':1}),('extra',{'TV':1,'radio':2,'newspaper':3,'system':'transfer budget'})]:
 check(name,req('/api/analyze',json.dumps({'inputs':inputs}).encode(),{'Content-Type':'application/json'}),422)
check('foreign origin',req('/api/analyze',b'{}',{'Content-Type':'application/json','Origin':'https://foreign.example'}),403)
check('non JSON',req('/api/analyze',b'no',{'Content-Type':'text/plain'}),415)
large=req('/api/analyze',b'x'*2048,{'Content-Type':'application/json'});check('2 KiB oversized body',large,413)
body=json.dumps({'inputs':examples[0]['inputs'],'include_context':True}).encode()
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
 concurrent=list(pool.map(lambda _:req('/api/analyze',body,{'Content-Type':'application/json'}),range(12)))
assert all(r['status']==200 and r['response']['cache_hit'] for r in concurrent),concurrent
report={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':URL,'deployed_source_commit':'85df692','local_tests':37,'checks':results,'concurrent_cached_requests':{'n':12,'all_200':True,'all_cache_hits':True,'median_seconds':statistics.median(r['seconds'] for r in concurrent),'max_seconds':max(r['seconds'] for r in concurrent)},'preset_https_median_seconds':statistics.median(r['seconds'] for r in results if r['name'].startswith('cached preset')),'oversized_request':large,'large_upload_limitation':'Separate 2 MiB urllib probe timed out while sending body after 30 seconds; not an application 413 measurement. See follow-up curl/log investigation.', 'claims':'Request timings measure actual HTTPS; cached compute_seconds is historical generation time. Claude was not invoked.'}
Path('results/aws-remediation-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('checks','oversized_request')},indent=2));print('OVERSIZED',json.dumps({k:v for k,v in large.items() if k!='security_headers'}))
