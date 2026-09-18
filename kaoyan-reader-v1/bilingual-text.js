import { escapeHtml } from './catalog.js';

const WORD_RE=/[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+(?:['’][A-Za-z]+)*)*|\d+(?:\.\d+)?/g;

export function renderEnglish(sentence) {
  const vocabulary=(sentence.vocab||[]).filter(v=>v.level>=6);
  let html='',at=0;
  for(const match of sentence.en.matchAll(WORD_RE)){
    const start=match.index,end=start+match[0].length;
    html+=escapeHtml(sentence.en.slice(at,start));
    const v=vocabulary.find(v=>start<v.end&&end>v.start);
    const classes=['read-token'];if(v)classes.push('vocab');
    let attrs=`class="${classes.join(' ')}" data-char-start="${start}" data-char-end="${end}"`;
    if(v){const studyGloss=v.study_gloss||v.meaning||'';attrs+=` data-pair="${v.start}:${v.end}" data-level="${v.level}" data-meaning="${escapeHtml(studyGloss)}"`;}
    html+=`<span ${attrs}>${escapeHtml(match[0])}</span>`;
    at=end;
  }
  return html+escapeHtml(sentence.en.slice(at));
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
      ? [...raw].map(c=>/\s/.test(c)?escapeHtml(c):`<span class="read-token">${escapeHtml(c)}</span>`).join('')
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
      return `<span class="semantic-group" data-semantic-index="${index}" data-en-word-start="${group.en_word_start}" data-en-word-end="${group.en_word_end}">${content}</span>`;
    }).join('');
  }
  return renderChineseSlice(sentence,ranges,0,sentence.zh.length,{legacyTokens:true});
}
