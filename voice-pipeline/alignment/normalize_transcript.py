"""Normalize known source transcript for CTC while retaining exact source offsets."""
from __future__ import annotations

import re

_ONES=['ZERO','ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','TEN','ELEVEN','TWELVE','THIRTEEN','FOURTEEN','FIFTEEN','SIXTEEN','SEVENTEEN','EIGHTEEN','NINETEEN']
_TENS={20:'TWENTY',30:'THIRTY',40:'FORTY',50:'FIFTY',60:'SIXTY',70:'SEVENTY',80:'EIGHTY',90:'NINETY'}
TOKEN_RE=re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+(?:['’][A-Za-z]+)*)*|\d+(?:\.\d+)?")


def _under_100(n:int)->str:
    if n<20:return _ONES[n]
    return _TENS[(n//10)*10]+('' if n%10==0 else _ONES[n%10])


def _number_normalized(surface:str)->str:
    if '.' in surface:
        left,right=surface.split('.',1)
        return _number_normalized(left)+'POINT'+''.join(_ONES[int(d)] for d in right)
    n=int(surface)
    if 0<=n<100:
        return _under_100(n)
    if 1000<=n<=2099:
        first=n//100;last=n%100
        if first in (19,20):
            return _under_100(first)+('HUNDRED' if last==0 else _under_100(last))
    return ''.join(_ONES[int(d)] for d in surface)


def normalize_transcript(text:str)->list[dict]:
    words=[]
    for m in TOKEN_RE.finditer(text):
        source=m.group(0)
        if source[0].isdigit():
            normalized=_number_normalized(source)
        else:
            normalized=re.sub(r"[^A-Za-z]",'',source).upper()
        if not normalized:
            continue
        words.append({'source':source,'char_start':m.start(),'char_end':m.end(),'normalized':normalized})
    return words


def ctc_text(words:list[dict])->str:
    return '|'.join(w['normalized'] for w in words)
