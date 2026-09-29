const finite=value=>Number.isFinite(Number(value))?Number(value):null;
const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
const roundMs=value=>Math.round(value*1000)/1000;

function overlap(start,end,left,right){return end>left&&start<right;}
function percentile(values,q){
  const list=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!list.length)return 0;
  const index=clamp((list.length-1)*q,0,list.length-1);
  const low=Math.floor(index),high=Math.ceil(index),mix=index-low;
  return list[low]*(1-mix)+list[high]*mix;
}

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
  const durationLimit=mediaDuration!==null&&mediaDuration>0?mediaDuration:Infinity;
  const startFloor=Math.max(0,rawStart-.16,previousEnd!==null&&previousEnd<rawStart?previousEnd:0);
  const endCeiling=Math.min(durationLimit,rawEnd+.16,nextStart!==null&&nextStart>rawEnd?nextStart:Infinity);

  let clipStart=Math.max(startFloor,rawStart-.09);
  let clipEnd=Math.min(endCeiling,rawEnd+.035);
  if(clipEnd<=clipStart+.04){
    clipStart=Math.max(0,rawStart-.05);
    clipEnd=Math.min(durationLimit,Math.max(rawEnd+.02,clipStart+.04));
  }
  return {
    start:roundMs(clipStart),
    end:roundMs(clipEnd),
    rawStart:roundMs(rawStart),
    rawEnd:roundMs(rawEnd),
    startFloor:roundMs(startFloor),
    endCeiling:Number.isFinite(endCeiling)?roundMs(endCeiling):null,
    previousEnd:previousEnd===null?null:roundMs(previousEnd),
    nextStart:nextStart===null?null:roundMs(nextStart),
    firstWord:firstIndex,
    lastWord:lastIndex,
    source:'aligned'
  };
}

function envelope(buffer,start,end,frameSeconds=.006){
  const sampleRate=Number(buffer?.sampleRate)||0;
  const channels=Math.max(1,Number(buffer?.numberOfChannels)||1);
  if(!sampleRate||typeof buffer?.getChannelData!=='function'||!(end>start))return [];
  const frameSize=Math.max(16,Math.round(sampleRate*frameSeconds));
  const first=Math.max(0,Math.floor(start*sampleRate));
  const last=Math.min(Number(buffer.length)||Math.floor((Number(buffer.duration)||end)*sampleRate),Math.ceil(end*sampleRate));
  const channelData=[];
  for(let channel=0;channel<channels;channel++){
    try{channelData.push(buffer.getChannelData(channel));}catch{break;}
  }
  if(!channelData.length)return [];
  const frames=[];
  for(let offset=first;offset<last;offset+=frameSize){
    const stop=Math.min(last,offset+frameSize);
    let sum=0,count=0;
    for(const data of channelData){
      for(let i=offset;i<stop;i++){const sample=Number(data[i])||0;sum+=sample*sample;count++;}
    }
    if(!count)continue;
    frames.push({start:offset/sampleRate,end:stop/sampleRate,rms:Math.sqrt(sum/count)});
  }
  return frames;
}

function quietThreshold(reference,side){
  const speech=Math.max(percentile(reference.map(x=>x.rms),.7),.0005);
  const floor=percentile(side.map(x=>x.rms),.2);
  return Math.max(.0007,Math.min(speech*.22,Math.max(speech*.10,floor*1.8)));
}

function lastQuietRun(frames,threshold,runLength=2){
  let run=0;
  for(let i=frames.length-1;i>=0;i--){
    if(frames[i].rms<=threshold){run++;if(run>=runLength)return frames[i+runLength-1]?.end??frames[i].end;}
    else run=0;
  }
  return null;
}
function firstQuietRun(frames,threshold,runLength=2){
  let run=0;
  for(let i=0;i<frames.length;i++){
    if(frames[i].rms<=threshold){run++;if(run>=runLength)return frames[i-runLength+1]?.start??frames[i].start;}
    else run=0;
  }
  return null;
}

export function refinePhraseWindowWithWaveform(buffer,clip){
  if(!clip||clip.source!=='aligned')return clip||null;
  const duration=finite(buffer?.duration)??finite(clip.endCeiling)??finite(clip.end);
  const rawStart=finite(clip.rawStart),rawEnd=finite(clip.rawEnd);
  if(rawStart===null||rawEnd===null||!(rawEnd>rawStart)||!duration)return clip;
  const startFloor=clamp(finite(clip.startFloor)??Math.max(0,rawStart-.16),0,duration);
  const endCeiling=clamp(finite(clip.endCeiling)??Math.min(duration,rawEnd+.16),0,duration);
  if(!(endCeiling>startFloor))return clip;

  const startReference=envelope(buffer,rawStart,Math.min(rawEnd,rawStart+.12));
  const startSide=envelope(buffer,startFloor,rawStart);
  let refinedStart=finite(clip.start)??Math.max(startFloor,rawStart-.09);
  if(startReference.length&&startSide.length){
    const threshold=quietThreshold(startReference,startSide);
    const quietEnd=lastQuietRun(startSide,threshold,2);
    if(quietEnd!==null)refinedStart=quietEnd-.022;
    else refinedStart=rawStart-.085;
  }
  refinedStart=clamp(refinedStart,startFloor,Math.max(startFloor,rawStart-.018));

  const endReference=envelope(buffer,Math.max(rawStart,rawEnd-.12),rawEnd);
  const endSide=envelope(buffer,rawEnd,endCeiling);
  let refinedEnd=finite(clip.end)??Math.min(endCeiling,rawEnd+.035);
  if(endReference.length&&endSide.length){
    const threshold=quietThreshold(endReference,endSide);
    const quietStart=firstQuietRun(endSide,threshold,2);
    if(quietStart!==null)refinedEnd=quietStart+.018;
    else refinedEnd=rawEnd+.035;
  }
  refinedEnd=clamp(refinedEnd,Math.min(endCeiling,rawEnd+.012),endCeiling);
  if(refinedEnd<=refinedStart+.04)return clip;
  return {...clip,start:roundMs(refinedStart),end:roundMs(refinedEnd),source:'aligned-waveform'};
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
