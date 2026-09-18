const DEFAULT_KEY='kaoyan-inline-phrase-highlights-v2';
const DEFAULT_PREFS_KEY='kaoyan-inline-phrase-prefs-v2';

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
export function semanticGroupsForYear(document,year,articleId){
  if(Number(document?.year)!==Number(year))return {};
  const articles=document?.articles;
  if(!articles||typeof articles!=='object'||Array.isArray(articles))return {};
  const article=articles[articleId];
  return article&&typeof article==='object'&&!Array.isArray(article)?article:{};
}
function semanticRanges({start,end,words,groups}){
  if(!Array.isArray(words)||!words.length||!Array.isArray(groups)||!groups.length)return null;
  const selected=[];
  words.forEach((word,index)=>{if(overlap(start,end,Number(word.char_start),Number(word.char_end)))selected.push(index);});
  if(!selected.length)return null;
  const first=selected[0],last=selected[selected.length-1]+1,selectedCount=last-first;
  const candidates=[];
  const covered=new Set();
  for(const group of groups){
    const gs=Number(group.en_word_start),ge=Number(group.en_word_end);
    if(!Number.isInteger(gs)||!Number.isInteger(ge)||ge<=gs)continue;
    const left=Math.max(first,gs),right=Math.min(last,ge),overlapWords=Math.max(0,right-left);
    if(!overlapWords)continue;
    const groupCoverage=overlapWords/(ge-gs);
    if(groupCoverage<0.65)continue;
    candidates.push(group);
    for(let i=left;i<right;i++)covered.add(i);
  }
  if(!candidates.length||covered.size/selectedCount<0.8)return null;
  const ranges=candidates.map(group=>({start:Number(group.zh_char_start),end:Number(group.zh_char_end)}));
  const merged=mergeRanges(ranges);
  return merged.length?merged:null;
}
function canBridgeChineseGap(text){
  const gap=String(text||'');
  return gap.length<=4&&!/[，。；：！？、,.!?;:\n\r]/.test(gap);
}
function bilingualRanges({start,end,pairs,zh}){
  if(!Array.isArray(pairs)||!pairs.length)return null;
  const matched=pairs.filter(pair=>overlap(start,end,Number(pair.en_start),Number(pair.en_end)))
    .sort((a,b)=>Number(a.en_start)-Number(b.en_start));
  const ranges=matched.flatMap(pair=>Array.isArray(pair.zh_spans)?pair.zh_spans:[])
    .map(span=>({start:Number(span.start),end:Number(span.end)}));
  const merged=mergeRanges(ranges);
  if(!merged.length)return null;
  if(merged.length<2||matched.length<2)return {ranges:merged,bridged:false};
  const bridged=[{...merged[0]}];
  let changed=false;
  for(const next of merged.slice(1)){
    const last=bridged.at(-1);
    const gap=String(zh||'').slice(last.end,next.start);
    if(next.start>=last.end&&canBridgeChineseGap(gap)){last.end=next.end;changed=true;}
    else bridged.push({...next});
  }
  return {ranges:bridged,bridged:changed};
}
export function resolveLinkedHighlight({sentence,selectionStart,selectionEnd,words=[],semanticGroups=[],bilingualPairs=[]}){
  const en=String(sentence?.en||'');
  const start=clamp(selectionStart,0,en.length),end=clamp(selectionEnd,start,en.length);
  const semantic=semanticRanges({start,end,words,groups:semanticGroups});
  if(semantic)return {enStart:start,enEnd:end,zhRanges:semantic,source:'semantic'};
  const bilingual=bilingualRanges({start,end,pairs:bilingualPairs,zh:sentence?.zh});
  if(bilingual)return {enStart:start,enEnd:end,zhRanges:bilingual.ranges,source:bilingual.bridged?'bilingual-context':'bilingual'};
  return {enStart:start,enEnd:end,zhRanges:[],source:'none'};
}
function parseArray(value){try{const result=JSON.parse(value);return Array.isArray(result)?result:[];}catch{return[];}}
function parseObject(value){try{const result=JSON.parse(value);return result&&typeof result==='object'&&!Array.isArray(result)?result:{};}catch{return{};}}
export function snippetFromRanges(text,ranges=[]){
  const source=String(text||'');
  return mergeRanges(ranges).map(range=>source.slice(range.start,range.end).trim()).filter(Boolean).join('…');
}

