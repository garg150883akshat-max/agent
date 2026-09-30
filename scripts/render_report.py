from __future__ import annotations
import html,json,sys
p=sys.argv[1] if len(sys.argv)>1 else "output.jsonl"
out=sys.argv[2] if len(sys.argv)>2 else "report.html"
rows=[json.loads(x) for x in open(p,encoding="utf-8") if x.strip()]
parts=["<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'><title>SignalPost Research Report</title>","<style>body{font-family:Inter,system-ui,sans-serif;max-width:1200px;margin:auto;padding:24px;background:#0b1020;color:#e8eefc} .card{background:#121a2d;border:1px solid #26324f;border-radius:16px;padding:20px;margin:16px 0} .muted{color:#9aaccc} a{color:#8dc8ff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.pill{display:inline-block;padding:4px 8px;border-radius:999px;background:#1d2a44}.fact{padding:10px 0;border-top:1px solid #22304b}.mono{font-family:ui-monospace,monospace} @media(max-width:600px){body{padding:12px}}</style>",f"<h1>SignalPost · {len(rows)} companies</h1>"]
for r in rows:
    prof=r.get("profile",{}); parts.append("<div class='card'>")
    parts.append(f"<h2>{html.escape(prof.get('legal_name') or r.get('company_number',''))}</h2><div class='muted mono'>{html.escape(r.get('company_number',''))} · {html.escape(r.get('status',''))}</div>")
    parts.append(f"<p>{html.escape(r.get('summary',''))}</p><div class='grid'><div>Industry<br><b>{html.escape(str(prof.get('industry') or 'Not available'))}</b></div><div>Employees<br><b>{html.escape(str(prof.get('employees') if prof.get('employees') is not None else 'Not available'))}</b></div><div>Workplaces<br><b>{html.escape(str(prof.get('workplace_count',0)))}</b></div><div>Jobs found<br><b>{html.escape(str(prof.get('job_count',0)))}</b></div></div>")
    for f in r.get('facts',[]):
        val=f.get('value'); ev=(f.get('evidence') or [])[0] if f.get('evidence') else {}
        v=html.escape(json.dumps(val,ensure_ascii=False) if isinstance(val,(dict,list)) else str(val))
        src=ev.get('source_url',''); link=f"<a href='{html.escape(src,quote=True)}' target='_blank' rel='noreferrer'>source</a>" if src else ""
        parts.append(f"<div class='fact'><span class='pill'>{html.escape(f.get('key',''))}</span> {v} · {link}</div>")
    parts.append("</div>")
open(out,'w',encoding='utf-8').write(''.join(parts))
print(out)
