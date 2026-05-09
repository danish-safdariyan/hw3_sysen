# hw3_report_validation_experiment.py
# Homework 3: AI Report Validation + Prompt Comparison Experiment
# Pairs with HOMEWORK3.md
# Tim Fraser
#
# Standalone copy: project root = directory containing this file.
#
# This script is a practical scaffold for Homework 3:
# - Generate the same underlying facts into an AI-written "report" using 3 different prompts
# - Validate each generated report with a customized rubric (not the LAB's Likert set)
# - Repeat many times (stochastic generation) and export a CSV for analysis
# - Print basic statistical tests (Bartlett + one-way ANOVA + an example t-test)
#
# Important course requirement:
# - Your ~500 word write-up in the .docx must be written in your own words (NOT AI-generated).

# 0. Setup #################################

## 0.1 Load Packages ############################

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from scipy.stats import bartlett, f_oneway, ttest_ind

# 1. CONFIG ###################################

## 1.1 Paths ###################################

# Standalone project root = folder that contains this script
PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(PROJECT_ROOT / ".env")

OUT_DIR = PROJECT_ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

## 1.2 AI provider settings #####################

AI_PROVIDER = os.getenv("HW3_AI_PROVIDER", "ollama").strip().lower()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip() or "llama3.2:latest"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

OLLAMA_OPTIONS_TEMPERATURE = float(os.getenv("HW3_OLLAMA_TEMPERATURE", "0.8"))
OPENAI_TEMPERATURE = float(os.getenv("HW3_OPENAI_TEMPERATURE", "0.8"))

## 1.3 Experiment settings #####################

N_REPLICATES = int(os.getenv("HW3_N_REPLICATES", "30"))
SLEEP_SECONDS = float(os.getenv("HW3_SLEEP_SECONDS", "0.25"))
SAVE_FULL_REPORTS = os.getenv("HW3_SAVE_FULL_REPORTS", "true").strip().lower() in {"1", "true", "yes", "y"}

SOURCE_FACTS = """
Dataset: White County, IL | Year: 2015 | Pollutant: PM10 | Metric: vehicle miles traveled (VMT) by vehicle class
Key table (approximate):
- Light Truck: 2.7M VMT (51.8%)
- Car/Bike: 1.9M VMT (36.1%)
- Combo Truck: 381.3k VMT (7.3%)
- Heavy Truck: 220.7k VMT (4.2%)
- Bus: 30.6k VMT (0.6%)

Hard constraints for grading:
- Percentages should sum to ~100% (within 1 percentage point)
- Light Truck is the largest share; Bus is the smallest share
- Do not invent other pollutants, years, or counties
""".strip()

PROMPTS = {
    "A": (
        "Write a short analyst memo (120-180 words) summarizing the transportation VMT breakdown.\n"
        "Audience: city policy staff.\n"
        "Tone: neutral and factual.\n"
        "Use 2 short paragraphs.\n"
        "Do not use bullet points.\n"
    ),
    "B": (
        "Write a structured briefing note (120-180 words) about the VMT breakdown.\n"
        "Use this exact section headers in this exact order:\n"
        "SUMMARY\n"
        "KEY NUMBERS\n"
        "IMPLICATIONS\n"
        "Each section should be 1-3 sentences.\n"
    ),
    "C": (
        "Write a skeptical audit-style note (120-180 words) about the VMT breakdown.\n"
        "Explicitly call out any claims that are not directly supported by the table.\n"
        "If everything is supported, say so plainly.\n"
        "Use a cautious tone.\n"
    ),
}


def _line_buffer_stdout() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, OSError, ValueError):
        pass


def _ollama_model_names() -> list[str]:
    url = f"{OLLAMA_HOST}/api/tags"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [m["name"] for m in data.get("models", []) if "name" in m]


def ensure_local_ollama_ready() -> None:
    if AI_PROVIDER != "ollama":
        return
    try:
        names = set(_ollama_model_names())
    except requests.RequestException as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_HOST} ({e}). "
            "Start Ollama or set OLLAMA_HOST in .env."
        ) from e
    if OLLAMA_MODEL not in names:
        avail = ", ".join(sorted(names)) if names else "(none — run `ollama pull <model>`)"
        raise RuntimeError(
            f"Model {OLLAMA_MODEL!r} is not installed locally. Installed: {avail}. "
            f"Set OLLAMA_MODEL in .env to one of these names, or run: ollama pull {OLLAMA_MODEL}"
        )


