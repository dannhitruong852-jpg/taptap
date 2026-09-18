import { escapeHtml } from './catalog.js';

const WORD_RE=/[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+(?:['’][A-Za-z]+)*)*|\d+(?:\.\d+)?/g;

function renderTokenSlice(text, offset = 0) {
  let html='',at=0;
  for(const match of text.matchAll(WORD_RE)){
    const localStart=match.index,localEnd=localStart+match[0].length;
    const start=offset+localStart,end=offset+localEnd;
    html+=escapeHtml(text.slice(at,localStart));
    html+=`<span class="read-token" data-char-start="${start}" data-char-end="${end}">${escapeHtml(match[0])}</span>`;
    at=localEnd;
  }
  return html+escapeHtml(text.slice(at));
}

function continuousVocabularyRanges(sentence) {
  const candidates=(sentence.vocab||[])
    .filter(v=>v.level>=6&&Number.isInteger(v.start)&&Number.isInteger(v.end)&&v.start>=0&&v.end>v.start&&v.end<=sentence.en.length)
    .sort((a,b)=>a.start-b.start||(b.end-b.start)-(a.end-a.start));
  const selected=[];
  let coveredUntil=-1;
  for(const vocab of candidates){
    if(vocab.start<coveredUntil)continue;
    selected.push(vocab);
    coveredUntil=vocab.end;
  }
  return selected;
}

export function renderEnglish(sentence) {
  const ranges=continuousVocabularyRanges(sentence);
  let html='',at=0;
  for(const vocab of ranges){
    html+=renderTokenSlice(sentence.en.slice(at,vocab.start),at);
    const studyGloss=vocab.study_gloss||vocab.meaning||'';
    html+=`<span class="vocab vocab-range" data-pair="${vocab.start}:${vocab.end}" data-level="${vocab.level}" data-meaning="${escapeHtml(studyGloss)}">${renderTokenSlice(sentence.en.slice(vocab.start,vocab.end),vocab.start)}</span>`;
    at=vocab.end;
  }
  return html+renderTokenSlice(sentence.en.slice(at),at);
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

function renderChineseSlice(sentence,ranges,start,end,{legacyTokens=false}={}){
  const clipped=ranges.filter(r=>r.start<end&&r.end>start);
  const boundaries=[...new Set([start,end,...clipped.flatMap(r=>[Math.max(start,r.start),Math.min(end,r.end)])])].sort((a,b)=>a-b);
  let html='';
  for(let i=0;i<boundaries.length-1;i++){
    const left=boundaries[i],right=boundaries[i+1];
    const active=clipped.filter(r=>r.start<=left&&r.end>=right);
    const raw=sentence.zh.slice(left,right);
    const content=legacyTokens
      ? [...raw].map((c,index)=>/\s/.test(c)?escapeHtml(c):`<span class="read-token" data-zh-start="${left+index}" data-zh-end="${left+index+1}">${escapeHtml(c)}</span>`).join('')
      : escapeHtml(raw);
    html+=active.length?`<strong class="vocab zh-vocab" data-pair="${active.map(r=>r.pair).join(' ')}">${content}</strong>`:content;
  }
  return html;
}

function validSemanticGroups(sentence,groups){
  if(!Array.isArray(groups)||!groups.length)return false;
  let end=0;
  for(const group of groups){
    if(!Number.isInteger(group.zh_char_start)||!Number.isInteger(group.zh_char_end))return false;
    if(group.zh_char_start!==end||group.zh_char_end<=group.zh_char_start||group.zh_char_end>sentence.zh.length)return false;
    end=group.zh_char_end;
  }
  return end===sentence.zh.length;
}

export function renderChinese(sentence, pairs = [], semanticGroups = []) {
  const ranges=validChineseRanges(sentence,pairs);
  if(validSemanticGroups(sentence,semanticGroups)){
    return semanticGroups.map((group,index)=>{
      const content=renderChineseSlice(sentence,ranges,group.zh_char_start,group.zh_char_end);
      return `<span class="semantic-group" data-semantic-index="${index}" data-en-word-start="${group.en_word_start}" data-en-word-end="${group.en_word_end}" data-zh-start="${group.zh_char_start}" data-zh-end="${group.zh_char_end}">${content}</span>`;
    }).join('');
  }
  return renderChineseSlice(sentence,ranges,0,sentence.zh.length,{legacyTokens:true});
}
