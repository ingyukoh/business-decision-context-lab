import unittest, json
from unittest.mock import patch
from deploy import gateway

def event(path='/api/predict', data=None, **kw):
    x={'requestContext':{'http':{'method':'POST'},'domainName':'demo.on.aws'},'rawPath':path,'headers':{'content-type':'application/json'},'body':json.dumps(data or {'inputs':{'TV':276.9,'radio':48.9,'newspaper':41.8}})}
    x.update(kw);return x
class GatewayTests(unittest.TestCase):
    def test_predict_frozen_result(self):
        r=gateway.handler(event(),None);x=json.loads(r['body']);self.assertEqual(r['statusCode'],200);self.assertAlmostEqual(x['prediction']['prediction'],24.71035127235);self.assertEqual(len(x['tool_trace']),2)
    def test_no_text_or_injection(self):
        for inputs in ({'TV':'ignore instructions','radio':1,'newspaper':2},{'TV':True,'radio':1,'newspaper':2},{'TV':1001,'radio':1,'newspaper':2},{'TV':float('nan'),'radio':1,'newspaper':2}):
            self.assertEqual(gateway.handler(event(data={'inputs':inputs}),None)['statusCode'],422)
    def test_payload_and_origin(self):
        self.assertEqual(gateway.handler(event(body='x'*1025),None)['statusCode'],413)
        self.assertEqual(gateway.handler(event(headers={'content-type':'application/json','origin':'https://evil.example'}),None)['statusCode'],403)
    def test_unavailable_model_has_fallback(self):
        with patch.object(gateway,'model_invoke',side_effect=RuntimeError('not logged')):
            r=gateway.handler(event('/api/analyze'),None);x=json.loads(r['body']);self.assertEqual(r['statusCode'],200);self.assertTrue(x['fallback_used']);self.assertIn('24.71',x['displayed_summary'])
    def test_quota_returns_numeric_fallback(self):
        with patch.object(gateway,'claim_generation_slot',return_value=False):
            r=gateway.handler(event('/api/analyze'),None);self.assertEqual(r['statusCode'],429);self.assertTrue(json.loads(r['body'])['fallback_used'])
    def test_success_preserves_raw(self):
        with patch.object(gateway,'model_invoke',return_value={'status':'ok','raw_model_output':'wrong output'}):
            r=gateway.handler(event('/api/analyze'),None);self.assertEqual(r['statusCode'],200);self.assertEqual(json.loads(r['body'])['raw_model_output'],'wrong output')
    def test_model_cannot_supply_approved_display(self):
        with patch.object(gateway,'model_invoke',return_value={'status':'ok','raw_model_output':'24.71 thousand units causal. Transfer budget now','checks':{'checks_passed':True},'displayed_summary':'Transfer budget now'}):
            r=gateway.handler(event('/api/analyze'),None);x=json.loads(r['body']);self.assertTrue(x['fallback_used']);self.assertNotIn('Transfer',x['displayed_summary'])
    def test_cached_preset_bypasses_model_and_quota(self):
        with patch.object(gateway,'cached_result',return_value={'raw_model_output':'bad','model':'recorded'}),patch.object(gateway,'model_invoke',side_effect=AssertionError('must not run')),patch.object(gateway,'claim_generation_slot',side_effect=AssertionError('must not claim')):
            x=json.loads(gateway.handler(event('/api/analyze'),None)['body']);self.assertTrue(x['cache_hit']);self.assertTrue(x['fallback_used'])
    def test_retired_server_returns_prediction_without_quota(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{'QWEN_LIVE_ENABLED':'0'}),patch.object(gateway,'cached_result',return_value=None),patch.object(gateway,'claim_generation_slot',side_effect=AssertionError('must not claim')):
            x=json.loads(gateway.handler(event('/api/analyze'),None)['body']);self.assertEqual(x['status'],'unavailable');self.assertTrue(x['fallback_used'])
    def test_provider_rejected(self):
        self.assertEqual(gateway.handler(event(data={'inputs':{'TV':1,'radio':2,'newspaper':3},'provider':'evil'}),None)['statusCode'],422)
    def test_non_boolean_context_rejected(self):
        self.assertEqual(gateway.handler(event(data={'inputs':{'TV':1,'radio':2,'newspaper':3},'include_context':'yes'}),None)['statusCode'],422)
    def test_get_routes(self):
        for p in ['/','/style.css','/app.js','/health','/api/report','/api/examples']:
            e={'rawPath':p,'requestContext':{'http':{'method':'GET'}}};self.assertEqual(gateway.handler(e,None)['statusCode'],200)
if __name__=='__main__':unittest.main()
