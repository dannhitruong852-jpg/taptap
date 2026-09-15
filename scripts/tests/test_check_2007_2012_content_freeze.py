import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'check_2007_2012_content_freeze.py'
YEARS = range(2007, 2013)
UNITS = ('cloze', 'text1', 'text2', 'text3', 'text4', 'partb', 'translation')


class FreezeGateTests(unittest.TestCase):
    def make_root(self, frozen=False, complete=True):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / '2007-2012-production-board.json').write_text(json.dumps({
            'content_frozen': frozen,
            'freeze_gate_remaining': [] if frozen else ['materialize_all_candidates'],
        }))
        if complete:
            for year in YEARS:
                directory = root / str(year)
                directory.mkdir(parents=True)
                for unit in UNITS:
                    (directory / f'{unit}.candidate.json').write_text(json.dumps({
                        'year': year,
                        'article': {'id': unit, 'rows': [[1, 'x', '中', 'report', []]]},
                    }))
        return td, root

    def run_gate(self, root, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(root), *extra],
            text=True,
            capture_output=True,
        )

    def test_informational_mode_allows_unfrozen_board(self):
        td, root = self.make_root(frozen=False, complete=False)
        self.addCleanup(td.cleanup)
        result = self.run_gate(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_require_frozen_rejects_unfrozen_even_when_candidates_complete(self):
        td, root = self.make_root(frozen=False, complete=True)
        self.addCleanup(td.cleanup)
        result = self.run_gate(root, '--require-frozen')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('content_frozen', result.stderr + result.stdout)

    def test_require_frozen_rejects_remaining_freeze_gates(self):
        td, root = self.make_root(frozen=True, complete=True)
        self.addCleanup(td.cleanup)
        board = json.loads((root / '2007-2012-production-board.json').read_text())
        board['freeze_gate_remaining'] = ['canonical_merge']
        (root / '2007-2012-production-board.json').write_text(json.dumps(board))
        result = self.run_gate(root, '--require-frozen')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('freeze_gate_remaining', result.stderr + result.stdout)

    def test_require_frozen_accepts_complete_frozen_board(self):
        td, root = self.make_root(frozen=True, complete=True)
        self.addCleanup(td.cleanup)
        result = self.run_gate(root, '--require-frozen')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


if __name__ == '__main__':
    unittest.main()
