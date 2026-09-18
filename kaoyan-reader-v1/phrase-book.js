const DEFAULT_ENTRY_KEY='kaoyan-phrase-book-v1';
const DEFAULT_BLUR_KEY='kaoyan-phrase-book-blur-v1';

function clamp(value,min,max){return Math.max(min,Math.min(max,Number(value)||0));}
function overlap(aStart,aEnd,bStart,bEnd){return aEnd>bStart&&aStart<bEnd;}
function trimSnippet(text){return String(text||'').trim().replace(/^[\s,.;:!?]+|[\s,.;:!?]+$/g,'');}

function semanticSnippet({sentence,start,end,words,groups}){
  if(!Array.isArray(words)||!words.length||!Array.isArray(groups)||!groups.length)return null;
  const selected=[];
  words.forEach((word,index)=>{if(overlap(start,end,Number(word.char_start),Number(word.char_end)))selected.push(index);});
  if(!selected.length)return null;
  const first=selected[0],last=selected[selected.length-1]+1;
  const matched=groups.filter(group=>overlap(first,last,Number(group.en_word_start),Number(group.en_word_end)));
  if(!matched.length)return null;
  const zhStart=Math.min(...matched.map(group=>Number(group.zh_char_start)));
  const zhEnd=Math.max(...matched.map(group=>Number(group.zh_char_end)));
  if(!Number.isFinite(zhStart)||!Number.isFinite(zhEnd)||zhEnd<=zhStart)return null;
  const text=trimSnippet(sentence.zh.slice(zhStart,zhEnd));
  return text?{text,source:'semantic',zhStart,zhEnd}:null;
}

function bilingualSnippet({sentence,start,end,pairs}){
  if(!Array.isArray(pairs)||!pairs.length)return null;
  const matched=pairs.filter(pair=>overlap(start,end,Number(pair.en_start),Number(pair.en_end)));
  const spans=matched.flatMap(pair=>Array.isArray(pair.zh_spans)?pair.zh_spans:[])
    .map(span=>({start:Number(span.start),end:Number(span.end),text:span.text}))
    .filter(span=>Number.isFinite(span.start)&&Number.isFinite(span.end)&&span.end>span.start)
    .sort((a,b)=>a.start-b.start);
  if(!spans.length)return null;
  const chunks=[];
  let previousEnd=null;
  for(const span of spans){
    const text=trimSnippet(span.text||sentence.zh.slice(span.start,span.end));
    if(!text)continue;
    if(previousEnd!==null&&span.start>previousEnd)chunks.push('...');
    chunks.push(text);previousEnd=Math.max(previousEnd??span.end,span.end);
  }
  const text=chunks.join('');
  return text?{text,source:'bilingual',zhStart:spans[0].start,zhEnd:spans[spans.length-1].end}:null;
}

function nearestChineseAnchor({start,end,pairs}){
  if(!Array.isArray(pairs)||!pairs.length)return null;
  const midpoint=(start+end)/2;
  let best=null;
  for(const pair of pairs){
    const spans=Array.isArray(pair.zh_spans)?pair.zh_spans:[];
    if(!spans.length)continue;
    const enMid=(Number(pair.en_start)+Number(pair.en_end))/2;
    const distance=Math.abs(midpoint-enMid);
    if(best&&best.distance<=distance)continue;
    const span=spans[0];
    best={distance,index:(Number(span.start)+Number(span.end))/2};
  }
  return best?.index??null;
}

function contextClause({sentence,start,end,pairs}){
  const zh=String(sentence.zh||'');
  if(!zh)return {text:'',source:'context-clause',zhStart:0,zhEnd:0};
  let target=nearestChineseAnchor({start,end,pairs});
  if(target===null){
    const enLength=Math.max(1,String(sentence.en||'').length);
    target=clamp(((start+end)/2)/enLength*zh.length,0,Math.max(0,zh.length-1));
  }
  const clauses=[];
  const re=/[^，。；！？!?]+[，。；！？!?]?/g;
  for(const match of zh.matchAll(re))clauses.push({start:match.index,end:match.index+match[0].length,text:trimSnippet(match[0])});
  const chosen=clauses.find(clause=>target>=clause.start&&target<clause.end)||clauses.at(-1)||{start:0,end:zh.length,text:trimSnippet(zh)};
  return {text:chosen.text,source:'context-clause',zhStart:chosen.start,zhEnd:chosen.end};
}

export function resolvePhraseSnippet({sentence,selectionStart,selectionEnd,words=[],semanticGroups=[],bilingualPairs=[]}){
  const en=String(sentence?.en||''),zh=String(sentence?.zh||'');
  const start=clamp(selectionStart,0,en.length),end=clamp(selectionEnd,start,en.length);
  const safeSentence={en,zh};
  return semanticSnippet({sentence:safeSentence,start,end,words,groups:semanticGroups})
    || bilingualSnippet({sentence:safeSentence,start,end,pairs:bilingualPairs})
    || contextClause({sentence:safeSentence,start,end,pairs:bilingualPairs});
}

function safeParse(value,fallback){try{return JSON.parse(value);}catch{return fallback;}}
function normalizePhrase(text){return String(text||'').trim().replace(/\s+/g,' ').toLocaleLowerCase('en');}

export function createPhraseBookStore({storage=null,entryKey=DEFAULT_ENTRY_KEY,blurKey=DEFAULT_BLUR_KEY}={}){
  let memoryEntries=[];
  let memoryBlurred=false;
  function readEntries(){
    if(!storage)return [...memoryEntries];
    try{const parsed=safeParse(storage.getItem(entryKey)||'[]',[]);return Array.isArray(parsed)?parsed:[];}catch{return [...memoryEntries];}
  }
  function writeEntries(entries){
    memoryEntries=[...entries];
    if(storage){try{storage.setItem(entryKey,JSON.stringify(entries));}catch{}}
  }
  function list(){return readEntries().sort((a,b)=>Number(b.createdAt||0)-Number(a.createdAt||0));}
  function signature(entry){return [entry.articleId,entry.sentenceId,entry.selectionStart,entry.selectionEnd,normalizePhrase(entry.selectedText)].join('|');}
  function add(entry){
    const entries=readEntries();
    const sig=signature(entry);
    const existing=entries.find(item=>signature(item)===sig);
    if(existing)return {added:false,entry:existing,entries:list()};
    const createdAt=Number(entry.createdAt)||Date.now();
    const id=encodeURIComponent(`${sig}|${createdAt}`);
    const saved={...entry,id,createdAt};
    entries.unshift(saved);writeEntries(entries);
    return {added:true,entry:saved,entries:list()};
  }
  function remove(id){
    const entries=readEntries();
    const next=entries.filter(item=>item.id!==id);
    if(next.length===entries.length)return false;
    writeEntries(next);return true;
  }
  function getBlurred(){
    if(!storage)return memoryBlurred;
    try{return storage.getItem(blurKey)==='1';}catch{return memoryBlurred;}
  }
  function setBlurred(value){
    memoryBlurred=Boolean(value);
    if(storage){try{storage.setItem(blurKey,memoryBlurred?'1':'0');}catch{}}
    return memoryBlurred;
  }
  return {list,add,remove,getBlurred,setBlurred};
}
