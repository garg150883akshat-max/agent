from __future__ import annotations
import argparse, json, os
from signalpost_agent.core import SignalpostAgent
from signalpost_agent.io import load_company_numbers

def main(argv=None):
    ap=argparse.ArgumentParser(description="Signalpost Norwegian company research agent")
    ap.add_argument("--input",default=os.getenv("SIGNALPOST_INPUT","input.jsonl"))
    ap.add_argument("--output",default=os.getenv("SIGNALPOST_OUTPUT","output.jsonl"))
    ap.add_argument("--workers",type=int,default=int(os.getenv("SIGNALPOST_WORKERS","12")))
    ap.add_argument("--request-limit",type=int,default=int(os.getenv("SIGNALPOST_REQUEST_LIMIT","2000")))
    ap.add_argument("--state-dir",default=os.getenv("SIGNALPOST_STATE_DIR","data/state"))
    ap.add_argument("--cache-dir",default=os.getenv("SIGNALPOST_CACHE_DIR","data/cache"))
    ap.add_argument("--no-web",action="store_true",help="official-registry-only mode for offline smoke tests")
    args=ap.parse_args(argv)
    nums=load_company_numbers(args.input)
    agent=SignalpostAgent(workers=args.workers,request_limit=args.request_limit,state_dir=args.state_dir,cache_dir=args.cache_dir,full_web=not args.no_web)
    results=agent.run_batch(nums)
    with open(args.output,"w",encoding="utf-8") as f:
        for r in results: f.write(json.dumps(r.to_dict(),ensure_ascii=False,separators=(",",":"))+"\n")
    print(f"Wrote {len(results)} complete company results to {args.output}; requests used: {agent.http.budget.used}/{agent.http.budget.limit}")

if __name__=="__main__": main()
