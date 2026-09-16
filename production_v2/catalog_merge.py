import copy


def merge_catalogs(existing, batch):
    result = copy.deepcopy(existing)
    old = {row['id']: row for row in result.get('articles', [])}
    additions = {row['id']: row for row in batch.get('articles', [])}

    overlap = sorted(set(old) & set(additions))
    if overlap:
        raise ValueError(f'batch attempts to overwrite existing article ids: {overlap}')

    merged = list(old.values()) + list(additions.values())
    merged.sort(key=lambda row: (row.get('year', 0), row.get('id', '')))
    result['articles'] = merged
    result['years'] = sorted({row.get('year') for row in merged if row.get('year') is not None})
    result.setdefault('version', batch.get('version', 1))
    if 'default_article' not in result and merged:
        result['default_article'] = merged[0]['id']
    return result
