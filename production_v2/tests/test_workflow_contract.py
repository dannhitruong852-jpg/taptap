import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / '.github/workflows/c-mode-production-v2.yml'


class WorkflowContractTests(unittest.TestCase):
    def test_canonical_workflow_has_required_gates(self):
        text = WORKFLOW.read_text()
        for token in [
            'batch_manifest:', 'prepare:', 'canary:', 'validate:', 'freeze:',
            'render:', 'merge:', 'release_guard:', 'publish:', 'verify_pages:',
        ]:
            self.assertIn(token, text)
        self.assertIn('needs: [prepare, freeze, voicepack]', text)
        self.assertIn('needs: [prepare, freeze, release_guard]', text)
        self.assertIn('origin/gh-pages', text)
        self.assertNotIn('git push --force origin HEAD:gh-pages', text)
        self.assertIn('production_v2.cli_release_guard', text)
        self.assertIn('production_v2.cli_freeze', text)
        self.assertIn('production_v2.cli_matrix', text)
        self.assertIn('pages build and deployment', text)
        self.assertIn("data['state']='published'", text)


if __name__ == '__main__':
    unittest.main()
