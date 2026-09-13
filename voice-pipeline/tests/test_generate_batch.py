import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import generate_batch


class GenerateBatchTests(unittest.TestCase):
    def test_select_shard_is_deterministic(self):
        items = [{'id': f's{i}'} for i in range(9)]
        self.assertEqual(
            [x['id'] for x in generate_batch.select_shard(items, 1, 3)],
            ['s3', 's4', 's5']
        )

    def test_cache_hit_skips_render(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / 'audio'
            out.mkdir()
            target = out / 's1.opus'
            target.write_bytes(b'audio')
            fp = generate_batch.item_fingerprint({'id': 's1', 'text': 'hello', 'actor_id': '01'})
            old = {
                'items': {
                    's1': {
                        'status': 'ok',
                        'fingerprint': fp,
                        'files': {'s1.opus': generate_batch.sha256_file(target)},
                    }
                }
            }
            calls = []
            result = generate_batch.run_batch(
                [{'id': 's1', 'text': 'hello', 'actor_id': '01'}],
                out,
                old,
                render_one=lambda item, attempt, directory: calls.append(item['id']),
            )
            self.assertEqual(calls, [])
            self.assertEqual(result['cache_hits'], 1)
            self.assertEqual(result['items']['s1']['status'], 'ok')

    def test_retry_is_isolated_per_item(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            attempts = {}

            def render(item, attempt, directory):
                attempts[item['id']] = attempts.get(item['id'], 0) + 1
                if item['id'] == 'bad':
                    raise RuntimeError('boom')
                p = directory / f"{item['id']}.opus"
                p.write_bytes(item['id'].encode())
                return {'files': {p.name: generate_batch.sha256_file(p)}}

            result = generate_batch.run_batch(
                [{'id': 'good', 'text': 'a', 'actor_id': '01'}, {'id': 'bad', 'text': 'b', 'actor_id': '02'}],
                out,
                {'items': {}},
                render_one=render,
                max_attempts=2,
            )
            self.assertEqual(attempts['good'], 1)
            self.assertEqual(attempts['bad'], 2)
            self.assertEqual(result['items']['good']['status'], 'ok')
            self.assertEqual(result['items']['bad']['status'], 'failed')
            self.assertEqual(len(result['failures']), 1)

    def test_merge_manifests_rejects_conflicting_successes(self):
        a = {'items': {'s1': {'status': 'ok', 'fingerprint': 'a'}}, 'failures': []}
        b = {'items': {'s1': {'status': 'ok', 'fingerprint': 'b'}}, 'failures': []}
        with self.assertRaises(ValueError):
            generate_batch.merge_manifests([a, b])

    def test_merge_manifests_prefers_success_over_failure(self):
        a = {'items': {'s1': {'status': 'failed', 'fingerprint': 'a'}}, 'failures': [{'id': 's1'}]}
        b = {'items': {'s1': {'status': 'ok', 'fingerprint': 'b'}}, 'failures': []}
        merged = generate_batch.merge_manifests([a, b])
        self.assertEqual(merged['items']['s1']['status'], 'ok')
        self.assertEqual(merged['failures'], [])


if __name__ == '__main__':
    unittest.main()
