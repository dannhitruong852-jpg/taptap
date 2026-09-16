import unittest

from production_v2.manifest import build_manifest, validate_manifest


class ManifestTests(unittest.TestCase):
    def test_manifest_requires_traceability_fields(self):
        doc = build_manifest('2013-2018', [2013, 2014], source_ref='abc123')
        self.assertEqual(validate_manifest(doc), [])
        for key in ['batch_id', 'pipeline_version', 'years', 'source_ref', 'state', 'created_at']:
            self.assertIn(key, doc)

    def test_years_must_be_sorted_unique(self):
        doc = build_manifest('x', [2014, 2013, 2013], source_ref='abc')
        errors = validate_manifest(doc)
        self.assertTrue(any('sorted unique' in error for error in errors))

    def test_invalid_state_is_rejected(self):
        doc = build_manifest('x', [2013], source_ref='abc')
        doc['state'] = 'whatever'
        errors = validate_manifest(doc)
        self.assertTrue(any('state' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
