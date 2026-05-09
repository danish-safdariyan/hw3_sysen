# Homework 3 — AI Report Validation (standalone)

Course project: **AI Report Validation System** (see [`HOMEWORK3.md`](HOMEWORK3.md)). This repo is self-contained.

**Public repo:** https://github.com/danish-safdariyan/hw3_sysen

## Contents

| File / folder | Purpose |
|---------------|--------|
| [`HOMEWORK3.md`](HOMEWORK3.md) | Full assignment text. |
| [`hw3_report_validation_experiment.py`](hw3_report_validation_experiment.py) | Generate memos (prompts A/B/C), validate with a custom rubric, export CSV, print Bartlett / ANOVA / example *t* test. |
| [`plot_hw3_scores.py`](plot_hw3_scores.py) | Boxplot of `overall_score_0_100` by `prompt_id` from the CSV (Homework screenshot helper). |
| [`examples/sample_hw3_validation_scores.csv`](examples/sample_hw3_validation_scores.csv) | Tiny example scores table for testing the plot script or doc links. |
| [`requirements.txt`](requirements.txt) | Python dependencies. |
| [`.env.example`](.env.example) | Copy to `.env` and edit (never commit `.env`). |

Generated runs go under **`outputs/`** (gitignored: CSV, report `.txt` files, PNG plots).

## Quick start

```bash
cd hw3_ai_report_validation
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`: set `HW3_AI_PROVIDER` (`ollama` or `openai`), `OLLAMA_MODEL` to a name from `ollama list`, or set `OPENAI_API_KEY` for cloud.

Run the experiment:

```bash
python3 hw3_report_validation_experiment.py --quick
python3 hw3_report_validation_experiment.py --n-replicates 10
python3 hw3_report_validation_experiment.py
```

Run each line **on its own**. On some zsh setups, text after `#` on the same line is not treated as a comment; that can break argparse if you paste comments from a guide.

After a successful run:

```bash
python3 plot_hw3_scores.py
```

writes `outputs/hw3_scores_by_prompt.png`. Use `--csv` / `--out` to override paths.

## Local Ollama

1. Install and start [Ollama](https://ollama.com/).
2. `ollama pull <model>` so `OLLAMA_MODEL` in `.env` matches `ollama list`.
3. The experiment script checks the model exists **before** the long loop (avoids HTTP 404 from a missing tag).

Default run with `HW3_N_REPLICATES=30` is about **180** LLM calls (generate + validate for each memo).

## Outputs

| Path | Description |
|------|-------------|
| `outputs/hw3_validation_scores.csv` | One row per generated memo (scores + `reviewer_notes`). |
| `outputs/report_promptX_repNNN.txt` | Saved memos when `HW3_SAVE_FULL_REPORTS=true` (default). |
| `outputs/hw3_scores_by_prompt.png` | Boxplot from `plot_hw3_scores.py`. |

The experiment writes the CSV via a temporary file, then replaces the final path, to avoid a broken half-written file.

## Course submission

Submit **one .docx** as described in `HOMEWORK3.md`: writing, git links, screenshots (including stats and a comparison figure), and documentation. Keep `outputs/` local or attach samples; that folder is not meant to be committed with secrets or huge logs.
