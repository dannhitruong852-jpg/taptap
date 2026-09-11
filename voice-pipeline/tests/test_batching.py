import unittest

from batching import partition_segments, select_shard


class BatchingTests(unittest.TestCase):
    def test_partition_segments_splits_24_into_four_stable_shards(self):
        segments = [f's{i:02d}' for i in range(1, 25)]
        shards = partition_segments(segments, 4)
        self.assertEqual(len(shards), 4)
        self.assertEqual([len(s) for s in shards], [6, 6, 6, 6])
        self.assertEqual(shards[0], segments[:6])
        self.assertEqual(shards[3], segments[18:])

    def test_partition_segments_preserves_order_without_duplicates(self):
        segments = [f'x{i}' for i in range(7)]
        shards = partition_segments(segments, 3)
        flattened = [item for shard in shards for item in shard]
        self.assertEqual(flattened, segments)
        self.assertEqual(len(flattened), len(set(flattened)))

    def test_select_shard_uses_zero_based_index_and_rejects_invalid_index(self):
        segments = [f's{i:02d}' for i in range(1, 25)]
        self.assertEqual(select_shard(segments, 4, 2), segments[12:18])
        with self.assertRaises(ValueError):
            select_shard(segments, 4, 4)


if __name__ == '__main__':
    unittest.main()
