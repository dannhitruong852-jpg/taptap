import unittest

from production_v2.pipeline_state import can_transition, next_state


class PipelineStateTests(unittest.TestCase):
    def test_happy_path_transitions_are_allowed(self):
        path = ['draft', 'validated', 'frozen', 'rendering', 'merged', 'release_candidate', 'published']
        for current, target in zip(path, path[1:]):
            self.assertTrue(can_transition(current, target), (current, target))

    def test_skipping_freeze_is_forbidden(self):
        self.assertFalse(can_transition('validated', 'rendering'))

    def test_published_is_terminal(self):
        self.assertFalse(can_transition('published', 'draft'))

    def test_next_state_is_deterministic(self):
        self.assertEqual(next_state('frozen'), 'rendering')


if __name__ == '__main__':
    unittest.main()
