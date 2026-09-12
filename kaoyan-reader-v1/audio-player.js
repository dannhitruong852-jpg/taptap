export function createAudioPlayer({ createAudio, onSegmentStart = () => {}, onSentenceEnd = () => {}, onError = () => {} }) {
  let active = null;
  let queue = [];
  let index = -1;
  let speed = 1;
  let generation = 0;
  function detach(audio) {
    if (!audio) return;
    audio.onended = null;
    audio.onerror = null;
  }
  function playAt(nextIndex, currentGeneration) {
    if (currentGeneration !== generation) return;
    if (nextIndex >= queue.length) {active = null;onSentenceEnd();return;}
    index = nextIndex;
    const segment = queue[index];
    const audio = createAudio(segment.path);
    active = audio;audio.preload = 'auto';audio.playbackRate = speed;
    audio.onended = () => {
      if (currentGeneration !== generation) return;
      detach(audio);playAt(index + 1, currentGeneration);
    };
    audio.onerror = event => {
      if (currentGeneration !== generation) return;
      detach(audio);active = null;onError(event, segment);
    };
    onSegmentStart(segment, index);
    const playResult = audio.play();
    if (playResult?.catch) playResult.catch(error => { if (currentGeneration === generation && active === audio) onError(error, segment); });
  }
  function stop() {
    generation += 1;
    if (active) {active.pause();detach(active);}
    active = null;queue = [];index = -1;
  }
  return {
    playSentence(nextQueue, playbackRate = 1) {
      stop();queue = [...nextQueue];speed = playbackRate;
      const currentGeneration = generation;
      if (queue.length === 0) {onSentenceEnd();return;}
      playAt(0, currentGeneration);
    },
    pause() { active?.pause(); },
    resume() { return active?.play(); },
    stop,
    setPlaybackRate(rate) {speed = rate;if (active) active.playbackRate = rate;},
    getState() { return { index, playing: Boolean(active && !active.paused), paused: Boolean(active?.paused) }; }
  };
}
