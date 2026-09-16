import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/c-mode-production-v2.yml'
CI_WORKFLOW = ROOT / '.github/workflows/c-mode-production-v2-ci.yml'


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

    def test_ci_runs_after_merge_to_canonical_branch(self):
        text = CI_WORKFLOW.read_text()
        self.assertIn('- c-mode-production-v2', text)
        self.assertIn('- c-v4-article-preview-actual', text)


if __name__ == '__main__':
    unittest.main()
