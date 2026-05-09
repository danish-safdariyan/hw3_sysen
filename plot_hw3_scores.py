#!/usr/bin/env python3
"""Boxplot of overall_score_0_100 by prompt_id (Homework 3 screenshot helper)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = PROJECT_ROOT / "outputs" / "hw3_validation_scores.csv"
DEFAULT_PNG = PROJECT_ROOT / "outputs" / "hw3_scores_by_prompt.png"


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot validation scores by prompt (boxplot).")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to hw3_validation_scores.csv")
    parser.add_argument("--out", type=Path, default=DEFAULT_PNG, help="Output PNG path")
    args = parser.parse_args()

    if not args.csv.is_file() or args.csv.stat().st_size == 0:
        print(
            f"Missing or empty CSV: {args.csv}\n"
            "Run the experiment first:\n"
            "  python3 hw3_report_validation_experiment.py\n"
            "Or point --csv at a copy (e.g. examples/sample_hw3_validation_scores.csv).",
            file=sys.stderr,
        )
        sys.exit(1)

    df = pd.read_csv(args.csv)
    if "prompt_id" not in df.columns or "overall_score_0_100" not in df.columns:
        print("CSV must include columns prompt_id and overall_score_0_100.", file=sys.stderr)
        sys.exit(1)

    order = sorted(df["prompt_id"].astype(str).unique())
    series = [df.loc[df["prompt_id"].astype(str) == p, "overall_score_0_100"].dropna().values for p in order]

    fig, ax = plt.subplots(figsize=(6, 4), layout="constrained")
    ax.boxplot(series, tick_labels=order, showmeans=True, meanline=True)
    ax.set_xlabel("Generation prompt")
    ax.set_ylabel("Overall score (0 to 100)")
    ax.set_title("HW3: validator overall score by prompt")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    plt.close(fig)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
