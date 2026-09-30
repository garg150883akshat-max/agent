import json
from signalpost_agent.models import Evidence, Fact
from signalpost_agent.utils import normalize_orgnr, norm_company, token_overlap

def test_orgnr_normalization():
    assert normalize_orgnr('979 543 883') == '979543883'

def test_company_normalization():
    assert norm_company('DIPS AS') == 'dips'
    assert token_overlap('DIPS AS','DIPS ASA') == 1.0

def test_fact_serialization():
    f=Fact('industry','Software',[Evidence('https://example.com','test','2026-09-29T00:00:00Z')],0.9)
    d=f.to_dict(); assert d['key']=='industry' and d['evidence'][0]['source_url'].startswith('https://')
