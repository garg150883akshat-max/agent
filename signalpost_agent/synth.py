from __future__ import annotations
from signalpost_agent.models import Fact

def _one(facts,key):
    for f in facts:
        if f.key==key: return f.value
    return None

def summarize(facts):
    name=_one(facts,"legal_name") or "The company"
    city=(_one(facts,"business_address") or {}).get("city") if isinstance(_one(facts,"business_address"),dict) else None
    industry=_one(facts,"industry")
    emp=_one(facts,"number_of_employees")
    rev=_one(facts,"reported_revenue")
    op=_one(facts,"operating_result")
    roles=[f.value for f in facts if f.key=="role" and isinstance(f.value,dict)]
    jobs=[f.value for f in facts if f.key=="job" and isinstance(f.value,dict)]
    activities=[f.value for f in facts if f.key=="public_activity" and isinstance(f.value,dict)]
    parts=[]
    p=f"{name}"
    if city: p+=f" is registered in {city}"
    if industry: p+=f" and is classified under {industry}"
    if emp is not None: p+=f"; the register shows {emp} employees"
    parts.append(p+".")
    if rev is not None or op is not None:
        fin=[]
        if rev is not None: fin.append(f"revenue {rev:,} NOK")
        if op is not None: fin.append(f"operating result {op:,} NOK")
        parts.append("The latest retrieved annual filing reports " + " and ".join(fin) + ".")
    if roles:
        lead=[r for r in roles if str(r.get("title","")).lower() in {"daglig leder","chief executive officer","styrets leder","chair of the board"}]
        if lead: parts.append("Registry-listed leadership includes " + ", ".join(f"{x['person']} ({x['title']})" for x in lead[:3]) + ".")
    if jobs: parts.append(f"The current NAV search returned {len(jobs)} employer-matched job posting(s).")
    else: parts.append("No employer-matched NAV job postings were found in the latest query.")
    if activities:
        latest=sorted(activities,key=lambda x:x.get("date") or "", reverse=True)[0]
        parts.append(f"A recent company-site activity item is dated {latest.get('date')} and titled {latest.get('title') or 'an update'}.")
    return " ".join(parts)
