"""Pure-Python Viterbi CTC trellis/backtrack for known target tokens."""
from __future__ import annotations

NEG=-1.0e30


def align_tokens(emissions:list[list[float]], tokens:list[int], blank_id:int=0)->list[dict]:
    if not tokens:
        return []
    if not emissions:
        raise ValueError('alignment failed: empty emissions')
    ext=[blank_id]
    for tok in tokens:
        ext.extend([tok,blank_id])
    T,S=len(emissions),len(ext)
    prev=[NEG]*S
    prev[0]=float(emissions[0][blank_id])
    if S>1:
        prev[1]=float(emissions[0][ext[1]])
    backs=[[-1]*S for _ in range(T)]
    backs[0][0]=0
    if S>1: backs[0][1]=0

    for t in range(1,T):
        cur=[NEG]*S
        for s,label in enumerate(ext):
            best=prev[s];src=s
            if s>=1 and prev[s-1]>best:
                best=prev[s-1];src=s-1
            if s>=2 and label!=blank_id and label!=ext[s-2] and prev[s-2]>best:
                best=prev[s-2];src=s-2
            if best<=NEG/2:
                continue
            cur[s]=best+float(emissions[t][label])
            backs[t][s]=src
        prev=cur
    finals=[S-1]
    if S>=2: finals.append(S-2)
    state=max(finals,key=lambda s:prev[s])
    if prev[state]<=NEG/2:
        raise ValueError('alignment failed: target cannot be placed in emissions')

    states=[state]
    for t in range(T-1,0,-1):
        state=backs[t][state]
        if state<0:
            raise ValueError('alignment failed: broken backtrack')
        states.append(state)
    states.reverse()

    chosen=[]
    for i,tok in enumerate(tokens):
        target_state=2*i+1
        frames=[t for t,s in enumerate(states) if s==target_state]
        if not frames:
            raise ValueError('alignment failed: missing token frame')
        frame=max(frames,key=lambda t:float(emissions[t][tok]))
        chosen.append({'token_id':tok,'frame':frame,'score':float(emissions[frame][tok])})
    if any(a['frame']>=b['frame'] for a,b in zip(chosen,chosen[1:])):
        raise ValueError('alignment failed: nonmonotonic token path')
    return chosen
