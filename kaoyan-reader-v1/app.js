import { buildSentenceQueue, nextSentenceIndex } from './playback.js';
import { createAudioPlayer } from './audio-player.js';
import { createAudioCache } from './audio-cache.js';
import { createDecodedAudioStore } from './decoded-audio-store.js';
import { createWebAudioPlayer } from './web-audio-player.js';
import { createHybridAudioPlayer } from './hybrid-audio-player.js?v=continuous-playback-20260928-v1';
import { createContinuousPlayback } from './continuous-playback.js?v=20260928-v1';
import { measureLatency } from './latency-metrics.js';
import { sentenceProgress, isExplicitLegacyTimingVersion } from './progress.js';
import { readStateAtTime, activeChineseGroups } from './time-index.js';
import { renderEnglish, renderChinese } from './bilingual-text.js?v=phrase-study-continuous-20260918-v2';
import { createTapGuard, createTapArbiter } from './reader-controls.js?v=phrase-study-20260918-v2';
import { resolvePlayerScroll } from './scroll-behavior.js';
import { pickArticle, selectArticles, adjacentArticle } from './catalog.js';
import { createArticleBundleStore } from './article-bundle-store.js';
import { resolveLinkedHighlight, createInlineHighlightStore, snippetFromRanges, semanticGroupsForYear, localStudyGloss, browserStudyGloss } from './inline-phrase-highlights.js?v=phrase-book-cloud-sync-20260921-v1';
import { createPhraseBookCloudSync } from './phrase-book-cloud-sync.js?v=20260921-v1';
import { copyTextWithFallback } from './clipboard-copy.js?v=phrase-copy-on-save-20260922-v1';
import { createUiLayerHistory } from './ui-history.js?v=system-back-20260929-v1';
import { sortPhraseEntries, findNearestPhraseEntry } from './phrase-book-position.js?v=source-order-20260929-v1';

