export function selectArticles(catalog, year, section = '') {
  return catalog.articles.filter(item => item.year === Number(year) && (!section || item.section_type === section));
}
export function pickArticle(catalog, id) {
  return catalog.articles.find(item => item.id === id) || catalog.articles[0];
}
export function adjacentArticle(catalog, id, delta) {
  const index=catalog.articles.findIndex(item=>item.id===id);
  const target=index+Number(delta||0);
  return index>=0&&target>=0&&target<catalog.articles.length?catalog.articles[target]:null;
}
export function escapeHtml(value) {
  return String(value).replace(/[&<>"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));
}
export function highlightVocabulary(en, vocabulary = [], enabled = true) {
  if (!enabled) return escapeHtml(en);
  const ranges = [];
  for (const item of vocabulary.filter(x => Number(x.level) >= 6)) {
    const escaped = item.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(?<![\\w-])${escaped}(?![\\w-])`, 'gi');
    for (const match of en.matchAll(regex)) ranges.push({start:match.index,end:match.index+match[0].length,item});
  }
  ranges.sort((a,b) => a.start-b.start || b.end-a.end);
  let at=0, html='';
  for (const {start,end,item} of ranges) {
    if (start < at) continue;
    html += escapeHtml(en.slice(at,start));
    html += `<strong class="vocab" data-level="${Number(item.level)}" data-meaning="${escapeHtml(item.meaning || '')}">${escapeHtml(en.slice(start,end))}</strong>`;
    at=end;
  }
  return html+escapeHtml(en.slice(at));
}
export function manifestForVersion(entry, audioVersion = '') {
  if (audioVersion === 'v4') {
    const prefix = `${entry.year}-`;
    const id = String(entry.id || '');
    const article = id.startsWith(prefix) ? id.slice(prefix.length) : id;
    return `./audio/${entry.year}/v4/c-${article}/manifest.json`;
  }
  return entry.manifest;
}
export function createSelectionLoader(fetcher = fetch, options = {}) {
  let generation=0;
  const explicit = options?.audioVersion;
  const fromLocation = typeof location !== 'undefined'
    ? new URLSearchParams(location.search).get('audioVersion') || ''
    : '';
  const audioVersion = explicit === undefined ? fromLocation : explicit;
  return async function load(entry) {
    const token=++generation;
    const manifestPath=manifestForVersion(entry,audioVersion);
    const [content, manifest] = await Promise.all([
      fetcher(entry.content).then(r => { if(!r.ok) throw new Error('content-load-failed'); return r.json(); }),
      fetcher(manifestPath, {cache:'no-cache'}).then(r => r.ok ? r.json() : {segments:{}}).catch(()=>({segments:{}}))
    ]);
    return token === generation ? {content,manifest} : null;
  };
}
