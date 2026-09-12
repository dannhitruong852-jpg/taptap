import { escapeHtml } from './catalog.js';

export function renderEnglish(sentence) {
  const vocabulary = (sentence.vocab || []).filter(v => v.level >= 6);
  return [...sentence.en.matchAll(/\s+|\S+/g)].map(match => {
    const raw = match[0];
    if (/^\s+$/.test(raw)) return escapeHtml(raw);
    const start = match.index, end = start + raw.length;
    const v = vocabulary.find(v => start < v.end && end > v.start);
    const attrs = v ? ` vocab" data-pair="${v.start}:${v.end}" data-level="${v.level}" data-meaning="${escapeHtml(v.meaning || '')}` : '';
    return `<span class="read-token${attrs}">${escapeHtml(raw)}</span>`;
  }).join('');
}

export function validChineseRanges(sentence, pairs = []) {
  const ranges = [];
  for (const pair of pairs) {
    if (!Number.isInteger(pair.en_start) || !Number.isInteger(pair.en_end) || pair.en_start < 0 || pair.en_end > sentence.en.length) continue;
    if (sentence.en.slice(pair.en_start,pair.en_end) !== pair.en_text) continue;
    if (!(sentence.vocab || []).some(v => v.level >= 6 && v.start === pair.en_start && v.end === pair.en_end)) continue;
    for (const span of pair.zh_spans || []) {
      if (!Number.isInteger(span.start) || !Number.isInteger(span.end) || span.start < 0 || span.end <= span.start || span.end > sentence.zh.length) continue;
      if (sentence.zh.slice(span.start,span.end) !== span.text) continue;
      ranges.push({...span, pair:`${pair.en_start}:${pair.en_end}`});
    }
  }
  return ranges;
}

export function renderChinese(sentence, pairs = []) {
  const ranges = validChineseRanges(sentence, pairs);
  const boundaries = [...new Set([0,sentence.zh.length,...ranges.flatMap(r => [r.start,r.end])])].sort((a,b)=>a-b);
  const tokens = str => [...str].map(c => /\s/.test(c) ? escapeHtml(c) : `<span class="read-token">${escapeHtml(c)}</span>`).join('');
  let html = '';
  for (let i=0; i<boundaries.length-1; i++) {
    const start=boundaries[i], end=boundaries[i+1];
    const active=ranges.filter(r => r.start<=start && r.end>=end);
    const content=tokens(sentence.zh.slice(start,end));
    html += active.length ? `<strong class="vocab zh-vocab" data-pair="${active.map(r=>r.pair).join(' ')}">${content}</strong>` : content;
  }
  return html;
}
