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

## Course submission

Submit **one .docx** per `HOMEWORK3.md` (writing in your own words, not AI-generated). Use screenshots from your run, links to this new repo, and the documentation table described in the homework.
