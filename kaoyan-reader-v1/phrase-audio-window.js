const finite=value=>Number.isFinite(Number(value))?Number(value):null;

function overlap(start,end,left,right){return end>left&&start<right;}

export function alignedPhraseWindow(words,enStart,enEnd,duration){
  if(!Array.isArray(words)||!words.length)return null;
  const start=Math.max(0,Number(enStart)||0);
  const end=Math.max(start+1,Number(enEnd)||start+1);
  const selected=[];
  words.forEach((word,index)=>{
    const left=finite(word?.char_start),right=finite(word?.char_end);
    if(left===null||right===null||right<=left)return;
    if(overlap(start,end,left,right))selected.push(index);
  });
  if(!selected.length)return null;
  const firstIndex=selected[0],lastIndex=selected.at(-1);
  const first=words[firstIndex],last=words[lastIndex];
  const rawStart=finite(first?.start),rawEnd=finite(last?.end);
  const mediaDuration=finite(duration);
  if(rawStart===null||rawEnd===null||rawEnd<=rawStart)return null;

  const previous=firstIndex>0?words[firstIndex-1]:null;
  const next=lastIndex+1<words.length?words[lastIndex+1]:null;
  const previousEnd=finite(previous?.end);
  const nextStart=finite(next?.start);

  let clipStart=Math.max(0,rawStart-.045);
  let clipEnd=rawEnd+.070;
  if(previousEnd!==null&&previousEnd<rawStart){
    const midpoint=(previousEnd+rawStart)/2;
    clipStart=Math.max(midpoint,clipStart);
  }else if(previousEnd!==null){
    clipStart=Math.max(0,rawStart-.012);
  }
  if(nextStart!==null&&nextStart>rawEnd){
    const midpoint=(rawEnd+nextStart)/2;
    clipEnd=Math.min(midpoint,clipEnd);
  }else if(nextStart!==null){
    clipEnd=rawEnd+.018;
  }
  if(mediaDuration!==null&&mediaDuration>0)clipEnd=Math.min(mediaDuration,clipEnd);
  if(clipEnd<=clipStart+.04)return null;
  return {
    start:Math.round(clipStart*1000)/1000,
    end:Math.round(clipEnd*1000)/1000,
    firstWord:firstIndex,
    lastWord:lastIndex,
    source:'aligned'
  };
}

export function estimatedPhraseWindow(source,enStart,enEnd,duration){
  const mediaDuration=finite(duration);
  if(!mediaDuration||mediaDuration<=0)return null;
  const text=String(source||'');
  const start=Math.max(0,Number(enStart)||0),end=Math.max(start+1,Number(enEnd)||start+1);
  const words=[...text.matchAll(/[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+(?:['’][A-Za-z]+)*)*/g)];
  if(!words.length)return null;
  const selected=[];
  words.forEach((word,index)=>{
    const left=Number(word.index)||0,right=left+word[0].length;
    if(overlap(start,end,left,right))selected.push(index);
  });
  if(!selected.length)return null;
  const weights=words.map(word=>.8+Math.min(1.35,word[0].replace(/[^A-Za-z]/g,'').length*.085));
  const prefix=[0];for(const weight of weights)prefix.push(prefix.at(-1)+weight);
  const total=prefix.at(-1)||1,first=selected[0],last=selected.at(-1)+1;
  return {
    start:Math.max(0,mediaDuration*(prefix[first]/total)-.07),
    end:Math.min(mediaDuration,mediaDuration*(prefix[last]/total)+.11),
    firstWord:first,
    lastWord:last-1,
    source:'estimated'
  };
}
