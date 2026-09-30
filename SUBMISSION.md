# SignalPost submission checklist

## Before submitting

- [ ] Register on Unstop and start the actual Builderr entry.
- [ ] Download the organiser's current Signalpost starter kit / full brief.
- [ ] Confirm the exact input file name and the exact terminal-result envelope.
- [ ] If the organiser's starter envelope differs from `CompanyResult.to_dict()`, make that adapter-only change in `signalpost_agent/cli.py` or `signalpost_agent/models.py` and rerun all tests.
- [ ] Run a 100-company smoke test and verify one complete result for every input.
- [ ] Run at least 1,000 companies locally using the organiser's public universe or equivalent official test input.
- [ ] Run from a clean virtual environment using the pinned `requirements.txt`.
- [ ] Keep `output.jsonl` and generated smoke-test data out of Git.
- [ ] Verify no API keys or private credentials are committed.
- [ ] Record models/APIs/licences and declared external cost in the submission email.
- [ ] Submit the repository URL, this exact commit hash, and the single run command.

## Recommended final command

```bash
python -m signalpost_agent.cli --input INPUT_FILE --output output.jsonl
```

For Builderr's official test, use the input file and output path required by their current harness. The challenge page is the source of truth for those details.
