from __future__ import annotations
import json, os
from pathlib import Path
from signalpost_agent.models import Change, Evidence, Fact
from signalpost_agent.utils import now_iso

class StateStore:
    def __init__(self, root="data/state"):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
    def path(self,orgnr): return self.root/f"{orgnr}.json"
    def load(self,orgnr):
        p=self.path(orgnr)
        try: return json.loads(p.read_text()) if p.exists() else None
        except Exception: return None
    def save(self,orgnr,result):
        tmp=self.path(orgnr).with_suffix(".tmp")
        tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
        tmp.replace(self.path(orgnr))
    def changes(self,orgnr,facts: list[Fact]) -> list[Change]:
        old=self.load(orgnr) or {}
        oldmap={f.get("key"):f.get("value") for f in old.get("facts",[]) or []}
        newmap={f.key:f.value for f in facts}
        out=[]
        for key,new in newmap.items():
            if key not in oldmap: continue
            if oldmap[key] != new:
                evidence=next((f.evidence for f in facts if f.key==key),[])
                out.append(Change(key,oldmap[key],new,evidence,now_iso()))
        return out
