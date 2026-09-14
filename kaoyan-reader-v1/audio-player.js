export function createAudioPlayer({ createAudio, resolveAudio = null, pinAudio = () => {}, unpinAudio = () => {}, onSegmentStart = () => {}, onTimeUpdate = () => {}, onSentenceEnd = () => {}, onError = () => {}, maxPreloadEntries = 12 }) {
  let active = null;
  let activeKey = null;
  let activeResolvedUnpin = null;
  let queue = [];
  let index = -1;
  let speed = 1;
  let generation = 0;
  const cache = new Map();

  function detach(audio) {
    if (!audio) return;
    audio.onended = null;
    audio.onerror = null;
    audio.ontimeupdate = null;
  }

  function releaseActiveKey() {
    if (activeResolvedUnpin) {
      try { activeResolvedUnpin(); } finally { activeResolvedUnpin = null; }
    }
    if (!activeKey) return;
    try { unpinAudio(activeKey); } finally { activeKey = null; }
  }

  function touch(path, audio) {
    if (cache.has(path)) cache.delete(path);
    cache.set(path, audio);
    while (cache.size > maxPreloadEntries) {
      const [oldestPath, oldestAudio] = cache.entries().next().value;
      if (oldestAudio === active && cache.size > 1) {
        cache.delete(oldestPath);
        cache.set(oldestPath, oldestAudio);
        continue;
      }
      cache.delete(oldestPath);
      if (oldestAudio !== active) {
        detach(oldestAudio);
        oldestAudio.pause?.();
        if ('src' in oldestAudio) oldestAudio.src = '';
      }
    }
  }

  function prepare(path) {
    if (!path) return null;
    const existing = cache.get(path);
    if (existing) {
      touch(path, existing);
      return existing;
    }
    const audio = createAudio(path);
    audio.preload = 'auto';
    audio.load?.();
    touch(path, audio);
    return audio;
  }

  function attachAndPlay(audio, segment, nextIndex, currentGeneration, resolved = null) {
    if (currentGeneration !== generation) return;
    index = nextIndex;
    active = audio;
    if (resolved?.local) {
      resolved.pin?.();
      activeResolvedUnpin = typeof resolved.unpin === 'function' ? resolved.unpin : null;
      if (resolved.key) {
        activeKey = resolved.key;
        pinAudio(activeKey);
      }
    }
    audio.playbackRate = speed;
    try { audio.currentTime = 0; } catch {}
    audio.ontimeupdate = () => {
      if (currentGeneration !== generation || active !== audio) return;
      const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : Number(segment.duration_seconds || 0);
      onTimeUpdate({ segment, index, currentTime: audio.currentTime || 0, duration });
    };
    audio.onended = () => {
      if (currentGeneration !== generation) return;
      onTimeUpdate({ segment, index, currentTime: Number(segment.duration_seconds || audio.duration || 0), duration: Number(segment.duration_seconds || audio.duration || 0), ended: true });
      detach(audio);releaseActiveKey();playAt(index + 1, currentGeneration);
    };
    audio.onerror = event => {
      if (currentGeneration !== generation) return;
      detach(audio);active=null;releaseActiveKey();cache.delete(segment.path);onError(event, segment);
    };
    onSegmentStart(segment, index);
    const playResult = audio.play();
    if (playResult?.catch) playResult.catch(error => {
      if (currentGeneration === generation && active === audio) {
        releaseActiveKey();onError(error, segment);
      }
    });
  }

  function playAt(nextIndex, currentGeneration) {
    if (currentGeneration !== generation) return;
    if (nextIndex >= queue.length) {active = null;releaseActiveKey();onSentenceEnd();return;}
    const segment = queue[nextIndex];
    if (!resolveAudio) {
      attachAndPlay(prepare(segment.path), segment, nextIndex, currentGeneration);
      return;
    }
    Promise.resolve(resolveAudio(segment)).then(resolved => {
      if (currentGeneration !== generation) return;
      const src = resolved?.src || segment.path;
      const audio = createAudio(src);
      audio.preload = 'auto';
      attachAndPlay(audio, segment, nextIndex, currentGeneration, resolved);
    }).catch(error => {
      if (currentGeneration === generation) onError(error, segment);
    });
  }

  function stop() {
    generation += 1;
    if (active) {active.pause();detach(active);}
    releaseActiveKey();
    active = null;queue=[];index=-1;
  }

  function clearPreload() {
    for (const audio of cache.values()) {
      if (audio !== active) {
        detach(audio);audio.pause?.();
        if ('src' in audio) audio.src='';
      }
    }
    if (active) {
      for (const [path,audio] of cache) if (audio !== active) cache.delete(path);
    } else cache.clear();
  }

  return {
    preload(nextQueue) { for (const item of nextQueue || []) if (item?.path) prepare(item.path); },
    clearPreload,
    playSentence(nextQueue, playbackRate = 1) {
      stop();queue=[...nextQueue];speed=playbackRate;
      const currentGeneration = generation;
      if (queue.length === 0) {onSentenceEnd();return;}
      playAt(0, currentGeneration);
    },
    pause() { active?.pause(); },
    resume() { return active?.play(); },
    stop,
    setPlaybackRate(rate) {speed=rate;if (active) active.playbackRate=rate;},
    getState() { return { index, playing:Boolean(active&&!active.paused), paused:Boolean(active?.paused), preloaded:cache.size }; }
  };
}
