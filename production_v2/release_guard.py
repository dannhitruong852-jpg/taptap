WATCHED_EXISTING_FIELDS = ('year', 'content', 'manifest')


def _index(catalog):
    return {row['id']: row for row in catalog.get('articles', [])}


def compare_catalogs(old_catalog, new_catalog):
    old = _index(old_catalog)
    new = _index(new_catalog)

    missing_article_ids = sorted(set(old) - set(new))
    old_years = {row.get('year') for row in old.values() if row.get('year') is not None}
    new_years = {row.get('year') for row in new.values() if row.get('year') is not None}
    missing_years = sorted(old_years - new_years)

    mutated_existing_ids = []
    for article_id in sorted(set(old) & set(new)):
        before = old[article_id]
        after = new[article_id]
        if any(before.get(key) != after.get(key) for key in WATCHED_EXISTING_FIELDS):
            mutated_existing_ids.append(article_id)

    return {
        'ok': not missing_article_ids and not missing_years and not mutated_existing_ids,
        'missing_article_ids': missing_article_ids,
        'missing_years': missing_years,
        'mutated_existing_ids': mutated_existing_ids,
        'old_article_count': len(old),
        'new_article_count': len(new),
    }
