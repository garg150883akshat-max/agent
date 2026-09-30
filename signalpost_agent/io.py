from __future__ import annotations
import csv, json
from pathlib import Path

def load_company_numbers(path: str) -> list[str]:
    p=Path(path); out=[]
    if p.suffix.lower() in {".jsonl",".ndjson"}:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            x=json.loads(line)
            out.append(_extract(x))
    elif p.suffix.lower()==".csv":
        with p.open(encoding="utf-8-sig",newline="") as f:
            for row in csv.DictReader(f): out.append(_extract(row))
    elif p.suffix.lower()==".json":
        x=json.loads(p.read_text(encoding="utf-8"))
        if isinstance(x,list): out.extend(_extract(y) for y in x)
        elif isinstance(x,dict):
            for k in ["company_number","organisation_number","organisasjonsnummer","orgnr","org_no"]:
                if k in x: out.append(x[k]); break
    else:
        out.extend(x.strip() for x in p.read_text().splitlines() if x.strip())
    return [str(x) for x in out if x not in (None,"")]

def _extract(x):
    if isinstance(x,(str,int)): return x
    for k in ["company_number","organisation_number","organisasjonsnummer","orgnr","org_no"]:
        if k in x: return x[k]
    raise ValueError(f"No company number in input record: {x}")
