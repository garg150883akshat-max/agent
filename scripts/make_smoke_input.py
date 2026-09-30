from __future__ import annotations
import argparse,csv,json,urllib.request,gzip,io,sys
p=argparse.ArgumentParser(); p.add_argument('--output',default='smoke_input.jsonl'); p.add_argument('--limit',type=int,default=1000); a=p.parse_args()
url='https://builderr.ai/signalpost-company-universe-2025.jsonl.gz'
try:
    raw=urllib.request.urlopen(url,timeout=20).read()
except Exception as e:
    print(f'Cannot download the public universe from this environment: {e}',file=sys.stderr); sys.exit(2)
text=gzip.decompress(raw).decode('utf-8')
out=[]
for line in text.splitlines():
    if len(out)>=a.limit: break
    x=json.loads(line)
    for k in ('company_number','organisation_number','organisasjonsnummer','orgnr'):
        if k in x: out.append({"company_number":str(x[k])}); break
with open(a.output,'w',encoding='utf-8') as f:
    for x in out: f.write(json.dumps(x)+'\n')
print(f'Wrote {len(out)} company numbers to {a.output}')
