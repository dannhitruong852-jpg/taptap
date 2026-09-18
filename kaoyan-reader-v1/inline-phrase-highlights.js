const DEFAULT_KEY='kaoyan-inline-phrase-highlights-v1';

function clamp(value,min,max){return Math.max(min,Math.min(max,Number(value)||0));}
function overlap(aStart,aEnd,bStart,bEnd){return aEnd>bStart&&aStart<bEnd;}
function mergeRanges(ranges){
  const sorted=ranges.filter(r=>Number.isFinite(r.start)&&Number.isFinite(r.end)&&r.end>r.start).sort((a,b)=>a.start-b.start);
  const merged=[];
  for(const range of sorted){
    const last=merged.at(-1);
    if(last&&range.start<=last.end)last.end=Math.max(last.end,range.end);
    else merged.push({start:range.start,end:range.end});
  }
  return merged;
}
function semanticRanges({start,end,words,groups}){
  if(!Array.isArray(words)||!words.length||!Array.isArray(groups)||!groups.length)return null;
  const selected=[];
  words.forEach((word,index)=>{if(overlap(start,end,Number(word.char_start),Number(word.char_end)))selected.push(index);});
  if(!selected.length)return null;
  const first=selected[0],last=selected[selected.length-1]+1;
  const ranges=groups.filter(group=>overlap(first,last,Number(group.en_word_start),Number(group.en_word_end)))
    .map(group=>({start:Number(group.zh_char_start),end:Number(group.zh_char_end)}));
  const merged=mergeRanges(ranges);
  return merged.length?merged:null;
}
function bilingualRanges({start,end,pairs}){
  if(!Array.isArray(pairs)||!pairs.length)return null;
  const ranges=pairs.filter(pair=>overlap(start,end,Number(pair.en_start),Number(pair.en_end)))
    .flatMap(pair=>Array.isArray(pair.zh_spans)?pair.zh_spans:[])
    .map(span=>({start:Number(span.start),end:Number(span.end)}));
  const merged=mergeRanges(ranges);
  return merged.length?merged:null;
}
function nearbyClause({sentence,start,end}){
  const zh=String(sentence.zh||''),en=String(sentence.en||'');
  if(!zh)return [];
  const target=clamp(((start+end)/2)/Math.max(1,en.length)*zh.length,0,Math.max(0,zh.length-1));
  const clauses=[];
  const re=/[^，。；！？!?]+[，。；！？!?]?/g;
  for(const match of zh.matchAll(re))clauses.push({start:match.index,end:match.index+match[0].length});
  const chosen=clauses.find(clause=>target>=clause.start&&target<clause.end)||clauses.at(-1)||{start:0,end:zh.length};
  return [chosen];
}

export function resolveLinkedHighlight({sentence,selectionStart,selectionEnd,words=[],semanticGroups=[],bilingualPairs=[]}){
  const en=String(sentence?.en||'');
  const start=clamp(selectionStart,0,en.length),end=clamp(selectionEnd,start,en.length);
  const semantic=semanticRanges({start,end,words,groups:semanticGroups});
  if(semantic)return {enStart:start,enEnd:end,zhRanges:semantic,source:'semantic'};
  const bilingual=bilingualRanges({start,end,pairs:bilingualPairs});
  if(bilingual)return {enStart:start,enEnd:end,zhRanges:bilingual,source:'bilingual'};
  return {enStart:start,enEnd:end,zhRanges:nearbyClause({sentence,start,end}),source:'context-clause'};
}

function parse(value){try{const result=JSON.parse(value);return Array.isArray(result)?result:[];}catch{return[];}}
export function createInlineHighlightStore({storage=null,key=DEFAULT_KEY}={}){
  let memory=[];
  function read(){
    if(!storage)return [...memory];
    try{return parse(storage.getItem(key)||'[]');}catch{return [...memory];}
  }
  function write(entries){memory=[...entries];if(storage){try{storage.setItem(key,JSON.stringify(entries));}catch{}}}
  function signature(entry){return [entry.articleId,entry.sentenceId,entry.enStart,entry.enEnd].join('|');}
  function add(entry){
    const entries=read(),sig=signature(entry),existing=entries.find(item=>signature(item)===sig);
    if(existing)return {added:false,entry:existing};
    const saved={...entry,createdAt:Number(entry.createdAt)||Date.now()};entries.push(saved);write(entries);return {added:true,entry:saved};
  }
  function list(articleId=null){const entries=read();return articleId?entries.filter(entry=>entry.articleId===articleId):entries;}
  return {add,list};
}
