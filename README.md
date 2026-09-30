# SignalPost — Norway Company Evidence Agent

A deterministic, source-first research agent designed for the Builderr Signalpost challenge.

## Why this architecture

The challenge rewards finding more verified facts, exact-company matching, current updates, evidence, synthesis and usability. The agent therefore uses **official Norwegian registry data as the identity anchor** and treats every external discovery as a corroborated fact, never as an unverified guess.

### Source order

1. **Brønnøysundregistrene Enhetsregisteret** — legal identity, organisation form, dates, industry, employees, addresses, website.
2. **Brønnøysundregistrene roles** — registered leadership/roles.
3. **Brønnøysundregistrene sub-entities** — workplaces/locations.
4. **Brønnøysundregistrene Regnskapsregisteret** — latest annual filing PDF; values are extracted only when a source-text match exists.
5. **Registry-linked company website** — description, site identity corroboration, linked public social profiles and dated company-site activity.
6. **NAV arbeidsplassen.no search** — employer-matched open jobs.

No fabricated values, zero-filling, or unsupported company matches are used.

## Reliability features

- Nine-digit organisation number is the primary key everywhere.
- Registry-provided website is the only website accepted as company-site evidence.
- NAV jobs are retained only when the employer text matches the normalized legal company name.
- Every fact carries source URL and retrieval time; financial facts also carry reporting year.
- Prior snapshots are stored locally. Re-running the same snapshot is idempotent; a changed value becomes a `changes[]` record rather than overwriting history invisibly.
- Each input company always produces exactly one terminal result state: `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous`, or `failed`.
- HTTP responses are cached; concurrent workers make better use of the published request/time budgets.
- `--request-limit` prevents accidental budget overruns.

## One-command run

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m signalpost_agent.cli --input input.jsonl --output output.jsonl
```

The challenge explicitly requires a reproducible install plus one run command; keep the pinned commit unchanged for the submitted version.

## Smoke test

Use a small file first:

```bash
python -m signalpost_agent.cli --input input.jsonl --output output.jsonl
python scripts/validate_output.py output.jsonl
python scripts/render_report.py output.jsonl report.html
```

For the organiser's public 1,000+ company universe, use:

```bash
python scripts/make_smoke_input.py --limit 1000 --output smoke_input.jsonl
python -m signalpost_agent.cli --input smoke_input.jsonl --output smoke_output.jsonl --request-limit 1900
python scripts/validate_output.py smoke_output.jsonl
```

If the public universe cannot be downloaded in your environment, use the exact company batch supplied by Builderr instead.

## Output contract

Each JSONL line is one company result:

```json
{
  "company_number": "979543883",
  "status": "available",
  "profile": {"legal_name":"DIPS AS", "organisation_number":"979543883"},
  "facts": [{
    "key":"reported_revenue",
    "value":790400865,
    "confidence":0.98,
    "evidence":[{
      "source_url":"https://data.brreg.no/regnskapsregisteret/...",
      "source_type":"brreg_annual_accounts",
      "retrieved_at":"2026-09-29T00:00:00Z",
      "reporting_period":"2025"
    }]
  }],
  "changes": [],
  "summary": "...",
  "missing": ["public activity"],
  "errors": [],
  "retrieved_at":"2026-09-29T00:00:00Z"
}
```

**Submission note:** the public challenge page describes the result envelope at a high level but the organiser's downloadable starter kit contains the authoritative exact field contract. Before the final commit, map `CompanyResult.to_dict()` to that starter-kit envelope exactly; do not submit a guessed schema.

## Scoring strategy

### Find useful information / recall
The agent spreads collection across the five data areas visible in Builderr's public sample: company record, financials, people & locations, company website, and hiring/public activity. It also keeps individual job, workplace, role and social-profile facts instead of collapsing them into one blob.

### Match correctly with evidence
The organisation number is the hard identity key. The company website is accepted only when it came from the registry's `hjemmeside` field. Roles/workplaces/financials are only published from the company-number-specific official endpoints. NAV results are filtered against the registry legal name and retained with the search URL as evidence.

### Update correctly
The state layer records previous values and source hashes. Changes are emitted only after a fresh retrieval. Duplicate records from identical values are merged, and the same source snapshot does not create a false change.

### Useful explanations
The summary is generated from retrieved facts only. It explains what the company does/classification, latest filing, leadership, hiring and recent activity, and `missing[]` makes gaps explicit.

### Easy to use
JSONL is machine-friendly; `render_report.py` produces a responsive HTML audit report where every fact has a clickable evidence source.

## Current official facts to keep in mind

Builderr says all official runs use the same fresh company batch, require one result per company, and run under a fixed time/request/cost budget. The current public challenge page states 2,000 outbound requests, 45 minutes and $10 in declared external API cost, with a 65/100 qualification floor. Treat the challenge page as the source of truth because details can change before submission.

## Licence / provenance

Code in this repository is MIT-licensed. Data are fetched at run time from public sources; this repo does not contain a precomputed company database or private credentials.
