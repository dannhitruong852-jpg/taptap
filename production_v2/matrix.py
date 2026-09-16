def _article_slug(entry):
    prefix = f"{entry['year']}-"
    article_id = entry['id']
    if not article_id.startswith(prefix):
        raise ValueError(f'article id/year mismatch: {article_id}')
    return article_id[len(prefix):]


def build_render_matrix(manifest, catalog, shards=3):
    years = set(manifest['years'])
    include = []
    for entry in sorted(
        catalog.get('articles', []),
        key=lambda row: (row.get('year'), row.get('id')),
    ):
        if entry.get('year') not in years:
            continue
        article = _article_slug(entry)
        for shard in range(int(shards)):
            include.append({
                'year': entry['year'],
                'article': article,
                'shard': shard,
            })
    return {'include': include}
