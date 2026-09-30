from __future__ import annotations
import re
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup
from signalpost_agent.models import Evidence, Fact
from signalpost_agent.utils import now_iso, norm_company, token_overlap

BASE="https://arbeidsplassen.nav.no/stillinger"

class NavJobsSource:
    def __init__(self,http): self.http=http

    def search(self, legal_name: str, orgnr: str | None = None, max_jobs: int=20) -> tuple[list[Fact], list[str]]:
        url=f"{BASE}?q={quote_plus(legal_name)}"
        try:
            r=self.http.get(url, headers={"Accept":"text/html,application/xhtml+xml"})
            if r.status_code in {401,403,429}: return [], [f"NAV blocked: {r.status_code}"]
            r.raise_for_status(); soup=BeautifulSoup(r.content,"lxml")
            facts=[]
            # The search page itself is evidence. We only retain cards whose visible employer text matches the registry name.
            name=norm_company(legal_name)
            anchors=soup.select('a[href*="/stillinger/"]')
            seen=set()
            for a in anchors:
                href=a.get("href"); title=" ".join(a.stripped_strings)
                if not href or not title or title in seen: continue
                if title.lower() in {"ledige stillinger","jobber","for bedrifter"}: continue
                parent=a.find_parent(["article","li","div"])
                block=" ".join(parent.stripped_strings) if parent else " ".join(a.parent.stripped_strings if a.parent else [])
                score=token_overlap(name, block)
                if name and (name in norm_company(block) or score>=0.55):
                    full=href if href.startswith("http") else "https://arbeidsplassen.nav.no"+href
                    ev=Evidence(url,"nav_jobs_search",now_iso(),match_score=score)
                    facts.append(Fact("job", {"title":title[:400],"url":full,"employer_match_score":round(score,3)}, [ev], min(0.98,0.75+score/4)))
                    seen.add(title)
                    if len(facts)>=max_jobs: break
            return self._dedup(facts), []
        except Exception as e: return [], [f"NAV jobs error: {e}"]
    @staticmethod
    def _dedup(fs):
        out=[]; seen=set()
        for f in fs:
            k=(f.key,str(f.value.get("url")))
            if k not in seen: seen.add(k); out.append(f)
        return out