let article={}, sentences=[], manifest={segments:{}};
let catalog=null, loading=true, selectionGeneration=0, bilingualMappings={}, semanticMappings={};
let currentEntry=null;
const semanticMapPromise=fetch('./content/2002/semantic-spans.json', {cache:'no-cache'}).then(r=>r.ok?r.json():null).catch(()=>null);
const articleBundleStore=createArticleBundleStore();
let globalArticlePreloadStarted=false;
const audioCache=createAudioCache();
audioCache.pruneOldGenerations();
let audioContext=null,decodedAudioStore=null,webAudioPlayer=null;
const articleSelect=document.querySelector('#article-select');
const sectionSelect=document.querySelector('#section-select');
const yearSelect=document.querySelector('#year-select');
const audioSupport=document.createElement('audio');
const supportsOpus=Boolean(audioSupport.canPlayType('audio/ogg; codecs="opus"'));
const listEl=document.querySelector('#sentence-list');
const playButton=document.querySelector('#play-toggle');
const previousButton=document.querySelector('#previous');
const nextButton=document.querySelector('#next');
const positionEl=document.querySelector('#player-position');
const moodEl=document.querySelector('#director-mood');
const statusEl=document.querySelector('#player-status');
const playerShell=document.querySelector('#player-shell');
const vocabButton=document.querySelector('#toggle-vocab');
const continuousButton=document.querySelector('#toggle-continuous');
const continuousPreferenceKey='kaoyan-continuous-playback-v1';
let continuousEnabled=false;
try{continuousEnabled=window.localStorage.getItem(continuousPreferenceKey)==='true';}catch{}
continuousButton.setAttribute('aria-checked',String(continuousEnabled));
const toast=document.querySelector('#toast');
const phraseStudyBar=document.querySelector('#phrase-study-bar');
const phraseHighlightSelectionText=document.querySelector('#phrase-highlight-selection');
const phraseHighlightAction=document.querySelector('#phrase-highlight-action');
const phraseBookOpenButton=document.querySelector('#phrase-book-open');
const phraseBookBackdrop=document.querySelector('#phrase-book-backdrop');
const phraseBookCloseButton=document.querySelector('#phrase-book-close');
const phraseBookYear=document.querySelector('#phrase-book-year');
const phraseBookScopeSelect=document.querySelector('#phrase-book-scope');
const phraseBookContext=document.querySelector('#phrase-book-context');
const phraseBookList=document.querySelector('#phrase-book-list');
const phraseBookEmpty=document.querySelector('#phrase-book-empty');
const phraseBookBlurButton=document.querySelector('#phrase-book-blur');
const phraseBookEditButton=document.querySelector('#phrase-book-edit');
const phraseBookSyncCopy=document.querySelector('#phrase-book-sync-copy');
const phraseBookSyncChange=document.querySelector('#phrase-book-sync-change');
let inlineHighlightStorage=null;
try{inlineHighlightStorage=window.localStorage;}catch{}
const inlineHighlightStore=createInlineHighlightStore({storage:inlineHighlightStorage});
const phraseBookCloudSync=createPhraseBookCloudSync({
 store:inlineHighlightStore,
 storage:inlineHighlightStorage,
 onMerged:()=>{
  applyAllInlineHighlights();
  if(!phraseBookBackdrop.hidden)renderPhraseBook(currentPhraseBookYear());
  updatePhraseBookButton();
 }
});
let phraseHighlightSelection=null,phraseHighlightFrame=null,phraseHighlightInvalidKey='',phraseHighlightSaving=false;
let phraseBookEditing=false,phraseBookDrafts=new Map(),phraseBookScope='article';
let phraseBookQuickEditor=null,phraseBookPhraseAudio=null,phraseBookSpeech=null,phraseBookSpeakingNode=null,phraseBookSavedTimer=null;
const phraseBookHistory=createUiLayerHistory({
 history,
 location,
 layer:'phrase-book',
 isOpen:()=>!phraseBookBackdrop.hidden,
 closeDirect:closePhraseBookDirect,
 currentUrl:()=>currentEntry?.id?`#${currentEntry.id}`:location.href
});
const state={current:0,speed:1,playing:false,paused:false,showVocab:true,timer:null,playerHidden:false,programmaticScrollUntil:0,scrollAnchorY:Math.max(0,window.scrollY||0),scrollFrame:null,playRequestedAt:null};
const emotionLabels={neutral:'自然讲述',warm:'温暖讲解',lively:'轻快生动',serious:'严肃克制',curious:'好奇追问',ironic:'冷幽默',tense:'紧张转折',emotional:'情绪加强'};
function hasSelectedText(){return Boolean(window.getSelection()?.toString());}
function nodeElement(node){return node?.nodeType===Node.ELEMENT_NODE?node:node?.parentElement||null;}
function hidePhraseHighlightAction(){phraseHighlightSelection=null;phraseStudyBar.hidden=true;}
function legacyCopyPhraseText(text){
 const textarea=document.createElement('textarea');
 textarea.value=String(text||'');
 textarea.setAttribute('readonly','');
 textarea.style.position='fixed';textarea.style.left='-9999px';textarea.style.top='0';textarea.style.opacity='0';textarea.style.pointerEvents='none';
 document.body.append(textarea);
 try{textarea.focus({preventScroll:true});}catch{textarea.focus();}
 textarea.select();textarea.setSelectionRange(0,textarea.value.length);
 let copied=false;
 try{copied=document.execCommand?.('copy')===true;}catch{}
 textarea.remove();
 return copied;
}
function selectionOffsets(range,enEl){
 const before=document.createRange();before.selectNodeContents(enEl);before.setEnd(range.startContainer,range.startOffset);
 const raw=range.toString();const leading=(raw.match(/^\s+/)||[''])[0].length;const trailing=(raw.match(/\s+$/)||[''])[0].length;
 const start=before.toString().length+leading;const end=before.toString().length+raw.length-trailing;
 return {start,end,text:raw.trim().replace(/\s+/g,' ')};
}
function phraseHighlightSelectionFromWindow(){
 const selection=window.getSelection();if(!selection||selection.rangeCount!==1||selection.isCollapsed)return null;
 const range=selection.getRangeAt(0);const startEn=nodeElement(range.startContainer)?.closest('.en');const endEn=nodeElement(range.endContainer)?.closest('.en');
 if(!startEn&&!endEn)return null;
 if(!startEn||!endEn||startEn!==endEn)return {invalid:'cross-sentence',key:selection.toString().slice(0,140)};
 const card=startEn.closest('.sentence-card');if(!card)return null;
 const offsets=selectionOffsets(range,startEn);if(!offsets.text)return null;
 if(offsets.text.length>120)return {invalid:'too-long',key:offsets.text.slice(0,140)};
 const index=Number(card.dataset.index);const sentence=sentences[index];if(!sentence)return null;
 return {card,enEl:startEn,index,sentence,start:offsets.start,end:offsets.end,text:offsets.text};
}
function refreshPhraseHighlightAction(){
 phraseHighlightFrame=null;
 const snapshot=phraseHighlightSelectionFromWindow();
 if(!snapshot){hidePhraseHighlightAction();phraseHighlightInvalidKey='';return;}
 if(snapshot.invalid){
  hidePhraseHighlightAction();
  if(snapshot.key!==phraseHighlightInvalidKey){phraseHighlightInvalidKey=snapshot.key;showToast(snapshot.invalid==='cross-sentence'?'请在同一句中选择词群':'词群请控制在 120 个英文字符以内');}
  return;
 }
 phraseHighlightInvalidKey='';phraseHighlightSelection=snapshot;tapGuard.cancel();tapArbiter.cancel();phraseHighlightSelectionText.textContent=snapshot.text;phraseStudyBar.hidden=false;
}
function schedulePhraseHighlightAction(){if(phraseHighlightFrame!==null)return;phraseHighlightFrame=window.requestAnimationFrame(refreshPhraseHighlightAction);}
function highlightWords(sentence,enEl){
 const timed=manifest.sentences?.[sentence.id]?.words;if(Array.isArray(timed)&&timed.length)return timed;
 return [...enEl.querySelectorAll('.read-token')].map(node=>({char_start:Number(node.dataset.charStart),char_end:Number(node.dataset.charEnd)})).filter(word=>Number.isFinite(word.char_start)&&Number.isFinite(word.char_end));
}
function overlapsRange(start,end,rangeStart,rangeEnd){return end>rangeStart&&start<rangeEnd;}
function applySentenceInlineHighlights(card,index){
 const sentence=sentences[index];if(!card||!sentence)return;
 const entries=inlineHighlightStore.list(currentEntry?.id||'').filter(entry=>entry.sentenceId===sentence.id);
 const enEl=card.querySelector('.en');
 if(enEl)enEl.innerHTML=renderEnglish(sentence,entries.map(entry=>({start:Number(entry.enStart),end:Number(entry.enEnd)})));
 card.querySelectorAll('.zh [data-zh-start][data-zh-end]').forEach(node=>{
  const start=Number(node.dataset.zhStart),end=Number(node.dataset.zhEnd);
  node.classList.toggle('phrase-mark-zh',entries.some(entry=>(entry.zhRanges||[]).some(range=>overlapsRange(start,end,Number(range.start),Number(range.end)))));
 });
}
function applyAllInlineHighlights(){listEl.querySelectorAll('.sentence-card').forEach(card=>applySentenceInlineHighlights(card,Number(card.dataset.index)));}
function currentPhraseBookYear(){return Number(phraseBookYear.value)||Number(currentEntry?.year)||inlineHighlightStore.years().at(-1)||2002;}
function updatePhraseBookButton(){phraseBookOpenButton.textContent='词群本';}
function setPhraseBookBlurred(year,blurred){
 inlineHighlightStore.setYearBlurred(year,blurred);
 phraseBookBackdrop.querySelector('.phrase-book-panel')?.classList.toggle('is-blurred',blurred);
 phraseBookBlurButton.setAttribute('aria-pressed',String(blurred));
 phraseBookBlurButton.textContent=blurred?'显示译文':'模糊译文';
}
function phraseEntryKey(entry){return [entry.articleId,entry.sentenceId,entry.enStart,entry.enEnd].join('|');}
function phraseBookArticleOrder(year){
 return (catalog?.articles||[]).filter(entry=>Number(entry.year)===Number(year)).map(entry=>entry.id);
}
function phraseBookSentenceOrderByArticle(){
 return currentEntry?.id?{[currentEntry.id]:sentences.map(sentence=>sentence.id)}:{};
}
function sortedPhraseBookEntries(year){
 const isArticle=phraseBookScope==='article';
 const visible=inlineHighlightStore.listYear(year).filter(entry=>!isArticle||entry.articleId===currentEntry?.id);
 return sortPhraseEntries(visible,{
  articleOrder:phraseBookArticleOrder(year),
  sentenceOrderByArticle:phraseBookSentenceOrderByArticle()
 });
}
function currentPlaybackPhraseTarget(entries){
 if(!(state.playing||state.paused)||!currentEntry)return null;
 const sentenceId=sentences[state.current]?.id;if(!sentenceId)return null;
 return findNearestPhraseEntry(entries,{
  articleId:currentEntry.id,
  sentenceId,
  sentenceOrder:sentences.map(sentence=>sentence.id)
 });
}
function scrollPhraseBookToEntry(entry){
 if(!entry)return false;const key=phraseEntryKey(entry);
 const item=[...phraseBookList.querySelectorAll('.phrase-book-item')].find(node=>node.dataset.phraseKey===key);
 if(!item)return false;
 item.scrollIntoView({behavior:'auto',block:'center',inline:'nearest'});return true;
}
function togglePhraseBookDetail(row,detail){
 if(phraseBookEditing||phraseBookQuickEditor)return;
 detail.hidden=!detail.hidden;row.setAttribute('aria-expanded',String(!detail.hidden));
}
function clearPhraseBookSpeakingState(){
 if(phraseBookSpeakingNode)phraseBookSpeakingNode.classList.remove('is-speaking');
 phraseBookSpeakingNode=null;
}
function stopPhraseBookAudio(){
 if(phraseBookPhraseAudio){
  try{phraseBookPhraseAudio.pause();phraseBookPhraseAudio.currentTime=0;}catch{}
  phraseBookPhraseAudio=null;
 }
 if(window.speechSynthesis){try{window.speechSynthesis.cancel();}catch{}}
 phraseBookSpeech=null;clearPhraseBookSpeakingState();
}
function phraseBookTts(text,node){
 if(!window.speechSynthesis||typeof window.SpeechSynthesisUtterance!=='function'){
  clearPhraseBookSpeakingState();showToast('当前设备不支持词群朗读');return false;
 }
 const utterance=new window.SpeechSynthesisUtterance(text);
 utterance.lang='en-US';utterance.rate=.94;utterance.pitch=1;
 try{
  const voices=window.speechSynthesis.getVoices?.()||[];
  const voice=voices.find(item=>String(item.lang||'').toLowerCase()==='en-us')||voices.find(item=>String(item.lang||'').toLowerCase().startsWith('en'));
  if(voice)utterance.voice=voice;
 }catch{}
 utterance.onend=()=>{if(phraseBookSpeech===utterance){phraseBookSpeech=null;clearPhraseBookSpeakingState();}};
 utterance.onerror=()=>{if(phraseBookSpeech===utterance){phraseBookSpeech=null;clearPhraseBookSpeakingState();showToast('词群朗读失败');}};
 phraseBookSpeech=utterance;window.speechSynthesis.speak(utterance);return true;
}
function phraseBookSentenceAudioMeta(entry){
 const sameArticle=entry.articleId===currentEntry?.id;
 const currentSentence=sameArticle?manifest.sentences?.[entry.sentenceId]:null;
 if(currentSentence){
  return {
   path:String(currentSentence.mp3_path||currentSentence.path||'').trim(),
   duration:Number(currentSentence.duration_seconds)||0
  };
 }
 const catalogEntry=(catalog?.articles||[]).find(item=>item.id===entry.articleId);
 const manifestPath=String(catalogEntry?.manifest||'');
 if(!catalogEntry||!manifestPath)return {path:'',duration:0};
 const base=manifestPath.replace(/manifest\.json(?:\?.*)?$/,'');
 const version=Number(catalogEntry.year)===2002?'v3':'v4';
 return {path:`${base}${version}-${entry.sentenceId}.mp3`,duration:0};
}
function phraseBookClipWindow(entry,duration){
 const source=String(entry.sourceSentence||'');
 const start=Math.max(0,Number(entry.enStart)||0),end=Math.max(start+1,Number(entry.enEnd)||start+1);
 const words=[...source.matchAll(/[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+(?:['’][A-Za-z]+)*)*/g)];
 if(!words.length||!Number.isFinite(duration)||duration<=0)return null;
 const selected=[];
 for(let i=0;i<words.length;i++){
  const left=Number(words[i].index)||0,right=left+words[i][0].length;
  if(right>start&&left<end)selected.push(i);
 }
 if(!selected.length)return null;
 const weights=words.map(word=>.8+Math.min(1.35,word[0].replace(/[^A-Za-z]/g,'').length*.085));
 const prefix=[0];for(const weight of weights)prefix.push(prefix.at(-1)+weight);
 const total=prefix.at(-1)||1;
 const first=selected[0],last=selected.at(-1)+1;
 const padBefore=.07,padAfter=.11;
 return {
  start:Math.max(0,duration*(prefix[first]/total)-padBefore),
  end:Math.min(duration,duration*(prefix[last]/total)+padAfter)
 };
}
function playPhraseBookSourceAudio(entry,node,text){
 const meta=phraseBookSentenceAudioMeta(entry);
 if(!meta.path||!meta.duration)return false;
 const clip=phraseBookClipWindow(entry,meta.duration);
 if(!clip||clip.end<=clip.start)return false;
 try{
  const fragment=`#t=${clip.start.toFixed(3)},${clip.end.toFixed(3)}`;
  const audio=new Audio(meta.path+fragment);phraseBookPhraseAudio=audio;
  audio.preload='auto';
  let stopped=false;
  const finish=()=>{
   if(stopped)return;stopped=true;
   try{audio.pause();}catch{}
   if(phraseBookPhraseAudio===audio)phraseBookPhraseAudio=null;
   clearPhraseBookSpeakingState();
  };
  const fallback=()=>{
   if(stopped)return;stopped=true;
   try{audio.pause();}catch{}
   if(phraseBookPhraseAudio===audio)phraseBookPhraseAudio=null;
   phraseBookTts(text,node);
  };
  audio.addEventListener('loadedmetadata',()=>{
   if(stopped)return;
   try{
    if(Math.abs((Number(audio.currentTime)||0)-clip.start)>.12)audio.currentTime=clip.start;
   }catch{}
  },{once:true});
  audio.addEventListener('timeupdate',()=>{if(!stopped&&Number(audio.currentTime)>=clip.end-.025)finish();});
  audio.addEventListener('ended',finish,{once:true});
  audio.addEventListener('error',fallback,{once:true});
  const started=audio.play();
  if(started?.catch)started.catch(fallback);
  return true;
 }catch{return false;}
}
function playPhraseBookEntry(entry,node){
 const text=String(entry.selectedText||node?.textContent||'').trim();if(!text)return;
 continuousPlayback.cancel();clearTimer();hybridAudioPlayer.stop();setPlaying(false,false);stopPhraseBookAudio();
 phraseBookSpeakingNode=node;node.classList.add('is-speaking');
 const directPath=String(entry.phraseAudioPath||entry.audioPath||entry.audioUrl||'').trim();
 if(directPath){
  try{
   const audio=new Audio(directPath);phraseBookPhraseAudio=audio;
   audio.onended=()=>{if(phraseBookPhraseAudio===audio){phraseBookPhraseAudio=null;clearPhraseBookSpeakingState();}};
   audio.onerror=()=>{if(phraseBookPhraseAudio===audio){phraseBookPhraseAudio=null;if(!playPhraseBookSourceAudio(entry,node,text))phraseBookTts(text,node);}};
   const started=audio.play();if(started?.catch)started.catch(()=>{if(phraseBookPhraseAudio===audio){phraseBookPhraseAudio=null;if(!playPhraseBookSourceAudio(entry,node,text))phraseBookTts(text,node);}});
   return;
  }catch{}
 }
 if(playPhraseBookSourceAudio(entry,node,text))return;
 phraseBookTts(text,node);
}
function selectPhraseBookText(node){
 try{
  const range=document.createRange();range.selectNodeContents(node);
  const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
 }catch{}
}
function finishQuickPhraseEdit({cancel=false,silent=false}={}){
 const active=phraseBookQuickEditor;if(!active)return false;
 phraseBookQuickEditor=null;
 const {node,entry,original,onBlur,onKeydown}=active;
 node.removeEventListener('blur',onBlur);node.removeEventListener('keydown',onKeydown);
 const typed=String(node.textContent||'').trim();
 const value=cancel?original:(typed||original);
 node.textContent=value;node.contentEditable='false';node.classList.remove('is-editing','is-quick-editing');node.removeAttribute('role');node.removeAttribute('aria-label');
 if(!cancel&&value!==original){
  inlineHighlightStore.add({...entry,studyGloss:value,glossSource:'user-edited'});
  phraseBookCloudSync.schedule();node.classList.add('has-translation','is-saved');
  window.clearTimeout(phraseBookSavedTimer);phraseBookSavedTimer=window.setTimeout(()=>node.classList.remove('is-saved'),900);
  if(!silent)showToast('词群释义已保存');
 }
 return true;
}
function beginQuickPhraseEdit(entry,node){
 if(phraseBookEditing){
  try{node.focus({preventScroll:true});}catch{node.focus();}
  selectPhraseBookText(node);return;
 }
 if(phraseBookQuickEditor?.node===node){selectPhraseBookText(node);return;}
 finishQuickPhraseEdit({silent:true});stopPhraseBookAudio();
 const original=String(node.textContent||'').trim();
 const onBlur=()=>finishQuickPhraseEdit();
 const onKeydown=event=>{
  if(event.key==='Enter'){event.preventDefault();node.blur();return;}
  if(event.key==='Escape'){event.preventDefault();finishQuickPhraseEdit({cancel:true});node.blur();}
 };
 phraseBookQuickEditor={node,entry,original,onBlur,onKeydown};
 node.contentEditable='true';node.spellcheck=false;node.classList.add('is-editing','is-quick-editing');node.setAttribute('role','textbox');node.setAttribute('aria-label',`${String(entry.selectedText||'词群')} 的中文释义`);
 node.addEventListener('blur',onBlur);node.addEventListener('keydown',onKeydown);
 try{node.focus({preventScroll:true});}catch{node.focus();}
 selectPhraseBookText(node);
}
function bindPhraseBookCellGestures(node,{single,double}){
 let tapTimer=null,lastTapAt=0;
 node.addEventListener('click',event=>{
  event.stopPropagation();
  if(node.getAttribute('contenteditable')==='true')return;
  event.preventDefault();
  const now=performance.now();
  if(lastTapAt&&now-lastTapAt<=340){
   lastTapAt=0;if(tapTimer!==null){window.clearTimeout(tapTimer);tapTimer=null;}
   window.getSelection()?.removeAllRanges();double();return;
  }
  lastTapAt=now;
  if(tapTimer!==null)window.clearTimeout(tapTimer);
  tapTimer=window.setTimeout(()=>{tapTimer=null;lastTapAt=0;single();},340);
 });
 node.addEventListener('dblclick',event=>{event.preventDefault();event.stopPropagation();});
}
function phraseBookItem(entry){
 const item=document.createElement('article');item.className='phrase-book-item';item.dataset.phraseKey=phraseEntryKey(entry);item.dataset.articleId=entry.articleId||'';item.dataset.sentenceId=entry.sentenceId||'';
 const row=document.createElement('div');row.className='phrase-book-row';row.setAttribute('role','button');row.tabIndex=0;row.setAttribute('aria-expanded','false');
 const en=document.createElement('span');en.className='phrase-book-en';en.textContent=entry.selectedText||entry.sourceSentence?.slice(entry.enStart,entry.enEnd)||'已标记词群';en.title='双击朗读词群';en.setAttribute('aria-label',`${en.textContent}，双击朗读`);
 const zh=document.createElement('span');zh.className='phrase-book-zh';zh.title='双击修改释义';
 const gloss=entry.studyGloss||entry.translationSnippet||'暂无中文释义';
 zh.textContent=phraseBookDrafts.get(phraseEntryKey(entry))?.value??gloss;
 if(entry.studyGloss||entry.translationSnippet)zh.classList.add('has-translation');
 if(entry.glossSource&&entry.glossSource!==entry.source)zh.title='系统生成学习释义；双击可修改';
 if(phraseBookEditing){
  zh.contentEditable='true';zh.spellcheck=false;zh.classList.add('is-editing');zh.setAttribute('role','textbox');zh.setAttribute('aria-label',`${en.textContent} 的中文释义`);
  zh.addEventListener('input',()=>phraseBookDrafts.set(phraseEntryKey(entry),{entry,value:zh.textContent.trim()}));
  zh.addEventListener('click',event=>event.stopPropagation());
 }
 row.append(en,zh);
 const detail=document.createElement('div');detail.className='phrase-book-detail';detail.hidden=true;
 const sourceEn=document.createElement('p');sourceEn.className='phrase-book-source-en';sourceEn.textContent=entry.sourceSentence||'';
 const sourceZh=document.createElement('p');sourceZh.className='phrase-book-source-zh';sourceZh.textContent=entry.sourceSentenceZh||'';
 const meta=document.createElement('div');meta.className='phrase-book-meta';
 const source=document.createElement('span');source.textContent=entry.articleTitle||entry.articleId||'';
 const remove=document.createElement('button');remove.className='phrase-book-delete';remove.type='button';remove.textContent='删除';
 remove.addEventListener('click',event=>{event.stopPropagation();finishQuickPhraseEdit({silent:true});inlineHighlightStore.remove(entry);phraseBookDrafts.delete(phraseEntryKey(entry));applyAllInlineHighlights();renderPhraseBook(currentPhraseBookYear());updatePhraseBookButton();phraseBookCloudSync.schedule();showToast('已删除标记');});
 meta.append(source,remove);detail.append(sourceEn,sourceZh,meta);
 const toggleDetail=()=>togglePhraseBookDetail(row,detail);
 bindPhraseBookCellGestures(en,{single:toggleDetail,double:()=>playPhraseBookEntry(entry,en)});
 bindPhraseBookCellGestures(zh,{single:toggleDetail,double:()=>beginQuickPhraseEdit(entry,zh)});
 row.addEventListener('click',event=>{if(phraseBookEditing||event.target.closest('[contenteditable="true"]'))return;toggleDetail();});
 row.addEventListener('keydown',event=>{if(phraseBookEditing||!['Enter',' '].includes(event.key))return;event.preventDefault();toggleDetail();});
 item.append(row,detail);return item;
}
function renderPhraseBook(year=currentPhraseBookYear(),{resetScroll=false}={}){
 if(phraseBookQuickEditor)finishQuickPhraseEdit({silent:true});
 const isArticle=phraseBookScope==='article';
 if(isArticle)year=Number(currentEntry?.year)||year;
 const years=[...new Set([...(catalog?.years||[]),...inlineHighlightStore.years(),year].map(Number).filter(Number.isFinite))].sort((a,b)=>a-b);
 phraseBookYear.replaceChildren(...years.map(value=>new Option(String(value),String(value))));
 phraseBookYear.value=String(year);
 phraseBookYear.disabled=phraseBookEditing||isArticle;
 phraseBookScopeSelect.value=phraseBookScope;phraseBookScopeSelect.disabled=phraseBookEditing;
 phraseBookContext.textContent=isArticle?`${year} · ${currentEntry?.title||'当前文章'}`:`${year} · 全年词群`;
 // Display order follows source position, never creation or edit time.
 const entries=sortedPhraseBookEntries(year);
 if(isArticle)phraseBookList.replaceChildren(...entries.map(phraseBookItem));
 else{
  const groups=new Map();
  for(const entry of entries){if(!groups.has(entry.articleId))groups.set(entry.articleId,[]);groups.get(entry.articleId).push(entry);}
  const catalogEntries=catalog?.articles||[];
  const order=new Map(catalogEntries.map((entry,index)=>[entry.id,index]));
  const sections=[...groups].sort(([a],[b])=>(order.get(a)??Infinity)-(order.get(b)??Infinity)||String(a).localeCompare(String(b))).map(([id,items])=>{
   const title=catalogEntries.find(entry=>entry.id===id)?.title||items[0].articleTitle||id||'未标明文章';
   const section=document.createElement('section');section.className='phrase-book-group';section.setAttribute('aria-label',title);
   const heading=document.createElement('h3');heading.textContent=title;
   section.append(heading,...items.map(phraseBookItem));return section;
  });
  phraseBookList.replaceChildren(...sections);
 }
 if(resetScroll)phraseBookList.scrollTop=0;
 phraseBookEmpty.hidden=entries.length>0;
 phraseBookEmpty.textContent=isArticle?'本篇还没有标记词群':'这一年还没有标记词群';
 setPhraseBookBlurred(year,inlineHighlightStore.getYearBlurred(year));
 return entries;
}
function setPhraseBookEditing(editing){
 phraseBookEditing=Boolean(editing);phraseBookEditButton.textContent=phraseBookEditing?'完成':'编辑';phraseBookEditButton.setAttribute('aria-pressed',String(phraseBookEditing));phraseBookYear.disabled=phraseBookEditing;
 renderPhraseBook(currentPhraseBookYear());
}
function togglePhraseBookEdit(){
 finishQuickPhraseEdit({silent:true});stopPhraseBookAudio();
 if(!phraseBookEditing){phraseBookDrafts.clear();setPhraseBookEditing(true);return;}
 savePhraseBookDrafts();setPhraseBookEditing(false);showToast('词群释义已保存');
}
function savePhraseBookDrafts(){
 const activeKeys=new Set(inlineHighlightStore.list().map(phraseEntryKey));
 for(const {entry,value} of phraseBookDrafts.values()){
  if(!value||!activeKeys.has(phraseEntryKey(entry)))continue;
  inlineHighlightStore.add({...entry,studyGloss:value,glossSource:'user-edited'});
 }
 if(phraseBookDrafts.size)phraseBookCloudSync.schedule();
 phraseBookDrafts.clear();
}
function followPhraseBookArticle(){
 // An automatic playback handoff must not discard a translation being edited.
 finishQuickPhraseEdit({silent:true});stopPhraseBookAudio();
 if(phraseBookEditing)savePhraseBookDrafts();
 phraseBookEditing=false;phraseBookEditButton.textContent='编辑';phraseBookEditButton.setAttribute('aria-pressed','false');
 phraseBookScope='article';renderPhraseBook(Number(currentEntry?.year),{resetScroll:true});
}
function openPhraseBook(){
 if(!phraseBookBackdrop.hidden)return;
 hidePhraseHighlightAction();window.getSelection()?.removeAllRanges();
 const hasPlaybackContext=Boolean((state.playing||state.paused)&&currentEntry&&sentences[state.current]);
 if(hasPlaybackContext)phraseBookScope='article';
 const year=phraseBookScope==='year'?currentPhraseBookYear():(Number(currentEntry?.year)||Number(yearSelect.value)||2002);
 phraseBookEditing=false;phraseBookDrafts.clear();phraseBookEditButton.textContent='编辑';phraseBookEditButton.setAttribute('aria-pressed','false');phraseBookYear.disabled=false;
 phraseBookHistory.open();const entries=renderPhraseBook(year,{resetScroll:true});phraseBookBackdrop.hidden=false;document.body.classList.add('phrase-book-opened');phraseBookCloseButton.focus();
 if(hasPlaybackContext)scrollPhraseBookToEntry(currentPlaybackPhraseTarget(entries));
}
function closePhraseBookDirect(){finishQuickPhraseEdit({silent:true});stopPhraseBookAudio();phraseBookEditing=false;phraseBookDrafts.clear();phraseBookEditButton.textContent='编辑';phraseBookEditButton.setAttribute('aria-pressed','false');phraseBookYear.disabled=false;phraseBookBackdrop.hidden=true;document.body.classList.remove('phrase-book-opened');phraseBookOpenButton.focus();}
function closePhraseBook(){phraseBookHistory.requestClose();}

async function saveCurrentPhraseHighlight(){
 const snapshot=phraseHighlightSelection;if(!snapshot||loading||phraseHighlightSaving)return;
 // Trigger clipboard access immediately from the user's click for mobile/WebView reliability.
 const clipboardPromise=copyTextWithFallback(snapshot.text,{legacyCopy:legacyCopyPhraseText});
 const words=highlightWords(snapshot.sentence,snapshot.enEl);
 const semanticGroups=semanticMappings[snapshot.sentence.id]||[];
 const bilingualPairs=bilingualMappings[snapshot.sentence.id]||[];
 const linked=resolveLinkedHighlight({
  sentence:snapshot.sentence,selectionStart:snapshot.start,selectionEnd:snapshot.end,
  words,semanticGroups,bilingualPairs
 });
 const translationSnippet=snippetFromRanges(snapshot.sentence.zh,linked.zhRanges);
 const localGloss=translationSnippet?{text:'',source:'none'}:localStudyGloss({
  sentence:snapshot.sentence,selectionStart:snapshot.start,selectionEnd:snapshot.end,
  words,semanticGroups,bilingualPairs
 });
 let browserPromise=null;
 if(!translationSnippet)browserPromise=browserStudyGloss(snapshot.text);
 phraseHighlightSaving=true;phraseHighlightAction.disabled=true;const originalLabel=phraseHighlightAction.textContent;
 if(browserPromise)phraseHighlightAction.textContent='生成中文…';
 try{
  const browserGloss=browserPromise?await browserPromise:'';
  const studyGloss=translationSnippet||browserGloss||localGloss.text||snapshot.sentence.zh;
  const glossSource=translationSnippet?linked.source:(browserGloss?'browser-translator':(localGloss.source!=='none'?localGloss.source:'sentence-context-generated'));
  const result=inlineHighlightStore.add({
   year:Number(currentEntry?.year)||null,
   articleId:currentEntry?.id||article.article_id||'',
   articleTitle:currentEntry?.title||article.title||'',
   sentenceId:snapshot.sentence.id,
   selectedText:snapshot.text,
   translationSnippet,
   studyGloss,
   glossSource,
   sourceSentence:snapshot.sentence.en,
   sourceSentenceZh:snapshot.sentence.zh,
   enStart:linked.enStart,enEnd:linked.enEnd,zhRanges:linked.zhRanges,source:linked.source,createdAt:Date.now()
  });
  applySentenceInlineHighlights(snapshot.card,snapshot.index);updatePhraseBookButton();
  window.getSelection()?.removeAllRanges();hidePhraseHighlightAction();
  phraseBookCloudSync.schedule();
  const copied=await clipboardPromise;
  const saveMessage=result.added?(translationSnippet?'已加入词群本':'已加入词群本 · 已生成中文'):(result.updated?'词群释义已更新':'这个词群已经标记过');
  showToast(`${saveMessage} · ${copied?'已复制':'复制失败'}`);
 }finally{
  phraseHighlightSaving=false;phraseHighlightAction.disabled=false;phraseHighlightAction.textContent=originalLabel||'标记词群';
 }
}
const tapGuard=createTapGuard();
const tapArbiter=createTapArbiter({delay:300});
function renderSentences(){
 listEl.innerHTML=sentences.map((sentence,index)=>`<article class="sentence-card${index===state.current?' is-active':''}" data-index="${index}" data-translation-open="false">
  <span class="sentence-number" aria-hidden="true">${String(index+1).padStart(2,'0')}</span>
  <div class="sentence-content" role="button" tabindex="0" aria-expanded="false" aria-controls="translation-${sentence.id}" aria-label="第 ${index+1} 句，点击显示或收起译文">
   <div class="en" lang="en">${renderEnglish(sentence)}</div>
   <div class="zh" lang="zh-CN" id="translation-${sentence.id}" hidden>${renderChinese(sentence,bilingualMappings[sentence.id]||[],manifest.sentences?.[sentence.id]?.words?semanticMappings[sentence.id]||[]:[])}</div>
  </div>
 </article>`).join('');
 applyAllInlineHighlights();
}
function toggleTranslation(card){
 const zh=card.querySelector('.zh');
 zh.hidden=!zh.hidden;
 card.dataset.translationOpen=String(!zh.hidden);
 card.querySelector('.sentence-content').setAttribute('aria-expanded',String(!zh.hidden));
}
function setPlaying(playing,paused=false){
 state.playing=playing;state.paused=paused;
 playButton.dataset.playing=String(playing);
 playButton.setAttribute('aria-label',playing?'暂停':'播放');
 const label=playButton.querySelector('.control-label');if(label)label.textContent=playing?'暂停':'播放';
}
function primarySegment(sentence){return sentence.segments[0]||{emotion:'neutral',intensity:0};}
function setSentenceProgressBar(card,currentTime,duration,ended=false){
 const progress=ended?1:(duration>0?Math.max(0,Math.min(1,currentTime/duration)):0);
 card.style.setProperty('--sentence-progress',`${progress*100}%`);
}
function clearReadClasses(card){card.querySelectorAll('.read-token,.semantic-group').forEach(token=>token.classList.remove('is-read','is-reading'));}
function paintLegacyReadProgress(index,progress){
 const card=listEl.querySelector(`.sentence-card[data-index="${index}"]`);if(!card)return;
 for(const line of card.querySelectorAll('.en,.zh')){
  const tokens=[...line.querySelectorAll('.read-token')];
  const read=Math.max(0,Math.min(tokens.length,Math.floor(progress*tokens.length+1e-6)));
  tokens.forEach((token,i)=>{token.classList.toggle('is-read',i<read);token.classList.toggle('is-reading',i===read&&progress<1);});
 }
 card.style.setProperty('--sentence-progress',`${Math.max(0,Math.min(1,progress))*100}%`);
}
function timedSemanticGroups(sentenceId,words){
 const groups=semanticMappings[sentenceId]||[];const timed=[];
 for(const group of groups){
  const start=Number(group.en_word_start),end=Number(group.en_word_end);
  if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<=start||end>words.length)return [];
  timed.push({...group,start:Number(words[start].start),end:Number(words[end-1].end)});
 }
 return timed;
}
function paintTimedReadProgress(index,words,currentTime,duration,ended=false){
 const card=listEl.querySelector(`.sentence-card[data-index="${index}"]`);if(!card)return;
 const tokens=[...card.querySelectorAll('.en .read-token')];
 const sourceMatches=tokens.length===words.length&&tokens.every((token,i)=>Number(token.dataset.charStart)===Number(words[i].char_start)&&Number(token.dataset.charEnd)===Number(words[i].char_end));
 if(sourceMatches){
  const readState=ended?{readThrough:words.length,active:-1}:readStateAtTime(words,currentTime);
  tokens.forEach((token,i)=>{token.classList.toggle('is-read',i<readState.readThrough);token.classList.toggle('is-reading',i===readState.active);});
 }else tokens.forEach(token=>token.classList.remove('is-read','is-reading'));
 const groups=timedSemanticGroups(sentences[index]?.id,words);const active=new Set(ended?[]:activeChineseGroups(groups,currentTime));
 [...card.querySelectorAll('.zh .semantic-group')].forEach((node,i)=>{const group=groups[i];const read=Boolean(group)&&(ended||Number(group.end)<=currentTime);node.classList.toggle('is-read',read);node.classList.toggle('is-reading',Boolean(group)&&active.has(i));});
 setSentenceProgressBar(card,currentTime,duration,ended);
}
function timingVersion(segment){return segment?.c_mode_version||manifest?.c_mode_version||segment?.render_version||manifest?.render_version||'';}
function paintPlaybackProgress(index,segment,currentTime,duration,ended=false){
 if(Array.isArray(segment?.words)&&segment.words.length){paintTimedReadProgress(index,segment.words,currentTime,duration,ended);return;}
 if(isExplicitLegacyTimingVersion(timingVersion(segment))){paintLegacyReadProgress(index,ended?1:progressFromUpdate(segment,currentTime,duration));return;}
 const card=listEl.querySelector(`.sentence-card[data-index="${index}"]`);if(card){clearReadClasses(card);setSentenceProgressBar(card,currentTime,duration,ended);}
}
function markSentenceComplete(index){const card=listEl.querySelector(`.sentence-card[data-index="${index}"]`);if(!card)return;card.querySelectorAll('.read-token,.semantic-group').forEach(node=>{node.classList.add('is-read');node.classList.remove('is-reading');});card.style.setProperty('--sentence-progress','100%');}
function resetSentenceProgress(index){const card=listEl.querySelector(`.sentence-card[data-index="${index}"]`);if(card){clearReadClasses(card);card.style.setProperty('--sentence-progress','0%');}}
function resetOtherProgress(active){document.querySelectorAll('.sentence-card').forEach((card,i)=>{if(i!==active){card.style.removeProperty('--sentence-progress');clearReadClasses(card);}});}
function updateActive(scroll=true){
 if(!sentences.length)return;const cards=[...document.querySelectorAll('.sentence-card')];cards.forEach((card,index)=>card.classList.toggle('is-active',index===state.current));
 const seg=primarySegment(sentences[state.current]);positionEl.textContent=`${String(state.current+1).padStart(2,'0')} / ${sentences.length}`;moodEl.textContent=`${emotionLabels[seg.emotion]||seg.emotion} · ${seg.intensity}`;document.body.dataset.mood=seg.emotion;
 if(scroll&&!hasSelectedText()&&!tapGuard.active&&cards[state.current]){state.programmaticScrollUntil=performance.now()+900;cards[state.current].scrollIntoView({behavior:'smooth',block:'center'});}
}
function clearTimer(){if(state.timer)window.clearTimeout(state.timer);state.timer=null;}
function progressFromUpdate(segment,currentTime,duration){
 const cues=segment?.cues;if(Array.isArray(cues)&&cues.length){let cueIndex=cues.findIndex(c=>currentTime<c.end);if(cueIndex<0)cueIndex=cues.length-1;const cue=cues[cueIndex];return sentenceProgress(cues,cueIndex,Math.max(0,currentTime-cue.start));}
 return duration>0?Math.max(0,Math.min(1,currentTime/duration)):0;
}
function queueForSentence(index){const sentence=sentences[index];if(!sentence)return[];return buildSentenceQueue(sentence,manifest).map(item=>({...item,path:!supportsOpus&&item.mp3_path?item.mp3_path:item.path}));}
function queueForBundle(bundle){
 const warm=[];
 for(const sentence of bundle?.content?.sentences||[]){
  warm.push(...buildSentenceQueue(sentence,bundle.manifest||{segments:{}}).map(item=>({...item,path:!supportsOpus&&item.mp3_path?item.mp3_path:item.path})));
 }
 return warm;
}
function onPlayerSegmentStart(segment){
 if(state.playRequestedAt!==null){measureLatency('audio-start',state.playRequestedAt);state.playRequestedAt=null;}
 setPlaying(true,false);statusEl.textContent=`演员 ${segment.actor_id||primarySegment(sentences[state.current]).actor_id} · ${emotionLabels[segment.emotion||primarySegment(sentences[state.current]).emotion]||segment.emotion||'自然讲述'}`;
}
function onPlayerTimeUpdate({segment,currentTime,duration,ended}){paintPlaybackProgress(state.current,segment,currentTime,duration,Boolean(ended));}
function onPlayerSentenceEnd(){
 if(loading||!state.playing)return;
 markSentenceComplete(state.current);
 if(state.current<sentences.length-1)speak(state.current+1);
 else void continuousPlayback.finishArticle();
}
function onPlayerError(){setPlaying(false,false);statusEl.textContent='音频暂时不可用';showToast('这句音频尚未生成或加载失败');}
const fallbackAudioPlayer=createAudioPlayer({
 createAudio:src=>new Audio(src),
 resolveAudio:item=>audioCache.resolve(item),
 onSegmentStart:onPlayerSegmentStart,
 onTimeUpdate:onPlayerTimeUpdate,
 onSentenceEnd:onPlayerSentenceEnd,
 onError:onPlayerError
});
function ensureWebAudio(){
 if(webAudioPlayer)return webAudioPlayer;
 const Ctor=window.AudioContext||window.webkitAudioContext;if(!Ctor)return null;
 try{
  audioContext=new Ctor({latencyHint:'interactive'});
  decodedAudioStore=createDecodedAudioStore({audioContext,audioCache});
  webAudioPlayer=createWebAudioPlayer({audioContext,resolveDecoded:item=>decodedAudioStore.get(item,{articleId:currentEntry?.id||'unknown'}),onSegmentStart:onPlayerSegmentStart,onTimeUpdate:onPlayerTimeUpdate,onSentenceEnd:onPlayerSentenceEnd,onError:onPlayerError});
  return webAudioPlayer;
 }catch{return null;}
}
const hybridAudioPlayer=createHybridAudioPlayer({getWebPlayer:ensureWebAudio,fallbackPlayer:fallbackAudioPlayer});
const continuousPlayback=createContinuousPlayback({
 enabled:continuousEnabled,
 getNext:()=>catalog&&currentEntry?adjacentArticle(catalog,currentEntry.id,1):null,
 open:entry=>{syncArticleSelectors(entry);return openArticle(entry,{automatic:true});},
 play:()=>speak(0),
 onWaiting:()=>{setPlaying(true,false);playButton.disabled=false;statusEl.textContent='正在接播下一篇…';},
 onStop:reason=>{
  setPlaying(false,false);
  statusEl.textContent=reason==='end'?'全部文章读完了 ✓':reason==='failed'?'下一篇加载失败，请重试':'这一篇读完了 ✓';
  if(reason==='failed')showToast('下一篇加载失败，请重新选择文章');
 }
});
function prepareAudio(warm,articleId=currentEntry?.id||'unknown'){
 if(!warm.length)return;
 const web=ensureWebAudio();
 if(web&&decodedAudioStore){void decodedAudioStore.preload(warm,{articleId});}
 else audioCache.warm(warm);
}
function warmRange(startIndex,count=4){
 const warm=[];const start=Math.max(0,startIndex);const end=Math.min(sentences.length,start+count);
 for(let i=start;i<end;i++)warm.push(...queueForSentence(i));
 prepareAudio(warm);
}
function warmVisibleSentences(){
 if(loading||!sentences.length)return;const cards=[...listEl.querySelectorAll('.sentence-card')];const viewportHeight=window.innerHeight||document.documentElement.clientHeight||0;
 const visible=cards.filter(card=>{const rect=card.getBoundingClientRect();return rect.bottom>=0&&rect.top<=viewportHeight;}).map(card=>Number(card.dataset.index)).filter(Number.isFinite);
 if(!visible.length)return;const start=Math.max(0,Math.min(...visible)-1);const end=Math.min(sentences.length-1,Math.max(...visible)+2);const warm=[];
 for(let i=start;i<=end;i++)warm.push(...queueForSentence(i));prepareAudio(warm);
}
function warmArticleRemainder(){
 const work=()=>{const warm=[];for(let i=4;i<sentences.length;i++)warm.push(...queueForSentence(i));prepareAudio(warm);};
 if('requestIdleCallback' in window)window.requestIdleCallback(work,{timeout:1200});else window.setTimeout(work,0);
}
async function warmAdjacentArticles(entry,selectionToken){
 if(!catalog||!decodedAudioStore||selectionToken!==selectionGeneration)return;
 const neighbors=[adjacentArticle(catalog,entry.id,-1),adjacentArticle(catalog,entry.id,1)].filter(Boolean);
 for(const neighbor of neighbors){
  if(selectionToken!==selectionGeneration)return;
  try{
   const bundle=await articleBundleStore.get(neighbor);if(selectionToken!==selectionGeneration)return;
   prepareAudio(queueForBundle(bundle),neighbor.id);
  }catch{}
 }
}
function scheduleAdjacentWarm(entry,selectionToken){
 const work=()=>{void warmAdjacentArticles(entry,selectionToken);};
 if('requestIdleCallback' in window)window.requestIdleCallback(work,{timeout:1800});else window.setTimeout(work,120);
}
function speak(index,{scroll=true}={}){
 if(loading||!sentences.length)return;clearTimer();hybridAudioPlayer.stop();state.current=nextSentenceIndex(index,0,sentences.length);resetOtherProgress(state.current);resetSentenceProgress(state.current);updateActive(scroll);
 const queue=queueForSentence(state.current);if(queue.length===0||queue.some(item=>!item.path)){setPlaying(false,false);statusEl.textContent='音频尚未生成';showToast('这句音频尚未生成');return;}
 setPlaying(true,false);state.playRequestedAt=performance.now();void hybridAudioPlayer.playSentence(queue,state.speed);warmRange(state.current+1,3);
}
function togglePlay(){
 if(continuousPlayback.isPending()){
  continuousPlayback.cancel();setPlaying(false,false);playButton.disabled=loading;statusEl.textContent='已暂停';return;
 }
 if(loading||!sentences.length)return;clearTimer();const playerState=hybridAudioPlayer.getState();
 if(playerState.playing||state.playing){
  if(playerState.playing)hybridAudioPlayer.pause();else hybridAudioPlayer.stop();
  setPlaying(false,Boolean(playerState.playing));statusEl.textContent='已暂停';return;
 }
 if(state.paused&&playerState.paused){state.playRequestedAt=performance.now();Promise.resolve(hybridAudioPlayer.resume()).catch(()=>{setPlaying(false,false);statusEl.textContent='音频暂时不可用';});setPlaying(true,false);statusEl.textContent='继续朗读';return;}
 speak(state.current,{scroll:false});
}
function showToast(message){toast.textContent=message;toast.classList.add('show');window.clearTimeout(showToast.timer);showToast.timer=window.setTimeout(()=>toast.classList.remove('show'),1900);}
function applyPlayerVisibility(hidden){state.playerHidden=hidden;playerShell.classList.toggle('is-collapsed',hidden);playerShell.setAttribute('data-collapsed',String(hidden));}
function handleViewportScroll(){state.scrollFrame=null;if(performance.now()<state.programmaticScrollUntil){state.scrollAnchorY=Math.max(0,window.scrollY||0);return;}const result=resolvePlayerScroll({anchorY:state.scrollAnchorY,currentY:window.scrollY,hidden:state.playerHidden,threshold:24,topBoundary:8});state.scrollAnchorY=result.anchorY;if(result.hidden!==state.playerHidden)applyPlayerVisibility(result.hidden);warmVisibleSentences();}
function queueViewportScroll(){if(state.scrollFrame!==null)return;state.scrollFrame=window.requestAnimationFrame(handleViewportScroll);}
function syncArticleSelectors(entry){
 yearSelect.value=String(entry.year);sectionSelect.value='';
 const entries=selectArticles(catalog,entry.year,'');articleSelect.replaceChildren(...entries.map(item=>new Option(item.title,item.id)));articleSelect.value=entry.id;
}
function updateArticleNavState(){
 if(!catalog||!currentEntry)return;previousButton.disabled=!adjacentArticle(catalog,currentEntry.id,-1);nextButton.disabled=!adjacentArticle(catalog,currentEntry.id,1);
}
function moveArticle(delta){
 if(!catalog||!currentEntry||(loading&&!continuousPlayback.isPending()))return;
 const target=adjacentArticle(catalog,currentEntry.id,delta);
 if(!target){showToast(delta<0?'已经是第一篇':'已经是最后一篇');return;}
 syncArticleSelectors(target);openArticle(target);
}
document.addEventListener('selectionchange',schedulePhraseHighlightAction);
phraseHighlightAction.addEventListener('pointerdown',event=>{event.preventDefault();event.stopPropagation();});
phraseHighlightAction.addEventListener('pointerup',event=>{event.preventDefault();event.stopPropagation();saveCurrentPhraseHighlight();});
phraseHighlightAction.addEventListener('click',event=>{event.preventDefault();event.stopPropagation();if(event.detail===0)saveCurrentPhraseHighlight();});
phraseBookOpenButton.addEventListener('click',openPhraseBook);
phraseBookCloseButton.addEventListener('click',closePhraseBook);
phraseBookYear.addEventListener('change',()=>renderPhraseBook(Number(phraseBookYear.value),{resetScroll:true}));
phraseBookScopeSelect.addEventListener('change',()=>{
 phraseBookScope=phraseBookScopeSelect.value==='year'?'year':'article';renderPhraseBook(currentPhraseBookYear(),{resetScroll:true});
});
phraseBookBlurButton.addEventListener('click',()=>{const year=currentPhraseBookYear();setPhraseBookBlurred(year,!inlineHighlightStore.getYearBlurred(year));});
phraseBookEditButton.addEventListener('click',togglePhraseBookEdit);
phraseBookSyncCopy.addEventListener('click',async()=>{
 const key=phraseBookCloudSync.getKey();
 try{
  await navigator.clipboard.writeText(key);
  showToast('同步码已复制');
 }catch{
  window.prompt('复制这个同步码到另一台设备：',key);
 }
});
phraseBookSyncChange.addEventListener('click',()=>{
 const next=window.prompt('输入另一台设备的同步码。切换后会自动合并两边的词群本：','');
 if(next===null)return;
 try{
  phraseBookCloudSync.setKey(next);
  void phraseBookCloudSync.syncNow().then(result=>{
   showToast(result.ok?'词群本已合并':'当前离线，稍后会自动同步');
  });
 }catch{
  showToast('同步码格式不正确');
 }
});
phraseBookBackdrop.addEventListener('click',event=>{if(event.target===phraseBookBackdrop)closePhraseBook();});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!phraseBookBackdrop.hidden)closePhraseBook();});
window.addEventListener('popstate',()=>{phraseBookHistory.handlePopState();});

listEl.addEventListener('pointerdown',event=>{
 const card=event.target.closest('.sentence-card');if(!card||event.target.closest('button'))return;
 if(tapArbiter.isDoubleCandidate(card.dataset.index))event.preventDefault();
 tapGuard.down(event,card.dataset.index,hasSelectedText());
});
listEl.addEventListener('pointermove',event=>tapGuard.move(event),{passive:true});
listEl.addEventListener('pointerup',event=>{
 const card=event.target.closest('.sentence-card');if(!card||loading||event.target.closest('button'))return;
 tapGuard.up(event);
 if(!tapGuard.accept(card.dataset.index,hasSelectedText()))return;
 tapArbiter.tap(card.dataset.index,{
  single:()=>{if(!loading&&card.isConnected)toggleTranslation(card);},
  double:()=>{
   if(loading)return;
   window.getSelection()?.removeAllRanges();
   speak(Number(card.dataset.index),{scroll:false});
   applyPlayerVisibility(false);
   state.scrollAnchorY=Math.max(0,window.scrollY||0);
  }
 });
},{passive:true});
window.addEventListener('pointerup',event=>tapGuard.up(event),{passive:true});
window.addEventListener('pointercancel',()=>tapGuard.cancel(),{passive:true});
listEl.addEventListener('contextmenu',()=>{tapGuard.cancel();tapArbiter.cancel();},{passive:true});
listEl.addEventListener('click',event=>{
 const card=event.target.closest('.sentence-card');if(!card||loading)return;
 if(event.detail===0)toggleTranslation(card);
});
listEl.addEventListener('keydown',event=>{if(event.key!=='Enter'&&event.key!==' ')return;if(!event.target.matches('.sentence-content')||hasSelectedText())return;event.preventDefault();toggleTranslation(event.target.closest('.sentence-card'));});
playButton.addEventListener('click',togglePlay);
previousButton.addEventListener('click',()=>moveArticle(-1));
nextButton.addEventListener('click',()=>moveArticle(1));
playerShell.addEventListener('click',event=>{if(state.playerHidden&&!event.target.closest('button')){applyPlayerVisibility(false);state.scrollAnchorY=Math.max(0,window.scrollY||0);}});
vocabButton.addEventListener('click',()=>{state.showVocab=!state.showVocab;document.body.classList.toggle('hide-vocab',!state.showVocab);vocabButton.setAttribute('aria-checked',String(state.showVocab));});
continuousButton.addEventListener('click',()=>{
 continuousEnabled=!continuousEnabled;const wasPending=continuousPlayback.isPending();
 continuousPlayback.setEnabled(continuousEnabled);continuousButton.setAttribute('aria-checked',String(continuousEnabled));
 try{window.localStorage.setItem(continuousPreferenceKey,String(continuousEnabled));}catch{}
 if(wasPending&&!continuousEnabled){setPlaying(false,false);playButton.disabled=loading;}
 showToast(continuousEnabled?'已开启连续播放，播完自动接下一篇':'已关闭连续播放');
});
window.addEventListener('wheel',()=>{state.programmaticScrollUntil=0;},{passive:true});
window.addEventListener('touchmove',()=>{state.programmaticScrollUntil=0;},{passive:true});
window.addEventListener('scrollend',()=>{state.programmaticScrollUntil=0;state.scrollAnchorY=Math.max(0,window.scrollY||0);},{passive:true});
window.addEventListener('scroll',()=>{hidePhraseHighlightAction();queueViewportScroll();},{passive:true});
window.addEventListener('beforeunload',()=>{continuousPlayback.cancel();hybridAudioPlayer.stop();audioCache.clearMemory();decodedAudioStore?.clearDecoded();});

async function openArticle(entry,{automatic=false}={}){
 if(!automatic)continuousPlayback.cancel();
 if(!entry)return;hidePhraseHighlightAction();window.getSelection()?.removeAllRanges();const switchStarted=performance.now();const selectionToken=++selectionGeneration;tapGuard.cancel();tapArbiter.cancel();loading=true;clearTimer();hybridAudioPlayer.stop();fallbackAudioPlayer.clearPreload();audioCache.clearMemory();setPlaying(false,false);playButton.disabled=true;statusEl.textContent='正在加载正文';
 articleBundleStore.cancelLowPriorityWork();
 try{
  const [loaded,semantic]=await Promise.all([articleBundleStore.get(entry),semanticMapPromise]);if(!loaded||selectionToken!==selectionGeneration)return;
  const articleChanged=currentEntry?.id!==entry.id;
  currentEntry=entry;if(articleChanged)followPhraseBookArticle();
  const mapArticles=loaded.bilingual?.articles||{};bilingualMappings=mapArticles[loaded.content.article_id]||mapArticles[entry.id]||{};semanticMappings=semanticGroupsForYear(semantic,entry.year,loaded.content.article_id);({article,sentences}=loaded.content);manifest=loaded.manifest;
  state.current=0;loading=false;playButton.disabled=false;document.querySelector('#article-title').textContent=article.title;document.title=`${article.title} · ${entry.year} 英语精读`;listEl.setAttribute('aria-label',`${article.title} 双语精读`);
  const audioCount=sentences.filter(s=>manifest.sentences?.[s.id]?.path||s.segments.every(x=>manifest.segments?.[x.id]?.path)).length;
  statusEl.textContent=audioCount===sentences.length?'音频已就绪 · 双击句框可重播':'正文已就绪 · 音频生成中';
  history.replaceState(history.state,'',`#${entry.id}`);renderSentences();updatePhraseBookButton();updateActive(false);resetSentenceProgress(0);updateArticleNavState();applyPlayerVisibility(false);measureLatency('article-switch',switchStarted);warmRange(0,4);warmArticleRemainder();scheduleAdjacentWarm(entry,selectionToken);
  if(!globalArticlePreloadStarted&&catalog){globalArticlePreloadStarted=true;void articleBundleStore.preload(catalog.articles.filter(item=>item.id!==entry.id));}
  return true;
 }catch(error){if(selectionToken!==selectionGeneration)return false;loading=false;setPlaying(false,false);playButton.disabled=true;statusEl.textContent='正文加载失败';showToast('请重新选择文章或刷新页面');return false;}
}
function fillArticleOptions(preferred){
 const entries=selectArticles(catalog,yearSelect.value,sectionSelect.value);articleSelect.replaceChildren(...entries.map(entry=>new Option(entry.title,entry.id)));if(entries.some(x=>x.id===preferred))articleSelect.value=preferred;openArticle(pickArticle(catalog,articleSelect.value));
}
articleSelect.addEventListener('change',()=>openArticle(pickArticle(catalog,articleSelect.value)));
sectionSelect.addEventListener('change',()=>fillArticleOptions());
yearSelect.addEventListener('change',()=>fillArticleOptions());
try{
 const response=await fetch('./content/catalog.json',{cache:'no-cache'});if(!response.ok)throw new Error('catalog-load-failed');catalog=await response.json();yearSelect.replaceChildren(...catalog.years.map(year=>new Option(String(year),String(year))));const selected=pickArticle(catalog,location.hash.slice(1)||catalog.default_article);yearSelect.value=String(selected.year);fillArticleOptions(selected.id);
}catch(error){statusEl.textContent='目录加载失败';showToast('目录加载失败，请刷新页面重试');}
void phraseBookCloudSync.syncNow();
window.addEventListener('online',()=>{void phraseBookCloudSync.syncNow();});
