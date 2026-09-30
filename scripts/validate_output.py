from __future__ import annotations
import json,sys
VALID={"available","not_available","blocked","not_applicable","ambiguous","failed"}
p=sys.argv[1] if len(sys.argv)>1 else "output.jsonl"
seen=set(); n=0; bad=[]
for line in open(p,encoding="utf-8"):
    if not line.strip(): continue
    n+=1; x=json.loads(line); o=str(x.get("company_number",""))
    if len(o)!=9 or not o.isdigit(): bad.append((n,"bad company number"))
    if x.get("status") not in VALID: bad.append((n,"bad status"))
    if o in seen: bad.append((n,"duplicate company"))
    seen.add(o)
    if "facts" not in x or "summary" not in x or "missing" not in x: bad.append((n,"incomplete envelope"))
print(json.dumps({"rows":n,"unique_company_numbers":len(seen),"problems":bad[:20],"complete":not bad},indent=2))
sys.exit(1 if bad else 0)
