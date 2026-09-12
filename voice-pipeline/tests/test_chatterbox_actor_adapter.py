import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.chatterbox_actor_adapter import resolve_controls


def profile(actor_id, ex, cfg, eligible=True, selected=True):
    p = {
        'schema_version': 'c-v4-actor-calibration-1',
        'calibration_id': f'actor-{actor_id}-audition-v1',
        'actor_id': actor_id,
        'eligible': eligible,
        'eligible_for': ['production'] if eligible else [],
        'references': {'curious': f'actor{actor_id}-curious.wav'},
        'intent_profiles': {
            'curious_probe': {
                'reference_state': 'curious',
                'center': {'exaggeration': ex, 'cfg_weight': cfg, 'temperature': 0.8, 'repetition_penalty': 1.18},
                'step': {'exaggeration': 0.08, 'cfg_weight': -0.035, 'temperature': 0.025},
                'intensity_shift': {'exaggeration': 0.025, 'cfg_weight': -0.015},
                'bounds': {'exaggeration': [0.25, 0.85], 'cfg_weight': [0.25, 0.7], 'temperature': [0.65, 0.95], 'repetition_penalty': [1.1, 1.3]},
            }
        },
        'selected_candidates': {'curious_probe': 'B'} if selected else {},
        'human_listening_qa': {'status': 'accepted' if eligible else 'pending'}
    }
    return p


class ActorAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / '05.json').write_text(json.dumps(profile('05', 0.59, 0.40)), encoding='utf-8')
        (self.dir / '08.json').write_text(json.dumps(profile('08', 0.68, 0.33)), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_intent_resolves_actor_specific_controls(self):
        a = resolve_controls('05', 'curious_probe', 1, self.dir)
        b = resolve_controls('08', 'curious_probe', 1, self.dir)
        self.assertNotEqual(a['exaggeration'], b['exaggeration'])
        self.assertNotEqual(a['cfg_weight'], b['cfg_weight'])
        self.assertEqual(a['artificial_pause_ms'], 0)
        self.assertFalse(a['post_tempo'])
        self.assertEqual(b['artificial_pause_ms'], 0)
        self.assertFalse(b['post_tempo'])

    def test_ineligible_actor_hard_fails(self):
        (self.dir / '04.json').write_text(json.dumps(profile('04', 0.5, 0.4, eligible=False)), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'not eligible'):
            resolve_controls('04', 'curious_probe', 1, self.dir)

    def test_missing_selected_calibration_hard_fails(self):
        (self.dir / '01.json').write_text(json.dumps(profile('01', 0.5, 0.4, selected=False)), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'no selected calibration'):
            resolve_controls('01', 'curious_probe', 1, self.dir)

    def test_unknown_intent_hard_fails(self):
        with self.assertRaisesRegex(ValueError, 'unknown director intent'):
            resolve_controls('05', 'punchline', 1, self.dir)

    def test_profile_fingerprint_is_stable_and_exposed(self):
        a = resolve_controls('05', 'curious_probe', 2, self.dir)
        b = resolve_controls('05', 'curious_probe', 2, self.dir)
        self.assertEqual(a['profile_hash'], b['profile_hash'])
        self.assertEqual(a['calibration_id'], 'actor-05-audition-v1')
        self.assertTrue(a['reference_path'].endswith('actor05-curious.wav'))

    def test_human_approval_overlay_can_promote_audition_profile(self):
        pending = profile('04', 0.52, 0.41, eligible=False, selected=False)
        (self.dir / '04.json').write_text(json.dumps(pending), encoding='utf-8')
        approvals = {
            'actors': {
                '04': {
                    'status': 'accepted',
                    'eligible_for': ['2002', 'production'],
                    'default_variant': 'B'
                }
            }
        }
        (self.dir / 'production_approvals.json').write_text(json.dumps(approvals), encoding='utf-8')
        resolved = resolve_controls('04', 'curious_probe', 1, self.dir)
        self.assertEqual(resolved['selected_variant'], 'B')
        self.assertEqual(resolved['approval_status'], 'accepted')


if __name__ == '__main__':
    unittest.main()
