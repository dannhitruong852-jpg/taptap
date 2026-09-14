import { buildSentenceQueue, nextSentenceIndex } from './playback.js';
import { createAudioPlayer } from './audio-player.js';
import { createAudioCache } from './audio-cache.js';
import { createDecodedAudioStore } from './decoded-audio-store.js';
import { createWebAudioPlayer } from './web-audio-player.js';
import { createHybridAudioPlayer } from './hybrid-audio-player.js';
import { sentenceProgress, isExplicitLegacyTimingVersion } from './progress.js';
import { readStateAtTime, activeChineseGroups } from './time-index.js';
import { renderEnglish, renderChinese } from './bilingual-text.js';
import { createTapGuard, attachSpeedControl } from './reader-controls.js';
import { resolvePlayerScroll } from './scroll-behavior.js';
import { pickArticle, selectArticles, adjacentArticle } from './catalog.js';
import { createArticleBundleStore } from './article-bundle-store.js';

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
const backgroundEl=document.querySelector('#article-background');
const playButton=document.querySelector('#play-toggle');
const previousButton=document.querySelector('#previous');
const nextButton=document.querySelector('#next');
const positionEl=document.querySelector('#player-position');
const moodEl=document.querySelector('#director-mood');
const statusEl=document.querySelector('#player-status');
const playerShell=document.querySelector('#player-shell');
const vocabButton=document.querySelector('#toggle-vocab');
const toast=document.querySelector('#toast');
const state={current:0,speed:1,playing:false,paused:false,showVocab:true,timer:null,playerHidden:false,programmaticScrollUntil:0,scrollAnchorY:Math.max(0,window.scrollY||0),scrollFrame:null};
const emotionLabels={neutral:'自然讲述',warm:'温暖讲解',lively:'轻快生动',serious:'严肃克制',curious:'好奇追问',ironic:'冷幽默',tense:'紧张转折',emotional:'情绪加强'};
function hasSelectedText(){return Boolean(window.getSelection()?.toString());}
const tapGuard=createTapGuard();
function renderSentences(){
 listEl.innerHTML=sentences.map((sentence,index)=>`<article class="sentence-card${index===state.current?' is-active':''}" data-index="${index}" data-translation-open="false">
  <button class="sentence-number sentence-play" type="button" aria-label="播放第 ${index+1} 句" title="播放本句"><span>${String(index+1).padStart(2,'0')}</span><span class="sentence-play-icon" aria-hidden="true">▶</span></button>
  <div class="sentence-content" role="button" tabindex="0" aria-expanded="false" aria-controls="translation-${sentence.id}" aria-label="第 ${index+1} 句，点击显示或收起译文">
   <div class="en" lang="en">${renderEnglish(sentence)}</div>
   <div class="zh" lang="zh-CN" id="translation-${sentence.id}" hidden>${renderChinese(sentence,bilingualMappings[sentence.id]||[],manifest.sentences?.[sentence.id]?.words?semanticMappings[sentence.id]||[]:[])}</div>
  </div>
 </article>`).join('');
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
function onPlayerSegmentStart(segment){setPlaying(true,false);statusEl.textContent=`演员 ${segment.actor_id||primarySegment(sentences[state.current]).actor_id} · ${emotionLabels[segment.emotion||primarySegment(sentences[state.current]).emotion]||segment.emotion||'自然讲述'}`;}
function onPlayerTimeUpdate({segment,currentTime,duration,ended}){paintPlaybackProgress(state.current,segment,currentTime,duration,Boolean(ended));}
function onPlayerSentenceEnd(){markSentenceComplete(state.current);if(state.current<sentences.length-1){speak(state.current+1);}else{setPlaying(false,false);statusEl.textContent='这一篇读完了 ✓';}}
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
function prepareAudio(warm){
 if(!warm.length)return;
 const web=ensureWebAudio();
 if(web&&decodedAudioStore){void decodedAudioStore.preload(warm,{articleId:currentEntry?.id||'unknown'});}
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
function speak(index,{scroll=true}={}){
 if(loading||!sentences.length)return;clearTimer();hybridAudioPlayer.stop();state.current=nextSentenceIndex(index,0,sentences.length);resetOtherProgress(state.current);resetSentenceProgress(state.current);updateActive(scroll);
 const queue=queueForSentence(state.current);if(queue.length===0||queue.some(item=>!item.path)){setPlaying(false,false);statusEl.textContent='音频尚未生成';showToast('这句音频尚未生成');return;}
 void hybridAudioPlayer.playSentence(queue,state.speed);warmRange(state.current+1,3);
}
function togglePlay(){
 if(loading||!sentences.length)return;clearTimer();const playerState=hybridAudioPlayer.getState();
 if(playerState.playing||state.playing){hybridAudioPlayer.pause();setPlaying(false,true);statusEl.textContent='已暂停';return;}
 if(state.paused&&playerState.paused){Promise.resolve(hybridAudioPlayer.resume()).catch(()=>{setPlaying(false,false);statusEl.textContent='音频暂时不可用';});setPlaying(true,false);statusEl.textContent='继续朗读';return;}
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
 if(loading||!catalog||!currentEntry)return;const target=adjacentArticle(catalog,currentEntry.id,delta);
 if(!target){showToast(delta<0?'已经是第一篇':'已经是最后一篇');return;}
 syncArticleSelectors(target);openArticle(target);
}
listEl.addEventListener('pointerdown',event=>{const card=event.target.closest('.sentence-card');if(card&&!event.target.closest('button'))tapGuard.down(event,card.dataset.index,hasSelectedText());},{passive:true});
listEl.addEventListener('pointermove',event=>tapGuard.move(event),{passive:true});
window.addEventListener('pointerup',event=>tapGuard.up(event),{passive:true});
window.addEventListener('pointercancel',()=>tapGuard.cancel(),{passive:true});
listEl.addEventListener('contextmenu',()=>tapGuard.cancel(),{passive:true});
listEl.addEventListener('click',event=>{
 const card=event.target.closest('.sentence-card');if(!card||loading)return;
 if(event.target.closest('.sentence-play')){speak(Number(card.dataset.index),{scroll:false});applyPlayerVisibility(false);state.scrollAnchorY=Math.max(0,window.scrollY||0);return;}
 if(event.detail>1)return;if(tapGuard.accept(card.dataset.index,hasSelectedText(),event.detail===0))toggleTranslation(card);
});
listEl.addEventListener('keydown',event=>{if(event.key!=='Enter'&&event.key!==' ')return;if(!event.target.matches('.sentence-content')||hasSelectedText())return;event.preventDefault();toggleTranslation(event.target.closest('.sentence-card'));});
playButton.addEventListener('click',togglePlay);
previousButton.addEventListener('click',()=>moveArticle(-1));
nextButton.addEventListener('click',()=>moveArticle(1));
playerShell.addEventListener('click',event=>{if(state.playerHidden&&!event.target.closest('button')){applyPlayerVisibility(false);state.scrollAnchorY=Math.max(0,window.scrollY||0);}});
attachSpeedControl(document.querySelector('#speed-control'),rate=>{state.speed=rate;hybridAudioPlayer.setPlaybackRate(rate);});
vocabButton.addEventListener('click',()=>{state.showVocab=!state.showVocab;document.body.classList.toggle('hide-vocab',!state.showVocab);vocabButton.setAttribute('aria-checked',String(state.showVocab));});
window.addEventListener('wheel',()=>{state.programmaticScrollUntil=0;},{passive:true});
window.addEventListener('touchmove',()=>{state.programmaticScrollUntil=0;},{passive:true});
window.addEventListener('scrollend',()=>{state.programmaticScrollUntil=0;state.scrollAnchorY=Math.max(0,window.scrollY||0);},{passive:true});
window.addEventListener('scroll',queueViewportScroll,{passive:true});
window.addEventListener('beforeunload',()=>{hybridAudioPlayer.stop();audioCache.clearMemory();decodedAudioStore?.clearDecoded();});

async function openArticle(entry){
 if(!entry)return;const selectionToken=++selectionGeneration;tapGuard.cancel();loading=true;clearTimer();hybridAudioPlayer.stop();fallbackAudioPlayer.clearPreload();audioCache.clearMemory();setPlaying(false,false);playButton.disabled=true;statusEl.textContent='正在加载正文';
 articleBundleStore.cancelLowPriorityWork();
 try{
  const [loaded,semantic]=await Promise.all([articleBundleStore.get(entry),semanticMapPromise]);if(!loaded||selectionToken!==selectionGeneration)return;
  currentEntry=entry;const mapArticles=loaded.bilingual?.articles||{};bilingualMappings=mapArticles[loaded.content.article_id]||mapArticles[entry.id]||{};semanticMappings=semantic?.articles?.[loaded.content.article_id]||{};({article,sentences}=loaded.content);manifest=loaded.manifest;
  state.current=0;loading=false;playButton.disabled=false;backgroundEl.textContent=article.background;document.querySelector('#article-title').textContent=article.title;document.querySelector('.year-chip').textContent=`${entry.year} · ${article.title.split(' · ')[0]}`;document.title=`${article.title} · ${entry.year} 英语精读`;listEl.setAttribute('aria-label',`${article.title} 双语精读`);
  const audioCount=sentences.filter(s=>manifest.sentences?.[s.id]?.path||s.segments.every(x=>manifest.segments?.[x.id]?.path)).length;const seamlessCount=sentences.filter(s=>manifest.sentences?.[s.id]?.path).length;
  document.querySelector('#content-status').textContent=`${sentences.length} 句中英对照 · 音频 ${audioCount}/${sentences.length} 句可播放${seamlessCount?` · C无缝 ${seamlessCount}/${sentences.length}`:''}`;
  statusEl.textContent=audioCount===sentences.length?'轻点查译文 · 点序号听本句':'正文已就绪 · 音频生成中';
  history.replaceState(null,'',`#${entry.id}`);renderSentences();updateActive(false);resetSentenceProgress(0);updateArticleNavState();applyPlayerVisibility(false);warmRange(0,4);warmArticleRemainder();
  if(!globalArticlePreloadStarted&&catalog){globalArticlePreloadStarted=true;void articleBundleStore.preload(catalog.articles.filter(item=>item.id!==entry.id));}
 }catch(error){if(selectionToken!==selectionGeneration)return;loading=false;statusEl.textContent='正文加载失败';showToast('请重新选择文章或刷新页面');}
}
function fillArticleOptions(preferred){
 const entries=selectArticles(catalog,yearSelect.value,sectionSelect.value);articleSelect.replaceChildren(...entries.map(entry=>new Option(entry.title,entry.id)));if(entries.some(x=>x.id===preferred))articleSelect.value=preferred;openArticle(pickArticle(catalog,articleSelect.value));
}
articleSelect.addEventListener('change',()=>openArticle(pickArticle(catalog,articleSelect.value)));
sectionSelect.addEventListener('change',()=>fillArticleOptions());
yearSelect.addEventListener('change',()=>fillArticleOptions());
try{
 const response=await fetch('./content/catalog.json',{cache:'no-cache'});if(!response.ok)throw new Error('catalog-load-failed');catalog=await response.json();yearSelect.replaceChildren(...catalog.years.map(year=>new Option(String(year),String(year))));const selected=pickArticle(catalog,location.hash.slice(1)||catalog.default_article);yearSelect.value=String(selected.year);fillArticleOptions(selected.id);
}catch(error){statusEl.textContent='目录加载失败';document.querySelector('#content-status').textContent='请刷新页面重试';}
