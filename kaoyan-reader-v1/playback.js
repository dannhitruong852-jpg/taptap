const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

export function buildSentenceQueue(sentence, manifest) {
  return sentence.segments.map(segment => ({
    ...segment,
    ...manifest.segments[segment.id]
  }));
}

export function applySpeed(baseRate, userSpeed) {
  return Number(clamp(baseRate * userSpeed, 0.5, 2).toFixed(2));
}

export function nextSentenceIndex(index, delta, length) {
  if (length <= 0) return 0;
  return clamp(index + delta, 0, length - 1);
}
