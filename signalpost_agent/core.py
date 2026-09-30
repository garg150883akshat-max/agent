from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from signalpost_agent.http import Budget, HttpClient
from signalpost_agent.models import CompanyResult, Fact
from signalpost_agent.sources.brreg import BrregSource
from signalpost_agent.sources.nav import NavJobsSource
from signalpost_agent.sources.website import WebsiteSource
from signalpost_agent.state import StateStore
from signalpost_agent.synth import summarize
from signalpost_agent.utils import normalize_orgnr, now_iso

class SignalpostAgent:
    def __init__(self, *, workers=12, request_limit=2000, state_dir="data/state", cache_dir="data/cache", full_web=True):
        budget=Budget(request_limit)
        self.http=HttpClient(cache_dir, budget)
        self.brreg=BrregSource(self.http); self.nav=NavJobsSource(self.http); self.website=WebsiteSource(self.http)
        self.state=StateStore(state_dir); self.workers=workers; self.full_web=full_web

    def research(self, orgnr: str) -> CompanyResult:
        started=now_iso(); orgnr=normalize_orgnr(orgnr); errors=[]; facts=[]
        entity, fs, err=self.brreg.entity(orgnr); facts.extend(fs); errors.extend(err)
        if not entity:
            return CompanyResult(orgnr,"not_available",{},[],[],"No verified entity was retrieved from Brønnøysundregistrene.",["company_record"],errors,started)

        legal=entity.get("navn") or ""
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs=[ex.submit(self.brreg.roles,orgnr), ex.submit(self.brreg.subunits,orgnr), ex.submit(self.brreg.latest_financial,orgnr)]
            if self.full_web and entity.get("hjemmeside"):
                futs.append(ex.submit(self.website.crawl,entity.get("hjemmeside"),legal,orgnr))
            if self.full_web:
                futs.append(ex.submit(self.nav.search,legal,orgnr))
            for fut in futs:
                try:
                    a,b=fut.result(); facts.extend(a); errors.extend(b)
                except Exception as e: errors.append(str(e))

        # Deduplicate at fact level, but preserve multi-source evidence for matching identical values.
        merged={}
        for f in facts:
            k=(f.key,repr(f.value))
            if k not in merged: merged[k]=f
            else: merged[k].evidence.extend(f.evidence)
        facts=list(merged.values())
        changes=self.state.changes(orgnr,facts)
        website=_value(facts,"website")
        profile={
          "legal_name":legal,
          "organisation_number":orgnr,
          "organisation_form":_value(facts,"organisation_form"),
          "city":((_value(facts,"business_address") or {}).get("city") if isinstance(_value(facts,"business_address"),dict) else None),
          "industry":_value(facts,"industry"),
          "website":website,
          "employees":_value(facts,"number_of_employees"),
          "workplace_count":len([f for f in facts if f.key=="registered_workplace"]),
          "job_count":len([f for f in facts if f.key=="job"]),
        }
        missing=[]
        for k,label in [("industry","industry"),("website","company website"),("reported_revenue","latest revenue"),("role","people/roles"),("registered_workplace","locations/workplaces"),("job","hiring"),("public_activity","public activity")]:
            if not any(f.key==k for f in facts): missing.append(label)
        status="available"
        if not facts: status="not_available"
        elif any(e.lower().startswith("brreg") and "error" in e.lower() for e in errors) and len(facts)<3: status="failed"
        summary=summarize(facts)
        result=CompanyResult(orgnr,status,profile,facts,changes,summary,missing,errors,started)
        self.state.save(orgnr,result.to_dict())
        return result

    def run_batch(self, orgnrs):
        uniq=[]; seen=set()
        for x in orgnrs:
            try: o=normalize_orgnr(x)
            except Exception: continue
            if o not in seen: seen.add(o); uniq.append(o)
        results=[None]*len(uniq)
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs={ex.submit(self.research,o):i for i,o in enumerate(uniq)}
            for fut in as_completed(futs):
                i=futs[fut]
                try: results[i]=fut.result()
                except Exception as e:
                    o=uniq[i]; results[i]=CompanyResult(o,"failed",{},[],[],"The company research run failed before a complete profile could be built.",[],[str(e)],now_iso())
        return results

def _value(facts,key):
    for f in facts:
        if f.key==key: return f.value
    return None
