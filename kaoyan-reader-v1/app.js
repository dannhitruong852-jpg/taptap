import { buildSentenceQueue, nextSentenceIndex } from './playback.js';
import { createAudioPlayer } from './audio-player.js';
import { resolvePlayerScroll } from './scroll-behavior.js';

const [content, manifest] = await Promise.all([
  fetch('./content/2002/text1.json').then(r => { if (!r.ok) throw new Error('content-load-failed'); return r.json(); }),
  fetch('./audio/2002/text1/manifest.json').then(r => { if (!r.ok) throw new Error('manifest-load-failed'); return r.json(); })
]);

const { article, sentences } = content;
const listEl = document.querySelector('#sentence-list');
const backgroundEl = document.querySelector('#article-background');
const playButton = document.querySelector('#play-toggle');
const previousButton = document.querySelector('#previous');
const nextButton = document.querySelector('#next');
const replayButton = document.querySelector('#replay');
const positionEl = document.querySelector('#player-position');
const moodEl = document.querySelector('#director-mood');
const statusEl = document.querySelector('#player-status');
const progressEl = document.querySelector('#progress-fill');
const playerShell = document.querySelector('#player-shell');
const chineseButton = document.querySelector('#toggle-chinese');
const vocabButton = document.querySelector('#toggle-vocab');
const movieButton = document.querySelector('#movie-mode');
const speedButtons = [...document.querySelectorAll('[data-speed]')];
const toast = document.querySelector('#toast');

const state = { current:0, speed:1, playing:false, paused:false, showChinese:true, showVocab:true, movie:false, timer:null, playerHidden:false, scrollAnchorY:Math.max(0, window.scrollY || 0), scrollFrame:null };
backgroundEl.textContent = article.background;

const emotionLabels = {
  neutral:'平静自然', warm:'温暖讲解', lively:'轻快生动', serious:'严肃克制',
  curious:'好奇追问', ironic:'冷幽默', tense:'紧张转折', emotional:'情绪加强'
};

