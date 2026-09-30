from pathlib import Path
from signalpost_agent.models import Evidence, Fact
from signalpost_agent.state import StateStore

def test_change_detection_is_value_based(tmp_path):
    s=StateStore(str(tmp_path))
    old={'company_number':'123456789','facts':[{'key':'employees','value':10}]}
    s.path('123456789').write_text(__import__('json').dumps(old))
    f=Fact('employees',10,[Evidence('https://example.com','test','2026-09-29T00:00:00Z')])
    assert s.changes('123456789',[f])==[]
    f2=Fact('employees',11,[Evidence('https://example.com','test','2026-09-29T00:00:00Z')])
    changes=s.changes('123456789',[f2])
    assert len(changes)==1 and changes[0].old_value==10 and changes[0].new_value==11
