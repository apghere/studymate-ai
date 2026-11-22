#!/usr/bin/env bash
# One command: real experiments + tests + PDFs + form answers.
#   export GEMINI_API_KEY="..."   (never commit it)
#   bash run_all.sh
set -e
cd "$(dirname "$0")"
if [ -z "$GEMINI_API_KEY" ]; then echo "Set GEMINI_API_KEY first:  export GEMINI_API_KEY=\"...\""; exit 1; fi
python3 -m pip install -q -r requirements-dev.txt
python3 code/run_experiments.py
python3 code/make_report.py
echo
echo "Done. Open docs/form_answers.md and the PDFs in docs/."