function escapeHtml(value){return value.replace(/[&<>\"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[char]));}
function escapeRegExp(value){return value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}
function markVocabulary(sentence){let html=escapeHtml(sentence.en);for(const item of [...(sentence.vocab||[])].sort((a,b)=>b.word.length-a.word.length)){const regex=new RegExp(`(${escapeRegExp(item.word)})`,'gi');html=html.replace(regex,`<span class="vocab" data-level="${item.level}" data-meaning="${escapeHtml(item.meaning)}">$1</span>`);}return html;}
function renderSentences(){listEl.innerHTML=sentences.map((sentence,index)=>`<article class="sentence-card${index===state.current?' is-active':''}" data-index="${index}" tabindex="0" aria-label="第 ${sentence.id} 句，点击朗读"><div class="sentence-number">${String(sentence.id).padStart(2,'0')}</div><div class="en">${markVocabulary(sentence)}</div><div class="zh">${escapeHtml(sentence.zh)}</div></article>`).join('');}
function setPlaying(playing,paused=false){state.playing=playing;state.paused=paused;playButton.textContent=playing?'❚❚':'▶';playButton.setAttribute('aria-label',playing?'暂停':'播放');}
function primarySegment(sentence){return sentence.segments[0] || { emotion:'neutral', intensity:0 };}
function updateActive(scroll=true){const cards=[...document.querySelectorAll('.sentence-card')];cards.forEach((card,index)=>card.classList.toggle('is-active',index===state.current));const sentence=sentences[state.current];const seg=primarySegment(sentence);positionEl.textContent=`${String(state.current+1).padStart(2,'0')} / ${sentences.length}`;moodEl.textContent=`${emotionLabels[seg.emotion]||seg.emotion} · ${seg.intensity}`;progressEl.style.width=`${((state.current+1)/sentences.length)*100}%`;document.body.dataset.mood=seg.emotion;if(scroll&&cards[state.current])cards[state.current].scrollIntoView({behavior:'smooth',block:'center'});}
function clearTimer(){if(state.timer)window.clearTimeout(state.timer);state.timer=null;}

const audioPlayer = createAudioPlayer({
  createAudio: src => new Audio(src),
  onSegmentStart: segment => {
    setPlaying(true,false);
    statusEl.textContent = `演员 ${segment.actor_id} · ${emotionLabels[segment.emotion]||segment.emotion}`;
  },
  onSentenceEnd: () => {
    if (state.current < sentences.length - 1) {
      state.timer = window.setTimeout(() => speak(state.current + 1), 260);
    } else {
      setPlaying(false,false);
      statusEl.textContent='这一篇读完了 ✓';
    }
  },
  onError: () => {
    setPlaying(false,false);
    statusEl.textContent='音频暂时不可用';
    showToast('这句音频尚未生成或加载失败');
  }
});

function speak(index,{scroll=true}={}){
  clearTimer();
  audioPlayer.stop();
  state.current=nextSentenceIndex(index,0,sentences.length);
  const sentence=sentences[state.current];
  updateActive(scroll);
  const queue=buildSentenceQueue(sentence,manifest);
  if(queue.length===0||queue.some(item=>!item.path)){
    setPlaying(false,false);
    statusEl.textContent='音频尚未生成';
    showToast('这句音频尚未生成');
    return;
  }
  audioPlayer.playSentence(queue,state.speed);
}

function togglePlay(){
  clearTimer();
  const playerState=audioPlayer.getState();
  if(playerState.playing){audioPlayer.pause();setPlaying(false,true);statusEl.textContent='已暂停';return;}
  if(state.paused&&playerState.paused){audioPlayer.resume();setPlaying(true,false);statusEl.textContent='继续朗读';return;}
  speak(state.current,{scroll:false});
}
function move(delta){speak(nextSentenceIndex(state.current,delta,sentences.length));}
function showToast(message){toast.textContent=message;toast.classList.add('show');window.clearTimeout(showToast.timer);showToast.timer=window.setTimeout(()=>toast.classList.remove('show'),1900);}
function applyPlayerVisibility(hidden){state.playerHidden=hidden;playerShell.classList.toggle('is-collapsed',hidden);playerShell.setAttribute('data-collapsed',String(hidden));}
function handleViewportScroll(){state.scrollFrame=null;const result=resolvePlayerScroll({anchorY:state.scrollAnchorY,currentY:window.scrollY,hidden:state.playerHidden,threshold:24,topBoundary:8});state.scrollAnchorY=result.anchorY;if(result.hidden!==state.playerHidden)applyPlayerVisibility(result.hidden);}
function queueViewportScroll(){if(state.scrollFrame!==null)return;state.scrollFrame=window.requestAnimationFrame(handleViewportScroll);}

listEl.addEventListener('click',event=>{const vocab=event.target.closest('.vocab');if(vocab&&state.showVocab){event.stopPropagation();showToast(`${vocab.textContent} · ${vocab.dataset.level}级 · ${vocab.dataset.meaning}`);return;}const card=event.target.closest('.sentence-card');if(card)speak(Number(card.dataset.index));});
listEl.addEventListener('keydown',event=>{if(event.key!=='Enter'&&event.key!==' ')return;const card=event.target.closest('.sentence-card');if(!card)return;event.preventDefault();speak(Number(card.dataset.index));});
playButton.addEventListener('click',togglePlay);previousButton.addEventListener('click',()=>move(-1));nextButton.addEventListener('click',()=>move(1));replayButton.addEventListener('click',()=>speak(state.current));
playerShell.addEventListener('click',event=>{if(state.playerHidden&&!event.target.closest('button')){applyPlayerVisibility(false);state.scrollAnchorY=Math.max(0,window.scrollY||0);}});
speedButtons.forEach(button=>button.addEventListener('click',()=>{state.speed=Number(button.dataset.speed);speedButtons.forEach(item=>item.classList.toggle('is-active',item===button));audioPlayer.setPlaybackRate(state.speed);showToast(`朗读速度 ${button.textContent}`);}));
chineseButton.addEventListener('click',()=>{state.showChinese=!state.showChinese;document.body.classList.toggle('hide-chinese',!state.showChinese);chineseButton.classList.toggle('is-on',state.showChinese);chineseButton.setAttribute('aria-pressed',String(state.showChinese));chineseButton.textContent=`中译 · ${state.showChinese?'开':'关'}`;});
vocabButton.addEventListener('click',()=>{state.showVocab=!state.showVocab;document.body.classList.toggle('hide-vocab',!state.showVocab);vocabButton.classList.toggle('is-on',state.showVocab);vocabButton.setAttribute('aria-pressed',String(state.showVocab));vocabButton.textContent=`难词 6+ · ${state.showVocab?'开':'关'}`;});
movieButton.addEventListener('click',()=>{state.movie=!state.movie;document.body.classList.toggle('movie',state.movie);movieButton.classList.toggle('is-on',state.movie);movieButton.setAttribute('aria-pressed',String(state.movie));movieButton.textContent=state.movie?'退出沉浸':'🎞 沉浸模式';if(state.movie)showToast('中文暂时隐藏，只听英文');});
window.addEventListener('scroll',queueViewportScroll,{passive:true});
window.addEventListener('beforeunload',()=>audioPlayer.stop());
renderSentences();
updateActive(false);
statusEl.textContent='预生成音频 · 零运行时 TTS';
