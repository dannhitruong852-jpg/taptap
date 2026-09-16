import unittest

from production_v2.matrix import build_render_matrix


class MatrixTests(unittest.TestCase):
    def test_matrix_uses_manifest_years_and_shards(self):
        manifest = {'years': [2013]}
        catalog = {'articles': [
            {'id': '2012-text1', 'year': 2012},
            {'id': '2013-cloze', 'year': 2013},
            {'id': '2013-text1', 'year': 2013},
        ]}
        matrix = build_render_matrix(manifest, catalog, shards=2)
        self.assertEqual(matrix['include'], [
            {'year': 2013, 'article': 'cloze', 'shard': 0},
            {'year': 2013, 'article': 'cloze', 'shard': 1},
            {'year': 2013, 'article': 'text1', 'shard': 0},
            {'year': 2013, 'article': 'text1', 'shard': 1},
        ])


if __name__ == '__main__':
    unittest.main()
