const finite = value => Number.isFinite(Number(value)) ? Number(value) : 0;

export function activeWordIndex(words, currentTime) {
  if (!Array.isArray(words) || words.length === 0) return -1;
  const time = finite(currentTime);
  for (let i=0; i<words.length; i++) {
    const start=finite(words[i]?.start), end=finite(words[i]?.end);
    if (time >= start && time < end) return i;
  }
  return -1;
}

export function readStateAtTime(words, currentTime) {
  if (!Array.isArray(words) || words.length === 0) return {readThrough:0,active:-1};
  const time=finite(currentTime);
  const active=activeWordIndex(words,time);
  let readThrough=0;
  for (const word of words) {
    if (finite(word?.end) <= time) readThrough += 1;
    else break;
  }
  if (active >= 0) readThrough=Math.min(readThrough,active);
  return {readThrough,active};
}

export function activeChineseGroups(groups, currentTime) {
  if (!Array.isArray(groups)) return [];
  const time=finite(currentTime);
  const active=[];
  groups.forEach((group,index)=>{
    const start=finite(group?.start), end=finite(group?.end);
    if (end > start && time >= start && time < end) active.push(index);
  });
  return active;
}
