# Homework 3 — AI Report Validation (standalone)

This folder is a **self-contained copy** of materials for **Homework 3: AI Report Validation System**. You can move or copy this entire directory into a **new git repository**; it does not depend on the parent `dsai` repo layout.

## Contents

| File | Purpose |
|------|---------|
| [`HOMEWORK3.md`](HOMEWORK3.md) | Assignment text (copied from course repo; image/footer adjusted for standalone use). |
| [`hw3_report_validation_experiment.py`](hw3_report_validation_experiment.py) | Generate reports (prompts A/B/C), validate with a custom rubric, export CSV, print ANOVA/t-test output. |
| [`requirements.txt`](requirements.txt) | Python dependencies. |
| [`/.env.example`](.env.example) | Example environment variables. |

Generated files (after you run the experiment) go under **`outputs/`** (gitignored by default).

## Quick start

```bash
cd hw3_ai_report_validation
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set Ollama or OpenAI as needed.

python3 hw3_report_validation_experiment.py
```

Outputs:

- `outputs/hw3_validation_scores.csv`
- `outputs/report_promptA_rep001.txt` (and similar), if full reports are saved

## Local Ollama

1. Install and start [Ollama](https://ollama.com/).
2. Set `HW3_AI_PROVIDER=ollama` in `.env` and set `OLLAMA_MODEL` to a name from `ollama list`. Pull if needed, e.g. `ollama pull qwen2.5:7b-instruct`.
3. **Fast sanity check** (about 18 LLM calls):  
   `python3 hw3_report_validation_experiment.py --quick`
4. **Heavier run for the assignment** (about 180 calls with default `HW3_N_REPLICATES=30`):  
   `python3 hw3_report_validation_experiment.py`  
   Or a middle ground: `--n-replicates 10`.

The script verifies your Ollama model is installed before the long loop (avoids a confusing HTTP 404).

## Course submission

Submit **one .docx** per `HOMEWORK3.md` (writing in your own words, not "AI-generated"). Use screenshots from your run, links to your git repo, and the documentation table described in the homework.