function vocabularyStudyGloss(sentence,start,end){
  const selectedLength=Math.max(1,end-start);
  const candidates=(sentence?.vocab||[]).map(v=>({
    start:Number(v.start),end:Number(v.end),gloss:String(v.study_gloss||v.meaning||'').trim()
  })).filter(v=>v.gloss&&Number.isFinite(v.start)&&Number.isFinite(v.end)&&overlap(start,end,v.start,v.end));
  const strong=candidates.filter(v=>{
    const amount=Math.max(0,Math.min(end,v.end)-Math.max(start,v.start));
    const vocabLength=Math.max(1,v.end-v.start);
    return amount/Math.min(selectedLength,vocabLength)>=0.7;
  });
  return [...new Set(strong.map(v=>v.gloss))].join('；');
}
function selectedWordBounds(start,end,words){
  const selected=[];
  (words||[]).forEach((word,index)=>{if(overlap(start,end,Number(word.char_start),Number(word.char_end)))selected.push(index);});
  return selected.length?{first:selected[0],last:selected.at(-1)+1}:null;
}
function semanticStudyGloss({start,end,words,groups,zh}){
  const bounds=selectedWordBounds(start,end,words);if(!bounds||!Array.isArray(groups)||!groups.length)return '';
  const ranges=[];
  for(const group of groups){
    const gs=Number(group.en_word_start),ge=Number(group.en_word_end);
    if(!Number.isInteger(gs)||!Number.isInteger(ge)||ge<=gs||ge<=bounds.first||gs>=bounds.last)continue;
    ranges.push({start:Number(group.zh_char_start),end:Number(group.zh_char_end)});
  }
  return snippetFromRanges(zh,ranges);
}
function anchorRange(pair){
  const spans=(pair?.zh_spans||[]).map(s=>({start:Number(s.start),end:Number(s.end)}))
    .filter(s=>Number.isFinite(s.start)&&Number.isFinite(s.end)&&s.end>s.start);
  if(!spans.length)return null;
  return {start:Math.min(...spans.map(s=>s.start)),end:Math.max(...spans.map(s=>s.end))};
}
function anchoredStudyGloss({start,end,pairs,zh}){
  const anchors=(pairs||[]).map(pair=>({
    enStart:Number(pair.en_start),enEnd:Number(pair.en_end),zh:anchorRange(pair)
  })).filter(x=>Number.isFinite(x.enStart)&&Number.isFinite(x.enEnd)&&x.zh).sort((a,b)=>a.enStart-b.enStart);
  let left=null,right=null;
  for(const anchor of anchors){
    if(anchor.enEnd<=start)left=anchor;
    if(anchor.enStart>=end){right=anchor;break;}
  }
  if(!left&&!right)return '';
  const source=String(zh||'');
  const zStart=left?left.zh.end:0,zEnd=right?right.zh.start:source.length;
  if(!(zEnd>zStart))return '';
  const raw=source.slice(zStart,zEnd).replace(/^[\s，。；：！？、,.!?;:]+|[\s，。；：！？、,.!?;:]+$/g,'').trim();
  if(!raw||raw.length>24||raw.length>Math.max(8,source.length*0.55))return '';
  return raw;
}
function clauseStudyGloss({sentence,start,end}){
  const en=String(sentence?.en||''),zh=String(sentence?.zh||'').trim();
  if(!en||!zh)return '';
  const ratio=clamp((start+end)/2,0,en.length)/Math.max(1,en.length);
  const clauses=[];let at=0;
  for(const match of zh.matchAll(/[，。；：！？]/g)){
    const stop=match.index;
    const text=zh.slice(at,stop).trim();
    if(text)clauses.push({start:at,end:stop,text});
    at=stop+match[0].length;
  }
  const tail=zh.slice(at).trim();if(tail)clauses.push({start:at,end:zh.length,text:tail});
  if(!clauses.length)return zh.length<=28?zh:'';
  const target=ratio*zh.length;
  const clause=clauses.find(c=>target>=c.start&&target<=c.end)
    || clauses.reduce((best,c)=>Math.abs((c.start+c.end)/2-target)<Math.abs((best.start+best.end)/2-target)?c:best,clauses[0]);
  if(!clause?.text)return '';
  if(clause.text.length<=28)return clause.text;
  const localRatio=clamp((target-clause.start)/Math.max(1,clause.end-clause.start),0,1);
  const center=Math.round(localRatio*clause.text.length);
  const left=Math.max(0,center-10),right=Math.min(clause.text.length,left+20);
  return clause.text.slice(left,right).trim();
}
export function localStudyGloss({sentence,selectionStart,selectionEnd,words=[],semanticGroups=[],bilingualPairs=[]}){
  const en=String(sentence?.en||'');
  const start=clamp(selectionStart,0,en.length),end=clamp(selectionEnd,start,en.length);
  const vocab=vocabularyStudyGloss(sentence,start,end);if(vocab)return {text:vocab,source:'vocabulary'};
  const semantic=semanticStudyGloss({start,end,words,groups:semanticGroups,zh:sentence?.zh});if(semantic)return {text:semantic,source:'semantic-context'};
  const anchored=anchoredStudyGloss({start,end,pairs:bilingualPairs,zh:sentence?.zh});if(anchored)return {text:anchored,source:'bilingual-context-generated'};
  const clause=clauseStudyGloss({sentence,start,end});if(clause)return {text:clause,source:'sentence-context-generated'};
  return {text:'',source:'none'};
}
export async function browserStudyGloss(text,{TranslatorApi=globalThis.Translator}={}){
  const input=String(text||'').trim();if(!input||!TranslatorApi?.create)return '';
  let translator=null;
  try{
    translator=await TranslatorApi.create({sourceLanguage:'en',targetLanguage:'zh'});
    return String(await translator.translate(input)||'').trim();
  }catch{return '';}
  finally{try{translator?.destroy?.();}catch{}}
}

