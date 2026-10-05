import unittest
from unittest.mock import patch
from deploy import model_handler as m
class FakeLLM:
    parameter_count=494032768
    def __init__(self,path):pass
    def generate(self,prompt):return 'Predicted sales: 24.71 million units. Association only.'
class ModelHandlerTests(unittest.TestCase):
    def tearDown(self):m._model=None
    def test_cached_generation_and_failed_units(self):
        m._model=None
        with patch.object(m,'LocalLLM',FakeLLM):
            x=m.handler({'inputs':{'TV':276.9,'radio':48.9,'newspaper':41.8}},None)
            y=m.handler({'inputs':{'TV':276.9,'radio':48.9,'newspaper':41.8}},None)
        self.assertTrue(x['cold_model_load']);self.assertFalse(y['cold_model_load']);self.assertTrue(x['fallback_used']);self.assertIn('million',x['raw_model_output']);self.assertEqual(x['parameters'],494032768)
    def test_model_loading_failure(self):
        m._model=None
        with patch.object(m,'LocalLLM',side_effect=OSError('private path not disclosed')):
            x=m.handler({'inputs':{'TV':1,'radio':2,'newspaper':3}},None)
        self.assertEqual(x['status'],'unavailable');self.assertNotIn('private path',x['error'])
if __name__=='__main__':unittest.main()
