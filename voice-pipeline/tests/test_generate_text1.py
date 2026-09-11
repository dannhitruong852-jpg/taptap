import unittest
from generate_text1 import flatten_segments


class GenerateTests(unittest.TestCase):
    def test_flatten_segments_preserves_sentence_and_segment_order(self):
        doc = {'sentences': [
            {'id': 1, 'segments': [{'id':'s01-a'}]},
            {'id': 9, 'segments': [{'id':'s09-a'},{'id':'s09-b'}]},
            {'id': 10, 'segments': [{'id':'s10-a'},{'id':'s10-b'},{'id':'s10-c'}]},
        ]}
        ids = [x['id'] for x in flatten_segments(doc)]
        self.assertEqual(ids, ['s01-a','s09-a','s09-b','s10-a','s10-b','s10-c'])


if __name__ == '__main__':
    unittest.main()