def _ollama_chat(messages: list[dict], format_json: bool) -> str:
    url = f"{OLLAMA_HOST}/api/chat"
    body = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": OLLAMA_OPTIONS_TEMPERATURE},
    }
    if format_json:
        body["format"] = "json"

    resp = requests.post(url, json=body, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"]


def _openai_chat(messages: list[dict], json_mode: bool) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY missing. Put it in your .env or export it in your shell.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": OPENAI_TEMPERATURE,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    resp = requests.post(url, headers=headers, json=body, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def ai_chat(messages: list[dict], *, format_json: bool) -> str:
    if AI_PROVIDER == "ollama":
        return _ollama_chat(messages, format_json=format_json)
    if AI_PROVIDER == "openai":
        return _openai_chat(messages, json_mode=format_json)
    raise ValueError("AI_PROVIDER must be 'ollama' or 'openai'.")


def extract_json_object(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def build_generation_messages(prompt_id: str) -> list[dict]:
    style = PROMPTS[prompt_id]
    user = (
        "You are generating a report for an internal government analytics workflow.\n"
        "Ground truth facts (must not contradict):\n"
        f"{SOURCE_FACTS}\n\n"
        "Generation instructions:\n"
        f"{style}\n"
    )
    return [{"role": "user", "content": user}]


def build_validation_prompt(report_text: str) -> str:
    return f"""
You are an independent validation reviewer evaluating an AI-generated report.

Ground truth facts (use as the benchmark for factual alignment):
{SOURCE_FACTS}

Report to evaluate:
---
{report_text}
---

Task:
Score the report using the rubric below. Be strict about factual alignment to the ground truth.

Rubric (each score is an integer 0-3):
- factual_alignment: 0=contains clear factual errors or inventions; 1=mostly aligned but some issues; 2=minor imprecision; 3=fully aligned
- structure_quality: 0=disorganized; 1=weak structure; 2=mostly clear; 3=excellent structure for the genre
- decision_usefulness: 0=not actionable; 1=limited utility; 2=useful; 3=high utility for policy staff
- hallucination_risk: 0=high risk (unsupported specifics); 1=moderate; 2=low; 3=minimal/unambiguous
- clarity: 0=confusing; 1=hard to read; 2=clear; 3=very clear
- brevity: 0=too long/fluff; 1=somewhat wordy; 2=reasonable; 3=appropriately concise

Also compute:
- overall_score_0_100: a single summary score from 0 to 100 using this fixed rule:
  overall_score_0_100 = round(100 * (factual_alignment*0.35 + structure_quality*0.15 + decision_usefulness*0.20
                              + (3 - hallucination_risk)*0.20 + clarity*0.05 + brevity*0.05) / 3)
  Note: hallucination_risk is "risk", so lower risk should increase the score via (3 - hallucination_risk).

Return ONLY valid JSON with this schema:
{{
  "factual_alignment": <int 0-3>,
  "structure_quality": <int 0-3>,
  "decision_usefulness": <int 0-3>,
  "hallucination_risk": <int 0-3>,
  "clarity": <int 0-3>,
  "brevity": <int 0-3>,
  "overall_score_0_100": <int 0-100>,
  "reviewer_notes": "<=40 words>"
}}
""".strip()


def validate_report(report_text: str) -> dict:
    prompt = build_validation_prompt(report_text)
    messages = [
        {"role": "system", "content": "You are a meticulous evaluator. Always return valid JSON only."},
        {"role": "user", "content": prompt},
    ]
    raw = ai_chat(messages, format_json=True)
    return extract_json_object(raw)


def generate_report(prompt_id: str) -> str:
    raw = ai_chat(build_generation_messages(prompt_id), format_json=False)
    return raw.strip()


@dataclass
class RunConfig:
    n_replicates: int
    save_full_reports: bool


def run_experiment(cfg: RunConfig) -> pd.DataFrame:
    rows: list[dict] = []
    for prompt_id in ["A", "B", "C"]:
        for rep in range(1, cfg.n_replicates + 1):
            print(
                f"🧪 prompt={prompt_id} replicate={rep}/{cfg.n_replicates} | generating...",
                flush=True,
            )
            report = generate_report(prompt_id)
            print(f"✅ prompt={prompt_id} replicate={rep} | validating...", flush=True)
            scores = validate_report(report)
            if cfg.save_full_reports:
                report_path = OUT_DIR / f"report_prompt{prompt_id}_rep{rep:03d}.txt"
                report_path.write_text(report, encoding="utf-8")
            rows.append(
                {
                    "prompt_id": prompt_id,
                    "replicate": rep,
                    "overall_score_0_100": int(scores["overall_score_0_100"]),
                    "factual_alignment": int(scores["factual_alignment"]),
                    "structure_quality": int(scores["structure_quality"]),
                    "decision_usefulness": int(scores["decision_usefulness"]),
                    "hallucination_risk": int(scores["hallucination_risk"]),
                    "clarity": int(scores["clarity"]),
                    "brevity": int(scores["brevity"]),
                    "reviewer_notes": str(scores.get("reviewer_notes", "")),
                }
            )
            time.sleep(SLEEP_SECONDS)
    return pd.DataFrame(rows)


def summarize_and_test(df: pd.DataFrame) -> None:
    print("\n====================================================")
    print("Descriptive summary (overall_score_0_100)")
    print("====================================================")
    print(df.groupby("prompt_id")["overall_score_0_100"].agg(["count", "mean", "std"]).round(2))
    a = np.asarray(df.query('prompt_id == "A"')["overall_score_0_100"], dtype=np.float64)
    b = np.asarray(df.query('prompt_id == "B"')["overall_score_0_100"], dtype=np.float64)
    c = np.asarray(df.query('prompt_id == "C"')["overall_score_0_100"], dtype=np.float64)
    equal_var = True
    try:
        b_stat, b_p = bartlett(a, b, c)
        print("\nBartlett test (homogeneity of variances)")
        print(f"  statistic={b_stat:.4f}, p-value={b_p:.4g}")
        equal_var = bool(b_p >= 0.05)
    except (ValueError, RuntimeError) as exc:
        print("\nBartlett test (homogeneity of variances)")
        print(f"  skipped ({type(exc).__name__}: {exc})")
        print("  using Welch t-test (unequal variances) for A vs B")
        equal_var = False
    print("\nOne-way ANOVA (overall_score_0_100 across A/B/C)")
    f_stat, p_anova = f_oneway(a, b, c)
    print(f"  F={f_stat:.4f}, p-value={p_anova:.4g}")
    print("\nExample pairwise t-test: A vs B (two-sided)")
    tt = ttest_ind(a, b, equal_var=equal_var, nan_policy="omit")
    print(f"  statistic={tt.statistic:.4f}, p-value={tt.pvalue:.4g}")


def main() -> None:
    _line_buffer_stdout()
    parser = argparse.ArgumentParser(description="Run Homework 3 validation + prompt comparison experiment.")
    parser.add_argument("--n-replicates", type=int, default=N_REPLICATES, help="Replicates per prompt (A/B/C).")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Short run for local dev: 3 replicates per prompt (~18 LLM calls). Use ~30 per prompt for the course write-up.",
    )
    parser.add_argument(
        "--save-full-reports",
        action=argparse.BooleanOptionalAction,
        default=SAVE_FULL_REPORTS,
        help="Write each generated report under outputs/ as a .txt file.",
    )
    args = parser.parse_args()
    if args.quick:
        args.n_replicates = 3
    ensure_local_ollama_ready()
    total_calls = args.n_replicates * 3 * 2
    print("HW3 experiment")
    print(f"  project_root={PROJECT_ROOT}")
    print(f"  provider={AI_PROVIDER}")
    if AI_PROVIDER == "ollama":
        print(f"  ollama_model={OLLAMA_MODEL!r} @ {OLLAMA_HOST}")
    print(f"  out_dir={OUT_DIR}")
    print(f"  n_replicates={args.n_replicates}")
    print(f"  save_full_reports={args.save_full_reports}")
    print(f"  approx_llm_calls={total_calls} (generate + validate per replicate)")
    df = run_experiment(RunConfig(n_replicates=args.n_replicates, save_full_reports=args.save_full_reports))
    csv_path = OUT_DIR / "hw3_validation_scores.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n💾 Wrote: {csv_path}")
    summarize_and_test(df)
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
