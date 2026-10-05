"""Four real public requests. Records a new file; never overwrites published evidence."""
import argparse,json,time,statistics,datetime,pathlib,httpx
a=argparse.ArgumentParser();a.add_argument('--url',default='https://gvk2rzatfezmfj5rk6givmxgue0vsrto.lambda-url.us-east-1.on.aws/');args=a.parse_args()
u=args.url.rstrip('/');c=httpx.Client(timeout=100);r={'url':u,'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inference':[]}
h=c.get(u+'/api/model-health');h.raise_for_status();assert h.json()['status']=='ready'
for inputs,ctx in [({'TV':276.9,'radio':48.9,'newspaper':41.8},True),({'TV':80.2,'radio':0,'newspaper':9.2},True),({'TV':276.9,'radio':48.9,'newspaper':41.8},False),({'TV':276.9,'radio':48.9,'newspaper':41.8},True)]:
    t=time.perf_counter();x=c.post(u+'/api/analyze',json={'inputs':inputs,'include_context':ctx});x.raise_for_status();v=x.json()
    assert v['parameters']==494032768 and v['status']=='ok'
    r['inference'].append({'inputs':inputs,'context':ctx,'https_seconds':time.perf_counter()-t,'result':v})
r['median_https_seconds']=statistics.median(x['https_seconds'] for x in r['inference'])
p=pathlib.Path(__file__).resolve().parents[1]/'results'/('aws-reverification-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
p.write_text(json.dumps(r,indent=2));print(p, 'median',r['median_https_seconds'])
