import { buildSentenceQueue, nextSentenceIndex } from './playback.js';
import { createAudioPlayer } from './audio-player.js';
import { sentenceProgress } from './progress.js';
import { resolvePlayerScroll } from './scroll-behavior.js';
import { pickArticle, selectArticles, createSelectionLoader } from './catalog.js';

let article={}, sentences=[], manifest={segments:{}};
let catalog=null, loading=true;
const loadSelection=createSelectionLoader();
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
const replayButton=document.querySelector('#replay');
const positionEl=document.querySelector('#player-position');
const moodEl=document.querySelector('#director-mood');
const statusEl=document.querySelector('#player-status');
const progressEl=document.querySelector('#progress-fill');
const playerShell=document.querySelector('#player-shell');
const chineseButton=document.querySelector('#toggle-chinese');
const vocabButton=document.querySelector('#toggle-vocab');
const movieButton=document.querySelector('#movie-mode');
const speedButtons=[...document.querySelectorAll('[data-speed]')];
const toast=document.querySelector('#toast');
const state={current:0,speed:1,playing:false,paused:false,showChinese:true,showVocab:true,movie:false,timer:null,playerHidden:false,scrollAnchorY:Math.max(0,window.scrollY||0),scrollFrame:null,preloader:null};
const emotionLabels={neutral:'自然讲述',warm:'温暖讲解',lively:'轻快生动',serious:'严肃克制',curious:'好奇追问',ironic:'冷幽默',tense:'紧张转折',emotional:'情绪加强'};
function escapeHtml(value){return value.replace(/[&<>"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[char]));}
function timedEnglish(sentence){
  const out=[];let offset=0;
  for(const match of sentence.en.matchAll(/\S+\s*/g)){
    const raw=match[0], start=match.index, end=start+raw.trimEnd().length;
    const vocab=sentence.vocab?.find(v=>start<v.end&&end>v.start&&v.level>=6);
    const attrs=vocab?` vocab" data-level="${vocab.level}" data-meaning="${escapeHtml(vocab.meaning)}`:'"';
    out.push(`<span class="read-token${attrs}">${escapeHtml(raw)}</span>`);offset=end;
  }
  if(offset<sentence.en.length)out.push(escapeHtml(sentence.en.slice(offset)));
  return out.join('');
}
function timedChinese(sentence){return [...sentence.zh].map(char=>/\s/.test(char)?escapeHtml(char):`<span class="read-token">${escapeHtml(char)}</span>`).join('');}
function renderSentences(){listEl.innerHTML=sentences.map((sentence,index)=>`<article class="sentence-card${index===state.current?' is-active':''}" data-index="${index}" tabindex="0" aria-label="第 ${index+1} 句，点击朗读"><div class="sentence-number">${String(index+1).padStart(2,'0')}</div><div class="en">${timedEnglish(sentence)}</div><div class="zh">${timedChinese(sentence)}</div></article>`).join('');}
function setPlaying(playing,paused=false){state.playing=playing;state.paused=paused;playButton.textContent=playing?'❚❚':'▶';playButton.setAttribute('aria-label',playing?'暂停':'播放');}
function primarySegment(sentence){return sentence.segments[0]||{emotion:'neutral',intensity:0};}
function paintReadProgress(index,progress){
  const card=listEl.querySelector(`.sentence-card[data-index="${index}"]`);if(!card)return;
  for(const line of card.querySelectorAll('.en,.zh')){
    const tokens=[...line.querySelectorAll('.read-token')];const read=Math.max(0,Math.min(tokens.length,Math.floor(progress*tokens.length+1e-6)));
    tokens.forEach((token,i)=>{token.classList.toggle('is-read',i<read);token.classList.toggle('is-reading',i===read&&progress<1);});
  }
  card.style.setProperty('--sentence-progress',`${Math.max(0,Math.min(1,progress))*100}%`);
}
function resetOtherProgress(active){document.querySelectorAll('.sentence-card').forEach((card,i)=>{if(i!==active){card.style.removeProperty('--sentence-progress');card.querySelectorAll('.read-token').forEach(t=>t.classList.remove('is-read','is-reading'));}});}
function updateActive(scroll=true){if(!sentences.length)return;const cards=[...document.querySelectorAll('.sentence-card')];cards.forEach((card,index)=>card.classList.toggle('is-active',index===state.current));const seg=primarySegment(sentences[state.current]);positionEl.textContent=`${String(state.current+1).padStart(2,'0')} / ${sentences.length}`;moodEl.textContent=`${emotionLabels[seg.emotion]||seg.emotion} · ${seg.intensity}`;progressEl.style.width=`${((state.current+1)/sentences.length)*100}%`;document.body.dataset.mood=seg.emotion;if(scroll&&cards[state.current])cards[state.current].scrollIntoView({behavior:'smooth',block:'center'});}
function clearTimer(){if(state.timer)window.clearTimeout(state.timer);state.timer=null;}
function progressFromUpdate(segment,currentTime,duration){
  const cues=segment?.cues;
  if(Array.isArray(cues)&&cues.length){
    let cueIndex=cues.findIndex(c=>currentTime<c.end);if(cueIndex<0)cueIndex=cues.length-1;
    const cue=cues[cueIndex];return sentenceProgress(cues,cueIndex,Math.max(0,currentTime-cue.start));
  }
  return duration>0?Math.max(0,Math.min(1,currentTime/duration)):0;
}
function queueForSentence(index){
  const sentence=sentences[index];if(!sentence)return[];
  return buildSentenceQueue(sentence,manifest).map(item=>({...item,path:!supportsOpus&&item.mp3_path?item.mp3_path:item.path}));
}
function preloadNext(index){
  if(state.preloader){state.preloader.src='';state.preloader=null;}
  const next=queueForSentence(index+1)[0];if(!next?.path)return;
  const preload=new Audio();preload.preload='auto';preload.src=next.path;preload.load?.();state.preloader=preload;
}
const audioPlayer=createAudioPlayer({
 createAudio:src=>new Audio(src),
 onSegmentStart:segment=>{setPlaying(true,false);statusEl.textContent=`演员 ${segment.actor_id||primarySegment(sentences[state.current]).actor_id} · ${emotionLabels[segment.emotion||primarySegment(sentences[state.current]).emotion]||segment.emotion||'自然讲述'}`;},
 onTimeUpdate:({segment,currentTime,duration,ended})=>paintReadProgress(state.current,ended?1:progressFromUpdate(segment,currentTime,duration)),
 onSentenceEnd:()=>{paintReadProgress(state.current,1);if(state.current<sentences.length-1){speak(state.current+1);}else{setPlaying(false,false);statusEl.textContent='这一篇读完了 ✓';}},
 onError:()=>{setPlaying(false,false);statusEl.textContent='音频暂时不可用';showToast('这句音频尚未生成或加载失败');}
});
function speak(index,{scroll=true}={}){
 if(loading||!sentences.length)return;
 clearTimer();audioPlayer.stop();state.current=nextSentenceIndex(index,0,sentences.length);resetOtherProgress(state.current);paintReadProgress(state.current,0);
 const sentence=sentences[state.current];updateActive(scroll);
 const queue=queueForSentence(state.current);
 if(queue.length===0||queue.some(item=>!item.path)){setPlaying(false,false);statusEl.textContent='音频尚未生成';showToast('这句音频尚未生成');return;}
 audioPlayer.playSentence(queue,state.speed);preloadNext(state.current);
}
function togglePlay(){
 if(loading||!sentences.length)return;
 clearTimer();const playerState=audioPlayer.getState();
 if(playerState.playing||state.playing){audioPlayer.pause();setPlaying(false,true);statusEl.textContent='已暂停';return;}
 if(state.paused&&playerState.paused){Promise.resolve(audioPlayer.resume()).catch(()=>{setPlaying(false,false);statusEl.textContent='音频暂时不可用';});setPlaying(true,false);statusEl.textContent='继续朗读';return;}
 speak(state.current,{scroll:false});
}
function move(delta){if(loading)return;speak(nextSentenceIndex(state.current,delta,sentences.length));}
function showToast(message){toast.textContent=message;toast.classList.add('show');window.clearTimeout(showToast.timer);showToast.timer=window.setTimeout(()=>toast.classList.remove('show'),1900);}
function applyPlayerVisibility(hidden){state.playerHidden=hidden;playerShell.classList.toggle('is-collapsed',hidden);playerShell.setAttribute('data-collapsed',String(hidden));}
function handleViewportScroll(){state.scrollFrame=null;const result=resolvePlayerScroll({anchorY:state.scrollAnchorY,currentY:window.scrollY,hidden:state.playerHidden,threshold:24,topBoundary:8});state.scrollAnchorY=result.anchorY;if(result.hidden!==state.playerHidden)applyPlayerVisibility(result.hidden);}
function queueViewportScroll(){if(state.scrollFrame!==null)return;state.scrollFrame=window.requestAnimationFrame(handleViewportScroll);}
listEl.addEventListener('click',event=>{const vocab=event.target.closest('.vocab');if(vocab&&state.showVocab){event.stopPropagation();showToast(`${vocab.textContent.trim()} · ${vocab.dataset.level}级 · ${vocab.dataset.meaning}`);return;}const card=event.target.closest('.sentence-card');if(card)speak(Number(card.dataset.index));});
listEl.addEventListener('keydown',event=>{if(event.key!=='Enter'&&event.key!==' ')return;const card=event.target.closest('.sentence-card');if(!card)return;event.preventDefault();speak(Number(card.dataset.index));});
playButton.addEventListener('click',togglePlay);previousButton.addEventListener('click',()=>move(-1));nextButton.addEventListener('click',()=>move(1));replayButton.addEventListener('click',()=>speak(state.current));
playerShell.addEventListener('click',event=>{if(state.playerHidden&&!event.target.closest('button')){applyPlayerVisibility(false);state.scrollAnchorY=Math.max(0,window.scrollY||0);}});
speedButtons.forEach(button=>button.addEventListener('click',()=>{state.speed=Number(button.dataset.speed);speedButtons.forEach(item=>item.classList.toggle('is-active',item===button));audioPlayer.setPlaybackRate(state.speed);showToast(`朗读速度 ${button.textContent}`);}));
chineseButton.addEventListener('click',()=>{state.showChinese=!state.showChinese;document.body.classList.toggle('hide-chinese',!state.showChinese);chineseButton.classList.toggle('is-on',state.showChinese);chineseButton.setAttribute('aria-pressed',String(state.showChinese));chineseButton.textContent=`中译 · ${state.showChinese?'开':'关'}`;});
vocabButton.addEventListener('click',()=>{state.showVocab=!state.showVocab;document.body.classList.toggle('hide-vocab',!state.showVocab);vocabButton.classList.toggle('is-on',state.showVocab);vocabButton.setAttribute('aria-pressed',String(state.showVocab));vocabButton.textContent=`难词 6+ · ${state.showVocab?'开':'关'}`;});
movieButton.addEventListener('click',()=>{state.movie=!state.movie;document.body.classList.toggle('movie',state.movie);movieButton.classList.toggle('is-on',state.movie);movieButton.setAttribute('aria-pressed',String(state.movie));movieButton.textContent=state.movie?'退出沉浸':'🎞 沉浸模式';if(state.movie)showToast('中文暂时隐藏，只听英文');});
window.addEventListener('scroll',queueViewportScroll,{passive:true});
window.addEventListener('beforeunload',()=>audioPlayer.stop());

async function openArticle(entry){
 if(!entry)return;
 loading=true;clearTimer();audioPlayer.stop();setPlaying(false,false);playButton.disabled=true;statusEl.textContent='正在加载正文';
 try{
  const loaded=await loadSelection(entry);if(!loaded)return;
  ({article,sentences}=loaded.content);manifest=loaded.manifest;
  state.current=0;loading=false;playButton.disabled=false;
  backgroundEl.textContent=article.background;
  document.querySelector('#article-title').textContent=article.title;
  document.querySelector('.year-chip').textContent=`2002 · ${article.title.split(' · ')[0]}`;
  document.title=`${article.title} · 2002 英语精读`;
  listEl.setAttribute('aria-label',`${article.title} 双语精读`);
  const audioCount=sentences.filter(s=>manifest.sentences?.[s.id]?.path||s.segments.every(x=>manifest.segments?.[x.id]?.path)).length;
  const seamlessCount=sentences.filter(s=>manifest.sentences?.[s.id]?.path).length;
  document.querySelector('#content-status').textContent=`${sentences.length} 句中英对照 · 音频 ${audioCount}/${sentences.length} 句可播放${seamlessCount?` · C v2无缝 ${seamlessCount}/${sentences.length}`:''}`;
  statusEl.textContent=audioCount===sentences.length?'静态音频 · 点句播放':'正文已就绪 · 音频生成中';
  history.replaceState(null,'',`#${entry.id}`);renderSentences();updateActive(false);paintReadProgress(0,0);applyPlayerVisibility(false);
 }catch(error){loading=false;statusEl.textContent='正文加载失败';showToast('请重新选择文章或刷新页面');}
}
function fillArticleOptions(preferred){
 const entries=selectArticles(catalog,yearSelect.value,sectionSelect.value);
 articleSelect.replaceChildren(...entries.map(entry=>new Option(entry.title,entry.id)));
 if(entries.some(x=>x.id===preferred))articleSelect.value=preferred;
 openArticle(pickArticle(catalog,articleSelect.value));
}
articleSelect.addEventListener('change',()=>openArticle(pickArticle(catalog,articleSelect.value)));
sectionSelect.addEventListener('change',()=>fillArticleOptions());
yearSelect.addEventListener('change',()=>fillArticleOptions());
try{
 const response=await fetch('./content/catalog.json',{cache:'no-cache'});
 if(!response.ok)throw new Error('catalog-load-failed');
 catalog=await response.json();yearSelect.replaceChildren(...catalog.years.map(year=>new Option(String(year),String(year))));
 const selected=pickArticle(catalog,location.hash.slice(1)||catalog.default_article);
 yearSelect.value=String(selected.year);fillArticleOptions(selected.id);
}catch(error){statusEl.textContent='目录加载失败';document.querySelector('#content-status').textContent='请刷新页面重试';}
