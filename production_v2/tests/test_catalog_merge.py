import unittest

from production_v2.catalog_merge import merge_catalogs


class CatalogMergeTests(unittest.TestCase):
    def test_preserves_old_and_adds_new(self):
        old = {
            'version': 1,
            'years': [2002, 2012],
            'default_article': '2002-text1',
            'articles': [
                {'id': '2002-text1', 'year': 2002},
                {'id': '2012-text1', 'year': 2012},
            ],
        }
        batch = {
            'version': 1,
            'years': [2013],
            'articles': [{'id': '2013-text1', 'year': 2013}],
        }
        result = merge_catalogs(old, batch)
        self.assertEqual(result['years'], [2002, 2012, 2013])
        self.assertEqual(
            [row['id'] for row in result['articles']],
            ['2002-text1', '2012-text1', '2013-text1'],
        )
        self.assertEqual(result['default_article'], '2002-text1')

    def test_existing_article_cannot_be_overwritten_by_default(self):
        old = {
            'version': 1,
            'years': [2012],
            'articles': [{'id': '2012-text1', 'year': 2012, 'content': 'old'}],
        }
        batch = {
            'version': 1,
            'years': [2012],
            'articles': [{'id': '2012-text1', 'year': 2012, 'content': 'changed'}],
        }
        with self.assertRaises(ValueError):
            merge_catalogs(old, batch)


if __name__ == '__main__':
    unittest.main()
