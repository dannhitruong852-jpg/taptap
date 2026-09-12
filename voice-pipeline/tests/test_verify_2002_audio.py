"""Mutation targets: missing segments, formats, hashes and unsafe paths must fail."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from generate_2002 import render_fingerprint
try:
    from verify_2002_audio import validate_manifest, verify_file, safe_relative
except ImportError:
    validate_manifest = verify_file = safe_relative = None


class Verify2002AudioTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(validate_manifest, 'release verification has not been implemented')
        self.segment = {'id': 's01-01', 'text': 'A complete sentence.', 'actor_id': '05',
                        'rate': 1, 'exaggeration': .5, 'cfg_weight': .5,
                        'pause_before_ms': 0, 'pause_after_ms': 120}
        self.doc = {'article_id': 'text1', 'sentences': [{'id': 1, 'segments': [self.segment]}]}
        self.entry = {'path': './audio/2002/c-text1/s01-01.opus',
                      'mp3_path': './audio/2002/c-text1/s01-01.mp3',
                      'files': {'s01-01.opus': 'x', 's01-01.mp3': 'y'},
                      'technical_qa': 'passed', 'qa_status': 'candidate',
                      'reference_sha256': 'ref', 'seed': 23,
                      'fingerprint': render_fingerprint(self.segment, 'ref', 23)}
        self.manifest = {'article': 'text1', 'status': 'complete_candidate', 'missing': [],
                         'segments': {'s01-01': self.entry}}

    def test_complete_candidate_remains_candidate_not_artistic_acceptance(self):
        self.assertEqual(validate_manifest(self.doc, self.manifest), [])
        self.assertEqual(self.entry['qa_status'], 'candidate')

    def test_missing_segment_fails_even_when_status_claims_complete(self):
        self.manifest['segments'].clear()
        self.assertTrue(validate_manifest(self.doc, self.manifest))

    def test_both_audio_formats_and_exact_paths_are_required(self):
        del self.entry['files']['s01-01.mp3']
        self.assertTrue(validate_manifest(self.doc, self.manifest))

    def test_stale_render_fingerprint_is_rejected(self):
        self.segment['rate'] = 1.05
        self.assertTrue(validate_manifest(self.doc, self.manifest))

    def test_duplicate_source_segment_ids_are_rejected(self):
        self.doc['sentences'][0]['segments'].append(copy.deepcopy(self.segment))
        self.assertTrue(validate_manifest(self.doc, self.manifest))

    def test_unsafe_paths_are_rejected(self):
        for path in ['../secret', '/absolute', 'https://example.com/a', 'audio/../a', 'a?x=1']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_relative(path)
        self.assertEqual(safe_relative('./audio/2002/c-text1/s01-01.opus'), 'audio/2002/c-text1/s01-01.opus')

    def test_hash_verification_rejects_corrupted_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'audio.opus'
            p.write_bytes(b'actual bytes')
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertTrue(verify_file(p, digest))
            p.write_bytes(b'changed bytes')
            self.assertFalse(verify_file(p, digest))


if __name__ == '__main__':
    unittest.main()
