#!/usr/bin/env bash
set -euo pipefail
python -m signalpost_agent.cli --input "${1:-input.jsonl}" --output "${2:-output.jsonl}"
