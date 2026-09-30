from __future__ import annotations
import io, re
from typing import Any
from urllib.parse import urljoin
from pypdf import PdfReader
from signalpost_agent.models import Evidence, Fact
from signalpost_agent.utils import now_iso, normalize_orgnr, norm_company, sha256_bytes

BASE = "https://data.brreg.no/enhetsregisteret/api"
REG_BASE = "https://data.brreg.no/regnskapsregisteret/regnskap"

class BrregSource:
    def __init__(self, http): self.http = http

    def entity(self, orgnr: str) -> tuple[dict[str, Any] | None, list[Fact], list[str]]:
        orgnr = normalize_orgnr(orgnr)
        url = f"{BASE}/enheter/{orgnr}?spraak=NOB"
        try:
            data, r = self.http.json(url, headers={"Accept": "application/json"})
            if r.status_code == 404: return None, [], ["Brreg entity not found"]
            r.raise_for_status()
            ev = Evidence(url, "brreg_entity", now_iso())
            facts=[]
            facts.append(Fact("company_record", {"organisation_number": orgnr, "legal_name": data.get("navn")}, [ev], 1.0))
            def add(k, v, note=None):
                if v not in (None, "", [], {}): facts.append(Fact(k, v, [ev], 1.0, note))
            add("legal_name", data.get("navn"))
            add("organisation_form", (data.get("organisasjonsform") or {}).get("beskrivelse") or (data.get("organisasjonsform") or {}).get("kode"))
            add("organisation_form_code", (data.get("organisasjonsform") or {}).get("kode"))
            add("registered_company_status", (data.get("enhetStatus") or {}).get("beskrivelse") or data.get("enhetStatus"))
            add("registration_date", data.get("registreringsdatoEnhetsregisteret"))
            add("founded_date", data.get("stiftelsesdato"))
            add("number_of_employees", data.get("antallAnsatte"))
            nk = data.get("naeringskode1") or {}
            add("industry_code", nk.get("kode")); add("industry", nk.get("beskrivelse"))
            add("website", data.get("hjemmeside"))
            add("vat_registered", data.get("registrertIMvaregisteret"))
            add("registered_in_foretaksregisteret", data.get("registrertIForetaksregisteret"))
            addr = data.get("forretningsadresse") or {}
            if addr:
                add("business_address", {k:v for k,v in {
                    "address": addr.get("adresse"), "postal_code": addr.get("postnummer"), "city": addr.get("poststed"), "country": addr.get("land") or addr.get("landkode")
                }.items() if v})
            post = data.get("postadresse") or {}
            if post:
                add("postal_address", {k:v for k,v in {
                    "address": post.get("adresse"), "postal_code": post.get("postnummer"), "city": post.get("poststed"), "country": post.get("land") or post.get("landkode")
                }.items() if v})
            return data, facts, []
        except Exception as e:
            return None, [], [f"Brreg entity error: {e}"]

    def roles(self, orgnr: str) -> tuple[list[Fact], list[str]]:
        url = f"{BASE}/enheter/{normalize_orgnr(orgnr)}/roller"
        try:
            data, r = self.http.json(url, headers={"Accept": "application/json"})
            if r.status_code == 404: return [], []
            r.raise_for_status(); ev=Evidence(url, "brreg_roles", now_iso()); facts=[]
            for group in data.get("rollegrupper", []) or []:
                for role in group.get("roller", []) or []:
                    rt = role.get("type") or {}
                    code, desc = rt.get("kode"), rt.get("beskrivelse")
                    person = role.get("person") or {}
                    navn = person.get("navn")
                    if not navn:
                        navn_obj = role.get("person") or {}
                        navn = " ".join(x for x in [navn_obj.get("fornavn"), navn_obj.get("mellomnavn"), navn_obj.get("etternavn")] if x)
                    if navn and not role.get("avregistrert"):
                        facts.append(Fact("role", {"code":code,"title":desc,"person":navn}, [ev], 1.0))
            return facts, []
        except Exception as e: return [], [f"Brreg roles error: {e}"]

    def subunits(self, orgnr: str) -> tuple[list[Fact], list[str]]:
        url = f"{BASE}/underenheter?overordnetEnhet={normalize_orgnr(orgnr)}&size=1000"
        try:
            data, r = self.http.json(url, headers={"Accept": "application/json"})
            r.raise_for_status(); ev=Evidence(url, "brreg_subunits", now_iso()); facts=[]
            items = (data.get("_embedded") or {}).get("underenheter") or []
            for x in items:
                facts.append(Fact("registered_workplace", {k:v for k,v in {
                    "name":x.get("navn"), "organisation_number":x.get("organisasjonsnummer"),
                    "address":x.get("beliggenhetsadresse") or x.get("forretningsadresse"),
                    "employees":x.get("antallAnsatte"), "industry":(x.get("naeringskode1") or {}).get("beskrivelse")
                }.items() if v not in (None, "", {})}, [ev], 1.0))
            return facts, []
        except Exception as e: return [], [f"Brreg subunits error: {e}"]

    def latest_financial(self, orgnr: str) -> tuple[list[Fact], list[str]]:
        orgnr=normalize_orgnr(orgnr)
        years_url=f"{REG_BASE}/aarsregnskap/kopi/{orgnr}/aar"
        try:
            data, r = self.http.json(years_url, headers={"Accept":"application/json"})
            r.raise_for_status()
            years=[]
            if isinstance(data, list): years=[int(y) for y in data if str(y).isdigit()]
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list): years += [int(y) for y in v if str(y).isdigit()]
                    elif isinstance(v, str) and v.isdigit(): years.append(int(v))
            if not years: return [], []
            year=max(years)
            pdf_url=f"{REG_BASE}/aarsregnskap/kopi/{orgnr}/{year}"
            resp=self.http.get(pdf_url, headers={"Accept":"application/pdf"}, binary=True)
            if resp.status_code != 200: return [], [f"financial PDF status {resp.status_code}"]
            text="\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(resp.content)).pages)
            ev=Evidence(pdf_url,"brreg_annual_accounts",now_iso(),reporting_period=str(year),content_hash=sha256_bytes(resp.content))
            facts=[]
            patterns={
              "reported_revenue":[r"Driftsinntekter\s+([0-9][0-9 .]*)", r"Sum driftsinntekter\s+([0-9][0-9 .]*)"],
              "operating_result":[r"Driftsresultat\s+(-?[0-9][0-9 .]*)"],
              "annual_result":[r"Årsresultat\s+(-?[0-9][0-9 .]*)",r"Årsoverskudd\s+(-?[0-9][0-9 .]*)"],
              "total_assets":[r"SUM EIENDELER\s+([0-9][0-9 .]*)"],
              "total_debt":[r"Sum gjeld\s+([0-9][0-9 .]*)"],
            }
            for key, regs in patterns.items():
                val=None
                for pat in regs:
                    m=re.search(pat,text,re.I)
                    if m:
                        raw=m.group(1).strip().replace(" ","").replace(".","").replace(",","")
                        neg=raw.startswith("(") and raw.endswith(")")
                        raw=raw.strip("()")
                        try: val=(-1 if neg else 1)*int(raw); break
                        except ValueError: pass
                if val is not None: facts.append(Fact(key,val,[ev],0.98))
            period=re.search(r"Årsregnskapets periode:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*-\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",text)
            if period: facts.append(Fact("reporting_period", {"from":period.group(1),"to":period.group(2)}, [ev],1.0))
            return facts, []
        except Exception as e: return [], [f"Brreg financial error: {e}"]
