import base64,gzip,glob,sys
ALPH='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
def decode(s):
 try:
  packed=base64.b64decode(s,validate=True); gzip.decompress(packed); return packed
 except Exception:return None
def repair_chunks(chunks):
 out=decode(''.join(chunks))
 if out is not None:return out
 short=[i for i,c in enumerate(chunks[:-1]) if len(c)%4!=0]
 if len(short)!=1: raise ValueError(f'expected one malformed chunk, got {short}')
 i=short[0]; c=chunks[i]
 for pos in range(len(c)+1):
  for ch in ALPH:
   trial=chunks.copy(); trial[i]=c[:pos]+ch+c[pos:]
   out=decode(''.join(trial))
   if out is not None:
    print(f'repaired chunk {i:03d}: inserted one base64 character at offset {pos}',file=sys.stderr)
    return out
 raise ValueError('unable to repair bundle')
def main():
 pattern,outpath=sys.argv[1:3]
 paths=sorted(glob.glob(pattern))
 if not paths: raise SystemExit('no chunks found')
 chunks=[open(p,encoding='ascii').read().strip() for p in paths]
 open(outpath,'wb').write(repair_chunks(chunks))
if __name__=='__main__': main()
