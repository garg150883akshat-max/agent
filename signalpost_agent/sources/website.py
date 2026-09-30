from __future__ import annotations
import json, re
import xml.etree.ElementTree as ET
from collections import deque
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup
from signalpost_agent.models import Evidence, Fact
from signalpost_agent.utils import now_iso, clean_url, same_host, norm_company, token_overlap, sha256_bytes

SOCIAL = {"linkedin.com":"linkedin", "facebook.com":"facebook", "instagram.com":"instagram", "youtube.com":"youtube"}
CAREER_WORDS={"career","careers","jobb","jobber","job","vacancies","ledige-stillinger","rekruttering","join-us","working-with-us"}
NEWS_WORDS={"news","aktuelt","nyheter","press","blogg","blog","media","innsikt","article","artikler"}

class WebsiteSource:
    def __init__(self,http): self.http=http

    def crawl(self, website: str, legal_name: str, orgnr: str, max_pages: int = 6) -> tuple[list[Fact], list[str]]:
        if not website: return [], []
        if not website.startswith("http"): website="https://"+website
        root=website.rstrip("/")
        q=deque([root]); seen=set(); pages=[]; errors=[]
        # Discover XML sitemap separately; many corporate sites expose news URLs there even when the homepage does not link them.
        try:
            sm=self.http.get(root + "/sitemap.xml", headers={"Accept":"application/xml,text/xml"})
            if sm.status_code==200 and "xml" in sm.headers.get("content-type",""):
                root_xml=ET.fromstring(sm.content)
                for loc in root_xml.iter():
                    if loc.tag.lower().endswith("loc") and loc.text:
                        v=clean_url(root,loc.text.strip())
                        if v and same_host(root,v) and any(w in urlparse(v).path.lower() for w in NEWS_WORDS|CAREER_WORDS):
                            q.append(v)
        except Exception:
            pass
        while q and len(pages)<max_pages:
            u=q.popleft()
            if u in seen: continue
            seen.add(u)
            try:
                r=self.http.get(u, headers={"Accept":"text/html,application/xhtml+xml"})
                if r.status_code in {401,403,429}: errors.append(f"website blocked: {u}"); continue
                if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): continue
                html=r.content; soup=BeautifulSoup(html,"lxml")
                text=" ".join(soup.stripped_strings)
                pages.append((u, soup, text, html))
                for a in soup.find_all("a", href=True):
                    v=clean_url(u,a.get("href"))
                    if not v or not same_host(root,v) or v in seen: continue
                    path=urlparse(v).path.lower()
                    if any(w in path for w in CAREER_WORDS|NEWS_WORDS) or v==root:
                        q.append(v)
                for link in soup.find_all("link", href=True):
                    v=clean_url(u,link.get("href"))
                    if v and same_host(root,v) and "sitemap" in (link.get("rel") or []) and v not in seen: q.append(v)
            except Exception as e:
                errors.append(f"website fetch {u}: {e}")

        facts=[]
        # Site identity is trusted because the URL is the current website returned by the official registry.
        for u,soup,text,html in pages:
            content_hash=sha256_bytes(html)
            ev=Evidence(u,"company_website",now_iso(),content_hash=content_hash)
            title=(soup.title.string.strip() if soup.title and soup.title.string else None)
            desc=None
            meta=soup.find("meta",attrs={"name":"description"}) or soup.find("meta",attrs={"property":"og:description"})
            if meta: desc=meta.get("content")
            if desc and len(desc)>80:
                facts.append(Fact("website_description", desc[:1000], [ev], 0.96))
            if title and any(x in norm_company(title) for x in norm_company(legal_name).split()[:2]):
                facts.append(Fact("website_title", title[:300], [ev], 0.97))
            # Registered organisation number or legal name on site = useful exact-identity corroboration.
            if orgnr in re.sub(r"\D", "", text):
                facts.append(Fact("website_identity_orgnr_confirmed", True, [ev], 1.0))
            # Social profiles linked by the registry-linked website.
            for a in soup.find_all("a", href=True):
                href=a.get("href",""); host=(urlparse(href).hostname or "").lower()
                for domain,kind in SOCIAL.items():
                    if host.endswith(domain):
                        facts.append(Fact("social_profile", {"platform":kind,"url":href}, [Evidence(href,"linked_social_profile",now_iso())], 0.98))
                        break
            # Date-bearing public activity on the same company website.
            date_value=None
            for tag in soup.find_all("time"):
                date_value=tag.get("datetime") or " ".join(tag.stripped_strings)
                if date_value: break
            if not date_value:
                m=soup.find("meta",attrs={"property":"article:published_time"}) or soup.find("meta",attrs={"name":"date"})
                if m: date_value=m.get("content")
            if not date_value:
                m=re.search(r"\b(20[2-9][0-9]-[01][0-9]-[0-3][0-9])\b", text)
                date_value=m.group(1) if m else None
            is_news=any(w in (urlparse(u).path.lower()+" "+(title or "").lower()) for w in NEWS_WORDS)
            if date_value and is_news:
                facts.append(Fact("public_activity", {"title":title or u,"url":u,"date":str(date_value)[:40],"snippet":text[:500]}, [ev], 0.9))
        # Select one concise description, avoiding navigation-heavy pages.
        descs=[f for f in facts if f.key=="website_description"]
        if descs:
            desc=max(descs,key=lambda f: len(str(f.value)))
            # Keep only if it overlaps the company/industry enough to be plausible, otherwise still keep as sourced website description.
        return self._dedup(facts), errors

    @staticmethod
    def _dedup(facts):
        out=[]; seen=set()
        for f in facts:
            key=(f.key, json.dumps(f.value,sort_keys=True,ensure_ascii=False))
            if key in seen: continue
            seen.add(key); out.append(f)
        return out
