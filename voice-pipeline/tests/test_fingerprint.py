import unittest
from render import generation_fingerprint, resolve_exaggeration

class FingerprintTest(unittest.TestCase):
    def test_generation_fingerprint_changes_only_when_render_inputs_change(self):
        base = dict(text='Who is that?', actor_id='12', reference_pack_version='1', emotion='curious', intensity=2, rate=0.90, model_version='chatterbox-english')
        a = generation_fingerprint(**base)
        b = generation_fingerprint(**base)
        self.assertEqual(a, b)
        changed = dict(base, rate=0.91)
        self.assertNotEqual(generation_fingerprint(**changed), a)

    def test_resolve_exaggeration_uses_intensity_rule(self):
        cfg = {'exaggeration': 0.6}
        self.assertEqual(resolve_exaggeration(cfg, 0), 0.52)
        self.assertEqual(resolve_exaggeration(cfg, 1), 0.6)
        self.assertEqual(resolve_exaggeration(cfg, 2), 0.7)

if __name__ == '__main__':
    unittest.main()
