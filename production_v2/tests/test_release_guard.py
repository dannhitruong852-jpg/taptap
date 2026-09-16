import unittest

from production_v2.release_guard import compare_catalogs


class ReleaseGuardTests(unittest.TestCase):
    def test_additive_release_is_allowed(self):
        old = {'articles': [
            {'id': '2002-text1', 'year': 2002},
            {'id': '2012-text4', 'year': 2012},
        ]}
        new = {'articles': [
            {'id': '2002-text1', 'year': 2002},
            {'id': '2012-text4', 'year': 2012},
            {'id': '2013-text1', 'year': 2013},
        ]}
        report = compare_catalogs(old, new)
        self.assertTrue(report['ok'])
        self.assertEqual(report['missing_article_ids'], [])

    def test_missing_old_article_blocks_release(self):
        old = {'articles': [
            {'id': '2003-text1', 'year': 2003},
            {'id': '2012-text4', 'year': 2012},
        ]}
        new = {'articles': [
            {'id': '2012-text4', 'year': 2012},
            {'id': '2013-text1', 'year': 2013},
        ]}
        report = compare_catalogs(old, new)
        self.assertFalse(report['ok'])
        self.assertEqual(report['missing_article_ids'], ['2003-text1'])
        self.assertEqual(report['missing_years'], [2003])

    def test_mutating_old_entry_blocks_release(self):
        old = {'articles': [
            {'id': '2012-text4', 'year': 2012, 'content': './old.json', 'manifest': './old-manifest.json'},
        ]}
        new = {'articles': [
            {'id': '2012-text4', 'year': 2012, 'content': './changed.json', 'manifest': './old-manifest.json'},
        ]}
        report = compare_catalogs(old, new)
        self.assertFalse(report['ok'])
        self.assertEqual(report['mutated_existing_ids'], ['2012-text4'])


if __name__ == '__main__':
    unittest.main()
