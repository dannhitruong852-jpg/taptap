const clamp = value => Math.min(1, Math.max(0, Number(value) || 0));

export function sentenceProgress(cues, cueIndex, cueTime) {
  if (!Array.isArray(cues) || cues.length === 0) return 0;
  const total = Number(cues.at(-1)?.end || 0);
  if (!(total > 0)) return 0;
  const cue = cues[Math.min(Math.max(Number(cueIndex) || 0, 0), cues.length - 1)];
  const absolute = Number(cue?.start || 0) + Math.max(0, Number(cueTime) || 0);
  return clamp(absolute / total);
}

export function progressStyle(progress) {
  const pct = Number((clamp(progress) * 100).toFixed(2));
  return `--read-progress:${pct}%`;
}
