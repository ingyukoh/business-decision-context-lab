from unittest.mock import patch
from fastapi.testclient import TestClient
from deploy import ec2_service as s
class FakeModel:
    parameter_count=494032768
    def __init__(self,path):pass
    def generate(self,prompt):return '24.71 million units; association only.'
def test_private_service_preloads_and_preserves_failure():
    with patch.object(s,'LocalLLM',FakeModel),TestClient(s.app) as c:
        assert c.get('/health').json()['status']=='ready'
        x=c.post('/analyze',json={'inputs':{'TV':276.9,'radio':48.9,'newspaper':41.8}}).json()
        assert x['parameters']==494032768 and not x['cold_model_load']
        assert x['fallback_used'] and 'million' in x['raw_model_output']
        assert 'thousands of units' in x['displayed_summary']
    s.model._model=None
def test_private_service_rejects_malformed_and_busy():
    with patch.object(s,'LocalLLM',FakeModel),TestClient(s.app) as c:
        for v in (True,'text',-1,1001):
            assert c.post('/analyze',json={'inputs':{'TV':v,'radio':2,'newspaper':3}}).status_code==422
        assert c.post('/analyze',json={'inputs':{'TV':1,'radio':2,'newspaper':3},'include_context':'yes'}).status_code==422
        s._lock.acquire()
        try:assert c.post('/analyze',json={'inputs':{'TV':1,'radio':2,'newspaper':3}}).status_code==503
        finally:s._lock.release()
    s.model._model=None
