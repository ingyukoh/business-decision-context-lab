import unittest
from lab import context, predict, prompt_for, validate_summary, reviewed_output


class LabTests(unittest.TestCase):
    def test_relationship_traversal_includes_data_limit(self):
        edges = context()
        self.assertTrue(any(e['subject']=='advertising' and e['relation']=='structure' for e in edges))
        self.assertTrue(any(e['relation']=='limitation' for e in edges))

    def test_unknown_metric_abstains(self):
        with self.assertRaises(ValueError): context('profit')

    def test_invalid_and_unsupported_fields(self):
        for x in ({'TV': 1}, {'TV': True, 'radio': 1, 'newspaper': 2},
                  {'TV': float('nan'), 'radio': 1, 'newspaper': 2}):
            with self.assertRaises(ValueError): predict(x)

    def test_out_of_range_flags_review(self):
        r = predict({'TV': 100000, 'radio': 1, 'newspaper': 2})
        self.assertFalse(r['within_marginal_training_bounds'])
        self.assertTrue(r['review_required'])

    def test_wrong_units_and_number_are_exposed(self):
        r = predict({'TV': 10, 'radio': 10, 'newspaper': 10})
        c = validate_summary('Guaranteed $100 revenue.', r)
        self.assertFalse(c['checks_passed'])
        self.assertEqual(len(c['failures']), 3)

    def test_llm_does_not_control_numeric_prediction(self):
        inputs = {'TV': 10, 'radio': 10, 'newspaper': 10}
        _, a = prompt_for(inputs, True)
        _, b = prompt_for(inputs, False)
        self.assertEqual(a, b)

    def test_singular_unit_and_million_mismatch(self):
        r = predict({'TV': 10, 'radio': 10, 'newspaper': 10})
        n = f"{r['prediction']:.2f}"
        self.assertTrue(validate_summary(n+' thousand units, association only.', r)['checks_passed'])
        self.assertFalse(validate_summary(n+' million units; thousands of units are the training unit; association only.', r)['checks_passed'])

    def test_failed_summary_has_numeric_fallback(self):
        r = predict({'TV': 10, 'radio': 10, 'newspaper': 10})
        output = reviewed_output('Guaranteed 99 million units.', r)
        self.assertTrue(output['fallback_used'])
        self.assertIn(f"{r['prediction']:.2f} thousands of units", output['displayed_summary'])

if __name__ == '__main__': unittest.main()
