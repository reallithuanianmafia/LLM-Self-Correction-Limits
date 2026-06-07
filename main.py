#!/usr/bin/env python3
"""
main.py - CLI entry point for the Compliance Bias study.

Usage examples
──────────────
# Run a mock experiment (no API key needed):
  python main.py run --provider mock --model "Mock Model" --bias 0.75

# Run against GPT-4o (needs OPENAI_API_KEY):
  python main.py run --provider openai --model "ChatGPT GPT-4o"

# Run against Claude (needs ANTHROPIC_API_KEY):
  python main.py run --provider anthropic --model "Claude 3.5 Sonnet"

# Run against Gemini (needs GOOGLE_API_KEY):
  python main.py run --provider google --model "Gemini 1.5 Pro"

# Analyse saved results:
  python main.py analyse results/Mock_Model_*.json

# Compare multiple models:
  python main.py compare results/*.json

# Run demo with four mock "models":
  python main.py demo
"""

import argparse
import glob
import json
import sys
from pathlib import Path

from src.experiment import ExperimentRunner, ExperimentConfig
from src.analysis import (
    load_results,
    compare_models,
    full_report,
    to_markdown_table,
    to_csv,
    cohens_kappa,
)


def cmd_run(args):
    config = ExperimentConfig(
        model_name=args.model,
        provider=args.provider,
        api_key=args.api_key,
        llm_model_id=args.model_id,
        repeat_per_question=args.repeat,
        delay_between_calls_s=args.delay,
        output_dir=args.output_dir,
        mock_bias_rate=args.bias,
        seed=args.seed,
    )
    runner = ExperimentRunner(config)
    runner.run()


def cmd_analyse(args):
    for path in args.files:
        results = load_results(path)
        print(full_report(results))
        print()


def cmd_compare(args):
    stats = compare_models(args.files)
    if not stats:
        print("No results found.")
        return
    print("\n" + to_markdown_table(stats))
    if args.csv:
        to_csv(stats, args.csv)


def cmd_demo(args):
    """
    Run four mock experiments simulating the paper's four models and
    then print a comparison.
    """
    configs = [
        ("ChatGPT (GPT-4o)",      0.78),
        ("Gemini 1.5 Pro",        0.71),
        ("Claude 3.5 Sonnet",     0.41),
        ("Grok-1.5",              0.82),
    ]

    result_files = []
    for model_name, bias_rate in configs:
        print(f"\n{'▓'*55}")
        print(f"  Running demo: {model_name}  (bias={bias_rate})")
        print(f"{'▓'*55}")
        config = ExperimentConfig(
            model_name=model_name,
            provider="mock",
            mock_bias_rate=bias_rate,
            output_dir="results",
            delay_between_calls_s=0.0,
            seed=42,
        )
        runner = ExperimentRunner(config)
        results = runner.run()

        # Find the saved file
        import os, glob as g
        files = sorted(g.glob(f"results/{model_name.replace(' ', '_').replace('(', '').replace(')', '')}*.json"))
        if files:
            result_files.append(files[-1])

    print("\n\n" + "═"*60)
    print("  CROSS-MODEL COMPARISON")
    print("═"*60)
    stats = compare_models(result_files)
    print(to_markdown_table(stats))

    # Also save a combined CSV
    to_csv(stats, "results/comparison_summary.csv")
    print("\n  See results/ for all JSON files and comparison_summary.csv")


def main():
    parser = argparse.ArgumentParser(
        description="Compliance Bias Experiment - LLM Sycophancy Study",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ────────────────────────────────────────────────
    run_p = sub.add_parser("run", help="Run an experiment against a single model")
    run_p.add_argument("--provider", required=True,
                       choices=["openai", "anthropic", "google", "mock"])
    run_p.add_argument("--model", required=True, help="Display name for the model")
    run_p.add_argument("--model-id", default=None,
                       help="API model id (e.g. gpt-4o). Defaults to provider default.")
    run_p.add_argument("--api-key", default=None,
                       help="API key (falls back to env var)")
    run_p.add_argument("--repeat", type=int, default=1,
                       help="Repetitions per question")
    run_p.add_argument("--delay", type=float, default=1.0,
                       help="Seconds between API calls")
    run_p.add_argument("--output-dir", default="results")
    run_p.add_argument("--bias", type=float, default=0.60,
                       help="Mock bias rate (only for --provider mock)")
    run_p.add_argument("--seed", type=int, default=42)
    run_p.set_defaults(func=cmd_run)

    # ── analyse ────────────────────────────────────────────
    ana_p = sub.add_parser("analyse", help="Print a report for one or more result files")
    ana_p.add_argument("files", nargs="+")
    ana_p.set_defaults(func=cmd_analyse)

    # ── compare ────────────────────────────────────────────
    cmp_p = sub.add_parser("compare", help="Compare multiple models side-by-side")
    cmp_p.add_argument("files", nargs="+")
    cmp_p.add_argument("--csv", default=None, help="Export comparison to CSV")
    cmp_p.set_defaults(func=cmd_compare)

    # ── demo ───────────────────────────────────────────────
    demo_p = sub.add_parser("demo", help="Run the full 4-model demo (mock, no API keys)")
    demo_p.set_defaults(func=cmd_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
