def partition_segments(segments, shard_count):
    """Split an ordered segment list into contiguous, near-even shards."""
    if shard_count <= 0:
        raise ValueError('shard_count must be positive')

    items = list(segments)
    base, remainder = divmod(len(items), shard_count)
    shards = []
    start = 0
    for index in range(shard_count):
        size = base + (1 if index < remainder else 0)
        end = start + size
        shards.append(items[start:end])
        start = end
    return shards