export function createInlineHighlightStore({storage=null,key=DEFAULT_KEY,prefsKey=DEFAULT_PREFS_KEY}={}){
  let memory=[],memoryPrefs={};
  function read(){
    if(!storage)return [...memory];
    try{return parseArray(storage.getItem(key)||'[]');}catch{return [...memory];}
  }
  function write(entries){memory=[...entries];if(storage){try{storage.setItem(key,JSON.stringify(entries));}catch{}}}
  function readPrefs(){
    if(!storage)return {...memoryPrefs};
    try{return parseObject(storage.getItem(prefsKey)||'{}');}catch{return {...memoryPrefs};}
  }
  function writePrefs(prefs){memoryPrefs={...prefs};if(storage){try{storage.setItem(prefsKey,JSON.stringify(prefs));}catch{}}}
  function signature(entry){return [entry.articleId,entry.sentenceId,entry.enStart,entry.enEnd].join('|');}
  function add(entry){
    const entries=read(),sig=signature(entry),index=entries.findIndex(item=>signature(item)===sig);
    if(index>=0){
      const existing=entries[index];
      const saved={...existing,...entry,year:Number(entry.year)||existing.year||null,createdAt:Number(existing.createdAt)||Number(entry.createdAt)||Date.now()};
      entries[index]=saved;write(entries);return {added:false,updated:true,entry:saved};
    }
    const saved={...entry,year:Number(entry.year)||null,createdAt:Number(entry.createdAt)||Date.now()};
    entries.push(saved);write(entries);return {added:true,updated:false,entry:saved};
  }
  function list(articleId=null){const entries=read();return articleId?entries.filter(entry=>entry.articleId===articleId):entries;}
  function entryYear(entry){const direct=Number(entry.year);if(Number.isFinite(direct)&&direct>0)return direct;const match=String(entry.articleId||'').match(/^(20\\d{2})/);return match?Number(match[1]):null;}
  function listYear(year){const target=Number(year);return read().filter(entry=>entryYear(entry)===target&&entry.selectedText).sort((a,b)=>Number(b.createdAt||0)-Number(a.createdAt||0));}
  function years(){return [...new Set(read().map(entryYear).filter(Number.isFinite))].sort((a,b)=>a-b);}
  function remove(entry){
    const sig=typeof entry==='string'?entry:signature(entry);const entries=read();const next=entries.filter(item=>signature(item)!==sig&&item.id!==sig);
    if(next.length===entries.length)return false;write(next);return true;
  }
  function getYearBlurred(year){return Boolean(readPrefs()[String(Number(year))]?.blurred);}
  function setYearBlurred(year,value){
    const prefs=readPrefs(),id=String(Number(year));prefs[id]={...(prefs[id]||{}),blurred:Boolean(value)};writePrefs(prefs);return Boolean(value);
  }
  return {add,list,listYear,years,remove,getYearBlurred,setYearBlurred};
}
